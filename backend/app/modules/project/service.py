from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Text, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import create_entity, touch_entity
from app.core.events import log_event
from app.core.models import Entity, Event, Link
from app.modules import DeadlineRow
from app.modules.project.models import Milestone, Project
from app.modules.project.schemas import MilestoneIn, MilestonePatch, ProjectIn, ProjectPatch
from app.modules.todo import service as todo_service
from app.modules.todo.models import Todo
from app.modules.todo.schemas import TodoIn
from app.modules.todo.service import _todo_out


async def project_out(
    session: AsyncSession,
    project: Project,
    entity_activity_at: datetime,
    todo_activity_at: datetime | None = None,
) -> dict:
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
        "last_activity_at": max(
            changed_at
            for changed_at in (entity_activity_at, project.last_activity_at, todo_activity_at)
            if changed_at is not None
        ),
        "notes": project.notes,
        "position": project.position,
        "milestones": milestones,
    }


async def _todo_activity_by_project(
    session: AsyncSession, project_ids: list[uuid.UUID]
) -> dict[uuid.UUID, datetime]:
    rows = (await session.execute(
        select(Link.to_id, func.max(Entity.updated_at))
        .join(Entity, Entity.id == Link.from_id)
        .where(Link.to_id.in_(project_ids), Link.relation == "belongs_to",
               Entity.type == "todo")
        .group_by(Link.to_id)
    )).all()
    return {project_id: changed_at for project_id, changed_at in rows}


async def list_projects(session: AsyncSession, status: str | None = None) -> list[dict]:
    stmt = select(Project, Entity.updated_at).join(Entity).where(Entity.archived_at.is_(None))
    if status:
        stmt = stmt.where(Project.status == status)
    rows = (await session.execute(stmt.order_by(Project.position))).all()
    activity = await _todo_activity_by_project(session, [project.id for project, _ in rows])
    return [
        await project_out(session, project, entity_activity_at, activity.get(project.id))
        for project, entity_activity_at in rows
    ]


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
    return await project_out(session, project, entity.updated_at)


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
    entity_activity_at = (
        await session.execute(select(Entity.updated_at).where(Entity.id == project.id))
    ).scalar_one()
    return await project_out(session, project, entity_activity_at)


async def add_milestone(
    session: AsyncSession, project_id: uuid.UUID, data: MilestoneIn
) -> Milestone | None:
    if await session.get(Project, project_id) is None:
        return None
    item = Milestone(project_id=project_id, **data.model_dump())
    session.add(item)
    await session.flush()
    await log_event(
        session,
        verb="project.milestone_added",
        entity_id=item.project_id,
        entity_type="project",
        payload={"milestone_id": str(item.id), "title": item.title},
    )
    await session.commit()
    return item


async def patch_milestone(
    session: AsyncSession, milestone_id: uuid.UUID, data: MilestonePatch
) -> Milestone | None:
    item = await session.get(Milestone, milestone_id)
    if item is None:
        return None
    values = data.model_dump(exclude_unset=True)
    changed_fields = list(values)
    completed = values.pop("completed", None)
    for key, value in values.items():
        setattr(item, key, value)
    if completed is not None:
        item.completed_at = datetime.now(UTC) if completed else None
    await log_event(
        session,
        verb="project.milestone_updated",
        entity_id=item.project_id,
        entity_type="project",
        payload={
            "milestone_id": str(item.id),
            "title": item.title,
            "fields": changed_fields,
        },
    )
    await session.commit()
    return item


async def delete_milestone(session: AsyncSession, milestone_id: uuid.UUID) -> bool:
    item = await session.get(Milestone, milestone_id)
    if item is None:
        return False
    await log_event(
        session,
        verb="project.milestone_deleted",
        entity_id=item.project_id,
        entity_type="project",
        payload={"milestone_id": str(item.id), "title": item.title},
    )
    await session.delete(item)
    await session.commit()
    return True


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


#: Issue'dan uretilen gorevlerin etiketi -- listede kaynagi belli olsun.
ISSUE_TAG = "github"


async def todo_from_issue(session: AsyncSession, project: Project, issue: dict) -> dict:
    """GitHub issue'sunu gorev yapar ve projeye baglar.

    Ayni issue ikinci kez gelirse YENI gorev acilmaz: eslesme entity.title
    icindeki "repo#numara" onekinden kurulur -- ayri bir eslestirme tablosu
    acmaya deger bir kazanc yok.
    """
    marker = f"{project.github_repo}#{issue['number']}"
    title = f"{marker} {issue['title']}"

    existing = (
        await session.execute(
            select(Todo, Entity.title)
            .join(Entity, Entity.id == Todo.id)
            .where(Entity.type == Todo.ENTITY_TYPE, Entity.title.startswith(f"{marker} "))
        )
    ).first()
    if existing is not None:
        return {**_todo_out(existing[0], existing[1]).model_dump(), "duplicate": True}

    body = (issue.get("body") or "").strip()
    # Tek gorev siniri todo_service.create (Faz 17): tag, proje bagi ve
    # event ayni transaction'da yazilir; arama metni govde disinda tutulur.
    todo = await todo_service.create(
        session,
        TodoIn(
            title=title,
            description=issue["url"],
            priority=2,
            status="open",
            tags=[ISSUE_TAG, *issue.get("labels", [])[:3]],
            project_id=project.id,
        ),
        search_text=body[:2000],
        commit=False,
    )
    await session.commit()
    return {**todo.model_dump(), "duplicate": False}


async def delete(session: AsyncSession, project_id: uuid.UUID) -> bool:
    """entity satirini siler -- project, milestone ve link cascade ile gider.

    Gorevler kalir: `link` silinince gorev sahipsiz kalir ama listede durur.
    """
    entity = await session.get(Entity, project_id)
    if entity is None:
        return False
    title = entity.title
    await session.delete(entity)
    await log_event(session, verb="project.deleted", entity_type="project",
                    payload={"title": title})
    await session.commit()
    return True


async def timeline(session: AsyncSession, project_id: uuid.UUID, limit: int = 60) -> list[dict]:
    """Projenin gunlugu: kendi olaylari + bagli gorevlerin olaylari + commit'ler.

    Uc kaynak tek listede birlesiyor cunku "bu projede ne oldu" sorusunun
    cevabi ucune de dagilmis durumda: proje kaydinin kendisi, ona bagli
    gorevler ve deponun commit'leri.
    """
    project = await session.get(Project, project_id)
    if project is None:
        return []

    todo_ids = (
        select(Link.from_id)
        .join(Todo, Todo.id == Link.from_id)
        .where(Link.to_id == project_id, Link.relation == "belongs_to")
    )
    conditions = [Event.entity_id == project_id, Event.entity_id.in_(todo_ids)]
    todo_ids_text = (
        select(cast(Link.from_id, Text))
        .join(Todo, Todo.id == Link.from_id)
        .where(Link.to_id == project_id, Link.relation == "belongs_to")
    )
    conditions.append(
        Event.verb.in_(("pomodoro.completed", "pomodoro.interrupted"))
        & Event.payload["context_entity_id"].astext.in_(todo_ids_text)
    )
    if project.github_repo:
        conditions.append(
            (Event.verb == "github.commit")
            & (Event.payload["repo"].astext == project.github_repo)
        )

    rows = (
        (
            await session.execute(
                select(Event)
                .where(or_(*conditions))
                .order_by(Event.occurred_at.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    titles = dict(
        (
            await session.execute(
                select(Entity.id, Entity.title).where(
                    Entity.id.in_([e.entity_id for e in rows if e.entity_id])
                )
            )
        ).all()
    )
    return [
        {
            "id": event.id,
            "verb": event.verb,
            "entity_id": event.entity_id,
            "entity_type": event.entity_type,
            "title": titles.get(event.entity_id),
            "payload": event.payload,
            "occurred_at": event.occurred_at,
        }
        for event in rows
    ]


async def deadline_provider(session: AsyncSession) -> list[DeadlineRow]:
    """Tamamlanmamis kilometre taslari (kural 16)."""
    from app.core.deadlines import rows_with_titles
    from app.modules.project.models import Milestone

    milestones = (await session.execute(
        select(Milestone).where(
            Milestone.due_at.is_not(None),
            Milestone.completed_at.is_(None),
        )
    )).scalars()
    ids = [m.id for m in milestones]
    due = {m.id: m.due_at for m in milestones}
    return await rows_with_titles(
        session, type_="milestone", module="project", ids=ids, due_at=due,
    )
