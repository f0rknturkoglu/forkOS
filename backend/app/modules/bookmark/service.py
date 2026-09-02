"""Bookmark/Inbox is mantigi.

Kural 2: entity yazan her yer core/entity.py helper'larini kullanir.
Kural 3: anlamli her aksiyondan sonra log_event().
Kural 7: Inbox ve Bookmark ayni tablo -- ayirici alan `collection`.
"""

from __future__ import annotations

import hashlib
import uuid
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import search as search_svc
from app.core import tags as tag_svc
from app.core.entity import create_entity, touch_entity
from app.core.events import log_event
from app.core.models import Entity
from app.core.time import local_day_bounds, local_today
from app.modules.bookmark.models import COLLECTIONS, Bookmark
from app.modules.bookmark.schemas import BookmarkOut, BookmarkUpdate, CaptureIn

_TRACKING_PREFIXES = ("utm_", "fbclid", "gclid", "mc_cid", "mc_eid", "ref")


def normalize_url(url: str) -> str:
    """Takip parametrelerini atar, host'u sadelestirir. Dedup burada baslar."""
    parts = urlsplit(url.strip())
    query = "&".join(
        p
        for p in parts.query.split("&")
        if p and not p.split("=")[0].lower().startswith(_TRACKING_PREFIXES)
    )
    host = parts.netloc.lower().removeprefix("www.")
    return urlunsplit((parts.scheme.lower(), host, parts.path.rstrip("/"), query, ""))


def url_hash(url: str) -> str:
    return hashlib.sha256(normalize_url(url).encode()).hexdigest()


def _search_text(*parts: str | None) -> str:
    return " ".join(p.strip() for p in parts if p and p.strip())


async def find_by_url(
    session: AsyncSession,
    url: str,
    *,
    exclude: uuid.UUID | None = None,
) -> Bookmark | None:
    """En eski eslesme -- "zaten kayitli" uyarisi icin."""
    stmt = (
        select(Bookmark)
        .where(Bookmark.url_hash == url_hash(url))
        .order_by(Bookmark.saved_at)
        .limit(1)
    )
    if exclude is not None:
        stmt = stmt.where(Bookmark.id != exclude)
    return (await session.execute(stmt)).scalar_one_or_none()


async def capture(
    session: AsyncSession,
    data: CaptureIn,
) -> tuple[Bookmark, bool, Bookmark | None]:
    """Idempotent capture.

    Doner: (bookmark, replayed, prior)
      replayed -> ayni client_uuid ikinci kez geldi, YENI KAYIT ACILMADI
      prior    -> ayni URL daha once kaydedilmis (hata degil, sadece bilgi)
    """
    if data.client_uuid:
        existing = (
            await session.execute(select(Bookmark).where(Bookmark.client_uuid == data.client_uuid))
        ).scalar_one_or_none()
        if existing is not None:
            return existing, True, None

    # Kendisiyle karsilastirmamak icin kayit ACILMADAN once bakilir.
    prior = await find_by_url(session, data.url)

    entity = await create_entity(
        session,
        type=Bookmark.ENTITY_TYPE,
        title=data.title.strip() or normalize_url(data.url),
        search_text=_search_text(data.url, data.description, data.selection, data.note),
    )
    bookmark = Bookmark(
        id=entity.id,
        url=data.url,
        url_hash=url_hash(data.url),
        description=data.description,
        selection=data.selection,
        note=data.note,
        collection=data.collection,
        source=data.source,
        client_uuid=data.client_uuid,
    )
    session.add(bookmark)
    await session.flush()

    if data.tags:
        await tag_svc.add_tags(session, entity.id, data.tags)

    await log_event(
        session,
        verb="bookmark.saved",
        entity_id=entity.id,
        entity_type="bookmark",
        payload={
            "collection": data.collection,
            "source": data.source,
            "url": data.url,
            "duplicate": prior is not None,
        },
    )
    await session.commit()
    return bookmark, False, prior


async def move(session: AsyncSession, bookmark_id: uuid.UUID, collection: str) -> Bookmark | None:
    bookmark = await session.get(Bookmark, bookmark_id)
    if bookmark is None:
        return None
    previous, bookmark.collection = bookmark.collection, collection
    await touch_entity(session, bookmark_id)
    if previous != collection:
        await log_event(
            session,
            verb="bookmark.moved",
            entity_id=bookmark_id,
            entity_type="bookmark",
            payload={"from": previous, "to": collection},
        )
    await session.commit()
    return bookmark


async def update(
    session: AsyncSession,
    bookmark_id: uuid.UUID,
    data: BookmarkUpdate,
) -> Bookmark | None:
    bookmark = await session.get(Bookmark, bookmark_id)
    if bookmark is None:
        return None

    if data.collection is not None and data.collection != bookmark.collection:
        await log_event(
            session,
            verb="bookmark.moved",
            entity_id=bookmark_id,
            entity_type="bookmark",
            payload={"from": bookmark.collection, "to": data.collection},
        )
        bookmark.collection = data.collection
    if data.note is not None:
        bookmark.note = data.note
    if data.description is not None:
        bookmark.description = data.description
    if data.favorite is not None and data.favorite != bookmark.favorite:
        bookmark.favorite = data.favorite
        await log_event(
            session,
            verb="bookmark.favorited",
            entity_id=bookmark_id,
            entity_type="bookmark",
            payload={"favorite": data.favorite},
        )
    if data.read_status is not None and data.read_status != bookmark.read_status:
        bookmark.read_status = data.read_status
        if data.read_status == "read":
            await log_event(
                session,
                verb="bookmark.read",
                entity_id=bookmark_id,
                entity_type="bookmark",
                payload={},
            )
    if data.tags is not None:
        await tag_svc.set_tags(session, bookmark_id, data.tags)

    await touch_entity(
        session,
        bookmark_id,
        title=data.title.strip() if data.title else None,
        search_text=_search_text(
            bookmark.url, bookmark.description, bookmark.selection, bookmark.note
        ),
    )
    await session.commit()
    return bookmark


async def delete(session: AsyncSession, bookmark_id: uuid.UUID) -> bool:
    """entity satirini siler -- bookmark, link ve tag cascade ile gider.

    event tablosuna DOKUNULMAZ (kural 3): entity_id NULL'a duser, entity_type kalir.
    """
    entity = await session.get(Entity, bookmark_id)
    if entity is None:
        return False
    await log_event(
        session,
        verb="bookmark.deleted",
        entity_id=bookmark_id,
        entity_type="bookmark",
        payload={"title": entity.title},
    )
    await session.flush()
    await session.delete(entity)
    await session.commit()
    return True


async def list_bookmarks(
    session: AsyncSession,
    *,
    collection: str | None = None,
    read_status: str | None = None,
    favorite: bool | None = None,
    source: str | None = None,
    q: str | None = None,
    tag: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[BookmarkOut]:
    stmt = (
        select(Bookmark, Entity.title)
        .join(Entity, Entity.id == Bookmark.id)
        .order_by(Bookmark.saved_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if collection:
        stmt = stmt.where(Bookmark.collection == collection)
    if read_status:
        stmt = stmt.where(Bookmark.read_status == read_status)
    if source:
        stmt = stmt.where(Bookmark.source == source)
    if favorite is not None:
        stmt = stmt.where(Bookmark.favorite.is_(favorite))
    if q and q.strip():
        stmt = stmt.where(search_svc.match_clause(q.strip()))
    if tag:
        ids = await tag_svc.entity_ids_with_tag(session, tag)
        if not ids:
            return []
        stmt = stmt.where(Bookmark.id.in_(ids))

    rows = (await session.execute(stmt)).all()
    tag_map = await tag_svc.tags_for(session, [b.id for b, _ in rows])
    return [_to_out(b, title, tag_map.get(b.id, [])) for b, title in rows]


async def get(session: AsyncSession, bookmark_id: uuid.UUID) -> BookmarkOut | None:
    row = (
        await session.execute(
            select(Bookmark, Entity.title)
            .join(Entity, Entity.id == Bookmark.id)
            .where(Bookmark.id == bookmark_id)
        )
    ).first()
    if row is None:
        return None
    bookmark, title = row
    tag_map = await tag_svc.tags_for(session, [bookmark.id])
    return _to_out(bookmark, title, tag_map.get(bookmark.id, []))


def _to_out(bookmark: Bookmark, title: str, tags: list[str]) -> BookmarkOut:
    return BookmarkOut(
        id=bookmark.id,
        title=title,
        url=bookmark.url,
        description=bookmark.description,
        collection=bookmark.collection,
        queue_kind=bookmark.queue_kind,
        source=bookmark.source,
        read_status=bookmark.read_status,
        favorite=bookmark.favorite,
        note=bookmark.note,
        selection=bookmark.selection,
        saved_at=bookmark.saved_at,
        tags=tags,
    )


async def stats(session: AsyncSession) -> dict:
    per_collection = dict(
        (
            await session.execute(
                select(Bookmark.collection, func.count()).group_by(Bookmark.collection)
            )
        ).all()
    )
    unread = (
        await session.execute(
            select(func.count()).select_from(Bookmark).where(Bookmark.read_status == "unread")
        )
    ).scalar_one()
    midnight, tomorrow = local_day_bounds(local_today())
    saved_today = (
        await session.execute(
            select(func.count()).select_from(Bookmark).where(
                Bookmark.saved_at >= midnight,
                Bookmark.saved_at < tomorrow,
            )
        )
    ).scalar_one()
    return {
        "inbox": per_collection.get("inbox", 0),
        "unread": unread,
        "saved_today": saved_today,
        "total": sum(per_collection.values()),
        "collections": [{"collection": c, "count": per_collection.get(c, 0)} for c in COLLECTIONS],
    }
