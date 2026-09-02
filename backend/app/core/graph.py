"""Bilgi grafi: entity'ler dugum, link'ler kenar.

Ayri bir graf deposu YOKTUR -- `link` tablosu zaten grafin kendisidir. Not
govdesindeki [[wikilink]]'ler `mentions` olarak buraya dusuyor (core/refs.py),
elle kurulan iliskiler de ayni tabloda. Bu uc ikisini birlikte dondurur.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity, Link

#: Tek seferde donen dugum tavani -- yerel makinede cizim maliyeti sinirli kalsin.
MAX_NODES = 400


async def _neighbours(session: AsyncSession, ids: set[uuid.UUID]) -> list[Link]:
    if not ids:
        return []
    return list(
        (
            await session.execute(
                select(Link).where(or_(Link.from_id.in_(ids), Link.to_id.in_(ids)))
            )
        ).scalars()
    )


async def build(
    session: AsyncSession,
    *,
    focus: uuid.UUID | None = None,
    depth: int = 2,
    limit: int = MAX_NODES,
) -> dict:
    """focus verilirse o dugumden `depth` adim genisler; yoksa tum graf.

    Genel gorunumde baglantisiz entity'ler yer almaz; tek istisna kisisel
    notlardir. Not, daha wikilink eklenmeden de bilgi haritasinda gorunur.
    """
    limit = max(1, min(limit, MAX_NODES))
    edges: dict[tuple[uuid.UUID, uuid.UUID, str], Link] = {}

    if focus is None:
        rows = list((await session.execute(select(Link).limit(limit * 4))).scalars())
        for row in rows:
            edges[(row.from_id, row.to_id, row.relation)] = row
        node_ids = {i for edge in edges for i in (edge[0], edge[1])}
        remaining = max(0, limit - len(node_ids))
        if remaining:
            note_ids = (
                await session.execute(
                    select(Entity.id)
                    .where(Entity.type == "note", Entity.archived_at.is_(None))
                    .order_by(Entity.updated_at.desc())
                    .limit(remaining)
                )
            ).scalars()
            node_ids.update(note_ids)
    else:
        node_ids = {focus}
        frontier = {focus}
        for _ in range(max(0, depth)):
            links = await _neighbours(session, frontier)
            nxt: set[uuid.UUID] = set()
            for row in links:
                edges[(row.from_id, row.to_id, row.relation)] = row
                for side in (row.from_id, row.to_id):
                    if side not in node_ids:
                        nxt.add(side)
            node_ids |= nxt
            frontier = nxt
            if not frontier or len(node_ids) >= limit:
                break

    node_ids = set(list(node_ids)[:limit])
    edge_rows = [
        {"from": str(f), "to": str(t), "relation": relation}
        for (f, t, relation) in edges
        if f in node_ids and t in node_ids
    ]

    entities = {
        e.id: e
        for e in (
            await session.execute(
                select(Entity).where(Entity.id.in_(node_ids), Entity.archived_at.is_(None))
            )
        ).scalars()
    }
    degree: dict[str, int] = {}
    for edge in edge_rows:
        degree[edge["from"]] = degree.get(edge["from"], 0) + 1
        degree[edge["to"]] = degree.get(edge["to"], 0) + 1

    nodes = [
        {
            "id": str(entity.id),
            "type": entity.type,
            "title": entity.title,
            "degree": degree.get(str(entity.id), 0),
        }
        for entity in entities.values()
    ]
    alive = {node["id"] for node in nodes}
    return {
        "nodes": sorted(nodes, key=lambda n: (-n["degree"], n["title"])),
        "edges": [e for e in edge_rows if e["from"] in alive and e["to"] in alive],
        "focus": str(focus) if focus else None,
    }


async def backlinks(session: AsyncSession, entity_id: uuid.UUID) -> list[dict]:
    """Bu kayda [[...]] ile baglanan entity'ler (ters yon, `mentions`)."""
    rows = (
        await session.execute(
            select(Entity)
            .join(Link, Link.from_id == Entity.id)
            .where(Link.to_id == entity_id, Link.relation == "mentions")
            .where(Entity.archived_at.is_(None))
            .order_by(func.lower(Entity.title))
        )
    ).scalars()
    return [{"id": str(e.id), "type": e.type, "title": e.title} for e in rows]
