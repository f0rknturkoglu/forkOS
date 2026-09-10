"""RSS saklama (prune) testleri.

Kritik davranis: saklama suresi once Ayarlar ekraninin yazdigi
`setting.rss.retention_days` degerinden okunur; ayar yoksa/bozuksa ortam
degiskeni varsayilanina dusulur. Bu bag kurulmadan ayar olu kaliyordu.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.config import settings
from app.core.entity import create_entity
from app.core.links import link
from app.core.models import Event
from app.db import SessionLocal
from app.modules.rss import service
from app.modules.rss.models import Feed, FeedItem
from app.modules.system.models import Setting


async def _seed_feed(session) -> Feed:
    entity = await create_entity(session, type=Feed.ENTITY_TYPE, title="Feed", search_text="feed")
    feed = Feed(id=entity.id, url="https://example.com/feed.xml")
    session.add(feed)
    await session.flush()
    return feed


async def _seed_item(session, feed: Feed, *, guid: str, age_days: int, read: bool = False):
    entity = await create_entity(session, type=FeedItem.ENTITY_TYPE, title=f"Item {guid}", search_text="item")
    fetched = datetime.now(UTC) - timedelta(days=age_days)
    item = FeedItem(
        id=entity.id,
        feed_id=feed.id,
        guid=guid,
        fetched_at=fetched,
        read_at=fetched if read else None,
    )
    session.add(item)
    await session.flush()
    return item


async def _remaining_guids(session) -> set[str]:
    rows = (await session.execute(select(FeedItem.guid))).scalars().all()
    return set(rows)


async def test_prune_uses_setting_retention_days():
    async with SessionLocal() as session:
        feed = await _seed_feed(session)
        await _seed_item(session, feed, guid="eski-okunmamis", age_days=20)
        await _seed_item(session, feed, guid="eski-okunmus", age_days=20, read=True)
        await _seed_item(session, feed, guid="taze", age_days=1)
        session.add(Setting(key="rss.retention_days", value=7))
        await session.commit()

        removed = await service.prune_items(session)

        assert removed == 1
        assert await _remaining_guids(session) == {"eski-okunmus", "taze"}


async def test_setting_wins_over_config_default():
    """30 gunluk kayit, ayar 7 gun iken silinir; ortam varsayilani 90 olsa da."""
    async with SessionLocal() as session:
        feed = await _seed_feed(session)
        await _seed_item(session, feed, guid="otuz-gunluk", age_days=30)
        session.add(Setting(key="rss.retention_days", value=7))
        await session.commit()

        assert await service.prune_items(session) == 1


async def test_prune_keeps_saved_items():
    async with SessionLocal() as session:
        feed = await _seed_feed(session)
        item = await _seed_item(session, feed, guid="kayitli", age_days=200)
        bookmark_entity = await create_entity(session, type="bookmark", title="Kayit", search_text="kayit")
        await link(session, item.id, bookmark_entity.id, "saved_from")
        session.add(Setting(key="rss.retention_days", value=7))
        await session.commit()

        assert await service.prune_items(session) == 0
        assert await _remaining_guids(session) == {"kayitli"}


async def test_explicit_days_argument_wins_over_setting():
    async with SessionLocal() as session:
        feed = await _seed_feed(session)
        await _seed_item(session, feed, guid="iki-gunluk", age_days=2)
        session.add(Setting(key="rss.retention_days", value=365))
        await session.commit()

        assert await service.prune_items(session, days=1) == 1


async def test_missing_or_invalid_setting_falls_back_to_config():
    """Ayar yok/bozuksa ortam varsayilani gecerli olur; esik degerine gore karar verir."""
    async with SessionLocal() as session:
        feed = await _seed_feed(session)
        await _seed_item(session, feed, guid="sinirda", age_days=20)
        await session.commit()

        default_days = settings.rss_retention_days
        expected = 1 if default_days < 20 else 0

        assert await service.prune_items(session) == expected

        session.add(Setting(key="rss.retention_days", value="çok"))
        await session.commit()

        # Bozuk ayar ortam varsayilanina duser; davranis degismez.
        assert await service.prune_items(session) == 0


async def test_prune_logs_event_with_effective_retention():
    async with SessionLocal() as session:
        feed = await _seed_feed(session)
        await _seed_item(session, feed, guid="silinecek", age_days=40)
        session.add(Setting(key="rss.retention_days", value=7))
        await session.commit()

        assert await service.prune_items(session) == 1

        event = (
            await session.execute(select(Event).where(Event.verb == "rss.pruned").order_by(Event.id.desc()))
        ).scalars().first()
        assert event is not None
        assert event.payload == {"count": 1, "days": 7}
