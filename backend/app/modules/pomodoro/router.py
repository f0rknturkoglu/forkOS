from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.pomodoro import service
from app.modules.pomodoro.schemas import (
    ContextOut,
    PomodoroAnalytics,
    PomodoroManual,
    PomodoroOut,
    PomodoroStart,
    PomodoroStats,
    PomodoroStop,
)

router = APIRouter(tags=["pomodoro"])


@router.post("/pomodoro/start", response_model=PomodoroOut, status_code=201)
async def start(body: PomodoroStart, session: AsyncSession = Depends(get_session)):
    try:
        return await service.start(session, body)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/pomodoro/{pomo_id}/stop", response_model=PomodoroOut)
async def stop(
    pomo_id: uuid.UUID, body: PomodoroStop, session: AsyncSession = Depends(get_session)
):
    result = await service.stop(session, pomo_id, body.interrupted)
    if result is None:
        raise HTTPException(404, "pomodoro bulunamadi")
    return result


@router.get("/pomodoro/contexts", response_model=list[ContextOut])
async def contexts(
    q: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    """Odak seansina baglam olabilecek kayitlar (gorev, konu, kaynak...)."""
    return await service.contexts(session, q)


@router.get("/pomodoro/active", response_model=PomodoroOut | None)
async def active(session: AsyncSession = Depends(get_session)):
    return await service.active(session)


@router.get("/pomodoro/stats", response_model=PomodoroStats)
async def stats(
    range: str = Query("week", pattern="^(day|week|month)$"),
    session: AsyncSession = Depends(get_session),
):
    return await service.stats(session, range)


@router.get("/pomodoro/analytics", response_model=PomodoroAnalytics)
async def analytics(
    range: str = Query("week", pattern="^(week|month|all)$"),
    session: AsyncSession = Depends(get_session),
):
    return await service.analytics(session, range)


@router.post("/pomodoro/{pomo_id}/pause", response_model=PomodoroOut)
async def pause(pomo_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    result = await service.pause(session, pomo_id)
    if result is None:
        raise HTTPException(404, "pomodoro bulunamadi")
    return result


@router.post("/pomodoro/{pomo_id}/resume", response_model=PomodoroOut)
async def resume(pomo_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    result = await service.resume(session, pomo_id)
    if result is None:
        raise HTTPException(404, "pomodoro bulunamadi")
    return result


@router.post("/pomodoro", response_model=PomodoroOut, status_code=201)
async def add_manual(body: PomodoroManual, session: AsyncSession = Depends(get_session)):
    """Sayac calistirilmadan yapilan isi gecmise isler."""
    try:
        return await service.add_manual(session, body)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.delete("/pomodoro/{pomo_id}", status_code=204)
async def delete(pomo_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    try:
        if not await service.delete(session, pomo_id):
            raise HTTPException(404, "pomodoro bulunamadi")
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/pomodoro/sessions", response_model=list[PomodoroOut])
async def sessions(
    limit: int = Query(20, ge=1, le=200), offset: int = Query(0, ge=0), session: AsyncSession = Depends(get_session)
):
    return await service.recent(session, limit=limit, offset=offset)


@router.put("/pomodoro/{pomo_id}", response_model=PomodoroOut)
async def update(pomo_id: uuid.UUID, body: PomodoroManual, session: AsyncSession = Depends(get_session)):
    try:
        result = await service.update(session, pomo_id, body)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if result is None:
        raise HTTPException(404, "pomodoro bulunamadi")
    return result
