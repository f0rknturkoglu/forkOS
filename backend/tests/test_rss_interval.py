"""RSS cekim araligi AYARDAN gelir (ortam degiskeni yalnizca varsayilan).

Ayar DB'ye yazildigi icin okunmazsa Ayarlar ekranindaki secim olu kalir; ayrica
"yalniz manuel" secildiginde zamanlanmis turun AGA CIKMAMASI gerekir.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.config import settings
from app.core.entity import create_entity
from app.db import SessionLocal
from app.modules.rss import service
from app.modules.rss.models import Feed
from app.modules.system.models import Setting
from app.worker import jobs


async def _seed_feed(session, *, fetched_minutes_ago: int | None) -> Feed:
    entity = await create_entity(
        session, type=Feed.ENTITY_TYPE, title="Feed", search_text="feed"
    )
    fetched = (
        None
        if fetched_minutes_ago is None
        else datetime.now(UTC) - timedelta(minutes=fetched_minutes_ago)
    )
    feed = Feed(id=entity.id, url=f"https://example.invalid/{uuid.uuid4().hex}", last_fetched_at=fetched)
    session.add(feed)
    await session.flush()
    return feed


async def test_interval_falls_back_to_environment() -> None:
    async with SessionLocal() as session:
        assert await service.poll_interval_minutes(session) == settings.rss_default_interval_minutes


async def test_interval_reads_the_setting() -> None:
    async with SessionLocal() as session:
        session.add(Setting(key="rss.interval_minutes", value=120))
        await session.commit()

        assert await service.poll_interval_minutes(session) == 120
        # `due_feeds` de ayni ayari kullanir.
        fresh = await _seed_feed(session, fetched_minutes_ago=60)
        stale = await _seed_feed(session, fetched_minutes_ago=180)
        await session.commit()

        due = {feed.id for feed in await service.due_feeds(session)}

    assert stale.id in due
    assert fresh.id not in due


async def test_broken_interval_setting_falls_back() -> None:
    async with SessionLocal() as session:
        session.add(Setting(key="rss.interval_minutes", value="çok"))
        await session.commit()

        assert await service.poll_interval_minutes(session) == settings.rss_default_interval_minutes


async def test_manual_only_interval_never_fetches_in_the_background(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Aralik 0 iken zamanlanmis tur NE AGA CIKMALI ne de satir yazmali."""
    async with SessionLocal() as session:
        session.add(Setting(key="rss.interval_minutes", value=0))
        await _seed_feed(session, fetched_minutes_ago=None)
        await session.commit()

    async def fail(*args, **kwargs):  # pragma: no cover - cagrilirsa test kirilir
        raise AssertionError("manuel modda aga cikilmamali")

    monkeypatch.setattr(service, "poll_feed", fail)
    monkeypatch.setattr(jobs.rss, "poll_feed", fail)

    assert await jobs.poll_feeds() == 0
    assert await jobs.catch_up() == 0, "acilis telafisi de manuel moda uymali"


async def test_manual_refresh_ignores_the_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    """Aralik 'yalniz manuel' olsa bile elle tazeleme calisir."""
    async with SessionLocal() as session:
        session.add(Setting(key="rss.interval_minutes", value=0))
        feed = await _seed_feed(session, fetched_minutes_ago=1)
        await session.commit()
        feed_id = feed.id

    called: list[uuid.UUID] = []

    async def fake_poll(session, feed):
        called.append(feed.id)
        return "ok", 0

    monkeypatch.setattr(service, "poll_feed", fake_poll)

    # Doner deger EKLENEN kayit sayisidir (fake 0 doner); kanit `called`.
    await service.refresh_all(ignore_interval=True)

    assert called == [feed_id], "elle tazeleme taze feed'i de cekmeli"
