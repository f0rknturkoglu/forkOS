"""Canonical operational goal commands and reproducible milestone progress."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import create_entity, touch_entity
from app.core.events import log_event
from app.core.models import Entity
from app.integrations.obsidian import semantic_memory as semantic_storage
from app.modules import DeadlineRow
from app.modules.goal.models import Goal, GoalMilestone
from app.modules.goal.schemas import (
    GoalIn,
    GoalMilestoneIn,
    GoalMilestoneOut,
    GoalMilestonePatch,
    GoalOut,
    GoalPatch,
)


def progress(completed: int, total: int) -> int | None:
    return min(100, round(completed * 100 / total)) if total > 0 else None


def _milestone_out(row: GoalMilestone) -> GoalMilestoneOut:
    return GoalMilestoneOut(
        id=row.id,
        goal_id=row.goal_id,
        title=row.title,
        due_at=row.due_at,
        completed_at=row.completed_at,
        position=row.position,
    )


def _goal_out(goal: Goal, entity: Entity, milestones: list[GoalMilestone]) -> GoalOut:
    done = sum(row.completed_at is not None for row in milestones)
    return GoalOut(
        id=goal.id,
        title=entity.title,
        description=goal.description,
        status=goal.status,
        horizon=goal.horizon,
        target_at=goal.target_at,
        position=goal.position,
        source_memory_id=goal.source_memory_id,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        milestones=[_milestone_out(row) for row in milestones],
        milestone_count=len(milestones),
        completed_milestones=done,
        progress_percent=progress(done, len(milestones)),
    )


async def list_goals(session: AsyncSession) -> list[GoalOut]:
    rows = (
        await session.execute(
            select(Goal, Entity)
            .join(Entity, Entity.id == Goal.id)
            .where(Entity.archived_at.is_(None))
            .order_by(Goal.position, Entity.created_at, Goal.id)
        )
    ).all()
    ids = [goal.id for goal, _ in rows]
    children = (
        await session.scalars(
            select(GoalMilestone)
            .where(GoalMilestone.goal_id.in_(ids))
            .order_by(GoalMilestone.position, GoalMilestone.id)
        )
    ).all()
    grouped: dict[uuid.UUID, list[GoalMilestone]] = {}
    for child in children:
        grouped.setdefault(child.goal_id, []).append(child)
    return [_goal_out(goal, entity, grouped.get(goal.id, [])) for goal, entity in rows]


async def get_goal(session: AsyncSession, goal_id: uuid.UUID) -> GoalOut | None:
    row = (
        await session.execute(
            select(Goal, Entity)
            .join(Entity, Entity.id == Goal.id)
            .where(Goal.id == goal_id, Entity.archived_at.is_(None))
        )
    ).first()
    if row is None:
        return None
    children = (
        await session.scalars(
            select(GoalMilestone)
            .where(GoalMilestone.goal_id == goal_id)
            .order_by(GoalMilestone.position, GoalMilestone.id)
        )
    ).all()
    return _goal_out(row[0], row[1], list(children))


def _check_memory(memory_id: str | None) -> None:
    if memory_id is None:
        return
    root = semantic_storage.readable_root()
    if root is None:
        raise ValueError("Semantik hedef kasası erişilemiyor")
    cards = semantic_storage.scan_semantic_cards(root)
    if not any(
        card.card_id == memory_id and card.kind == "goal" and card.effective_status == "active"
        for card in cards
    ):
        raise ValueError("Etkin semantik hedef kartı bulunamadı")


async def create_goal(session: AsyncSession, data: GoalIn, *, commit: bool = True) -> GoalOut:
    _check_memory(data.source_memory_id)
    entity = await create_entity(
        session, type=Goal.ENTITY_TYPE, title=data.title, search_text=data.description or ""
    )
    goal = Goal(id=entity.id, **data.model_dump(exclude={"title"}))
    session.add(goal)
    await log_event(
        session,
        verb="goal.created",
        entity_id=goal.id,
        entity_type=Goal.ENTITY_TYPE,
        payload={"horizon": goal.horizon, "source_memory_id": goal.source_memory_id},
    )
    if commit:
        await session.commit()
    else:
        await session.flush()
    return _goal_out(goal, entity, [])


async def update_goal(
    session: AsyncSession, goal_id: uuid.UUID, data: GoalPatch, *, commit: bool = True
) -> GoalOut | None:
    goal = await session.get(Goal, goal_id)
    if goal is None:
        return None
    values = data.model_dump(exclude_unset=True)
    title = values.pop("title", None)
    for key, value in values.items():
        setattr(goal, key, value)
    await touch_entity(session, goal.id, title=title, search_text=goal.description or "")
    await log_event(
        session,
        verb="goal.updated",
        entity_id=goal.id,
        entity_type=Goal.ENTITY_TYPE,
        payload={"fields": sorted(data.model_fields_set)},
    )
    if commit:
        await session.commit()
    else:
        await session.flush()
    return await get_goal(session, goal_id)


async def add_goal_milestone(
    session: AsyncSession, goal_id: uuid.UUID, data: GoalMilestoneIn, *, commit: bool = True
) -> GoalMilestoneOut | None:
    if await session.get(Goal, goal_id) is None:
        return None
    entity = await create_entity(
        session, type=GoalMilestone.ENTITY_TYPE, title=data.title, search_text=data.title
    )
    item = GoalMilestone(
        id=entity.id,
        goal_id=goal_id,
        title=data.title,
        due_at=data.due_at,
        position=data.position,
    )
    session.add(item)
    await log_event(
        session,
        verb="goal.milestone_added",
        entity_id=goal_id,
        entity_type=Goal.ENTITY_TYPE,
        payload={"milestone_id": str(item.id), "title": item.title},
    )
    if commit:
        await session.commit()
    else:
        await session.flush()
    return _milestone_out(item)


async def update_goal_milestone(
    session: AsyncSession,
    milestone_id: uuid.UUID,
    data: GoalMilestonePatch,
    *,
    commit: bool = True,
) -> GoalMilestoneOut | None:
    item = await session.get(GoalMilestone, milestone_id)
    if item is None:
        return None
    values = data.model_dump(exclude_unset=True)
    title = values.pop("title", None)
    completed = values.pop("completed", None)
    for key, value in values.items():
        setattr(item, key, value)
    if title is not None:
        item.title = title
    if completed is not None:
        item.completed_at = datetime.now(UTC) if completed else None
    await touch_entity(session, item.id, title=title)
    await touch_entity(session, item.goal_id)
    await log_event(
        session,
        verb="goal.milestone_updated",
        entity_id=item.goal_id,
        entity_type=Goal.ENTITY_TYPE,
        payload={"milestone_id": str(item.id), "fields": sorted(data.model_fields_set)},
    )
    if commit:
        await session.commit()
    else:
        await session.flush()
    return _milestone_out(item)


async def deadline_provider(session: AsyncSession) -> list[DeadlineRow]:
    goals = (
        await session.execute(
            select(Goal.id, Entity.title, Goal.target_at)
            .join(Entity, Entity.id == Goal.id)
            .where(
                Goal.status == "active", Goal.target_at.is_not(None), Entity.archived_at.is_(None)
            )
        )
    ).all()
    milestones = (
        await session.execute(
            select(GoalMilestone.id, GoalMilestone.title, GoalMilestone.due_at)
            .join(Goal, Goal.id == GoalMilestone.goal_id)
            .where(
                Goal.status == "active",
                GoalMilestone.due_at.is_not(None),
                GoalMilestone.completed_at.is_(None),
            )
        )
    ).all()
    return [
        DeadlineRow(entity_id=id_, type="goal", title=title, due_at=due, module="goal")
        for id_, title, due in goals
    ] + [
        DeadlineRow(entity_id=id_, type="goal_milestone", title=title, due_at=due, module="goal")
        for id_, title, due in milestones
    ]
