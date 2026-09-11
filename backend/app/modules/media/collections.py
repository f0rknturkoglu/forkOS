"""Medya koleksiyon CRUD ve koleksiyon-item baglari."""

from __future__ import annotations

import base64
import binascii
import json
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import create_entity, delete_entity, touch_entity
from app.core.events import log_event
from app.core.links import unlink
from app.core.models import Entity, Link
from app.modules.media.models import (
    MEDIA_COLLECTION_ITEM_RELATION,
    MediaCollection,
    MediaItem,
)
from app.modules.media.schemas import (
    MediaCollectionDetailOut,
    MediaCollectionIn,
    MediaCollectionOut,
    MediaCollectionUpdate,
)
from app.modules.media.search import _to_item_out

#: Koleksiyon kartinda gosterilen kapak sayisi.
_COVER_COUNT = 4
#: Yerel kapak dosyalarinin servis edildigi yol (frontend mediaCoverUrl ile ayni).
_ASSET_PREFIX = "/api/media/assets/"

#: Koleksiyon uyeleri icin desteklenen siralama (search.list_items ile ayni mantik).
_LIST_ORDERS = {
    "updated": (Entity.updated_at.desc(), MediaItem.id.desc()),
    "created": (Entity.created_at.desc(), MediaItem.id.desc()),
    "title": (func.lower(Entity.title).asc(), MediaItem.id.asc()),
    "score": (
        MediaItem.score.desc().nulls_last(),
        Entity.updated_at.desc(),
        Entity.id.desc(),
    ),
    "progress": (
        MediaItem.progress.desc().nulls_last(),
        Entity.updated_at.desc(),
        Entity.id.desc(),
    ),
}


def _cover_asset_url(cover_path: str | None, cover_url: str | None) -> str | None:
    """Yerel kapak varsa asset URL'i uretir; yoksa uzak kapaga duser.

    `cover_path` DB'de bazen ciplak dosya adi, bazen hazir
    `/api/media/assets/<ad>` bicimidir; ikisi de kabul edilir.
    """
    if cover_path:
        name = (
            cover_path[len(_ASSET_PREFIX):]
            if cover_path.startswith(_ASSET_PREFIX)
            else cover_path
        )
        if name and not any(bad in name for bad in ("/", "\\", "?", "#", "%")):
            return f"{_ASSET_PREFIX}{name}"
    return cover_url


def _encode_cursor(offset: int) -> str:
    raw = json.dumps({"offset": offset}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_cursor(cursor: str | None) -> int:
    """Offset imlecini cozer; bozuk imlec ilk sayfayi doner.

    Router bu ucta MediaCommandError'i yakalamiyor (imza donuk), bu yuzden
    cozulemeyen imlec 500 yerine sayfa basindan devam eder.
    """
    if not cursor:
        return 0
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        value = json.loads(base64.urlsafe_b64decode(padded).decode())
        offset = int(value["offset"])
        return offset if offset >= 0 else 0
    except (
        binascii.Error,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        UnicodeDecodeError,
        ValueError,
    ):
        return 0


def _to_collection_out(
    collection: MediaCollection,
    title: str,
    item_count: int = 0,
    covers: list[str] | None = None,
) -> MediaCollectionOut:
    return MediaCollectionOut(
        id=collection.id,
        title=title,
        description=collection.description,
        color=collection.color,
        position=collection.position,
        item_count=item_count,
        covers=covers or [],
        created_at=collection.created_at,
        updated_at=collection.updated_at,
    )


async def _collection_meta(
    session: AsyncSession, collection_ids: list[uuid.UUID]
) -> dict[uuid.UUID, tuple[int, list[str]]]:
    """Koleksiyon -> (uye sayisi, en yeni 4 kapak) haritasi; N+1 yok.

    Tek sorguda pencere fonksiyonu: her koleksiyon icin toplam uye ve en yeni
    uyelerin kapaklari ayni geciste hesaplanir.
    """
    if not collection_ids:
        return {}
    ranked = (
        select(
            Link.from_id.label("collection_id"),
            MediaItem.cover_path,
            MediaItem.cover_url,
            func.count().over(partition_by=Link.from_id).label("item_count"),
            func.row_number()
            .over(
                partition_by=Link.from_id,
                order_by=(Link.created_at.desc(), Link.id.desc()),
            )
            .label("rank"),
        )
        .join(MediaItem, MediaItem.id == Link.to_id)
        .join(Entity, Entity.id == Link.to_id)
        .where(
            Link.from_id.in_(collection_ids),
            Link.relation == MEDIA_COLLECTION_ITEM_RELATION,
            Entity.archived_at.is_(None),
        )
        .subquery()
    )
    rows = (
        await session.execute(
            select(
                ranked.c.collection_id,
                ranked.c.item_count,
                ranked.c.cover_path,
                ranked.c.cover_url,
            )
            .where(ranked.c.rank <= _COVER_COUNT)
            .order_by(ranked.c.collection_id, ranked.c.rank)
        )
    ).all()
    meta: dict[uuid.UUID, tuple[int, list[str]]] = {}
    for collection_id, item_count, cover_path, cover_url in rows:
        count, covers = meta.setdefault(collection_id, (int(item_count), []))
        url = _cover_asset_url(cover_path, cover_url)
        if url:
            covers.append(url)
    return meta


async def list_collections(session: AsyncSession) -> list[MediaCollectionOut]:
    rows = (
        await session.execute(
            select(MediaCollection, Entity.title)
            .join(Entity, Entity.id == MediaCollection.id)
            .order_by(MediaCollection.position, Entity.title)
        )
    ).all()
    meta = await _collection_meta(session, [collection.id for collection, _ in rows])
    return [
        _to_collection_out(collection, title, *meta.get(collection.id, (0, [])))
        for collection, title in rows
    ]


async def collection_detail(
    session: AsyncSession,
    collection_id: uuid.UUID,
    *,
    q: str | None = None,
    sort: str = "updated",
    cursor: str | None = None,
    limit: int = 48,
) -> MediaCollectionDetailOut | None:
    row = (
        await session.execute(
            select(MediaCollection, Entity.title)
            .join(Entity, Entity.id == MediaCollection.id)
            .where(MediaCollection.id == collection_id)
        )
    ).first()
    if row is None:
        return None
    collection, title = row
    if sort not in _LIST_ORDERS:
        raise ValueError(f"Gecersiz koleksiyon siralamasi: {sort}")
    stmt = (
        select(MediaItem, Entity)
        .join(
            Link,
            (Link.to_id == MediaItem.id)
            & (Link.from_id == collection_id)
            & (Link.relation == MEDIA_COLLECTION_ITEM_RELATION),
        )
        .join(Entity, Entity.id == MediaItem.id)
        .where(Entity.archived_at.is_(None))
    )
    if q:
        for token in q.split():
            pattern = f"%{token}%"
            stmt = stmt.where(
                or_(Entity.title.ilike(pattern), Entity.search_text.ilike(pattern))
            )
    total = int(
        (
            await session.execute(
                select(func.count()).select_from(stmt.order_by(None).subquery())
            )
        ).scalar_one()
    )
    offset = _decode_cursor(cursor)
    rows = (
        await session.execute(
            stmt.order_by(*_LIST_ORDERS[sort]).offset(offset).limit(limit)
        )
    ).all()
    item_count, covers = (await _collection_meta(session, [collection_id])).get(
        collection_id, (0, [])
    )
    return MediaCollectionDetailOut(
        collection=_to_collection_out(collection, title, item_count, covers),
        items=[_to_item_out(item, entity) for item, entity in rows],
        total=total,
        next_cursor=_encode_cursor(offset + limit) if offset + len(rows) < total else None,
    )


async def create_collection(session: AsyncSession, data: MediaCollectionIn) -> MediaCollectionOut:
    entity = await create_entity(
        session,
        type=MediaCollection.ENTITY_TYPE,
        title=data.title.strip(),
        search_text=data.description or "",
    )
    collection = MediaCollection(
        id=entity.id,
        description=data.description,
        color=data.color,
        position=data.position,
    )
    session.add(collection)
    await log_event(
        session,
        verb="media.collection_created",
        entity_id=collection.id,
        entity_type="media_collection",
        payload={"title": entity.title},
    )
    await session.commit()
    return _to_collection_out(collection, entity.title)


async def update_collection(
    session: AsyncSession, collection_id: uuid.UUID, data: MediaCollectionUpdate
) -> MediaCollectionOut | None:
    collection = await session.get(MediaCollection, collection_id)
    entity = await session.get(Entity, collection_id)
    if collection is None or entity is None:
        return None
    changes = data.model_dump(exclude_unset=True)
    title = changes.pop("title", None)
    for key, value in changes.items():
        setattr(collection, key, value)
    await touch_entity(
        session,
        collection_id,
        title=title.strip() if title else None,
        search_text=collection.description or "",
    )
    await log_event(
        session,
        verb="media.collection_updated",
        entity_id=collection_id,
        entity_type="media_collection",
        payload={"title": title or entity.title, "changes": list(changes)},
    )
    await session.commit()
    return _to_collection_out(collection, title or entity.title)


async def delete_collection(session: AsyncSession, collection_id: uuid.UUID) -> bool:
    collection = await session.get(MediaCollection, collection_id)
    entity = await session.get(Entity, collection_id)
    if collection is None or entity is None:
        return False
    await log_event(
        session,
        verb="media.collection_deleted",
        entity_id=collection_id,
        entity_type="media_collection",
        payload={"collection_id": str(collection_id), "title": entity.title},
    )
    await session.flush()
    await delete_entity(session, collection_id)
    await session.commit()
    return True


async def add_collection_item(
    session: AsyncSession, collection_id: uuid.UUID, item_id: uuid.UUID
) -> bool | None:
    """Uyeligi ekler: None=kayit yok, True=eklendi, False=zaten uye.

    On kontrol YOK: es zamanli iki ekleme de "yok" gorse bile karari
    `link_uniq` kisiti verir; kaybeden taraf IntegrityError ile False doner
    (onceden iki cagri da True donuyordu).
    """
    collection = await session.get(MediaCollection, collection_id)
    item = await session.get(MediaItem, item_id)
    if collection is None or item is None:
        return None
    session.add(
        Link(
            from_id=collection_id,
            to_id=item_id,
            relation=MEDIA_COLLECTION_ITEM_RELATION,
        )
    )
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        return False
    await log_event(
        session,
        verb="media.collection_item_added",
        entity_id=item_id,
        entity_type="media_item",
        payload={"collection_id": str(collection_id)},
    )
    await session.commit()
    return True


async def remove_collection_item(
    session: AsyncSession, collection_id: uuid.UUID, item_id: uuid.UUID
) -> bool | None:
    if await session.get(MediaCollection, collection_id) is None:
        return None
    if await session.get(MediaItem, item_id) is None:
        return None
    exists = (
        await session.execute(
            select(Link.id).where(
                Link.from_id == collection_id,
                Link.to_id == item_id,
                Link.relation == MEDIA_COLLECTION_ITEM_RELATION,
            )
        )
    ).scalar_one_or_none()
    if exists is not None:
        await unlink(session, collection_id, item_id, MEDIA_COLLECTION_ITEM_RELATION)
        await log_event(
            session,
            verb="media.collection_item_removed",
            entity_id=item_id,
            entity_type="media_item",
            payload={"collection_id": str(collection_id)},
        )
        await session.commit()
        return True
    return False
