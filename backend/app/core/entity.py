"""Entity yasam dongusu. Modul servisleri HER ZAMAN bu helper'lari kullanmali."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity


async def create_entity(
    session: AsyncSession, *, type: str, title: str, search_text: str = "",
) -> Entity:
    entity = Entity(type=type, title=title, search_text=search_text)
    session.add(entity)
    await session.flush()          # entity.id lazim, commit degil
    return entity


async def touch_entity(
    session: AsyncSession, entity_id: uuid.UUID, *,
    title: str | None = None, search_text: str | None = None,
) -> None:
    """Modul kaydi degistiginde entity'nin baslik/arama metnini senkron tutar."""
    entity = await session.get(Entity, entity_id)
    if entity is None:
        return
    if title is not None:
        entity.title = title
    if search_text is not None:
        entity.search_text = search_text
    entity.updated_at = func.now()


async def archive_entity(session: AsyncSession, entity_id: uuid.UUID) -> None:
    entity = await session.get(Entity, entity_id)
    if entity is not None:
        entity.archived_at = func.now()


async def restore_entity(session: AsyncSession, entity_id: uuid.UUID) -> None:
    """Arsivlenmis entity'yi tekrar aktif gorunume al."""
    entity = await session.get(Entity, entity_id)
    if entity is not None:
        entity.archived_at = None
        entity.updated_at = func.now()


async def delete_entity(session: AsyncSession, entity_id: uuid.UUID) -> bool:
    """Entity-backed bir nesneyi cascade kurallarini kullanarak kalici sil."""
    entity = await session.get(Entity, entity_id)
    if entity is None:
        return False
    await session.delete(entity)
    return True


async def get_entities(session: AsyncSession, ids: list[uuid.UUID]) -> dict[uuid.UUID, Entity]:
    if not ids:
        return {}
    rows = (await session.execute(select(Entity).where(Entity.id.in_(ids)))).scalars()
    return {e.id: e for e in rows}
