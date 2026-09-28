from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.goal import service
from app.modules.goal.schemas import (
    GoalIn,
    GoalMilestoneIn,
    GoalMilestoneOut,
    GoalMilestonePatch,
    GoalOut,
    GoalPatch,
)

router = APIRouter(tags=["goals"])


@router.get("/goals", response_model=list[GoalOut])
async def goals(session: AsyncSession = Depends(get_session)):
    return await service.list_goals(session)


@router.get("/goals/{goal_id}", response_model=GoalOut)
async def goal(goal_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await service.get_goal(session, goal_id)
    if result is None:
        raise HTTPException(404, "Hedef bulunamadı")
    return result


@router.post("/goals", response_model=GoalOut, status_code=201)
async def create_goal(body: GoalIn, session: AsyncSession = Depends(get_session)):
    try:
        return await service.create_goal(session, body)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.patch("/goals/{goal_id}", response_model=GoalOut)
async def update_goal(goal_id: UUID, body: GoalPatch, session: AsyncSession = Depends(get_session)):
    result = await service.update_goal(session, goal_id, body)
    if result is None:
        raise HTTPException(404, "Hedef bulunamadı")
    return result


@router.post("/goals/{goal_id}/milestones", response_model=GoalMilestoneOut, status_code=201)
async def add_milestone(
    goal_id: UUID, body: GoalMilestoneIn, session: AsyncSession = Depends(get_session)
):
    result = await service.add_goal_milestone(session, goal_id, body)
    if result is None:
        raise HTTPException(404, "Hedef bulunamadı")
    return result


@router.patch("/goal-milestones/{milestone_id}", response_model=GoalMilestoneOut)
async def update_milestone(
    milestone_id: UUID, body: GoalMilestonePatch, session: AsyncSession = Depends(get_session)
):
    result = await service.update_goal_milestone(session, milestone_id, body)
    if result is None:
        raise HTTPException(404, "Hedef kilometre taşı bulunamadı")
    return result
