"""Global search. Turkce icin FTS + trigram karisimi.

Postgres'te hazir Turkce stemmer YOK -> 'simple' config + immutable_unaccent + pg_trgm.
to_tsvector('turkish', ...) YAZMA -- o config Postgres'te mevcut degil.
"""
from __future__ import annotations

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity

TRIGRAM_THRESHOLD = 0.2


def match_clause(query: str) -> ColumnElement[bool]:
    """Modul liste endpoint'leri de ayni eslesme mantigini kullansin diye ayri.

    FTS tam kelimeyi yakalar, trigram yazim hatasi/ek almis kelimeyi yakalar.
    """
    ts = func.plainto_tsquery("simple", func.immutable_unaccent(query))
    return or_(
        Entity.search_vec.op("@@")(ts),
        func.similarity(Entity.title, query) > TRIGRAM_THRESHOLD,
        Entity.title.ilike(f"%{query}%"),
    )


def rank_expr(query: str):
    return func.similarity(Entity.title, query)


async def search_entities(
    session: AsyncSession, query: str, *,
    types: list[str] | None = None, limit: int = 30,
) -> list[Entity]:
    if not query.strip():
        return []

    stmt = (
        select(Entity)
        .where(Entity.archived_at.is_(None))
        .where(match_clause(query))
        .order_by(rank_expr(query).desc(), Entity.updated_at.desc())
        .limit(limit)
    )
    if types:
        stmt = stmt.where(Entity.type.in_(types))
    return list((await session.execute(stmt)).scalars())
