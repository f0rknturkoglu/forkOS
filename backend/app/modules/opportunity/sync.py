from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import log_event
from app.core.models import SourceRun, SourceSyncBatch

ACTIVE_STATUSES = ("queued", "running")


def batch_out(batch: SourceSyncBatch) -> dict:
    total = batch.total_sources or 0
    progress = int(batch.completed_sources * 100 / total) if total else 0
    return {
        "id": str(batch.id),
        "status": batch.status,
        "source_ids": batch.source_ids,
        "total_sources": total,
        "completed_sources": batch.completed_sources,
        "ok_sources": batch.ok_sources,
        "empty_sources": batch.empty_sources,
        "error_sources": batch.error_sources,
        "items_found": batch.items_found,
        "progress_pct": progress,
        "created_at": batch.created_at,
        "started_at": batch.started_at,
        "finished_at": batch.finished_at,
    }


async def create_or_extend_batch(
    session: AsyncSession, source_ids: list[str]
) -> tuple[SourceSyncBatch, list[str]]:
    ids = list(dict.fromkeys(source_ids))
    batch = (
        await session.execute(
            select(SourceSyncBatch)
            .where(SourceSyncBatch.status.in_(ACTIVE_STATUSES))
            .order_by(SourceSyncBatch.created_at.desc())
            .limit(1)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if batch is None:
        now = datetime.now(UTC)
        batch = SourceSyncBatch(
            status="running",
            source_ids=ids,
            total_sources=len(ids),
            started_at=now,
        )
        session.add(batch)
        await session.flush()
        await log_event(
            session,
            verb="source_sync.started",
            entity_type="source_sync",
            payload={"batch_id": str(batch.id), "total_sources": len(ids)},
        )
        return batch, ids

    existing = set(batch.source_ids or [])
    added = [source_id for source_id in ids if source_id not in existing]
    if added:
        batch.source_ids = [*(batch.source_ids or []), *added]
        batch.total_sources += len(added)
        await log_event(
            session,
            verb="source_sync.sources_added",
            entity_type="source_sync",
            payload={"batch_id": str(batch.id), "count": len(added)},
        )
    return batch, added


async def finish_batch_source(
    session: AsyncSession,
    batch_id: uuid.UUID,
    *,
    status: str,
    items_found: int = 0,
) -> None:
    batch = (
        await session.execute(
            select(SourceSyncBatch)
            .where(SourceSyncBatch.id == batch_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if batch is None or batch.status not in ACTIVE_STATUSES:
        return
    batch.completed_sources += 1
    batch.items_found += items_found
    if status == "ok":
        batch.ok_sources += 1
    elif status == "empty":
        batch.empty_sources += 1
    else:
        batch.error_sources += 1
    if batch.completed_sources >= batch.total_sources:
        batch.status = "completed_with_errors" if batch.error_sources else "completed"
        batch.finished_at = datetime.now(UTC)
        await log_event(
            session,
            verb="source_sync.completed",
            entity_type="source_sync",
            payload={
                "batch_id": str(batch.id),
                "count": batch.items_found,
                "errors": batch.error_sources,
            },
        )


async def current_status(session: AsyncSession) -> dict:
    last_completed = (
        await session.execute(
            select(SourceSyncBatch)
            .where(~SourceSyncBatch.status.in_(ACTIVE_STATUSES))
            .order_by(SourceSyncBatch.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    batch = (
        await session.execute(
            select(SourceSyncBatch)
            .where(SourceSyncBatch.status.in_(ACTIVE_STATUSES))
            .order_by(SourceSyncBatch.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if batch is None:
        return {
            "active": None,
            "last_completed": batch_out(last_completed) if last_completed else None,
            "sources": [],
            "running": [],
        }
    rows = list(
        (
            await session.execute(
                select(SourceRun)
                .where(SourceRun.batch_id == batch.id)
                .order_by(SourceRun.started_at.desc())
            )
        ).scalars()
    )
    latest: dict[str, SourceRun] = {}
    for row in rows:
        latest.setdefault(row.source, row)
    sources = [
        {
            "source": source_id,
            "status": latest[source_id].status if source_id in latest else "queued",
            "started_at": latest[source_id].started_at if source_id in latest else None,
            "finished_at": latest[source_id].finished_at if source_id in latest else None,
            "items_found": latest[source_id].items_found if source_id in latest else 0,
            "error": latest[source_id].error if source_id in latest else None,
        }
        for source_id in batch.source_ids
    ]
    running = [row for row in sources if row["status"] == "running"]
    return {
        "active": batch_out(batch),
        "last_completed": batch_out(last_completed) if last_completed else None,
        "sources": sources,
        "running": running,
    }


async def history(session: AsyncSession, limit: int = 10) -> list[dict]:
    rows = (
        await session.execute(
            select(SourceSyncBatch)
            .where(~SourceSyncBatch.status.in_(ACTIVE_STATUSES))
            .order_by(SourceSyncBatch.created_at.desc())
            .limit(limit)
        )
    ).scalars()
    return [batch_out(batch) for batch in rows]
