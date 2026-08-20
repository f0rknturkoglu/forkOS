"""Activity log. Append-only."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Event


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
    session: AsyncSession, *, limit: int = 50,
    since: datetime | None = None, verbs: list[str] | None = None,
) -> list[Event]:
    stmt = select(Event).order_by(Event.occurred_at.desc()).limit(limit)
    if since is not None:
        stmt = stmt.where(Event.occurred_at >= since)
    if verbs:
        stmt = stmt.where(Event.verb.in_(verbs))
    return list((await session.execute(stmt)).scalars())
