"""Canonical work completion, separate from outcome measurements."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select

from app.core.events import log_event
from app.core.links import link
from app.core.models import Entity, Link
from app.modules.goal.models import Goal, GoalMilestone
from app.modules.learning.models import StudyTopic
from app.modules.todo.models import Todo


class WorkAction(BaseModel):
    id: UUID
    type: Literal["todo", "study_topic"]
    title: str
    completed: bool
    milestone_ids: list[UUID] = Field(default_factory=list)


class WorkMilestone(BaseModel):
    id: UUID
    title: str
    manual_completed: bool
    completed: bool
    progress_percent: int
    action_ids: list[UUID] = Field(default_factory=list)


class GoalWork(BaseModel):
    progress_percent: int | None = None
    completed_count: int = 0
    total_count: int = 0
    milestones: list[WorkMilestone] = Field(default_factory=list)
    actions: list[WorkAction] = Field(default_factory=list)
    truncated: bool = False


class GoalActionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client_uuid: UUID
    kind: Literal["todo", "study_topic"]
    milestone_id: UUID
    area_id: UUID | None = None
    new_area_title: str | None = Field(default=None, min_length=1, max_length=100)
    plan_day: date | None = None

    @field_validator("new_area_title")
    @classmethod
    def area_title(cls, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Alan adı gerekli")
        return value

    @model_validator(mode="after")
    def destination(self):
        if self.kind == "study_topic" and bool(self.area_id) == bool(self.new_area_title):
            raise ValueError("Öğrenme alanı seçilmeli")
        if (
            self.kind == "todo"
            and (self.area_id or self.new_area_title)
            or self.kind == "study_topic"
            and self.plan_day
        ):
            raise ValueError("Seçilen türle uyumsuz alan")
        return self


class GoalActionOut(BaseModel):
    id: UUID
    type: Literal["todo", "study_topic"]
    title: str


async def load_work(db, goals, *, scope=None) -> dict[UUID, GoalWork]:
    owners = {g.id: g.id for g in goals}
    milestone_owner = {m.id: g.id for g in goals for m in g.milestones}
    owners.update(milestone_owner)
    if scope is None:
        from app.modules.goal.contributions import current_scope

        scope = await current_scope(db, [g.id for g in goals], milestone_owner)
    links = list(
        await db.scalars(
            select(Link)
            .where(
                Link.to_id.in_(owners),
                Link.relation.in_(["advances_goal", "advances_goal_milestone"]),
            )
            .order_by(Link.from_id, Link.to_id)
            .limit(5001)
        )
    )
    truncated = len(links) > 5000 or scope.truncated
    links = links[:5000]
    ids = {row.from_id for row in links}
    entities = {
        e.id: e
        for e in await db.scalars(
            select(Entity).where(
                Entity.id.in_(ids),
                Entity.type.in_(["todo", "study_topic"]),
                Entity.archived_at.is_(None),
            )
        )
    }
    todos = {r.id: r for r in await db.scalars(select(Todo).where(Todo.id.in_(entities)))}
    topics = {
        r.id: r for r in await db.scalars(select(StudyTopic).where(StudyTopic.id.in_(entities)))
    }
    by_goal = defaultdict(dict)
    for row in links:
        if not scope.allows(row.from_id, row.to_id):
            continue
        entity = entities.get(row.from_id)
        if entity is None or entity.id not in todos and entity.id not in topics:
            continue
        if row.to_id in milestone_owner and row.relation != "advances_goal_milestone":
            continue
        if row.to_id not in milestone_owner and row.relation != "advances_goal":
            continue
        gid = owners[row.to_id]
        action = by_goal[gid].setdefault(
            entity.id,
            WorkAction(
                id=entity.id,
                type=entity.type,
                title=entity.title,
                completed=(todos.get(entity.id) or topics.get(entity.id)).status == "done",
            ),
        )
        if row.to_id in milestone_owner and row.to_id not in action.milestone_ids:
            action.milestone_ids.append(row.to_id)
    result = {}
    for goal in goals:
        actions = list(by_goal[goal.id].values())
        steps = []
        fractions = []
        for milestone in goal.milestones:
            pair = (milestone.id, goal.id)
            if (
                pair in scope.declared
                and pair not in scope.active
                and not any(milestone.id in a.milestone_ids for a in actions)
            ):
                continue
            children = [a for a in actions if milestone.id in a.milestone_ids]
            manual = bool(milestone.completed_at)
            ratio = (
                1.0
                if manual
                else sum(a.completed for a in children) / len(children)
                if children
                else 0.0
            )
            fractions.append(ratio)
            steps.append(
                WorkMilestone(
                    id=milestone.id,
                    title=milestone.title,
                    manual_completed=manual,
                    completed=manual or not truncated and ratio == 1,
                    progress_percent=round(ratio * 100),
                    action_ids=[a.id for a in children],
                )
            )
        fractions.extend(float(a.completed) for a in actions if not a.milestone_ids)
        result[goal.id] = GoalWork(
            progress_percent=round(sum(fractions) / len(fractions) * 100)
            if fractions and not truncated
            else None,
            completed_count=sum(r == 1 for r in fractions),
            total_count=len(fractions),
            milestones=steps,
            actions=actions,
            truncated=truncated,
        )
    return result


async def create_action(db, goal_id, data):
    from app.modules.bookmark.receipts import capture_once
    from app.modules.learning import service as learning
    from app.modules.learning.schemas import AreaIn, TopicIn
    from app.modules.todo import service as todos
    from app.modules.todo.schemas import TodoIn

    goal = await db.get(Goal, goal_id)
    entity = await db.get(Entity, goal_id)
    if not goal or not entity or entity.archived_at:
        raise HTTPException(404, "Hedef bulunamadı")

    async def write():
        # Lock the existing milestone so two independent clicks cannot create duplicate conversions.
        milestone = await db.scalar(
            select(GoalMilestone)
            .where(
                GoalMilestone.id == data.milestone_id,
                GoalMilestone.goal_id == goal_id,
            )
            .with_for_update()
        )
        if not milestone:
            raise HTTPException(404, "Hedef adımı bulunamadı")
        existing = await db.scalar(
            select(Entity)
            .join(Link, Link.from_id == Entity.id)
            .where(
                Link.to_id == milestone.id,
                Link.relation == "advances_goal_milestone",
                Entity.type == data.kind,
                Entity.archived_at.is_(None),
            )
            .order_by(Entity.created_at)
            .limit(1)
        )
        if existing:
            return {"id": str(existing.id), "type": existing.type, "title": existing.title}
        title = (await db.get(Entity, milestone.id)).title
        if data.kind == "todo":
            item = await todos.create(db, TodoIn(title=title, plan_day=data.plan_day), commit=False)
            identity = item.id
        else:
            try:
                area_id = data.area_id
                if data.new_area_title:
                    area = await learning.create_area(
                        db, AreaIn(title=data.new_area_title), commit=False
                    )
                    area_id = area["id"]
                item = await learning.create_topic(
                    db, TopicIn(title=title, area_id=area_id), commit=False
                )
            except learning.LearningCommandError as exc:
                raise HTTPException(422, str(exc)) from exc
            identity = item["id"]
        await link(db, identity, milestone.id, "advances_goal_milestone")
        await log_event(
            db,
            verb="link.created",
            entity_id=identity,
            payload={"to_id": str(milestone.id), "relation": "advances_goal_milestone"},
        )
        return {"id": str(identity), "type": data.kind, "title": title}

    result, _ = await capture_once(db, data, f"goal-action:{goal_id}", write)
    return GoalActionOut.model_validate(result)


def feedback_context(work):
    result = work.model_dump(mode="json")
    actions = result["actions"]
    result["actions"] = [a for a in actions if a["completed"]][:20] + [
        a for a in actions if not a["completed"]
    ][:20]
    result["milestones"] = result["milestones"][:20]
    result["details_truncated"] = len(actions) > 40 or len(work.milestones) > 20
    return result
