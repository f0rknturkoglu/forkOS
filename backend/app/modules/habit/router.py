from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.habit import service
from app.modules.habit.schemas import HabitCheck, HabitGridEntry, HabitIn, HabitOut, HabitUpdate

router = APIRouter(tags=["habit"])


@router.get("/habits", response_model=list[HabitOut])
async def list_habits(active: bool | None = True,
                      session: AsyncSession = Depends(get_session)):
    return await service.list_habits(session, active)


@router.post("/habits", response_model=HabitOut, status_code=201)
async def create_habit(body: HabitIn, session: AsyncSession = Depends(get_session)):
    try:
        return await service.create(session, body)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.patch("/habits/{habit_id}", response_model=HabitOut)
async def update_habit(habit_id: uuid.UUID, body: HabitUpdate,
                       session: AsyncSession = Depends(get_session)):
    result = await service.update(session, habit_id, body)
    if result is None:
        raise HTTPException(404, "habit bulunamadi")
    return result


@router.post("/habits/{habit_id}/check", response_model=HabitOut)
async def check_habit(habit_id: uuid.UUID, body: HabitCheck,
                      session: AsyncSession = Depends(get_session)):
    result = await service.check(session, habit_id, body)
    if result is None:
        raise HTTPException(404, "habit bulunamadi")
    return result


@router.get("/habits/grid", response_model=list[HabitGridEntry])
async def habit_grid(weeks: int = Query(8, ge=1, le=52),
                     session: AsyncSession = Depends(get_session)):
    return await service.grid(session, weeks)
