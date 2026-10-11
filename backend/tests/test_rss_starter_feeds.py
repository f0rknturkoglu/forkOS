"""Startup has no starter subscription job; historical markers remain untouched."""

from unittest.mock import AsyncMock

from sqlalchemy import select

from app.core.models import Entity
from app.db import SessionLocal
from app.main import app, lifespan
from app.modules.rss import service
from app.modules.rss.models import Feed
from app.modules.rss.schemas import FeedIn
from app.modules.system.models import Setting


async def test_startup_has_no_implicit_subscriptions_or_marker(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "_startup_critical_catch_up", AsyncMock())
    monkeypatch.setattr(main, "_startup_maintenance", AsyncMock())

    async def reject_probe(*args):
        raise AssertionError("Startup must not contact RSS providers")

    monkeypatch.setattr(service, "_probe_title", reject_probe)
    async with lifespan(app), SessionLocal() as db:
        assert list(await db.scalars(select(Feed))) == []
        assert await db.get(Setting, "rss.starter_feeds.v1") is None


async def test_existing_subscriptions_and_historical_marker_survive_startup(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "_startup_critical_catch_up", AsyncMock())
    monkeypatch.setattr(main, "_startup_maintenance", AsyncMock())
    async with SessionLocal() as db:
        feed, _ = await service.add_feed(
            db,
            FeedIn(url="https://fmhy.net/feed.rss", title="Kendi başlığım", category="Kişisel"),
            probe=False,
        )
        identity = feed.id
        db.add(Setting(key="rss.starter_feeds.v1", value={"version": 1}))
        await db.commit()
    async with lifespan(app), SessionLocal() as db:
        assert (await db.get(Entity, identity)).title == "Kendi başlığım"
        assert (await db.get(Feed, identity)).category == "Kişisel"
        assert await db.get(Setting, "rss.starter_feeds.v1") is not None
        assert await service.delete_feed(db, identity)
    async with lifespan(app), SessionLocal() as db:
        assert list(await db.scalars(select(Feed))) == []
        assert await db.get(Setting, "rss.starter_feeds.v1") is not None
