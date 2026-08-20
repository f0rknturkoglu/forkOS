"""RSS is mantigi.

Feed ve feed_item da birer entity'dir (kural 1) -- boylece global search,
link ve activity bedava gelir. Item'i "Save -> Read Later" yapmak yeni bir
bookmark uretir ve aralarina link(feed_item -> bookmark, 'saved_from') kurar.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import delete as sa_delete
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.config import settings
from app.core import runs as run_svc
from app.core import search as search_svc
from app.core.entity import create_entity, touch_entity
from app.core.events import log_event
from app.core.links import link
from app.core.models import Entity, Link
from app.modules.bookmark.models import Bookmark
from app.modules.bookmark.schemas import CaptureIn
from app.modules.bookmark.service import capture as capture_bookmark
from app.modules.rss.models import Feed, FeedItem
from app.modules.rss.schemas import FeedIn, FeedItemOut, FeedOut, FeedUpdate
from app.sources.base import RawItem
from app.sources.opml import parse_opml
from app.sources.rss_source import (
    EMPTY,
    ERROR,
    NOT_MODIFIED,
    OK,
    FetchResult,
    RssSource,
    feed_title,
)

MAX_ERRORS_BEFORE_DISABLE = 5
SAVED_FROM = "saved_from"


# ── Feed CRUD ──────────────────────────────────────────────────────────────

async def _probe_title(url: str) -> tuple[str, str | None]:
    """Feed'in kendi basligini cek. Ag hatasi feed eklemeyi ENGELLEMEZ."""
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            return feed_title(response.content, url)
    except Exception:
        return url, None


async def add_feed(
    session: AsyncSession, data: FeedIn, *, probe: bool = True,
) -> tuple[Feed, bool]:
    """Doner: (feed, created). Ayni URL ikinci kez eklenirse mevcut kayit doner."""
    existing = (await session.execute(
        select(Feed).where(Feed.url == data.url)
    )).scalar_one_or_none()
    if existing is not None:
        return existing, False

    title, site_url = (data.title.strip(), None)
    if not title and probe:
        title, site_url = await _probe_title(data.url)
    title = title or data.url

    entity = await create_entity(session, type=Feed.ENTITY_TYPE, title=title,
                                 search_text=f"{data.url} {data.category or ''}")
    feed = Feed(id=entity.id, url=data.url, site_url=site_url, category=data.category)
    session.add(feed)
    await log_event(session, verb="rss.feed_added", entity_id=entity.id,
                    entity_type="feed", payload={"url": data.url, "category": data.category})
    await session.commit()
    return feed, True


async def update_feed(
    session: AsyncSession, feed_id: uuid.UUID, data: FeedUpdate,
) -> Feed | None:
    feed = await session.get(Feed, feed_id)
    if feed is None:
        return None
    if data.category is not None:
        feed.category = data.category
    if data.active is not None:
        feed.active = data.active
        if data.active:
            feed.error_count = 0          # elle yeniden acilinca temiz sayfa
    await touch_entity(session, feed_id, title=data.title.strip() if data.title else None)
    await session.commit()
    return feed


async def delete_feed(session: AsyncSession, feed_id: uuid.UUID) -> bool:
    """entity silinince feed + feed_item'lar cascade ile gider."""
    entity = await session.get(Entity, feed_id)
    if entity is None:
        return False
    item_ids = list((await session.execute(
        select(FeedItem.id).where(FeedItem.feed_id == feed_id)
    )).scalars())
    await log_event(session, verb="rss.feed_removed", entity_id=feed_id,
                    entity_type="feed", payload={"title": entity.title})
    await session.flush()
    await session.delete(entity)
    if item_ids:
        # feed_item.id -> entity.id FK; feed cascade item'i siler ama entity satiri kalir
        await session.execute(sa_delete(Entity).where(Entity.id.in_(item_ids)))
    await session.commit()
    return True


async def list_feeds(session: AsyncSession, *, category: str | None = None) -> list[FeedOut]:
    unread_counts = dict((await session.execute(
        select(FeedItem.feed_id, func.count())
        .where(FeedItem.read_at.is_(None))
        .group_by(FeedItem.feed_id)
    )).all())

    stmt = (select(Feed, Entity.title)
            .join(Entity, Entity.id == Feed.id)
            .order_by(Feed.category.nulls_last(), Entity.title))
    if category:
        stmt = stmt.where(Feed.category == category)

    return [
        FeedOut(
            id=f.id, title=title, url=f.url, site_url=f.site_url, category=f.category,
            active=f.active, error_count=f.error_count, last_status=f.last_status,
            last_fetched_at=f.last_fetched_at, unread=unread_counts.get(f.id, 0),
        )
        for f, title in (await session.execute(stmt)).all()
    ]


async def import_opml(session: AsyncSession, content: bytes) -> tuple[int, int, list[str]]:
    """OPML -> feed'ler. Ag'a hic cikmaz (baslik OPML'den gelir), 200 feed hizli girer."""
    added, skipped, names = 0, 0, []
    for entry in parse_opml(content):
        feed, created = await add_feed(
            session,
            FeedIn(url=entry.url, title=entry.title, category=entry.category),
            probe=False,
        )
        if created:
            added += 1
            names.append(entry.title)
        else:
            skipped += 1
    return added, skipped, names


# ── Item okuma ─────────────────────────────────────────────────────────────

async def list_items(
    session: AsyncSession, *,
    feed_id: uuid.UUID | None = None,
    category: str | None = None,
    unread_only: bool = False,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[FeedItemOut]:
    FeedEntity = aliased(Entity, name="feed_entity")
    stmt = (
        select(FeedItem, Entity.title, FeedEntity.title)
        .join(Entity, Entity.id == FeedItem.id)
        .join(Feed, Feed.id == FeedItem.feed_id)
        .join(FeedEntity, FeedEntity.id == Feed.id)
        .order_by(FeedItem.published_at.desc().nulls_last(), FeedItem.fetched_at.desc())
        .limit(limit).offset(offset)
    )
    if feed_id:
        stmt = stmt.where(FeedItem.feed_id == feed_id)
    if category:
        stmt = stmt.where(Feed.category == category)
    if unread_only:
        stmt = stmt.where(FeedItem.read_at.is_(None))
    if q and q.strip():
        stmt = stmt.where(search_svc.match_clause(q.strip()))

    rows = (await session.execute(stmt)).all()
    saved = await _saved_bookmarks(session, [item.id for item, _, _ in rows])
    return [
        FeedItemOut(
            id=item.id, feed_id=item.feed_id, feed_title=ftitle, title=title,
            url=item.url, author=item.author, summary=item.summary,
            published_at=item.published_at, fetched_at=item.fetched_at,
            read_at=item.read_at, saved_bookmark_id=saved.get(item.id),
        )
        for item, title, ftitle in rows
    ]


async def get_item(session: AsyncSession, item_id: uuid.UUID) -> FeedItemOut | None:
    FeedEntity = aliased(Entity, name="feed_entity")
    row = (await session.execute(
        select(FeedItem, Entity.title, FeedEntity.title)
        .join(Entity, Entity.id == FeedItem.id)
        .join(Feed, Feed.id == FeedItem.feed_id)
        .join(FeedEntity, FeedEntity.id == Feed.id)
        .where(FeedItem.id == item_id)
    )).first()
    if row is None:
        return None
    item, title, feed_title_ = row
    saved = await _saved_bookmarks(session, [item.id])
    return FeedItemOut(
        id=item.id, feed_id=item.feed_id, feed_title=feed_title_, title=title,
        url=item.url, author=item.author, summary=item.summary,
        published_at=item.published_at, fetched_at=item.fetched_at,
        read_at=item.read_at, saved_bookmark_id=saved.get(item.id),
    )


async def _saved_bookmarks(
    session: AsyncSession, item_ids: list[uuid.UUID],
) -> dict[uuid.UUID, uuid.UUID]:
    if not item_ids:
        return {}
    rows = (await session.execute(
        select(Link.from_id, Link.to_id)
        .where(Link.from_id.in_(item_ids), Link.relation == SAVED_FROM)
    )).all()
    return {from_id: to_id for from_id, to_id in rows}


async def mark_read(
    session: AsyncSession, item_id: uuid.UUID, *, read: bool = True,
) -> FeedItem | None:
    item = await session.get(FeedItem, item_id)
    if item is None:
        return None
    was_read = item.read_at is not None
    item.read_at = datetime.now(UTC) if read else None
    if read and not was_read:
        await log_event(session, verb="rss.item_read", entity_id=item_id,
                        entity_type="feed_item", payload={"feed_id": str(item.feed_id)})
    await session.commit()
    return item


async def mark_all_read(session: AsyncSession, *, feed_id: uuid.UUID | None = None) -> int:
    stmt = select(FeedItem).where(FeedItem.read_at.is_(None))
    if feed_id:
        stmt = stmt.where(FeedItem.feed_id == feed_id)
    items = list((await session.execute(stmt)).scalars())
    now = datetime.now(UTC)
    for item in items:
        item.read_at = now
    if items:
        await log_event(session, verb="rss.marked_all_read",
                        entity_id=feed_id, entity_type="feed" if feed_id else None,
                        payload={"count": len(items), "feed_id": str(feed_id) if feed_id else None})
    await session.commit()
    return len(items)


async def save_item(
    session: AsyncSession, item_id: uuid.UUID, collection: str,
) -> Bookmark | None:
    """Item -> bookmark. Iki entity arasinda 'saved_from' link'i kurar."""
    row = (await session.execute(
        select(FeedItem, Entity.title)
        .join(Entity, Entity.id == FeedItem.id)
        .where(FeedItem.id == item_id)
    )).first()
    if row is None:
        return None
    item, title = row

    existing_id = (await _saved_bookmarks(session, [item_id])).get(item_id)
    if existing_id is not None:
        existing = await session.get(Bookmark, existing_id)
        if existing is not None:
            return existing

    bookmark, _, _ = await capture_bookmark(session, CaptureIn(
        url=item.url or "", title=title, description=item.summary,
        collection=collection, source="rss",
    ))
    await link(session, item_id, bookmark.id, SAVED_FROM)
    if item.read_at is None:
        item.read_at = datetime.now(UTC)
    await log_event(session, verb="rss.item_saved", entity_id=item_id,
                    entity_type="feed_item",
                    payload={"bookmark_id": str(bookmark.id), "collection": collection})
    await session.commit()
    return bookmark


async def stats(session: AsyncSession) -> dict:
    total = (await session.execute(select(func.count()).select_from(Feed))).scalar_one()
    active = (await session.execute(
        select(func.count()).select_from(Feed).where(Feed.active.is_(True))
    )).scalar_one()
    failing = (await session.execute(
        select(func.count()).select_from(Feed)
        .where(or_(Feed.active.is_(False), Feed.error_count > 0))
    )).scalar_one()
    unread = (await session.execute(
        select(func.count()).select_from(FeedItem).where(FeedItem.read_at.is_(None))
    )).scalar_one()
    return {"feeds": total, "active_feeds": active, "failing_feeds": failing, "unread": unread}


# ── Worker tarafi ──────────────────────────────────────────────────────────

async def due_feeds(session: AsyncSession, *, interval_minutes: int | None = None) -> list[Feed]:
    """Suresi gelmis feed'ler. last_fetched_at NULL olanlar hep once gelir (catch-up)."""
    # 0 gecerli bir deger (catch-up "hepsini simdi cek" der) -- "or" ile ezme
    interval = (settings.rss_default_interval_minutes
                if interval_minutes is None else interval_minutes)
    cutoff = datetime.now(UTC) - timedelta(minutes=interval)
    return list((await session.execute(
        select(Feed)
        .where(Feed.active.is_(True))
        .where(or_(Feed.last_fetched_at.is_(None), Feed.last_fetched_at < cutoff))
        .order_by(Feed.last_fetched_at.nulls_first())
    )).scalars())


def source_for(feed: Feed) -> RssSource:
    return RssSource(str(feed.id), feed.url, etag=feed.etag, last_modified=feed.last_modified)


async def ingest(session: AsyncSession, feed: Feed, items: list[RawItem]) -> int:
    """Yeni item'lari yazar. (feed_id, guid) zaten varsa atlar. Doner: yeni sayisi."""
    if not items:
        return 0
    guids = [i.external_id for i in items]
    known = set((await session.execute(
        select(FeedItem.guid).where(FeedItem.feed_id == feed.id, FeedItem.guid.in_(guids))
    )).scalars())

    added = 0
    for raw in items:
        if raw.external_id in known:
            continue
        known.add(raw.external_id)
        entity = await create_entity(
            session, type=FeedItem.ENTITY_TYPE, title=raw.title,
            search_text=" ".join(filter(None, [raw.url, raw.summary])),
        )
        session.add(FeedItem(
            id=entity.id, feed_id=feed.id, guid=raw.external_id, url=raw.url,
            author=raw.extra.get("author"), summary=raw.summary,
            published_at=raw.published_at,
        ))
        added += 1

    if added:
        await log_event(session, verb="rss.items_added", entity_id=feed.id,
                        entity_type="feed", payload={"count": added, "feed_url": feed.url})
    return added


async def record_fetch(session: AsyncSession, feed: Feed, result: FetchResult) -> None:
    """Feed'in conditional GET durumunu ve hata sayacini gunceller.

    5 ardisik hata -> feed kapatilir + bildirim event'i (kural 6).
    """
    feed.last_fetched_at = datetime.now(UTC)
    feed.last_status = result.status

    if result.status == ERROR:
        feed.error_count += 1
        await log_event(session, verb="rss.feed_failed", entity_id=feed.id,
                        entity_type="feed",
                        payload={"error": result.error, "count": feed.error_count,
                                 "url": feed.url})
        if feed.error_count >= MAX_ERRORS_BEFORE_DISABLE:
            feed.active = False
            await log_event(session, verb="rss.feed_disabled", entity_id=feed.id,
                            entity_type="feed",
                            payload={"url": feed.url, "errors": feed.error_count,
                                     "message": f"{feed.url}: {feed.error_count} hata, kapatildi"})
        return

    feed.error_count = 0
    if result.status != NOT_MODIFIED:
        feed.etag = result.etag
        feed.last_modified = result.last_modified



async def poll_feed(session: AsyncSession, feed: Feed) -> tuple[str, int]:
    """Tek feed'i cek, source_run'a yaz, yeni item'lari kaydet.

    Worker da, "simdi yenile" butonu da BURAYI cagirir -- mantik tek yerde.
    Doner: (status, eklenen_item_sayisi)
    """
    source_id = f"rss:{feed.id}"
    run = await run_svc.start_run(session, source_id)
    result = await source_for(feed).fetch_result()

    added = 0
    if result.status in (OK, EMPTY):
        added = await ingest(session, feed, result.items)
    await record_fetch(session, feed, result)

    # 304 = degisiklik yok; 'bos' saymayiz, yoksa saglikli feed'ler uyari uretir.
    run_status = {OK: run_svc.OK, EMPTY: run_svc.EMPTY,
                  NOT_MODIFIED: run_svc.OK, ERROR: run_svc.ERROR}[result.status]
    if result.status == OK and added == 0:
        run_status = run_svc.EMPTY          # feed 200 donuyor ama yeni bir sey yok
    await run_svc.finish_run(session, run, status=run_status, items_found=added,
                             error=result.error)
    await session.commit()

    if run_status == run_svc.EMPTY:
        await run_svc.check_stalled(session, source_id, label=feed.url)
        await session.commit()
    return result.status, added

async def prune_items(session: AsyncSession, *, days: int | None = None) -> int:
    """Okunmamis + kaydedilmemis eski item'lari siler.

    Yoksa entity tablosu yilda ~50k satir siser. Kaydedilmis (link'li) veya
    okunmus item'lara DOKUNULMAZ.
    """
    retention = settings.rss_retention_days if days is None else days
    cutoff = datetime.now(UTC) - timedelta(days=retention)
    saved = select(Link.from_id).where(Link.relation == SAVED_FROM)
    ids = list((await session.execute(
        select(FeedItem.id)
        .where(FeedItem.fetched_at < cutoff)
        .where(FeedItem.read_at.is_(None))
        .where(FeedItem.id.not_in(saved))
    )).scalars())
    if not ids:
        return 0
    await session.execute(sa_delete(Entity).where(Entity.id.in_(ids)))
    await log_event(session, verb="rss.pruned", payload={"count": len(ids), "days": retention})
    await session.commit()
    return len(ids)
