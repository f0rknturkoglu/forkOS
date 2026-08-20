"""Kaynak kosum kaydi (source_run).

Kural 6: her scraper/feed kosusu buraya yazar. Ust uste 3 'empty' -> bildirim.
"Sessiz olum" (feed hala 200 donuyor ama artik item uretmiyor) tek yakalama noktasi burasi.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import log_event
from app.core.models import SourceRun

EMPTY_STREAK_ALERT = 3      # ust uste bu kadar bos kosum -> bildirim
OK = "ok"
EMPTY = "empty"
ERROR = "error"


async def start_run(session: AsyncSession, source: str) -> SourceRun:
    run = SourceRun(source=source, status="running")
    session.add(run)
    await session.flush()
    return run


async def finish_run(
    session: AsyncSession, run: SourceRun, *,
    status: str, items_found: int = 0, error: str | None = None,
) -> None:
    run.status = status
    run.items_found = items_found
    run.error = (error or "")[:2000] or None
    run.finished_at = datetime.now(UTC)


async def last_statuses(session: AsyncSession, source: str, limit: int) -> list[str]:
    return list((await session.execute(
        select(SourceRun.status)
        .where(SourceRun.source == source, SourceRun.status != "running")
        .order_by(SourceRun.started_at.desc())
        .limit(limit)
    )).scalars())


async def check_stalled(session: AsyncSession, source: str, *, label: str = "") -> bool:
    """Son N kosum bos mu? Oyleyse bir kere bildirim event'i uretir.

    Bildirim 'event' tablosuna yazilir; Today/Activity ekrani buradan besleniyor.
    """
    statuses = await last_statuses(session, source, EMPTY_STREAK_ALERT)
    if len(statuses) < EMPTY_STREAK_ALERT or any(s != EMPTY for s in statuses):
        return False
    await log_event(
        session, verb="source.stalled",
        payload={"source": source, "label": label, "streak": EMPTY_STREAK_ALERT,
                 "message": f"{label or source}: ust uste {EMPTY_STREAK_ALERT} kosum bos dondu"},
    )
    return True


async def health(session: AsyncSession, limit: int = 50) -> list[dict]:
    """Her kaynagin son durumu -- Settings/Today icin ozet."""
    newest = (
        select(SourceRun.source, func.max(SourceRun.started_at).label("last_at"))
        .where(SourceRun.status != "running")
        .group_by(SourceRun.source)
        .subquery()
    )
    rows = (await session.execute(
        select(SourceRun)
        .join(newest, (SourceRun.source == newest.c.source)
              & (SourceRun.started_at == newest.c.last_at))
        .order_by(SourceRun.started_at.desc())
        .limit(limit)
    )).scalars()
    return [
        {"source": r.source, "status": r.status, "items_found": r.items_found,
         "error": r.error, "started_at": r.started_at, "finished_at": r.finished_at}
        for r in rows
    ]
