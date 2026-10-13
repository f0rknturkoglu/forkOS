from __future__ import annotations

import uuid
from collections.abc import Collection
from datetime import UTC, date, datetime

from sqlalchemy import Text, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import create_entity, delete_entity, touch_entity
from app.core.events import log_event
from app.core.models import Entity, Event, Link
from app.core.time import local_zone
from app.modules import DeadlineRow
from app.modules.project.models import Milestone, Project
from app.modules.project.schemas import (
    MilestoneIn,
    MilestonePatch,
    ProjectIn,
    ProjectPatch,
    ProjectResourceIn,
)
from app.modules.todo import service as todo_service
from app.modules.todo.models import Todo
from app.modules.todo.schemas import TodoIn
from app.modules.todo.service import _todo_out


async def project_out(
    session: AsyncSession,
    project: Project,
    entity_activity_at: datetime,
    todo_activity_at: datetime | None = None,
    progress: dict | None = None,
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
    if progress is None:
        from app.core.progress import project_progress
        progress = (await project_progress(session, [project.id]))[project.id]
    return {
        "execution_progress": progress,
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
    from app.core.progress import project_progress
    progress = await project_progress(session, [project.id for project, _ in rows])
    return [
        await project_out(session, project, entity_activity_at, activity.get(project.id), progress.get(project.id))
        for project, entity_activity_at in rows
    ]


async def create(session: AsyncSession, data: ProjectIn) -> dict:
    values = data.model_dump()
    title = values.pop("title")
    entity = await create_entity(
        session,
        type="project",
        title=title,
        search_text=" ".join(data.stack),
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
        search_text=" ".join(project.stack or []),
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
    # Kural 2: entity helper'lari -- baslik Entity.title'da yasar.
    entity = await create_entity(
        session, type="milestone", title=data.title, search_text=data.title
    )
    item = Milestone(
        id=entity.id,
        project_id=project_id,
        title=data.title,
        **data.model_dump(exclude={"title"}),
    )
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
    # Baslik Entity.title'da yasar; degisince entity'yi de guncelle.
    if "title" in values:
        await touch_entity(session, item.id, title=values["title"])
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
    # Kural 2: entity helper -- entity silinince milestone cascade gider.
    await delete_entity(session, item.id)
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


async def github_issue_todo_ids(
    session: AsyncSession,
    project: Project,
    issue_numbers: Collection[int],
) -> dict[int, uuid.UUID]:
    """GitHub issue numaralarini mevcut gorev entity'leriyle tek sorguda eslestirir."""
    numbers = set(issue_numbers)
    if not project.github_repo or not numbers:
        return {}

    rows = (
        await session.execute(
            select(Entity.id, Entity.title).where(
                Entity.type == Todo.ENTITY_TYPE,
                Entity.title.startswith(f"{project.github_repo}#"),
            )
        )
    ).all()
    markers = {f"{project.github_repo}#{number} ": number for number in numbers}
    matches: dict[int, uuid.UUID] = {}
    for entity_id, title in rows:
        for marker, number in markers.items():
            if title.startswith(marker):
                matches[number] = entity_id
                break
    return matches


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
        Event.verb.in_(("pomodoro.completed", "pomodoro.interrupted", "pomodoro.updated", "pomodoro.deleted"))
        & or_(Event.payload["context_entity_id"].astext.in_(todo_ids_text),
               Event.payload["context_entity_id"].astext == str(project_id),
               Event.payload["before"]["context_entity_id"].astext.in_(todo_ids_text),
               Event.payload["before"]["context_entity_id"].astext == str(project_id))
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


async def journal(
    session: AsyncSession, project_id: uuid.UUID, limit: int = 60
) -> list[dict]:
    """Proje olaylarini gun basliklari altinda gruplar.

    Gunluk METNI artik forkOS'ta tutulmaz: proje gunlugu Vault sahipligindedir
    (bkz. `POST /projects/{id}/journal/{day}/obsidian`). Bu gorunum yalnizca
    operasyonel zaman cizelgesidir -- not gövdesi, `notes_about` bagi veya
    `note.*` olayi URETILMEZ.
    """
    events = (await timeline(session, project_id, limit))[:limit]
    zone = local_zone()
    groups: dict[date, dict] = {}
    for event in events:
        event_day = event["occurred_at"].astimezone(zone).date()
        group = groups.setdefault(event_day, {"day": event_day, "events": []})
        group["events"].append(event)
    return [groups[day] for day in sorted(groups, reverse=True)]


async def deadline_provider(session: AsyncSession) -> list[DeadlineRow]:
    """Tamamlanmamis kilometre taslari (kural 16)."""
    from app.core.deadlines import rows_with_titles
    from app.modules.project.models import Milestone

    # Iterator'i bir kez tüket; iki kez gezmek due haritasini bos birakir
    # ve milestone deadline'lari sessizce duser (kural 16 hatti).
    milestones = list((
        await session.execute(
            select(Milestone).where(
                Milestone.due_at.is_not(None),
                Milestone.completed_at.is_(None),
            )
        )
    ).scalars())
    ids = [m.id for m in milestones]
    due = {m.id: m.due_at for m in milestones}
    return await rows_with_titles(
        session, type_="milestone", module="project", ids=ids, due_at=due,
    )


async def resources(session: AsyncSession, project_id: uuid.UUID) -> list[dict] | None:
    from app.modules.bookmark.models import Bookmark

    if await session.get(Project, project_id) is None:
        return None
    rows = (await session.execute(
        select(Bookmark.id, Entity.title, Bookmark.url)
        .join(Entity, Entity.id == Bookmark.id)
        .join(Link, Link.to_id == Bookmark.id)
        .where(Link.from_id == project_id, Link.relation == "references", Entity.archived_at.is_(None))
        .order_by(Entity.created_at)
    )).all()
    return [{"id": row.id, "title": row.title, "url": row.url} for row in rows]


async def add_resource(session: AsyncSession, project_id: uuid.UUID, data: ProjectResourceIn) -> dict | None:
    from app.core.links import link
    from app.modules.bookmark.receipts import capture_once
    from app.modules.bookmark.schemas import CaptureIn
    from app.modules.bookmark.service import capture

    if await session.get(Project, project_id) is None:
        return None

    async def write():
        bookmark, _, _ = await capture(session, CaptureIn(
            url=data.url, title=data.title.strip(), collection="projects", source="project",
        ), commit=False)
        await link(session, project_id, bookmark.id, "references")
        await touch_entity(session, project_id)
        await log_event(session, verb="link.created", entity_id=project_id, entity_type="project",
                        payload={"to_id": str(bookmark.id), "relation": "references"})
        return {"id": str(bookmark.id), "title": data.title.strip(), "url": data.url}

    result, _ = await capture_once(session, data, f"project-resource:{project_id}", write)
    return result
