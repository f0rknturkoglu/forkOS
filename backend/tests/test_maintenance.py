"""Gunluk hafif bakim: gun kapisi, adim bagimsizligi ve kapsam.

Bakim worker'dan bagimsiz calisir (gunluk kullanimda worker kapali), bu
yuzden kapi ve kurtarma davranisi guardrail'dir: yanlis kurulursa ya her
acilista agir is kosar ya da hic kosmaz ve veritabani sessizce buyur.
"""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text

from app.core.models import Event, SourceRun
from app.db import SessionLocal
from app.main import app
from app.modules.media import artwork
from app.modules.system import maintenance

DAY_SECONDS = 24 * 60 * 60


def _age(path: Path, days: float) -> None:
    stamp = time.time() - days * DAY_SECONDS
    os.utime(path, (stamp, stamp))


@pytest.fixture(autouse=True)
def isolated_artwork_dir(tmp_path: Path, monkeypatch) -> Path:
    """Bakim testleri KULLANICININ gercek gorsel onbellegine DOKUNMAMALI."""
    target = tmp_path / "media"
    target.mkdir()
    monkeypatch.setattr(artwork, "default_asset_dir", lambda: target)
    return target


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


async def test_maintenance_runs_at_most_once_per_day(monkeypatch: pytest.MonkeyPatch) -> None:
    """Gun kapisi: ayni gun ikinci cagri hicbir adim kosmadan None doner."""
    calls: list[datetime] = []

    async def probe(session, moment: datetime) -> dict[str, int]:
        calls.append(moment)
        return {"pruned": 1}

    monkeypatch.setattr(maintenance, "STEPS", (("probe", probe),))

    async with SessionLocal() as session:
        first = await maintenance.run_maintenance(session)
        calls_after_first = len(calls)
        second = await maintenance.run_maintenance(session)
        calls_after_second = len(calls)
        day = (await maintenance.last_run(session))["day"]
        forced = await maintenance.run_maintenance(session, force=True)
        stored = await maintenance.last_run(session)

    assert first is not None
    assert first["status"] == "completed"
    assert first["results"] == {"probe": {"pruned": 1}}
    assert calls_after_first == 1
    assert second is None
    assert calls_after_second == 1, "gun kapisi kapaliyken adim kosmamali"
    assert day == first["day"]
    # Elle tetikleme gun kapisini atlar.
    assert forced is not None
    assert len(calls) == 2
    assert stored is not None and stored["day"] == first["day"]


async def test_failing_step_does_not_stop_the_others(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bir adim patlarsa transaction kurtarilir ve kalan adimlar kosar."""

    async def boom(session, moment: datetime) -> dict[str, int]:
        # Gercek bir SQL hatasi: transaction'i iptal eder.
        await session.execute(text("select * from bakim_testi_olmayan_tablo"))
        return {"unreachable": 1}

    async def ok(session, moment: datetime) -> dict[str, int]:
        count = (await session.execute(select(func.count()).select_from(Event))).scalar_one()
        return {"events": count}

    monkeypatch.setattr(maintenance, "STEPS", (("boom", boom), ("ok", ok)))

    async with SessionLocal() as session:
        summary = await maintenance.run_maintenance(session)

    assert summary is not None
    assert summary["status"] == "completed_with_errors"
    assert summary["results"] == {"ok": {"events": 0}}
    assert len(summary["errors"]) == 1 and "boom" in summary["errors"][0]


async def test_maintenance_prunes_operational_rows_and_keeps_events() -> None:
    """Gercek adimlar bagli: kaynak kosulari budanir, `event` dokunulmaz."""
    now = datetime.now(UTC)
    async with SessionLocal() as session:
        session.add(
            Event(verb="note.created", payload={"keep": True}, occurred_at=now - timedelta(days=900))
        )
        # Kaynak basina son 20 kosu korunur: eski kosunun gitmesi icin
        # onunde 20 taze kosu olmali.
        session.add(SourceRun(source="feed", status="ok", started_at=now - timedelta(days=400)))
        for _ in range(20):
            session.add(SourceRun(source="feed", status="ok", started_at=now - timedelta(days=1)))
        await session.commit()

        summary = await maintenance.run_maintenance(session, now=now, force=True)

        runs = (await session.execute(select(func.count()).select_from(SourceRun))).scalar_one()
        kept = (
            await session.execute(
                select(func.count()).select_from(Event).where(Event.verb == "note.created")
            )
        ).scalar_one()
        audited = (
            await session.execute(
                select(func.count()).select_from(Event).where(Event.verb == "system.maintenance")
            )
        ).scalar_one()

    assert summary is not None and summary["status"] == "completed"
    assert summary["results"]["retention"]["source_run"] == 1
    assert runs == 20
    assert kept == 1, "event kisisel aktivite hafizasi: bakim dokunmamali"
    assert audited == 1, "bakim kendi kosumunu event olarak kaydetmeli"


async def test_maintenance_prunes_stale_artwork(
    client: AsyncClient, isolated_artwork_dir: Path
) -> None:
    """Gorsel budama bakima bagli: referanssiz + eski dosya silinir."""
    referenced = isolated_artwork_dir / "referenced.jpg"
    referenced.write_bytes(b"referenced")
    orphan = isolated_artwork_dir / "orphan.jpg"
    orphan.write_bytes(b"orphan-bytes")
    _age(referenced, 10)
    _age(orphan, 10)

    created = await client.post(
        "/api/media",
        json={
            "source": "manual",
            "title": "Kapaklı Kitap",
            "kind": "book",
            "cover_path": "/api/media/assets/referenced.jpg",
        },
    )
    assert created.status_code == 201, created.text

    async with SessionLocal() as session:
        summary = await maintenance.run_maintenance(session, force=True)

    assert summary is not None
    assert summary["results"]["artwork"] == {"files": 1, "freed_bytes": len(b"orphan-bytes")}
    assert referenced.exists(), "referansli gorsel silinmemeli"
    assert not orphan.exists()
