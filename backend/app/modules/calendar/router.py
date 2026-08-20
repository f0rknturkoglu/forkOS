from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.calendar import service

router = APIRouter(tags=["calendar"])


@router.get("/calendar/events")
async def calendar_events(
    from_at: datetime = Query(default_factory=lambda: datetime.now(UTC), alias="from"),
    to_at: datetime = Query(
        default_factory=lambda: datetime.now(UTC) + timedelta(days=7), alias="to"
    ),
    session: AsyncSession = Depends(get_session),
):
    return await service.events(session, from_at, to_at)


@router.post("/calendar/sync")
async def sync_calendar(session: AsyncSession = Depends(get_session)):
    try:
        return {"synced": await service.sync_google(session)}
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.post("/plan/{slot_id}/push")
async def push_plan(slot_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    try:
        result = await service.push_slot(session, slot_id)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    if result is None:
        raise HTTPException(404, "plan slot bulunamadı")
    return result
