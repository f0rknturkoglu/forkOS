from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import log_event
from app.core.links import link
from app.core.models import Entity, Link, SourceRun
from app.db import get_session
from app.modules.opportunity import service
from app.modules.opportunity.models import Notification, Opportunity, OpportunityRequirement
from app.modules.opportunity.schemas import (
    DeadlineOut,
    NotificationOut,
    OpportunityIn,
    OpportunityOut,
    OpportunityPatch,
    RequirementIn,
)
from app.modules.opportunity.worker import poll_named_source
from app.modules.todo import service as todo_service
from app.modules.todo.models import Todo
from app.modules.todo.schemas import TodoIn, TodoOut
from app.sources.announcements import SOURCES as ANNOUNCEMENT_SOURCES
from app.sources.forkjob_port import forkjob_sources

router = APIRouter(tags=["opportunities"])


class RequirementDocumentIn(BaseModel):
    document_entity_id: UUID | None


@router.get("/opportunities", response_model=list[OpportunityOut])
async def opportunities(
    status: str | None = None,
    kind: str | None = None,
    limit: int = 200,
    session: AsyncSession = Depends(get_session),
):
    return await service.list_opportunities(session, status, kind, min(limit, 500))


@router.get("/opportunities/{item_id}", response_model=OpportunityOut)
async def opportunity_detail(item_id: UUID, session: AsyncSession = Depends(get_session)):
    row = (
        await session.execute(
            select(Opportunity, Entity.title)
            .join(Entity, Entity.id == Opportunity.id)
            .where(Opportunity.id == item_id)
        )
    ).first()
    if row is None:
        raise HTTPException(404)
    return service._out(row)


@router.post("/opportunities", response_model=OpportunityOut, status_code=201)
async def create(body: OpportunityIn, session: AsyncSession = Depends(get_session)):
    return await service.create(session, body)


@router.patch("/opportunities/{item_id}", response_model=OpportunityOut)
async def patch(
    item_id: UUID, body: OpportunityPatch, session: AsyncSession = Depends(get_session)
):
    result = await service.patch(session, item_id, body)
    if result is None:
        raise HTTPException(404)
    return result


@router.get("/opportunities/{item_id}/requirements")
async def requirements(item_id: UUID, session: AsyncSession = Depends(get_session)):
    return list(
        (
            await session.execute(
                select(OpportunityRequirement)
                .where(OpportunityRequirement.opportunity_id == item_id)
                .order_by(OpportunityRequirement.position)
            )
        ).scalars()
    )


@router.post("/opportunities/{item_id}/requirements", status_code=201)
async def requirement(
    item_id: UUID, body: RequirementIn, session: AsyncSession = Depends(get_session)
):
    result = await service.add_requirement(session, item_id, body)
    if result is None:
        raise HTTPException(404)
    return result


@router.patch("/requirements/{requirement_id}/document")
async def bind_requirement_document(
    requirement_id: UUID,
    body: RequirementDocumentIn,
    session: AsyncSession = Depends(get_session),
):
    requirement = await session.get(OpportunityRequirement, requirement_id)
    if requirement is None:
        raise HTTPException(404, "requirement bulunamadı")
    if body.document_entity_id is not None:
        document = await session.get(Entity, body.document_entity_id)
        if document is None or document.type != "document":
            raise HTTPException(400, "document bulunamadı")
    requirement.document_entity_id = body.document_entity_id
    requirement.status = "satisfied" if body.document_entity_id else "missing"
    await log_event(
        session,
        verb="opportunity.requirement_document_bound",
        entity_id=requirement.opportunity_id,
        entity_type="opportunity",
        payload={
            "requirement_id": str(requirement.id),
            "document_entity_id": str(body.document_entity_id) if body.document_entity_id else None,
        },
    )
    await session.commit()
    return requirement


@router.get("/opportunities/{item_id}/todos", response_model=list[TodoOut])
async def opportunity_todos(item_id: UUID, session: AsyncSession = Depends(get_session)):
    ids = select(Link.to_id).where(Link.from_id == item_id, Link.relation == "application_step")
    rows = (
        await session.execute(
            select(Todo, Entity.title)
            .join(Entity, Entity.id == Todo.id)
            .where(Todo.id.in_(ids))
            .order_by(Todo.status, Todo.due_at.asc().nullslast())
        )
    ).all()
    return [todo_service._todo_out(todo, title) for todo, title in rows]


@router.post("/opportunities/{item_id}/todos", response_model=TodoOut, status_code=201)
async def add_opportunity_todo(
    item_id: UUID, body: TodoIn, session: AsyncSession = Depends(get_session)
):
    if await session.get(Opportunity, item_id) is None:
        raise HTTPException(404)
    todo = await todo_service.create(session, body, commit=False)
    await link(session, item_id, todo.id, "application_step")
    await session.commit()
    return todo


@router.get("/deadlines", response_model=list[DeadlineOut])
async def deadlines(session: AsyncSession = Depends(get_session)):
    rows = (
        (await session.execute(text("select * from deadline_v order by due_at limit 200")))
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]


@router.get("/notifications", response_model=list[NotificationOut])
async def notifications(session: AsyncSession = Depends(get_session)):
    return list(
        (
            await session.execute(
                select(Notification)
                .where(Notification.dismissed_at.is_(None))
                .order_by(Notification.created_at.desc())
                .limit(100)
            )
        ).scalars()
    )


@router.post("/notifications/{notification_id}/read")
async def read_notification(notification_id: int, session: AsyncSession = Depends(get_session)):
    item = await session.get(Notification, notification_id)
    if item is None:
        raise HTTPException(404)
    item.read_at = datetime.now(UTC)
    await session.commit()
    return {"ok": True}


@router.get("/sources/runs")
async def source_runs(session: AsyncSession = Depends(get_session)):
    return list(
        (
            await session.execute(
                select(SourceRun).order_by(SourceRun.started_at.desc()).limit(100)
            )
        ).scalars()
    )


@router.get("/sources/catalog")
async def source_catalog():
    return [
        {
            "id": source.id,
            "interval_minutes": source.interval_minutes,
            "kind": "announcement" if source in ANNOUNCEMENT_SOURCES else "job",
        }
        for source in [*forkjob_sources(), *ANNOUNCEMENT_SOURCES]
    ]


@router.post("/sources/{source_id:path}/refresh")
async def refresh_source(source_id: str):
    try:
        added = await poll_named_source(source_id)
    except KeyError as exc:
        raise HTTPException(404, "kaynak bulunamadı") from exc
    return {"source": source_id, "added": added}
