from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import create_entity, touch_entity
from app.core.events import log_event
from app.core.models import Entity, Link
from app.modules.project.models import Milestone, Project
from app.modules.project.schemas import MilestoneIn, MilestonePatch, ProjectIn, ProjectPatch
from app.modules.todo.models import Todo
from app.modules.todo.service import _todo_out


async def project_out(session: AsyncSession, project: Project) -> dict:
    title = (
        await session.execute(select(Entity.title).where(Entity.id == project.id))
    ).scalar_one()
    milestones = list(
        (
            await session.execute(
                select(Milestone)
                .where(Milestone.project_id == project.id)
                .order_by(Milestone.position, Milestone.due_at.asc().nullslast())
            )
        ).scalars()
    )
    return {
        "id": project.id,
        "title": title,
        "status": project.status,
        "github_repo": project.github_repo,
        "url": project.url,
        "stack": project.stack or [],
        "next_action": project.next_action,
        "last_activity_at": project.last_activity_at,
        "notes": project.notes,
        "position": project.position,
        "milestones": milestones,
    }


async def list_projects(session: AsyncSession, status: str | None = None) -> list[dict]:
    stmt = select(Project).join(Entity).where(Entity.archived_at.is_(None))
    if status:
        stmt = stmt.where(Project.status == status)
    projects = list((await session.execute(stmt.order_by(Project.position))).scalars())
    return [await project_out(session, item) for item in projects]


async def create(session: AsyncSession, data: ProjectIn) -> dict:
    values = data.model_dump()
    title = values.pop("title")
    entity = await create_entity(
        session,
        type="project",
        title=title,
        search_text=" ".join(data.stack) + " " + (data.notes or ""),
    )
    project = Project(id=entity.id, **values)
    session.add(project)
    await log_event(
        session, verb="project.created", entity_id=project.id, entity_type="project", payload={}
    )
    await session.commit()
    return await project_out(session, project)


async def patch(session: AsyncSession, project_id: uuid.UUID, data: ProjectPatch) -> dict | None:
    project = await session.get(Project, project_id)
    if project is None:
        return None
    values = data.model_dump(exclude_unset=True)
    title = values.pop("title", None)
    for key, value in values.items():
        setattr(project, key, value)
    await touch_entity(
        session,
        project.id,
        title=title,
        search_text=" ".join(project.stack or []) + " " + (project.notes or ""),
    )
    await log_event(
        session,
        verb="project.updated",
        entity_id=project.id,
        entity_type="project",
        payload={"fields": list(values)},
    )
    await session.commit()
    return await project_out(session, project)


async def add_milestone(
    session: AsyncSession, project_id: uuid.UUID, data: MilestoneIn
) -> Milestone | None:
    if await session.get(Project, project_id) is None:
        return None
    item = Milestone(project_id=project_id, **data.model_dump())
    session.add(item)
    await session.commit()
    return item


async def patch_milestone(
    session: AsyncSession, milestone_id: uuid.UUID, data: MilestonePatch
) -> Milestone | None:
    item = await session.get(Milestone, milestone_id)
    if item is None:
        return None
    values = data.model_dump(exclude_unset=True)
    completed = values.pop("completed", None)
    for key, value in values.items():
        setattr(item, key, value)
    if completed is not None:
        item.completed_at = datetime.now(UTC) if completed else None
    await session.commit()
    return item


async def project_todos(session: AsyncSession, project_id: uuid.UUID) -> list[dict]:
    ids = select(Link.from_id).where(Link.to_id == project_id, Link.relation == "belongs_to")
    rows = (
        await session.execute(
            select(Todo, Entity.title)
            .join(Entity, Entity.id == Todo.id)
            .where(Todo.id.in_(ids))
            .order_by(Todo.status, Todo.priority.desc())
        )
    ).all()
    return [_todo_out(todo, title) for todo, title in rows]
