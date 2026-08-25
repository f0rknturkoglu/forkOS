"""Medya koleksiyon CRUD ve koleksiyon-item baglari."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import create_entity, delete_entity, touch_entity
from app.core.events import log_event
from app.core.links import link, unlink
from app.core.models import Entity, Link
from app.modules.media.models import (
    MEDIA_COLLECTION_ITEM_RELATION,
    MediaCollection,
    MediaItem,
)
from app.modules.media.schemas import (
    MediaCollectionIn,
    MediaCollectionOut,
    MediaCollectionUpdate,
)


def _to_collection_out(collection: MediaCollection, title: str) -> MediaCollectionOut:
    return MediaCollectionOut(
        id=collection.id,
        title=title,
        description=collection.description,
        color=collection.color,
        position=collection.position,
        created_at=collection.created_at,
        updated_at=collection.updated_at,
    )


async def list_collections(session: AsyncSession) -> list[MediaCollectionOut]:
    rows = (
        await session.execute(
            select(MediaCollection, Entity.title)
            .join(Entity, Entity.id == MediaCollection.id)
            .order_by(MediaCollection.position, Entity.title)
        )
    ).all()
    return [_to_collection_out(*row) for row in rows]


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
    collection = await session.get(MediaCollection, collection_id)
    item = await session.get(MediaItem, item_id)
    if collection is None or item is None:
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
    if exists is None:
        await link(session, collection_id, item_id, MEDIA_COLLECTION_ITEM_RELATION)
        await log_event(
            session,
            verb="media.collection_item_added",
            entity_id=item_id,
            entity_type="media_item",
            payload={"collection_id": str(collection_id)},
        )
        await session.commit()
        return True
    return False


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
