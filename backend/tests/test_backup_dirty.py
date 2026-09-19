"""Zamanlanmis yedegin "degisiklik yoksa atla" davranisi.

Kritik denge: kalp atisi / kaynak sagligi / cache bakimi yedegi TETIKLEMEMELI,
kullanici verisi TETIKLEMELI. Ikisi de sessizce bozulabilecegi icin kilitlenir.
"""

from __future__ import annotations

import os
import time
from datetime import datetime
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.events import log_event
from app.db import SessionLocal
from app.modules.system import backup, dirty

DAY_SECONDS = 24 * 60 * 60


@pytest.fixture
async def client():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


@pytest.fixture(autouse=True)
def isolated_backup_dir(tmp_path: Path, monkeypatch) -> Path:
    """Testler KULLANICININ gercek yedek dizinine YAZMAMALI."""
    target = tmp_path / "backups"
    target.mkdir()
    monkeypatch.setattr(backup, "BACKUP_DIR", target)
    return target


def _expire_backups(target: Path) -> None:
    """24 saat kapisini gecir ki icerik kapisi test edilebilsin."""
    stamp = time.time() - 3 * DAY_SECONDS
    for path in target.glob("lifeos-*.json.gz"):
        os.utime(path, (stamp, stamp))


async def _seed_unique_row(session, title: str) -> None:
    await session.execute(
        text(
            "insert into saved_view (id,name,module,filter,pinned,position) "
            "values (gen_random_uuid(), :name, 'todo', '{}', false, 0)"
        ),
        {"name": title},
    )


async def test_scheduled_backup_skips_when_nothing_changed(isolated_backup_dir: Path) -> None:
    async with SessionLocal() as session:
        first = await backup.create_backup(session)
    assert first.exists()

    _expire_backups(isolated_backup_dir)

    async with SessionLocal() as session:
        assert await backup.backup_if_stale(session) is None
        assert await dirty.has_changes_since_last_backup(session) is False


async def test_scheduled_backup_runs_after_a_user_change(isolated_backup_dir: Path) -> None:
    async with SessionLocal() as session:
        await backup.create_backup(session)
    _expire_backups(isolated_backup_dir)

    async with SessionLocal() as session:
        await log_event(session, verb="note.created", payload={})
        await session.commit()
        assert await dirty.has_changes_since_last_backup(session) is True
        second = await backup.backup_if_stale(session)

    assert second is not None and second.exists()


async def test_settings_change_triggers_a_backup(
    isolated_backup_dir: Path, client: AsyncClient
) -> None:
    """Ayar degisikligi event yazar; yoksa yedek sessizce atlanirdi."""
    async with SessionLocal() as session:
        await backup.create_backup(session)
    _expire_backups(isolated_backup_dir)

    response = await client.put("/api/settings/rss.retention_days", json={"value": 30})
    assert response.status_code == 200

    async with SessionLocal() as session:
        assert await dirty.has_changes_since_last_backup(session) is True
        assert await backup.backup_if_stale(session) is not None


async def test_operational_noise_does_not_trigger_a_backup(isolated_backup_dir: Path) -> None:
    """Kalp atisi, kaynak kosusu ve operasyonel eventler YEDEK TETIKLEMEZ."""
    async with SessionLocal() as session:
        await backup.create_backup(session)
    _expire_backups(isolated_backup_dir)

    async with SessionLocal() as session:
        # 1) Kaynak sagligi (yedek kapsami disinda)
        await session.execute(
            text(
                "insert into source_run (source, status, items_found, started_at) "
                "values ('osym', 'ok', 3, now())"
            )
        )
        # 2) Worker kalp atisi (yalnizca setting yazar, event yazmaz)
        await session.execute(
            text(
                "insert into setting (key, value) values "
                "('worker.heartbeat', jsonb_build_object('at', now()::text)) "
                "on conflict (key) do update set value = excluded.value"
            )
        )
        # 3) Operasyonel eventler: kaynak kuyrugu + saglik + cache bakimi
        for verb in (
            "source_sync.started",
            "source_sync.completed",
            "source.stalled",
            "rss.pruned",
            "system.maintenance",
        ):
            await log_event(session, verb=verb, payload={})
        await session.commit()

        assert await dirty.has_changes_since_last_backup(session) is False
        assert await backup.backup_if_stale(session) is None


async def test_manual_backup_always_runs(isolated_backup_dir: Path) -> None:
    """Elle 'Backup now' degisiklik kapisini KULLANMAZ."""
    async with SessionLocal() as session:
        await backup.create_backup(session)
    _expire_backups(isolated_backup_dir)

    async with SessionLocal() as session:
        assert await dirty.has_changes_since_last_backup(session) is False
        # Elle tetikleme create_backup'i dogrudan cagirir (router boyle yapar).
        again = await backup.create_backup(session)

    assert again.exists()


async def test_event_only_change_still_triggers_a_backup(isolated_backup_dir: Path) -> None:
    """Kullanici aksiyonu yalnizca event yazsa da yedek tetiklenir."""
    async with SessionLocal() as session:
        await backup.create_backup(session)
    _expire_backups(isolated_backup_dir)

    async with SessionLocal() as session:
        await log_event(session, verb="settings.reset", payload={})
        await session.commit()

        assert await dirty.has_changes_since_last_backup(session) is True
        assert await backup.backup_if_stale(session) is not None


async def test_backup_status_reports_change_state(isolated_backup_dir: Path) -> None:
    async with SessionLocal() as session:
        await backup.create_backup(session)
        fresh = await backup.backup_status(session)

        await log_event(session, verb="todo.created", payload={})
        await session.commit()
        changed = await backup.backup_status(session)

    assert fresh["changes_since_backup"] is False
    assert changed["changes_since_backup"] is True
    assert fresh["next_backup_scheduled"] == backup.SCHEDULED_AT
    # Kapsam disi tablolar yedege girmez.
    assert "source_run" not in fresh["includes"]
    assert "note" in fresh["includes"]


async def test_operational_verbs_are_real_verbs() -> None:
    """Operasyonel fiil listesi kayit defteriyle uyusmali (yazim hatasi olmasin)."""
    from app.core.registry import all_event_verbs

    registered = set(all_event_verbs())
    unknown = sorted(
        verb
        for verb in dirty.OPERATIONAL_EVENT_VERBS
        # `backup.*` fiilleri sabit uzerinden log'lanir; kayit defterinde
        # etiketleri yoktur (mevcut durum, bu fazin kapsami disinda).
        if not verb.startswith("backup.") and verb not in registered
    )
    assert not unknown, f"kayit defterinde olmayan operasyonel fiiller: {unknown}"


async def test_revision_is_a_dict_with_the_watermark() -> None:
    async with SessionLocal() as session:
        value = await dirty.revision(session)

    assert set(value) == {"event", "at"}
    assert isinstance(value["event"], int) and value["event"] >= 0
    datetime.fromisoformat(value["at"])


async def test_first_ever_backup_has_no_revision(isolated_backup_dir: Path) -> None:
    """Bilinmeyen durumda yedek ALINIR (sessiz atlama olmaz)."""
    async with SessionLocal() as session:
        assert await dirty.stored_revision(session) is None
        assert await dirty.has_changes_since_last_backup(session) is True
        assert await backup.backup_if_stale(session) is not None


def test_backup_revision_is_runtime_state() -> None:
    from app.modules.system.settings_schema import RUNTIME_SETTING_KEYS

    assert dirty.REVISION_KEY in RUNTIME_SETTING_KEYS
