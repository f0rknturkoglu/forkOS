from __future__ import annotations

import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import local_today
from app.db import get_session
from app.modules.todo import service
from app.modules.todo.schemas import (
    PlanSlotIn,
    PlanSlotOut,
    PlanSlotUpdate,
    TodoIn,
    TodoOut,
    TodoUpdate,
)

router = APIRouter(tags=["todo"])


@router.get("/todos", response_model=list[TodoOut])
async def list_todos(
    status: str | None = None,
    due_before: datetime | None = None,
    priority: int | None = None,
    include_undated: bool = False,
    completed_after: datetime | None = None,
    recur_only: bool = False,
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
):
    return await service.list_todos(
        session,
        status=status,
        due_before=due_before,
        priority=priority,
        include_undated=include_undated,
        completed_after=completed_after,
        recur_only=recur_only,
        limit=limit,
    )


@router.post("/todos", response_model=TodoOut, status_code=201)
async def create_todo(
    body: TodoIn, response: Response, session: AsyncSession = Depends(get_session)
):
    try:
        result = await service.create(session, body)
        if session.info.pop("capture_replayed", False):
            response.headers["Idempotency-Replayed"] = "true"
        return result
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.patch("/todos/{todo_id}", response_model=TodoOut)
async def update_todo(
    todo_id: uuid.UUID, body: TodoUpdate, session: AsyncSession = Depends(get_session)
):
    try:
        result = await service.update(session, todo_id, body)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if result is None:
        raise HTTPException(404, "todo bulunamadi")
    return result


@router.post("/todos/{todo_id}/complete", response_model=TodoOut)
async def complete_todo(todo_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    result = await service.complete(session, todo_id)
    if result is None:
        raise HTTPException(404, "todo bulunamadi")
    return result


@router.delete("/todos/{todo_id}", status_code=204)
async def delete_todo(todo_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    if not await service.delete(session, todo_id):
        raise HTTPException(404, "todo bulunamadi")


class CarryOverIn(BaseModel):
    day: date
    target: date


@router.post("/plan/carry-over")
async def carry_over(body: CarryOverIn, session: AsyncSession = Depends(get_session)):
    """Bir gunun acik todo slotlarini hedef gune tasir (Faz 33) -- tek
    transaction, atomik; tamamlanmis/dropped gorev slotlari tasinmaz."""
    if body.target <= body.day:
        raise HTTPException(400, "hedef gun kaynak gunden sonra olmali")
    moved = await service.carry_over(session, body.day, body.target)
    return {"moved": moved}


@router.get("/plan", response_model=list[PlanSlotOut])
async def get_plan(
    week: date = Query(default_factory=local_today), session: AsyncSession = Depends(get_session)
):
    return await service.list_plan(session, week)


@router.post("/plan", response_model=PlanSlotOut, status_code=201)
async def create_slot(body: PlanSlotIn, session: AsyncSession = Depends(get_session)):
    try:
        return await service.schedule(session, body)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.patch("/plan/{slot_id}", response_model=PlanSlotOut)
async def update_slot(
    slot_id: uuid.UUID, body: PlanSlotUpdate, session: AsyncSession = Depends(get_session)
):
    result = await service.update_slot(session, slot_id, body)
    if result is None:
        raise HTTPException(404, "plan slot bulunamadi")
    return result


@router.delete("/plan/{slot_id}", status_code=204)
async def delete_slot(slot_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    if not await service.delete_slot(session, slot_id):
        raise HTTPException(404, "plan slot bulunamadi")
