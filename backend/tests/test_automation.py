"""Arka plan otomasyonu, profiller ve acilis tazeleme kapilari.

Sozlesme:
  - `modules.disabled` ARAYUZ kararidir; arka plan trafigi ayri anahtarla
    yonetilir (`automation.<domain>.enabled`, varsayilan ACIK).
  - Otomasyon kapaliyken worker DIS KAYNAGA CIKMAZ.
  - Elle aksiyonlar (POST uclari, "tumunu tazele") otomasyondan bagimsizdir.
  - Hazir bir profil tek cagriyla tutarli bir ayar kumesi yazar.
  - Acilista taze kaynaklar tekrar cekilmez (worker restart = ag patlamasi
    DEGIL).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.core.entity import create_entity
from app.core.events import log_event
from app.core.models import SourceRun, SourceSyncBatch
from app.db import SessionLocal
from app.main import app
from app.modules.rss.models import Feed
from app.modules.system import automation
from app.modules.system.models import Setting
from app.worker import jobs


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


def _fail(*_args, **_kwargs):  # pragma: no cover - cagrilirsa test kirilir
    raise AssertionError("otomasyon kapaliyken dis kaynaga cikilmamali")


async def _seed_feed(session, *, minutes_ago: int) -> Feed:
    entity = await create_entity(
        session, type=Feed.ENTITY_TYPE, title="Feed", search_text="feed"
    )
    feed = Feed(
        id=entity.id,
        url=f"https://example.invalid/{uuid.uuid4().hex}",
        last_fetched_at=datetime.now(UTC) - timedelta(minutes=minutes_ago),
    )
    session.add(feed)
    await session.flush()
    return feed


async def test_automation_defaults_to_enabled() -> None:
    async with SessionLocal() as session:
        assert await automation.active_domains(session) == dict.fromkeys(automation.DOMAINS, True)
        # RSS'in ayri bir otomasyon anahtari YOK; araligi 0 ise yalniz manuel.
        assert "rss" not in automation.ENABLED_KEYS


async def test_github_interval_is_stored_in_hours() -> None:
    async with SessionLocal() as session:
        assert await automation.interval_minutes(session, "github") == 180
        assert await automation.interval_minutes(session, "calendar") == 30


async def test_profile_writes_a_coherent_set_of_settings() -> None:
    async with SessionLocal() as session:
        applied = await automation.set_profile(session, "manual")
        await session.commit()

        assert applied["automation.opportunity.enabled"] is False
        assert await automation.active_domains(session) == dict.fromkeys(automation.DOMAINS, False)
        interval_row = await session.get(Setting, "rss.interval_minutes")
        assert interval_row.value == 0
        assert await automation.current_profile(session) == "manual"

        await automation.set_profile(session, "balanced")
        await session.commit()
        assert await automation.active_domains(session) == dict.fromkeys(automation.DOMAINS, True)
        assert await automation.interval_minutes(session, "opportunity") == 30
        assert (await session.get(Setting, "rss.interval_minutes")).value == 60
        assert await automation.current_profile(session) == "balanced"


async def test_unknown_profile_is_rejected() -> None:
    async with SessionLocal() as session:
        with pytest.raises(ValueError):
            await automation.set_profile(session, "turbo")


async def test_disabled_domains_never_reach_the_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with SessionLocal() as session:
        await automation.set_profile(session, "manual")
        await session.commit()

    monkeypatch.setattr(jobs, "poll_media_sources", _fail)
    monkeypatch.setattr(jobs, "_poll_opportunities", _fail)
    monkeypatch.setattr(jobs, "sync_google", _fail)
    monkeypatch.setattr(jobs, "sync_github_service", _fail)

    assert await jobs.poll_media() == 0
    assert await jobs.catch_up_media() == 0
    assert await jobs.poll_opportunities() == 0
    assert await jobs.sync_calendar() == 0
    assert await jobs.sync_github() == 0


async def test_manual_actions_still_work_when_automation_is_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`ignore_interval=True` elle tazelemedir; otomasyon ayarini bypass eder."""
    async with SessionLocal() as session:
        await automation.set_profile(session, "manual")
        await session.commit()

    called: list[str] = []

    async def fake_media(*, ignore_interval: bool = False) -> int:
        called.append("media")
        return 0

    monkeypatch.setattr(jobs, "poll_media_sources", fake_media)
    assert await jobs.poll_media(ignore_interval=True) == 0
    assert called == ["media"]


async def test_fresh_calendar_and_github_are_not_synced_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with SessionLocal() as session:
        await log_event(session, verb="calendar.synced", payload={})
        session.add(SourceRun(source="github", status="ok", started_at=datetime.now(UTC)))
        await session.commit()

    monkeypatch.setattr(jobs, "sync_google", _fail)
    monkeypatch.setattr(jobs, "sync_github_service", _fail)

    assert await jobs.sync_calendar() == 0
    assert await jobs.sync_github() == 0


async def test_startup_rss_catch_up_skips_fresh_feeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Worker restart taze feed'leri yeniden cekmemeli."""
    async with SessionLocal() as session:
        await _seed_feed(session, minutes_ago=1)  # varsayilan aralik 30 dk
        await session.commit()

    monkeypatch.setattr(jobs.rss, "poll_feed", _fail)

    assert await jobs.catch_up() == 0
    assert await jobs.poll_feeds() == 0


async def test_startup_rss_catch_up_fetches_stale_feeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Makine kapaliyken kacirilan turlar yine kapanir."""
    async with SessionLocal() as session:
        await _seed_feed(session, minutes_ago=600)
        await session.commit()

    polled: list[uuid.UUID] = []

    async def fake_poll(session, feed):
        polled.append(feed.id)
        return "ok", 0

    monkeypatch.setattr(jobs.rss, "poll_feed", fake_poll)

    assert await jobs.catch_up() == 0
    assert len(polled) == 1


async def test_critical_catch_up_skips_recently_run_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Acilis kritik kaynaklari taze ise kuyruga ALMAZ."""
    from app.modules.opportunity.worker import critical_source_ids

    ids = critical_source_ids()[: jobs.CRITICAL_CATCH_UP_LIMIT]
    if not ids:  # pragma: no cover - katalog bos ise kapi zaten anlamsiz
        pytest.skip("kritik kaynak yok")

    async with SessionLocal() as session:
        for source_id in ids:
            session.add(SourceRun(source=source_id, status="ok", started_at=datetime.now(UTC)))
        await session.commit()

    # Taze kaynaklar icin batch OLUSMAMALI.
    assert await jobs.critical_catch_up() == 0
    async with SessionLocal() as session:
        batches = (
            await session.execute(
                select(func.count()).select_from(SourceSyncBatch)
            )
        ).scalar_one()
    assert batches == 0


async def test_automation_endpoints_apply_and_report(client: AsyncClient) -> None:
    state = (await client.get("/api/system/automation")).json()
    assert state["profile"] == "balanced"
    assert set(state["domains"]) == set(automation.DOMAINS)
    assert all(domain["enabled"] for domain in state["domains"].values())

    applied = await client.post("/api/system/automation/profile", json={"profile": "manual"})
    assert applied.status_code == 200, applied.text
    body = applied.json()
    assert body["profile"] == "manual"
    assert not any(domain["enabled"] for domain in body["domains"].values())

    assert (
        await client.post("/api/system/automation/profile", json={"profile": "turbo"})
    ).status_code == 422


async def test_profile_change_marks_backup_dirty(client: AsyncClient) -> None:
    """Profil degisikligi anlamli bir aksiyondur: event yazar."""
    from app.core.models import Event

    before = (await client.get("/api/system/automation")).json()["profile"]
    assert before == "balanced"

    await client.post("/api/system/automation/profile", json={"profile": "active"})

    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(Event).where(Event.verb == "system.automation_profile")
            )
        ).scalars().all()
    assert len(rows) == 1
