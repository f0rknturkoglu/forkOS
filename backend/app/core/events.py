"""Activity log. Append-only."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Text, cast, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import contributions
from app.core.models import Entity, Event


async def log_event(
    session: AsyncSession, *, verb: str,
    entity_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    payload: dict | None = None,
) -> Event:
    """Ornek: await log_event(s, verb="bookmark.saved", entity_id=b.id,
                              entity_type="bookmark", payload={"collection": "inbox"})"""
    event = Event(verb=verb, entity_id=entity_id, entity_type=entity_type,
                  payload=payload or {})
    session.add(event)
    return event


async def recent_events(
    session: AsyncSession, *, limit: int = 50, offset: int = 0,
    since: datetime | None = None, verbs: list[str] | None = None,
    category: str | None = None, q: str | None = None,
) -> list[Event]:
    """Hareket akisi. Sira deterministik (occurred_at, id) -- offset'le sayfalama
    ayni kaydi iki kez gostermesin.

    `category` emek haritasinin kategorileridir ("read", "task", "focus",
    "routine", "study", "media") + "system": haritada SAYILMAYAN fiiller
    (worker gurultusu). Kategori kumesi tek kaynaktan (contributions) gelir;
    burada ikinci bir liste tutulmaz.
    """
    stmt = select(Event).order_by(Event.occurred_at.desc(), Event.id.desc())
    if since is not None:
        stmt = stmt.where(Event.occurred_at >= since)
    if verbs:
        stmt = stmt.where(Event.verb.in_(verbs))
    if category == "system":
        stmt = stmt.where(Event.verb.not_in(contributions.COUNTED_VERBS))
    elif category in contributions.KINDS:
        stmt = stmt.where(Event.verb.in_(contributions.KINDS[category]))
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Event.verb.ilike(pattern),
                cast(Event.payload, Text).ilike(pattern),
                Entity.title.ilike(pattern),
            )
        ).outerjoin(Entity, Entity.id == Event.entity_id)
    stmt = stmt.offset(max(0, offset)).limit(limit)
    return list((await session.execute(stmt)).scalars())
