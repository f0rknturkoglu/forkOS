"""V1 preserves legacy subscriptions and never creates implicit starter feeds."""
from sqlalchemy import select

from app.core.models import Entity
from app.db import SessionLocal
from app.modules.rss import service
from app.modules.rss.models import Feed
from app.modules.rss.schemas import FeedIn
from app.modules.system.models import Setting


async def test_empty_installation_has_no_starter_feeds_or_marker(monkeypatch):
    async def reject_probe(*args):
        raise AssertionError("Startup must not contact providers")
    monkeypatch.setattr(service, "_probe_title", reject_probe)
    async with SessionLocal() as session:
        assert await service.ensure_starter_feeds(session) == (0,0)
        assert list(await session.scalars(select(Feed))) == []
        assert await session.get(Setting, service.STARTER_FEEDS_SETTING_KEY) is None

async def test_existing_explicit_rss_is_untouched_and_deleted_feeds_stay_deleted():
    async with SessionLocal() as session:
        feed, _ = await service.add_feed(session, FeedIn(url="https://fmhy.net/feed.rss",title="Kendi başlığım",category="Kişisel"),probe=False)
        assert await service.ensure_starter_feeds(session) == (0,0)
        assert await session.scalar(select(Entity.title).where(Entity.id == feed.id)) == "Kendi başlığım"
        assert feed.category == "Kişisel"
        assert len(list(await session.scalars(select(Feed)))) == 1
        await service.delete_feed(session,feed.id)
        assert await service.ensure_starter_feeds(session) == (0,0)
        assert list(await session.scalars(select(Feed))) == []
