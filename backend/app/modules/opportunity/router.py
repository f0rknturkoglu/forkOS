from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import log_event
from app.core.links import link
from app.core.models import Entity, Link, SourceRun
from app.db import get_session
from app.modules.opportunity import service
from app.modules.opportunity import sync as sync_service
from app.modules.opportunity.models import Notification, Opportunity, OpportunityRequirement
from app.modules.opportunity.schemas import (
    DeadlineOut,
    NotificationOut,
    OpportunityIn,
    OpportunityOut,
    OpportunityPatch,
    RequirementIn,
    SourceRefreshOut,
    SourceSyncBatchOut,
    SourceSyncStatusOut,
)
from app.modules.todo import service as todo_service
from app.modules.todo.models import Todo
from app.modules.todo.schemas import TodoIn, TodoOut
from app.sources.announcements import SOURCES as ANNOUNCEMENT_SOURCES
from app.sources.forkjob_port import forkjob_sources

router = APIRouter(tags=["opportunities"])


class RequirementDocumentIn(BaseModel):
    document_entity_id: UUID | None


class SourceRefreshIn(BaseModel):
    """Bos govde = katalogun tamami."""

    source_ids: list[str] | None = None
    kind: Literal["job", "announcement"] | None = None


@router.get("/opportunities", response_model=list[OpportunityOut])
async def opportunities(
    status: str | None = None,
    kind: str | None = None,
    limit: int = 200,
    trashed_only: bool = False,
    session: AsyncSession = Depends(get_session),
):
    return await service.list_opportunities(
        session, status, kind, min(limit, 2000), trashed_only=trashed_only
    )


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


@router.post("/opportunities/{item_id}/trash", response_model=OpportunityOut)
async def trash(item_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await service.trash_opportunity(session, item_id)
    if result is None:
        raise HTTPException(404)
    return result


@router.post("/opportunities/{item_id}/restore", response_model=OpportunityOut)
async def restore(item_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await service.restore_opportunity(session, item_id)
    if result is None:
        raise HTTPException(404)
    return result


@router.delete("/opportunities/{item_id}", status_code=204)
async def delete(item_id: UUID, session: AsyncSession = Depends(get_session)):
    item = await session.get(Opportunity, item_id)
    if item is None:
        raise HTTPException(404)
    if item.trashed_at is None:
        raise HTTPException(409, "Fırsat kalıcı silinmeden önce çöpe taşınmalı")
    if not await service.delete_opportunity(session, item_id):
        raise HTTPException(404)


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
    # entity ile outer join: bildirimin hedef turu arayuzde rota secimine gider.
    rows = (
        await session.execute(
            select(Notification, Entity.type)
            .outerjoin(Entity, Entity.id == Notification.entity_id)
            .where(Notification.dismissed_at.is_(None))
            .order_by(Notification.created_at.desc())
            .limit(100)
        )
    ).all()
    return [
        NotificationOut(
            id=item.id,
            kind=item.kind,
            title=item.title,
            body=item.body,
            entity_id=item.entity_id,
            entity_type=entity_type,
            importance=item.importance,
            created_at=item.created_at,
            read_at=item.read_at,
        )
        for item, entity_type in rows
    ]


@router.post("/notifications/{notification_id}/read")
async def read_notification(notification_id: int, session: AsyncSession = Depends(get_session)):
    item = await session.get(Notification, notification_id)
    if item is None:
        raise HTTPException(404)
    item.read_at = datetime.now(UTC)
    await session.commit()
    return {"ok": True}


@router.post("/notifications/read-all")
async def read_all_notifications(session: AsyncSession = Depends(get_session)):
    """Panelin 'tumunu okundu isaretle' dugmesi. Kayitlar durur, yalnizca okundu olur."""
    now = datetime.now(UTC)
    result = await session.execute(
        update(Notification)
        .where(Notification.read_at.is_(None), Notification.dismissed_at.is_(None))
        .values(read_at=now)
    )
    await session.commit()
    return {"read": result.rowcount or 0}


@router.post("/notifications/{notification_id}/dismiss")
async def dismiss_notification(notification_id: int, session: AsyncSession = Depends(get_session)):
    """Bildirimi panelden kaldirir. Silmez -- event gecmisi append-only kalir."""
    item = await session.get(Notification, notification_id)
    if item is None:
        raise HTTPException(404)
    now = datetime.now(UTC)
    item.dismissed_at = now
    if item.read_at is None:
        item.read_at = now
    await session.commit()
    return {"ok": True}


@router.post("/notifications/dismiss-all")
async def dismiss_all_notifications(session: AsyncSession = Depends(get_session)):
    now = datetime.now(UTC)
    result = await session.execute(
        update(Notification)
        .where(Notification.dismissed_at.is_(None))
        .values(dismissed_at=now, read_at=func.coalesce(Notification.read_at, now))
    )
    await session.commit()
    return {"dismissed": result.rowcount or 0}


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
        for source in [*forkjob_sources(include_opt_in=True), *ANNOUNCEMENT_SOURCES]
    ]


@router.get("/sources/sync", response_model=SourceSyncStatusOut)
async def sync_status(session: AsyncSession = Depends(get_session)):
    """Aktif manuel batch ve kaynak bazli kesin ilerleme."""
    return await sync_service.current_status(session)


@router.get("/sources/sync/history", response_model=list[SourceSyncBatchOut])
async def sync_history(limit: int = 10, session: AsyncSession = Depends(get_session)):
    return await sync_service.history(session, min(limit, 50))


@router.post("/sources/refresh", response_model=SourceRefreshOut)
async def refresh_sources(
    body: SourceRefreshIn, session: AsyncSession = Depends(get_session)
):
    """Secmeli ya da toplu cekim.

    source_ids verilirse yalnizca onlar; kind verilirse o turun tamami; ikisi
    de bossa katalogun hepsi. API yalnızca kalıcı batch oluşturur; çekimi
    worker yapar ve ilerleme /sources/sync'ten izlenir.
    """
    catalog = {
        source.id: source
        for source in [*forkjob_sources(include_opt_in=True), *ANNOUNCEMENT_SOURCES]
    }
    announcement_ids = {source.id for source in ANNOUNCEMENT_SOURCES}

    if body.source_ids:
        unknown = [item for item in body.source_ids if item not in catalog]
        if unknown:
            raise HTTPException(404, f"kaynak bulunamadı: {', '.join(unknown[:5])}")
        ids = list(dict.fromkeys(body.source_ids))
    elif body.kind:
        ids = [
            source_id
            for source_id in catalog
            if ("announcement" if source_id in announcement_ids else "job") == body.kind
        ]
    else:
        ids = list(catalog)

    if not ids:
        return {"batch_id": None, "queued": 0, "total_sources": 0}

    batch, newly_queued = await sync_service.create_or_extend_batch(session, ids)
    await session.commit()
    return {
        "batch_id": str(batch.id),
        "queued": len(newly_queued),
        "total_sources": batch.total_sources,
    }


@router.post("/sources/{source_id:path}/refresh")
async def refresh_source(source_id: str, session: AsyncSession = Depends(get_session)):
    try:
        catalog = {
            source.id
            for source in [*forkjob_sources(include_opt_in=True), *ANNOUNCEMENT_SOURCES]
        }
        if source_id not in catalog:
            raise KeyError(source_id)
        batch, newly_queued = await sync_service.create_or_extend_batch(session, [source_id])
        await session.commit()
        if not newly_queued:
            return {"source": source_id, "added": 0, "batch_id": str(batch.id)}
    except KeyError as exc:
        raise HTTPException(404, "kaynak bulunamadı") from exc
    return {"source": source_id, "added": 0, "batch_id": str(batch.id)}
