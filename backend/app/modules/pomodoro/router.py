from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.pomodoro import service
from app.modules.pomodoro.schemas import PomodoroOut, PomodoroStart, PomodoroStats, PomodoroStop

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
async def stop(pomo_id: uuid.UUID, body: PomodoroStop,
               session: AsyncSession = Depends(get_session)):
    result = await service.stop(session, pomo_id, body.interrupted)
    if result is None:
        raise HTTPException(404, "pomodoro bulunamadi")
    return result


@router.get("/pomodoro/active", response_model=PomodoroOut | None)
async def active(session: AsyncSession = Depends(get_session)):
    return await service.active(session)


@router.get("/pomodoro/stats", response_model=PomodoroStats)
async def stats(range: str = Query("week", pattern="^(day|week|month)$"),
                session: AsyncSession = Depends(get_session)):
    return await service.stats(session, range)
