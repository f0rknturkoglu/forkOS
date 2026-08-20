"""Entity'ler arasi iliski."""
from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity, Link


async def link(
    session: AsyncSession, from_id: uuid.UUID, to_id: uuid.UUID,
    relation: str = "related",
) -> None:
    if from_id == to_id:
        return
    stmt = insert(Link).values(from_id=from_id, to_id=to_id, relation=relation)
    await session.execute(stmt.on_conflict_do_nothing(constraint="link_uniq"))


async def unlink(
    session: AsyncSession, from_id: uuid.UUID, to_id: uuid.UUID,
    relation: str = "related",
) -> None:
    row = (await session.execute(
        select(Link).where(Link.from_id == from_id, Link.to_id == to_id,
                           Link.relation == relation))).scalar_one_or_none()
    if row is not None:
        await session.delete(row)


async def related(session: AsyncSession, entity_id: uuid.UUID) -> list[Entity]:
    """Yon fark etmeksizin bagli tum entity'ler."""
    links = (await session.execute(
        select(Link).where(or_(Link.from_id == entity_id, Link.to_id == entity_id))
    )).scalars()
    other_ids = {lk.to_id if lk.from_id == entity_id else lk.from_id for lk in links}
    if not other_ids:
        return []
    return list((await session.execute(
        select(Entity).where(Entity.id.in_(other_ids)))).scalars())
