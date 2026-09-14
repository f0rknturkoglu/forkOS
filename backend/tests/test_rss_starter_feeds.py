"""RSS başlangıç abonelikleri; gerçek ağa çıkmaz."""

from sqlalchemy import select

from app.core.models import Entity
from app.db import SessionLocal
from app.modules.rss import service
from app.modules.rss.models import Feed
from app.modules.rss.schemas import FeedIn
from app.modules.system.models import Setting


async def test_starter_feeds_are_added_once_without_probe(monkeypatch) -> None:
    async def reject_probe(url: str):
        raise AssertionError(f"başlangıç kurulumu dış ağa çıkmamalı: {url}")

    monkeypatch.setattr(service, "_probe_title", reject_probe)

    async with SessionLocal() as session:
        # Kullanıcının önceden eklediği aynı URL ikinci bir satır üretmemeli;
        # başlığı korunurken kanonik başlangıç kategorisi eşitlenmeli.
        await service.add_feed(
            session,
            FeedIn(
                url="https://fmhy.net/feed.rss",
                title="Kendi FMHY Başlığım",
                category="Kişisel",
            ),
            probe=False,
        )

        assert await service.ensure_starter_feeds(session) == (1, 1)

        rows = (
            await session.execute(
                select(Feed, Entity.title).join(Entity, Entity.id == Feed.id).order_by(Feed.url)
            )
        ).all()
        assert [(feed.url, title, feed.category) for feed, title in rows] == [
            (
                "https://fmhy.net/feed.rss",
                "Kendi FMHY Başlığım",
                "Rehberler / Araçlar",
            ),
            (
                "https://github.com/champagnewiki/champagne-wiki/commits.atom",
                "Champagne Piracy",
                "Arşiv / Güvenlik",
            ),
        ]
        assert await session.get(Setting, service.STARTER_FEEDS_SETTING_KEY) is not None

        # İşaret varken tekrar çalıştırmak no-op'tur.
        assert await service.ensure_starter_feeds(session) == (0, 0)
        assert len((await session.execute(select(Feed))).scalars().all()) == 2


async def test_deleted_starter_feed_is_not_forced_back() -> None:
    async with SessionLocal() as session:
        assert await service.ensure_starter_feeds(session) == (2, 0)
        champagne = (
            await session.execute(
                select(Feed).where(
                    Feed.url == "https://github.com/champagnewiki/champagne-wiki/commits.atom"
                )
            )
        ).scalar_one()
        assert await service.delete_feed(session, champagne.id) is True

        assert await service.ensure_starter_feeds(session) == (0, 0)
        urls = set((await session.execute(select(Feed.url))).scalars())
        assert urls == {"https://fmhy.net/feed.rss"}
