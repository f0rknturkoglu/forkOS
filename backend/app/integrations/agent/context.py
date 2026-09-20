from __future__ import annotations

import os
import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core import links as links_svc
from app.core import registry as registry_svc
from app.core import search as search_svc
from app.core.deadlines import collect_deadlines
from app.core.models import Entity, Event, Notification
from app.core.time import local_today, local_zone
from app.integrations.agent.knowledge import get_brain_status
from app.integrations.agent.models import (
    ActivityEventData,
    BriefingData,
    EntityContextData,
    EntitySearchResult,
    KnowledgePointer,
    ProjectContextData,
    sanitize_payload,
)
from app.integrations.obsidian.service import (
    VaultConflictError,
    resolve_managed_item,
    vault_index,
)
from app.modules.flashcard.models import FlashcardCard
from app.modules.opportunity.lifecycle import APPLICATION_TERMINAL, JOB_KINDS
from app.modules.opportunity.models import Application, Opportunity
from app.modules.project import service as project_svc
from app.modules.project.models import Milestone, Project
from app.modules.today import service as today_svc
from app.modules.todo.models import Todo

FROZEN_LEGACY_TYPES = {"note", "note_folder", "note_attachment"}


def _resolve_route(entity_type: str, entity_id: uuid.UUID) -> str:
    spec = registry_svc.type_spec(entity_type)
    if spec and spec.route:
        return spec.route.replace("{id}", str(entity_id))
    return f"/{entity_type}s/{entity_id}"


def _parse_since(since: str | None) -> datetime | None:
    if not since or not since.strip():
        return None
    s = since.strip().lower()
    now = datetime.now(UTC)
    zone = local_zone()
    today_dt = datetime.combine(local_today(), time.min, tzinfo=zone).astimezone(UTC)

    if s == "today":
        return today_dt
    elif s == "yesterday":
        return today_dt - timedelta(days=1)
    elif s == "7d":
        return now - timedelta(days=7)
    elif s == "30d":
        return now - timedelta(days=30)
    else:
        try:
            return datetime.fromisoformat(since.strip())
        except Exception as exc:
            raise ValueError(
                f"INVALID_SINCE: '{since}' is not a valid preset (today, yesterday, 7d, 30d) or ISO datetime."
            ) from exc


def _resolve_knowledge_pointer(forkos_id: uuid.UUID) -> KnowledgePointer:
    """Resolve granular knowledge pointer state for an entity (available, missing, unavailable, conflict)."""
    fid_str = str(forkos_id)

    # 1. Check if Vault path is configured and directory exists / is accessible
    v_root = settings.resolved_obsidian_vault_path
    if v_root is None:
        return KnowledgePointer(
            state="unavailable",
            available=False,
            forkos_id=None,
            relative_path=None,
            title=None,
            diagnostic="Obsidian Vault is not configured (OBSIDIAN_VAULT_PATH is empty).",
        )

    if not v_root.exists() or not v_root.is_dir():
        return KnowledgePointer(
            state="unavailable",
            available=False,
            forkos_id=None,
            relative_path=None,
            title=None,
            diagnostic=f"Obsidian Vault directory does not exist or is not a directory: '{v_root}'.",
        )

    if not os.access(v_root, os.R_OK):
        return KnowledgePointer(
            state="unavailable",
            available=False,
            forkos_id=None,
            relative_path=None,
            title=None,
            diagnostic=f"Obsidian Vault directory is not readable: '{v_root}'.",
        )

    # 2. Try resolve_managed_item
    try:
        v_item = resolve_managed_item(forkos_id)
    except VaultConflictError as exc:
        return KnowledgePointer(
            state="conflict",
            available=False,
            forkos_id=None,
            relative_path=None,
            title=None,
            diagnostic=str(exc),
        )
    except (RuntimeError, PermissionError, FileNotFoundError) as exc:
        return KnowledgePointer(
            state="unavailable",
            available=False,
            forkos_id=None,
            relative_path=None,
            title=None,
            diagnostic=str(exc),
        )

    # 3. If item is None, check fallback for projects
    if v_item is None:
        try:
            v_item = vault_index.find_by_note_kind("project", project_id=fid_str)
        except Exception:
            v_item = None

    # 4. If still None -> missing
    if v_item is None:
        return KnowledgePointer(
            state="missing",
            available=False,
            forkos_id=None,
            relative_path=None,
            title=None,
            diagnostic="No managed knowledge note exists for this entity.",
        )

    # 5. If found -> available
    return KnowledgePointer(
        state="available",
        available=True,
        forkos_id=v_item.forkos_id,
        relative_path=v_item.relative_path,
        title=v_item.title,
        diagnostic=None,
    )


async def get_briefing_context(session: AsyncSession, day: str | None = None) -> BriefingData:
    """Factual, bounded day packet from existing forkOS services."""
    target_date: date
    if day:
        try:
            target_date = date.fromisoformat(day.strip())
        except (ValueError, TypeError) as exc:
            raise ValueError(f"INVALID_DATE: '{day}' is not in valid YYYY-MM-DD format.") from exc
    else:
        target_date = local_today()

    day_str = target_date.isoformat()

    # 1. Agenda items (capped at 30)
    agenda_rows: list[dict[str, Any]] = []
    today_out = await today_svc.agenda(session, target_date)
    raw_agenda = today_out.timed + today_out.checklist
    for row in raw_agenda[:30]:
        agenda_rows.append({
            "kind": row.kind,
            "title": row.title,
            "completed": row.completed,
            "starts_at": row.starts_at.isoformat() if row.starts_at else None,
            "duration_min": row.duration_min,
            "project_title": row.project_title,
        })

    # 2. Open todos (ordered by priority, capped at 20)
    todos_stmt = (
        select(Todo, Entity.title)
        .join(Entity, Entity.id == Todo.id)
        .where(Todo.status != "done", Entity.archived_at.is_(None))
        .order_by(Todo.priority.asc(), Todo.due_at.asc().nulls_last())
        .limit(20)
    )
    todos_res = await session.execute(todos_stmt)
    open_todos: list[dict[str, Any]] = []
    for todo, title in todos_res.all():
        open_todos.append({
            "id": str(todo.id),
            "title": title,
            "priority": todo.priority,
            "status": todo.status,
            "due_at": todo.due_at.isoformat() if todo.due_at else None,
        })

    # 3. Deadlines (within next 7 days, capped at 15)
    deadlines: list[dict[str, Any]] = []
    raw_deadlines = await collect_deadlines(session, limit=15)
    for d in raw_deadlines:
        due = d.get("due_at")
        deadlines.append({
            "id": str(d["entity_id"]),
            "title": d["title"],
            "due_at": due.isoformat() if hasattr(due, "isoformat") else str(due) if due else None,
            "entity_type": d["type"],
            "module": d.get("module"),
            "priority": d.get("priority"),
        })

    # 4. Active projects (capped at 10)
    proj_stmt = (
        select(Project, Entity.title)
        .join(Entity, Entity.id == Project.id)
        .where(Project.status != "completed", Entity.archived_at.is_(None))
        .order_by(Project.position.asc(), Project.last_activity_at.desc().nulls_last())
        .limit(10)
    )
    proj_res = await session.execute(proj_stmt)
    active_projects: list[dict[str, Any]] = []
    for proj, title in proj_res.all():
        active_projects.append({
            "id": str(proj.id),
            "title": title,
            "status": proj.status,
            "next_action": proj.next_action,
            "github_repo": proj.github_repo,
        })

    # 5. Learning due (flashcards due, capped at 10)
    learning_due: list[dict[str, Any]] = []
    now_dt = datetime.now(UTC)
    fc_stmt = (
        select(FlashcardCard, Entity.title)
        .join(Entity, Entity.id == FlashcardCard.id)
        .where(
            FlashcardCard.due_at <= now_dt,
            Entity.archived_at.is_(None),
        )
        .order_by(FlashcardCard.due_at.asc())
        .limit(10)
    )
    fc_res = await session.execute(fc_stmt)
    for card, title in fc_res.all():
        learning_due.append({
            "id": str(card.id),
            "title": title,
            "due_at": card.due_at.isoformat() if card.due_at else None,
            "reps": card.reps,
        })

    # 6. Opportunity attention (active applications + active announcements, capped at 10)
    opportunity_attention: list[dict[str, Any]] = []
    # 6a. Non-terminal applications
    app_stmt = (
        select(Application, Opportunity, Entity.title)
        .join(Opportunity, Opportunity.id == Application.opportunity_id)
        .join(Entity, Entity.id == Opportunity.id)
        .where(
            Application.status.not_in(APPLICATION_TERMINAL),
            Entity.archived_at.is_(None),
        )
        .order_by(Opportunity.deadline_at.asc().nulls_last())
        .limit(10)
    )
    app_res = await session.execute(app_stmt)
    for app, opp, title in app_res.all():
        opportunity_attention.append({
            "id": str(opp.id),
            "title": title,
            "kind": opp.kind,
            "organization": opp.organization,
            "company": opp.organization,
            "status": app.status,
            "stage": app.status,
            "deadline_at": opp.deadline_at.isoformat() if opp.deadline_at else None,
        })

    # 6b. Active announcements (action_required, watching, new)
    remaining_slots = 10 - len(opportunity_attention)
    if remaining_slots > 0:
        ann_stmt = (
            select(Opportunity, Entity.title)
            .join(Entity, Entity.id == Opportunity.id)
            .where(
                Opportunity.kind.not_in(JOB_KINDS),
                Opportunity.status.in_({"action_required", "watching", "new"}),
                Entity.archived_at.is_(None),
            )
            .order_by(Opportunity.deadline_at.asc().nulls_last())
            .limit(remaining_slots)
        )
        ann_res = await session.execute(ann_stmt)
        for opp, title in ann_res.all():
            opportunity_attention.append({
                "id": str(opp.id),
                "title": title,
                "kind": opp.kind,
                "organization": opp.organization,
                "company": opp.organization,
                "status": opp.status,
                "stage": opp.status,
                "deadline_at": opp.deadline_at.isoformat() if opp.deadline_at else None,
            })

    # 7. Notifications (unread, capped at 10)
    notif_stmt = (
        select(Notification)
        .where(Notification.read_at.is_(None), Notification.dismissed_at.is_(None))
        .order_by(Notification.created_at.desc())
        .limit(10)
    )
    notif_res = await session.execute(notif_stmt)
    notifications = [
        {
            "id": str(n.id),
            "title": n.title,
            "message": n.body or "",
            "created_at": n.created_at.isoformat(),
        }
        for n in notif_res.scalars().all()
    ]

    # 8. Recent activity summary (last 10 events)
    recent_events = await get_recent_activity_context(session, limit=10)
    recent_activity_summary = [e.model_dump(mode="json") for e in recent_events]

    # 9. Vault status
    vault_status = get_brain_status().model_dump(mode="json")

    return BriefingData(
        day=day_str,
        agenda=agenda_rows,
        open_todos=open_todos,
        deadlines=deadlines,
        active_projects=active_projects,
        learning_due=learning_due,
        opportunity_attention=opportunity_attention,
        notifications=notifications,
        recent_activity_summary=recent_activity_summary,
        vault_status=vault_status,
    )


async def search_operational_context(
    session: AsyncSession,
    query: str,
    entity_types: list[str] | None = None,
    limit: int = 10,
) -> list[EntitySearchResult]:
    """Search active operational entities, strictly excluding legacy note entities."""
    q = query.strip()
    if len(q) < 2:
        raise ValueError("QUERY_TOO_SHORT: Query must be at least 2 characters.")
    if len(q) > 200:
        raise ValueError("QUERY_TOO_LONG: Query must be at most 200 characters.")

    # Determine types
    all_searchable = [t for t in search_svc.searchable_types() if t not in FROZEN_LEGACY_TYPES]
    if entity_types:
        types_filter = [t for t in entity_types if t in all_searchable]
    else:
        types_filter = all_searchable

    if not types_filter:
        return []

    cap = max(1, min(limit, 30))
    raw_entities = await search_svc.search_entities(session, q, types=types_filter, limit=cap)

    results: list[EntitySearchResult] = []
    for ent in raw_entities:
        if ent.type in FROZEN_LEGACY_TYPES:
            continue
        route = _resolve_route(ent.type, ent.id)
        results.append(
            EntitySearchResult(
                id=str(ent.id),
                type=ent.type,
                title=ent.title,
                route=route,
                summary=ent.search_text[:200] if ent.search_text else "",
            )
        )

    return results


async def get_entity_context(session: AsyncSession, entity_id: str) -> EntityContextData:
    """Inspect identity, deep links, relationships, and activity for an entity."""
    try:
        ent_uuid = uuid.UUID(entity_id.strip())
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"INVALID_UUID: Invalid entity UUID '{entity_id}'.") from exc

    ent_res = await session.execute(select(Entity).where(Entity.id == ent_uuid))
    entity = ent_res.scalar_one_or_none()
    if entity is None:
        raise ValueError(f"ENTITY_NOT_FOUND: Entity '{entity_id}' does not exist.")

    # Check for legacy frozen note
    if entity.type in FROZEN_LEGACY_TYPES:
        return EntityContextData(
            id=str(entity.id),
            type=entity.type,
            title=entity.title,
            route="/notes",
            details={
                "status": "frozen legacy archive",
                "note": "Legacy Note entities are frozen. Active knowledge lives in the f0rknbrain Vault.",
            },
            related_entities=[],
            recent_events=[],
            knowledge_ref=None,
        )

    route = _resolve_route(entity.type, entity.id)

    # Fetch links (related entities) using canonical service which strictly excludes ARCHIVED_ENTITY_TYPES
    raw_related = await links_svc.related(session, ent_uuid)
    related: list[dict[str, Any]] = [
        {
            "id": r["entity"]["id"],
            "type": r["entity"]["type"],
            "title": r["entity"]["title"],
            "relation": r["relation"],
            "direction": r["direction"],
            "route": _resolve_route(r["entity"]["type"], uuid.UUID(r["entity"]["id"])),
        }
        for r in raw_related[:20]
    ]

    # Fetch recent events touching this entity
    events_stmt = (
        select(Event)
        .where(Event.entity_id == ent_uuid)
        .order_by(Event.occurred_at.desc())
        .limit(5)
    )
    events_res = await session.execute(events_stmt)
    recent_events = [
        {
            "id": ev.id,
            "verb": ev.verb,
            "timestamp": ev.occurred_at.isoformat(),
            "payload": sanitize_payload(ev.payload or {}),
        }
        for ev in events_res.scalars().all()
    ]

    # Check if a Vault note is linked to this entity (fresh canonical resolve)
    knowledge_ref = _resolve_knowledge_pointer(ent_uuid)

    return EntityContextData(
        id=str(entity.id),
        type=entity.type,
        title=entity.title,
        route=route,
        details={
            "created_at": entity.created_at.isoformat() if entity.created_at else None,
            "updated_at": entity.updated_at.isoformat() if entity.updated_at else None,
        },
        related_entities=related,
        recent_events=recent_events,
        knowledge_ref=knowledge_ref,
    )


async def get_project_context(session: AsyncSession, project_id: str) -> ProjectContextData:
    """Compact project operational packet with Vault pointer only."""
    try:
        proj_uuid = uuid.UUID(project_id.strip())
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"INVALID_UUID: Invalid project UUID '{project_id}'.") from exc

    proj_stmt = (
        select(Project, Entity.title)
        .join(Entity, Entity.id == Project.id)
        .where(Project.id == proj_uuid)
    )
    proj_res = await session.execute(proj_stmt)
    row = proj_res.first()
    if not row:
        raise ValueError(f"PROJECT_NOT_FOUND: Project '{project_id}' does not exist.")

    project, title = row

    # Milestones
    ms_stmt = (
        select(Milestone)
        .where(Milestone.project_id == proj_uuid)
        .order_by(Milestone.position.asc(), Milestone.due_at.asc().nulls_last())
    )
    ms_res = await session.execute(ms_stmt)
    milestones_data = [
        {
            "id": str(m.id),
            "title": m.title,
            "due_at": m.due_at.isoformat() if m.due_at else None,
            "completed": m.completed_at is not None,
        }
        for m in ms_res.scalars().all()
    ]
    milestone_ids = [m["id"] for m in milestones_data]

    # Open todos linked to this project (via canonical belongs_to or milestone)
    raw_project_todos = await project_svc.project_todos(session, proj_uuid)
    todo_ids_seen = {
        str(t["id"] if isinstance(t, dict) else t.id)
        for t in raw_project_todos
    }
    extra_todos: list[dict[str, Any]] = []
    if milestone_ids:
        ms_todos_stmt = (
            select(Todo, Entity.title)
            .join(Entity, Entity.id == Todo.id)
            .where(
                Todo.milestone_id.in_([uuid.UUID(mid) for mid in milestone_ids]),
                Todo.id.not_in([uuid.UUID(tid) for tid in todo_ids_seen]) if todo_ids_seen else True,
                Entity.archived_at.is_(None),
            )
            .order_by(Todo.priority.asc(), Todo.due_at.asc().nulls_last())
        )
        ms_todos_res = await session.execute(ms_todos_stmt)
        for t, t_title in ms_todos_res.all():
            extra_todos.append({
                "id": str(t.id),
                "title": t_title,
                "status": t.status,
                "priority": t.priority,
                "due_at": t.due_at.isoformat() if t.due_at else None,
            })

    todos_data: list[dict[str, Any]] = []
    for item in raw_project_todos:
        t_id = str(item["id"] if isinstance(item, dict) else item.id)
        t_title = item["title"] if isinstance(item, dict) else item.title
        t_status = item.get("status", "open") if isinstance(item, dict) else item.status
        t_priority = item.get("priority", 0) if isinstance(item, dict) else item.priority
        raw_due = item.get("due_at") if isinstance(item, dict) else getattr(item, "due_at", None)
        due_str = raw_due.isoformat() if hasattr(raw_due, "isoformat") else str(raw_due) if raw_due else None
        if t_status != "done":
            todos_data.append({
                "id": t_id,
                "title": t_title,
                "priority": t_priority,
                "status": t_status,
                "due_at": due_str,
            })

    for item in extra_todos:
        if item.get("status") != "done":
            todos_data.append(item)

    todos_data = todos_data[:20]

    # Recent activity from canonical project timeline service (includes project, linked todos, and commits)
    raw_timeline = await project_svc.timeline(session, proj_uuid, limit=10)
    activity_data = [
        {
            "id": ev["id"],
            "verb": ev["verb"],
            "timestamp": ev["occurred_at"].isoformat() if hasattr(ev.get("occurred_at"), "isoformat") else str(ev.get("occurred_at")),
            "payload": sanitize_payload(ev.get("payload") or {}),
        }
        for ev in raw_timeline
    ]

    # Deadlines for this project
    deadlines = [m for m in milestones_data if m.get("due_at") and not m.get("completed")]

    # Vault knowledge pointer only (fresh canonical resolve)
    knowledge_data = _resolve_knowledge_pointer(proj_uuid)

    return ProjectContextData(
        project={
            "id": str(project.id),
            "title": title,
            "status": project.status,
            "next_action": project.next_action,
            "stack": project.stack or [],
            "github_repo": project.github_repo,
        },
        milestones=milestones_data,
        todos=todos_data,
        recent_activity=activity_data,
        deadlines=deadlines,
        knowledge=knowledge_data,
    )


async def get_recent_activity_context(
    session: AsyncSession,
    since: str | None = None,
    entity_type: str | None = None,
    verb: str | None = None,
    limit: int = 30,
) -> list[ActivityEventData]:
    """Retrieve sanitized, bounded append-only event log."""
    cap = max(1, min(limit, 100))
    since_dt = _parse_since(since)

    stmt = select(Event, Entity.title).outerjoin(Entity, Entity.id == Event.entity_id)

    if since_dt:
        stmt = stmt.where(Event.occurred_at >= since_dt)
    if entity_type:
        stmt = stmt.where(Event.entity_type == entity_type)
    if verb:
        stmt = stmt.where(Event.verb == verb)

    stmt = stmt.order_by(Event.occurred_at.desc()).limit(cap)
    res = await session.execute(stmt)

    events: list[ActivityEventData] = []
    for ev, title in res.all():
        events.append(
            ActivityEventData(
                id=ev.id,
                timestamp=ev.occurred_at.isoformat(),
                verb=ev.verb,
                entity_id=str(ev.entity_id) if ev.entity_id else None,
                entity_type=ev.entity_type,
                title=title or "",
                payload=sanitize_payload(ev.payload or {}),
            )
        )

    return events
