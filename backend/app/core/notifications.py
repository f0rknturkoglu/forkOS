from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Notification


async def notify(
    session: AsyncSession,
    *,
    kind: str,
    title: str,
    body: str | None,
    dedup_key: str,
    entity_id: uuid.UUID | None = None,
    importance: int = 1,
) -> None:
    statement = (
        insert(Notification)
        .values(
            kind=kind,
            title=title,
            body=body,
            entity_id=entity_id,
            importance=importance,
            dedup_key=dedup_key,
            created_at=datetime.now(UTC),
        )
        .on_conflict_do_nothing(index_elements=[Notification.dedup_key])
    )
    await session.execute(statement)
