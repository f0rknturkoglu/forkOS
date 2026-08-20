"""Tag yonetimi. Tag'ler entity'ye baglanir -- modul tablosuna DEGIL.

Boylece bookmark, feed_item, todo... hepsi ayni etiket havuzunu paylasir.
"""
from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import EntityTag, Tag


async def get_or_create(session: AsyncSession, name: str) -> Tag:
    clean = name.strip()
    existing = (await session.execute(
        select(Tag).where(func.lower(Tag.name) == clean.lower())
    )).scalar_one_or_none()
    if existing is not None:
        return existing
    tag = Tag(name=clean)
    session.add(tag)
    await session.flush()
    return tag


async def set_tags(session: AsyncSession, entity_id: uuid.UUID, names: list[str]) -> list[str]:
    """Entity'nin etiketlerini verilen listeyle DEGISTIRIR (idempotent)."""
    clean = [n.strip() for n in names if n and n.strip()]
    await session.execute(delete(EntityTag).where(EntityTag.entity_id == entity_id))
    for name in clean:
        tag = await get_or_create(session, name)
        await session.execute(
            insert(EntityTag).values(entity_id=entity_id, tag_id=tag.id)
            .on_conflict_do_nothing()
        )
    return clean


async def add_tags(session: AsyncSession, entity_id: uuid.UUID, names: list[str]) -> None:
    for name in names:
        if not name or not name.strip():
            continue
        tag = await get_or_create(session, name)
        await session.execute(
            insert(EntityTag).values(entity_id=entity_id, tag_id=tag.id)
            .on_conflict_do_nothing()
        )


async def tags_for(
    session: AsyncSession, entity_ids: list[uuid.UUID],
) -> dict[uuid.UUID, list[str]]:
    """N+1 kacinmak icin toplu okuma. Liste endpoint'leri bunu kullanir."""
    if not entity_ids:
        return {}
    rows = (await session.execute(
        select(EntityTag.entity_id, Tag.name)
        .join(Tag, Tag.id == EntityTag.tag_id)
        .where(EntityTag.entity_id.in_(entity_ids))
        .order_by(Tag.name)
    )).all()
    out: dict[uuid.UUID, list[str]] = {}
    for entity_id, name in rows:
        out.setdefault(entity_id, []).append(name)
    return out


async def entity_ids_with_tag(session: AsyncSession, name: str) -> list[uuid.UUID]:
    return list((await session.execute(
        select(EntityTag.entity_id)
        .join(Tag, Tag.id == EntityTag.tag_id)
        .where(func.lower(Tag.name) == name.strip().lower())
    )).scalars())


async def list_tags(session: AsyncSession) -> list[tuple[str, int]]:
    rows = (await session.execute(
        select(Tag.name, func.count(EntityTag.entity_id))
        .outerjoin(EntityTag, EntityTag.tag_id == Tag.id)
        .group_by(Tag.name)
        .order_by(func.count(EntityTag.entity_id).desc(), Tag.name)
    )).all()
    return [(name, count) for name, count in rows]
