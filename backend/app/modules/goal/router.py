from __future__ import annotations

from enum import IntEnum
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.goal import service, strategy
from app.modules.goal.context_schemas import GoalContextSnapshot, RoadmapOwner
from app.modules.goal.schemas import (
    GoalIn,
    GoalMilestoneIn,
    GoalMilestoneOut,
    GoalMilestonePatch,
    GoalOut,
    GoalPatch,
)
from app.modules.goal.strategy_schemas import (
    KeyResultIn,
    KeyResultOut,
    PillarIn,
    PillarOut,
    PlanIn,
    PlanOut,
    StrategyHistory,
    StrategyOverview,
)
from app.modules.goal.studio_router import router as studio_router
from app.modules.goal.work import GoalActionIn, GoalActionOut, create_action


class StrategyWindow(IntEnum):
    week = 7
    month = 30
    quarter = 90


router = APIRouter(tags=["goals"])
router.include_router(studio_router)


@router.get("/goals/strategy/overview", response_model=StrategyOverview)
async def strategy_overview(
    days: StrategyWindow = StrategyWindow.month, session: AsyncSession = Depends(get_session)
):
    return await strategy.overview(session, days=int(days))


@router.get("/goals/strategy/history", response_model=StrategyHistory)
async def strategy_history(session: AsyncSession = Depends(get_session)):
    return await strategy.history(session)


@router.post("/goals/strategy/plans", response_model=PlanOut, status_code=201)
async def plan_create(body: PlanIn, session: AsyncSession = Depends(get_session)):
    try:
        return await strategy.save_plan(session, body)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.put("/goals/strategy/plans/{plan_id}", response_model=PlanOut)
async def plan_update(plan_id: UUID, body: PlanIn, session: AsyncSession = Depends(get_session)):
    try:
        return await strategy.save_plan(session, body, plan_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/goals/strategy/plans/{plan_id}/pillars", response_model=PillarOut, status_code=201)
async def pillar_create(
    plan_id: UUID, body: PillarIn, session: AsyncSession = Depends(get_session)
):
    try:
        return await strategy.save_pillar(session, plan_id, body)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.put("/goals/strategy/plans/{plan_id}/pillars/{pillar_id}", response_model=PillarOut)
async def pillar_update(
    plan_id: UUID, pillar_id: UUID, body: PillarIn, session: AsyncSession = Depends(get_session)
):
    try:
        return await strategy.save_pillar(session, plan_id, body, pillar_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/goals/{goal_id}/key-results", response_model=KeyResultOut, status_code=201)
async def kr_create(goal_id: UUID, body: KeyResultIn, session: AsyncSession = Depends(get_session)):
    try:
        return await strategy.save_kr(session, goal_id, body)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.put("/goals/{goal_id}/key-results/{kr_id}", response_model=KeyResultOut)
async def kr_update(
    goal_id: UUID, kr_id: UUID, body: KeyResultIn, session: AsyncSession = Depends(get_session)
):
    try:
        return await strategy.save_kr(session, goal_id, body, kr_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


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
    try:
        result = await service.update_goal(session, goal_id, body)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
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


@router.post("/goals/{goal_id}/actions", response_model=GoalActionOut, status_code=201)
async def add_goal_action(
    goal_id: UUID, body: GoalActionIn, session: AsyncSession = Depends(get_session)
):
    return await create_action(session, goal_id, body)


from app.modules.goal.roadmap import RoadmapOut  # noqa: E402
from app.modules.goal.studio_schemas import StudioSessionOut  # noqa: E402


@router.get("/goals/{goal_id}/roadmap", response_model=RoadmapOut)
async def roadmap_read(goal_id: UUID, session: AsyncSession = Depends(get_session)):
    from app.modules.goal.roadmap import read

    try:
        return await read(session, goal_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/goals/roadmap-nodes/{node_id}", response_model=RoadmapOwner)
async def roadmap_owner(node_id: UUID, session: AsyncSession = Depends(get_session)):
    from app.modules.goal.roadmap_models import GoalRoadmapNode

    node = await session.get(GoalRoadmapNode, node_id)
    if not node:
        raise HTTPException(404, "Yol haritası düğümü bulunamadı")
    return {"goal_id": str(node.goal_id), "node_id": str(node.id)}


@router.get("/goals/{goal_id}/workspace", response_model=GoalContextSnapshot)
async def living_workspace(goal_id: UUID, session: AsyncSession = Depends(get_session)):
    from app.modules.goal.context_snapshot import build

    try:
        return await build(session, goal_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/goals/{goal_id}/conversation", response_model=StudioSessionOut)
async def living_conversation(goal_id: UUID, session: AsyncSession = Depends(get_session)):
    from sqlalchemy import func, select

    from app.core.models import Entity
    from app.modules.goal.studio import out
    from app.modules.goal.studio_models import GoalStudioSession

    row = await session.scalar(
        select(GoalStudioSession)
        .join(Entity, Entity.id == GoalStudioSession.id)
        .where(
            func.jsonb_array_length(GoalStudioSession.data["messages"]) > 0,
            GoalStudioSession.data["goal_id"].astext == str(goal_id),
            GoalStudioSession.data["mode"].astext == "living",
        )
        .order_by(Entity.created_at.desc(), GoalStudioSession.id.desc())
        .limit(1)
    )
    if not row:
        raise HTTPException(404, "Henüz görüşme yok")
    return await out(session, row)
