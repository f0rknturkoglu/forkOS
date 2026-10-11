from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.integrations.google_router import router as google_router
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


def _google_error(exc: httpx.HTTPStatusError) -> str:
    """Google'in kendi aciklamasini yuzeye cikar.

    Aksi halde arayuze "Internal Server Error" dusuyor ve asil sebep
    (ornegin Cloud projesinde Calendar API'nin kapali olmasi) log'da
    gomulu kaliyordu.
    """
    try:
        detail = exc.response.json()["error"]["message"]
    except (ValueError, KeyError, TypeError):
        detail = exc.response.text[:300] or exc.response.reason_phrase
    return f"Google Takvim {exc.response.status_code}: {detail}"


@router.post("/calendar/sync")
async def sync_calendar(session: AsyncSession = Depends(get_session)):
    try:
        return {"synced": await service.sync_google(session)}
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, _google_error(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"Google Takvim'e ulasilamadi: {exc}") from exc


@router.post("/plan/{slot_id}/push")
async def push_plan(slot_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    try:
        result = await service.push_slot(session, slot_id)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, _google_error(exc)) from exc
    if result is None:
        raise HTTPException(404, "plan slot bulunamadı")
    return result


# Calendar retains independent Google OAuth; Drive scopes and clients are retired.

router.include_router(google_router)
