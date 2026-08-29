from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import log_event
from app.core.links import link
from app.core.models import Entity, Link
from app.db import get_session
from app.modules.opportunity import service
from app.modules.opportunity.browse import BrowseFilters, browse_opportunities
from app.modules.opportunity.models import Opportunity, OpportunityRequirement
from app.modules.opportunity.schemas import (
    OpportunityBrowseOut,
    OpportunityIn,
    OpportunityOut,
    OpportunityPatch,
    RequirementIn,
    TransitionIn,
)
from app.modules.opportunity.sources_router import router as sources_router
from app.modules.todo import service as todo_service
from app.modules.todo.models import Todo
from app.modules.todo.schemas import TodoIn, TodoOut

router = APIRouter(tags=["opportunities"])

class RequirementDocumentIn(BaseModel):
    document_entity_id: UUID | None


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


@router.get("/opportunities/browse", response_model=OpportunityBrowseOut)
async def opportunity_browse(
    section: str = "jobs",
    announcement_source: str | None = None,
    category: str | None = None,
    search: str | None = None,
    status: str | None = None,
    source: str | None = None,
    region: str | None = None,
    remote: str | None = None,
    period_days: int | None = None,
    year: int | None = None,
    min_score: float | None = Query(None, ge=-1, le=100),
    max_score: float | None = Query(None, ge=-1, le=100),
    sort: str = "score",
    offset: int = 0,
    limit: int = 40,
    session: AsyncSession = Depends(get_session),
):
    if section not in {"jobs", "announcements", "trash"}:
        raise HTTPException(422, "Geçersiz fırsat bölümü")
    if sort not in {"score", "score_asc", "newest", "oldest", "deadline"}:
        raise HTTPException(422, "Geçersiz sıralama")
    if min_score is not None and max_score is not None and min_score > max_score:
        raise HTTPException(422, "Minimum skor maksimum skordan büyük olamaz")
    return await browse_opportunities(
        session,
        BrowseFilters(
            section=section,
            announcement_source=announcement_source,
            category=category,
            search=search,
            status=status,
            source=source,
            region=region,
            remote=remote,
            period_days=min(period_days, 3650) if period_days else None,
            year=year,
            min_score=min_score if section == "jobs" else None,
            max_score=max_score if section == "jobs" else None,
            sort=sort,
            offset=max(offset, 0),
            limit=min(max(limit, 1), 120),
        ),
    )


@router.get("/opportunities/followups", response_model=list[service.FollowupOut])
async def followups(
    days: int = 30, session: AsyncSession = Depends(get_session),
):
    return await service.list_followups(session, days=min(days, 90))


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


# Application CRM endpointleri
# ═════════════════════════════════════════════════════════════════════


@router.get("/applications/rejection-reasons")
async def rejection_reasons():
    return service.REJECTION_REASONS


@router.get("/applications/funnel", response_model=service.FunnelOut)
async def applications_funnel(session: AsyncSession = Depends(get_session)):
    return await service.funnel(session)


@router.get("/opportunities/{item_id}/application", response_model=service.ApplicationOut)
async def application_detail(item_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await service.get_application(session, item_id)
    if result is None:
        raise HTTPException(404)
    return result


@router.put("/opportunities/{item_id}/application", response_model=service.ApplicationOut)
async def application_update(
    item_id: UUID, body: service.ApplicationIn, session: AsyncSession = Depends(get_session),
):
    result = await service.upsert_application(session, item_id, body)
    if result is None:
        raise HTTPException(404)
    return result


@router.post("/opportunities/{item_id}/apply", response_model=service.OpportunityOut)
async def apply(
    item_id: UUID, body: service.ApplyIn, session: AsyncSession = Depends(get_session),
):
    """Basvur: durum applied, snapshot + CV kunyesi ilk kayitta saklanir."""
    try:
        result = await service.apply(session, item_id, body)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if result is None:
        raise HTTPException(404)
    return result


@router.get("/opportunities/{item_id}/history", response_model=list[service.HistoryOut])
async def history(item_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.list_history(session, item_id)


@router.post("/opportunities/{item_id}/transition", response_model=service.OpportunityOut)
async def transition(
        item_id: UUID, body: TransitionIn, session: AsyncSession = Depends(get_session),
):
    """Durum gecisi: gecmis + event yazar; terminal durumlara takilir."""
    try:
        result = await service.transition_status(
            session, item_id, to=body.to, note=body.note,
            rejection_reason=body.rejection_reason,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if result is None:
        raise HTTPException(404)
    return result


@router.get("/opportunities/{item_id}/interviews", response_model=list[service.InterviewOut])
async def interviews(item_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.list_interviews(session, item_id)


@router.post(
    "/opportunities/{item_id}/interviews", response_model=service.InterviewOut, status_code=201)
async def add_interview(
    item_id: UUID, body: service.InterviewIn, session: AsyncSession = Depends(get_session),
):
    result = await service.add_interview(session, item_id, body)
    if result is None:
        raise HTTPException(404)
    return result


@router.patch("/interviews/{interview_id}", response_model=service.InterviewOut)
async def patch_interview(
    interview_id: UUID, body: service.InterviewIn, session: AsyncSession = Depends(get_session),
):
    result = await service.patch_interview(session, interview_id, body)
    if result is None:
        raise HTTPException(404)
    return result


@router.delete("/interviews/{interview_id}", status_code=204)
async def delete_interview(interview_id: UUID, session: AsyncSession = Depends(get_session)):
    if not await service.delete_interview(session, interview_id):
        raise HTTPException(404)


# Kaynak/jobhunter uclari (sources*, sync*, jobhunter) sources_router'da.
# include_router() bu FastAPI surumunde lazy _IncludedRouter sarmali uretir ve
# route.path erisimini kiran testlerle uyumsuzdur; rotalari dogrudan ekliyoruz.
router.routes.extend(sources_router.routes)
