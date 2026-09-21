"""H7 karar/yürütme uçları — inceleme, karar ve sınırlı yürütme.

Karar uçları canonical mutasyon YAPMAZ; yalnızca plan durumunu değiştirir.
Gerçek mutasyon yalnızca `execute` sırasında ve H1 üzerinden olur.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.execution import service
from app.modules.execution.models import MAX_LIST_LIMIT
from app.modules.execution.state import TransitionError

router = APIRouter()


def _error(exc: Exception) -> HTTPException:
    if isinstance(exc, (service.ExecutionPlanError, TransitionError)):
        code = exc.code
    else:
        code = "EXECUTION_ERROR"
    status = 404 if code in {"PLAN_NOT_FOUND"} else 409 if "EXECUTING" in code else 422
    return HTTPException(status_code=status, detail=str(exc))


class DecisionIn(BaseModel):
    """Karar gövdesi: revizyon (isteğe bağlı, eskimiş onayı yakalar)."""

    revision: str | None = Field(default=None, max_length=80)


class RespondIn(BaseModel):
    answers: dict = Field(default_factory=dict)


@router.get("/execution/plans")
async def list_plans(
    states: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=20, ge=1, le=MAX_LIST_LIMIT),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    selected = [item.strip() for item in states.split(",") if item.strip()] if states else None
    return await service.list_plans(session, states=selected, limit=limit)


@router.get("/execution/plans/{plan_row_id}")
async def get_plan(plan_row_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    try:
        return await service.get_plan(session, plan_row_id)
    except service.ExecutionPlanError as exc:
        raise _error(exc) from exc


@router.post("/execution/plans/{plan_row_id}/approve")
async def approve(
    plan_row_id: int, data: DecisionIn, session: AsyncSession = Depends(get_session)
) -> dict:
    try:
        plan = await service.approve(session, plan_row_id=plan_row_id, revision=data.revision)
    except (service.ExecutionPlanError, TransitionError) as exc:
        raise _error(exc) from exc
    return await service.get_plan(session, plan.id)


@router.post("/execution/plans/{plan_row_id}/reject")
async def reject(
    plan_row_id: int, data: DecisionIn, session: AsyncSession = Depends(get_session)
) -> dict:
    try:
        plan = await service.reject(session, plan_row_id=plan_row_id)
    except (service.ExecutionPlanError, TransitionError) as exc:
        raise _error(exc) from exc
    return await service.get_plan(session, plan.id)


@router.post("/execution/plans/{plan_row_id}/respond")
async def respond(
    plan_row_id: int, data: RespondIn, session: AsyncSession = Depends(get_session)
) -> dict:
    try:
        plan = await service.respond(session, plan_row_id=plan_row_id, answers=data.answers)
    except (service.ExecutionPlanError, TransitionError) as exc:
        raise _error(exc) from exc
    return await service.get_plan(session, plan.id)


@router.post("/execution/plans/{plan_row_id}/cancel")
async def cancel(
    plan_row_id: int, data: DecisionIn, session: AsyncSession = Depends(get_session)
) -> dict:
    try:
        plan = await service.cancel(session, plan_row_id=plan_row_id)
    except (service.ExecutionPlanError, TransitionError) as exc:
        raise _error(exc) from exc
    return await service.get_plan(session, plan.id)


@router.post("/execution/plans/{plan_row_id}/recover")
async def recover(
    plan_row_id: int, data: DecisionIn, session: AsyncSession = Depends(get_session)
) -> dict:
    """Çökmüş yürütmeyi kurtarır; canlı yürütücü DEVRALINMAZ."""
    try:
        plan, outcome = await service.recover(session, plan_row_id=plan_row_id)
    except (service.ExecutionPlanError, TransitionError) as exc:
        raise _error(exc) from exc
    view = await service.get_plan(session, plan.id)
    view["final_status"] = outcome.final_status
    return view


@router.post("/execution/plans/{plan_row_id}/execute")
async def execute(
    plan_row_id: int, data: DecisionIn, session: AsyncSession = Depends(get_session)
) -> dict:
    try:
        plan, outcome = await service.execute(
            session, plan_row_id=plan_row_id, revision=data.revision
        )
    except (service.ExecutionPlanError, TransitionError) as exc:
        raise _error(exc) from exc
    view = await service.get_plan(session, plan.id)
    view["final_status"] = outcome.final_status
    return view
