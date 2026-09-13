from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import log_event
from app.core.links import link
from app.core.models import Entity, Link
from app.db import get_session
from app.modules.note import service as note_service
from app.modules.note.schemas import NoteIn, NoteOut
from app.modules.opportunity import career as career_service
from app.modules.opportunity import lifecycle, service
from app.modules.opportunity.browse import BrowseFilters, browse_opportunities
from app.modules.opportunity.intelligence import (
    classify_reply,
    enrich_opportunities,
    evaluate_opportunity,
    list_silent_applications,
    update_evaluation,
)
from app.modules.opportunity.models import Application, Opportunity, OpportunityRequirement
from app.modules.opportunity.schemas import (
    ApplicationTimelineOut,
    CareerConnectionOut,
    CareerConnectionsImportOut,
    CareerStoryIn,
    CareerStoryOut,
    CareerStoryPatch,
    CoverLetterReviewIn,
    CoverLetterReviewOut,
    OpportunityBrowseOut,
    OpportunityConnectionsOut,
    OpportunityEvaluationOut,
    OpportunityEvaluationPatch,
    OpportunityIn,
    OpportunityOut,
    OpportunityPatch,
    PrunePreviewOut,
    PruneResultOut,
    ReplyAnalysisIn,
    ReplyAnalysisOut,
    RequirementIn,
    RequirementOut,
    SalaryConsistencyOut,
    SilentApplicationOut,
    TransitionIn,
)
from app.modules.opportunity.sources_router import router as sources_router
from app.modules.todo import service as todo_service
from app.modules.todo.models import Todo
from app.modules.todo.schemas import TodoIn, TodoOut

router = APIRouter(tags=["opportunities"])


class RequirementDocumentIn(BaseModel):
    document_entity_id: UUID | None


async def _load_opportunity(session: AsyncSession, item_id: UUID) -> Opportunity:
    item = await session.get(Opportunity, item_id)
    if item is None:
        raise HTTPException(404, "Fırsat bulunamadı")
    return item


def _require_job(item: Opportunity) -> None:
    """Basvuru/CV/mulakat uclari duyurularda calismaz (Faz 1.3)."""
    if not lifecycle.is_job_kind(item.kind):
        raise HTTPException(
            409, "Bu işlem yalnızca iş ilanları için geçerlidir; duyurularda kullanılamaz"
        )


def _require_announcement(item: Opportunity) -> None:
    if lifecycle.is_job_kind(item.kind):
        raise HTTPException(
            409, "Bu işlem yalnızca duyurular için geçerlidir; iş ilanlarında kullanılamaz"
        )


@router.get("/career/stories", response_model=list[CareerStoryOut])
async def career_stories(session: AsyncSession = Depends(get_session)):
    return await career_service.list_stories(session)


@router.post("/career/stories", response_model=CareerStoryOut, status_code=201)
async def create_career_story(
    body: CareerStoryIn,
    session: AsyncSession = Depends(get_session),
):
    return await career_service.create_story(session, body)


@router.patch("/career/stories/{story_id}", response_model=CareerStoryOut)
async def patch_career_story(
    story_id: UUID,
    body: CareerStoryPatch,
    session: AsyncSession = Depends(get_session),
):
    result = await career_service.patch_story(session, story_id, body)
    if result is None:
        raise HTTPException(404, "Kariyer hikâyesi bulunamadı")
    return result


@router.delete("/career/stories/{story_id}", status_code=204)
async def archive_career_story(
    story_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    if not await career_service.archive_story(session, story_id):
        raise HTTPException(404, "Kariyer hikâyesi bulunamadı")


@router.post("/career/cover-letter-review", response_model=CoverLetterReviewOut)
async def cover_letter_review(
    body: CoverLetterReviewIn,
    session: AsyncSession = Depends(get_session),
):
    return await career_service.review_cover_letter(session, body.text)


@router.get("/career/connections", response_model=list[CareerConnectionOut])
async def career_connections(
    search: str | None = None,
    limit: int = Query(200, ge=1, le=2000),
    session: AsyncSession = Depends(get_session),
):
    return await career_service.list_connections(session, search=search, limit=limit)


@router.post("/career/connections/import", response_model=CareerConnectionsImportOut)
async def import_career_connections(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    if not (file.filename or "").casefold().endswith(".csv"):
        raise HTTPException(422, "LinkedIn Connections.csv dosyasi bekleniyor")
    content = await file.read(10 * 1024 * 1024 + 1)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "Connections.csv en fazla 10 MB olabilir")
    try:
        return await career_service.import_connections(session, content)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get(
    "/opportunities/{item_id}/connections",
    response_model=OpportunityConnectionsOut,
)
async def connections_for_opportunity(
    item_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    _require_job(await _load_opportunity(session, item_id))
    result = await career_service.opportunity_connections(session, item_id)
    if result is None:
        raise HTTPException(404, "Fırsat bulunamadı")
    return result


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
    archetype: str | None = None,
    recommendation: str | None = None,
    period_days: int | None = None,
    year: int | None = None,
    min_score: float | None = Query(None, ge=-1, le=100),
    max_score: float | None = Query(None, ge=-1, le=100),
    skill: str | None = None,
    min_skill_match: float | None = Query(None, ge=0, le=1),
    max_skill_match: float | None = Query(None, ge=0, le=1),
    skill_match_state: Literal["any", "computed", "uncomputed"] | None = None,
    source_status: Literal["active", "stale", "all"] = "active",
    sort: str = "score",
    offset: int = 0,
    limit: int = 40,
    session: AsyncSession = Depends(get_session),
):
    if section not in {"jobs", "announcements", "trash"}:
        raise HTTPException(422, "Geçersiz fırsat bölümü")
    if sort not in {"score", "score_asc", "skill_match", "newest", "oldest", "deadline"}:
        raise HTTPException(422, "Geçersiz sıralama")
    if min_score is not None and max_score is not None and min_score > max_score:
        raise HTTPException(422, "Minimum skor maksimum skordan büyük olamaz")
    if (
        min_skill_match is not None
        and max_skill_match is not None
        and min_skill_match > max_skill_match
    ):
        raise HTTPException(422, "Minimum uyum maksimum uyumdan büyük olamaz")
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
            archetype=archetype if section == "jobs" else None,
            recommendation=recommendation if section == "jobs" else None,
            period_days=min(period_days, 3650) if period_days else None,
            year=year,
            min_score=min_score if section == "jobs" else None,
            max_score=max_score if section == "jobs" else None,
            skill=skill if section == "jobs" else None,
            min_skill_match=min_skill_match if section == "jobs" else None,
            max_skill_match=max_skill_match if section == "jobs" else None,
            skill_match_state=(
                skill_match_state
                if section == "jobs" and skill_match_state not in (None, "any")
                else None
            ),
            source_status=source_status,
            sort=sort,
            offset=max(offset, 0),
            limit=min(max(limit, 1), 120),
        ),
    )


@router.get("/opportunities/lifecycle")
async def opportunity_lifecycle():
    """Kesif, basvuru ve duyuru durum makineleri.

    Frontend durum seceneklerini ve izinli gecisleri BURADAN okur; elle
    kopyalanmis statu listesi tutmaz (AGENTS.md kural 13).
    """
    return lifecycle.lifecycle_payload()


@router.get("/opportunities/followups", response_model=list[service.FollowupOut])
async def followups(
    days: int = 30,
    session: AsyncSession = Depends(get_session),
):
    return await service.list_followups(session, days=min(days, 90))


@router.get("/opportunities/silence", response_model=list[SilentApplicationOut])
async def silent_applications(
    days: int = Query(21, ge=7, le=90),
    session: AsyncSession = Depends(get_session),
):
    return await list_silent_applications(session, days=days)


@router.get(
    "/opportunities/{item_id}/salary-consistency",
    response_model=SalaryConsistencyOut,
)
async def opportunity_salary_consistency(
    item_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    _require_job(await _load_opportunity(session, item_id))
    return await career_service.salary_consistency(session, item_id)


@router.post(
    "/opportunities/{item_id}/evaluation",
    response_model=OpportunityEvaluationOut,
)
async def generate_evaluation(
    item_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    _require_job(await _load_opportunity(session, item_id))
    result = await evaluate_opportunity(session, item_id)
    if result is None:
        raise HTTPException(404, "Fırsat bulunamadı")
    return result


@router.put(
    "/opportunities/{item_id}/evaluation",
    response_model=OpportunityEvaluationOut,
)
async def save_evaluation(
    item_id: UUID,
    body: OpportunityEvaluationPatch,
    session: AsyncSession = Depends(get_session),
):
    _require_job(await _load_opportunity(session, item_id))
    try:
        result = await update_evaluation(session, item_id, body)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if result is None:
        raise HTTPException(409, "Önce ilanı değerlendirin")
    return result


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
    app = await service.get_application(session, item_id)
    enriched = await enrich_opportunities(
        session, [row], [service._out(row, application=app)]
    )
    return enriched[0]


@router.post(
    "/opportunities/{item_id}/reply-analysis",
    response_model=ReplyAnalysisOut,
)
async def reply_analysis(
    item_id: UUID,
    body: ReplyAnalysisIn,
    session: AsyncSession = Depends(get_session),
):
    _require_job(await _load_opportunity(session, item_id))
    return classify_reply(body.text)


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


@router.get("/opportunities/{item_id}/requirements", response_model=list[RequirementOut])
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


@router.post("/opportunities/{item_id}/requirements", response_model=RequirementOut, status_code=201)
async def requirement(
    item_id: UUID, body: RequirementIn, session: AsyncSession = Depends(get_session)
):
    # Belge gereksinimi duyurularda da anlamli (kilavuz, ek belge, basvuru kosulu).
    await _load_opportunity(session, item_id)
    result = await service.add_requirement(session, item_id, body)
    if result is None:
        raise HTTPException(404)
    return result


@router.patch("/requirements/{requirement_id}/document", response_model=RequirementOut)
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


@router.get("/opportunities/{item_id}/notes", response_model=list[NoteOut])
async def opportunity_notes(item_id: UUID, session: AsyncSession = Depends(get_session)):
    if await session.get(Opportunity, item_id) is None:
        raise HTTPException(404, "Fırsat bulunamadı")
    return await note_service.list_notes(session, about=item_id)


@router.post("/opportunities/{item_id}/research-note", response_model=NoteOut)
async def get_or_create_research_note(item_id: UUID, session: AsyncSession = Depends(get_session)):
    item = await session.get(Opportunity, item_id)
    if item is None:
        raise HTTPException(404, "Fırsat bulunamadı")
    existing = await note_service.list_notes(session, about=item_id)
    if existing:
        return existing[0]

    entity = await session.get(Entity, item_id)
    title = entity.title if entity else (item.organization or "Fırsat")
    org = item.organization or "Kurum"
    body = (
        f"# {org} — {title}\n\n"
        f"- **Pozisyon:** {title}\n"
        f"- **Kurum:** {org}\n"
        f"- **İlan:** {item.url or 'Yok'}\n"
        f"- **Durum:** {item.status}\n\n"
        f"## Şirket Araştırması\n"
        f"- Faaliyet Alanı & Ürünler:\n"
        f"- Teknoloji Yığını:\n"
        f"- Kültür & Güncel Gelişmeler:\n\n"
        f"## Mülakat Hazırlığı\n"
        f"- Neden bu rol ve şirket?\n"
        f"- Görüşmeciye Sorulacak Sorular:\n"
        f"  1. \n"
        f"  2. \n\n"
        f"## Görüşme Notları\n"
        f"- \n"
    )
    note = await note_service.create(
        session,
        NoteIn(body=body, relate_to=item_id, tags=["mülakat", "araştırma"]),
    )
    return note


# Application CRM endpointleri
# ═════════════════════════════════════════════════════════════════════


@router.get("/applications/rejection-reasons")
async def rejection_reasons():
    return service.REJECTION_REASONS


@router.get("/applications/funnel", response_model=service.FunnelOut)
async def applications_funnel(session: AsyncSession = Depends(get_session)):
    return await service.funnel(session)


@router.get("/applications", response_model=list[OpportunityOut])
async def applications_list(
    status: str | None = None,
    limit: int = Query(120, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    """Başvurular çalışma alanı: YALNIZCA gerçek başvuru kayıtları.

    Keşfedilmiş ilanlar buraya hiçbir koşulda girmez (Faz 4.1).
    """
    if status is not None and status not in lifecycle.APPLICATION_FLOW:
        raise HTTPException(422, "Geçersiz başvuru durumu")
    rows = (
        await session.execute(
            select(Opportunity, Entity.title, Application)
            .join(Entity, Entity.id == Opportunity.id)
            .join(Application, Application.opportunity_id == Opportunity.id)
            .where(
                Opportunity.trashed_at.is_(None),
                *( [Application.status == status] if status else [] ),
            )
            .order_by(
                Application.status_changed_at.desc().nulls_last(),
                Opportunity.found_at.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
    ).all()
    outs = [
        service._out((opportunity, title), include_raw=False, application=application)
        for opportunity, title, application in rows
    ]
    return outs


@router.get("/opportunities/{item_id}/application", response_model=service.ApplicationOut)
async def application_detail(item_id: UUID, session: AsyncSession = Depends(get_session)):
    _require_job(await _load_opportunity(session, item_id))
    result = await service.get_application(session, item_id)
    if result is None:
        raise HTTPException(404)
    return result


@router.put("/opportunities/{item_id}/application", response_model=service.ApplicationOut)
async def application_update(
    item_id: UUID,
    body: service.ApplicationIn,
    session: AsyncSession = Depends(get_session),
):
    _require_job(await _load_opportunity(session, item_id))
    try:
        result = await service.upsert_application(session, item_id, body)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    if result is None:
        raise HTTPException(404)
    return result


@router.post("/opportunities/{item_id}/apply", response_model=service.OpportunityOut)
async def apply(
    item_id: UUID,
    body: service.ApplyIn,
    session: AsyncSession = Depends(get_session),
):
    """Basvur: basvuru kaydi 'applied' olur, snapshot + CV kunyesi saklanir."""
    try:
        result = await service.apply(session, item_id, body)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    if result is None:
        raise HTTPException(404)
    return result


@router.post("/applications/{item_id}/transition", response_model=service.ApplicationOut)
async def application_transition(
    item_id: UUID,
    body: TransitionIn,
    session: AsyncSession = Depends(get_session),
):
    """Basvuru hatti gecisi (yalnizca gercek basvuru kayitlari)."""
    try:
        result = await service.transition_application(
            session,
            item_id,
            to=body.to,
            note=body.note,
            rejection_reason=body.rejection_reason,
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    if result is None:
        raise HTTPException(404, "Bu fırsat için başvuru kaydı yok")
    return await service.get_application(session, item_id)


@router.get("/opportunities/{item_id}/timeline", response_model=ApplicationTimelineOut)
async def application_timeline(item_id: UUID, session: AsyncSession = Depends(get_session)):
    """Birlesik basvuru zaman cizelgesi (kesif + basvuru + gorusme + not + gorev)."""
    result = await service.timeline(session, item_id)
    if result is None:
        raise HTTPException(404)
    return result


@router.get("/opportunities/{item_id}/history", response_model=list[service.HistoryOut])
async def history(item_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.list_history(session, item_id)


@router.post("/opportunities/{item_id}/transition", response_model=service.OpportunityOut)
async def transition(
    item_id: UUID,
    body: TransitionIn,
    session: AsyncSession = Depends(get_session),
):
    """Kesif/duyuru durum gecisi: gecmis + event yazar; tur kumesine uyar."""
    try:
        result = await service.transition_status(session, item_id, to=body.to, note=body.note)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    if result is None:
        raise HTTPException(404)
    return result


@router.get("/opportunities/{item_id}/interviews", response_model=list[service.InterviewOut])
async def interviews(item_id: UUID, session: AsyncSession = Depends(get_session)):
    _require_job(await _load_opportunity(session, item_id))
    return await service.list_interviews(session, item_id)


@router.post(
    "/opportunities/{item_id}/interviews", response_model=service.InterviewOut, status_code=201
)
async def add_interview(
    item_id: UUID,
    body: service.InterviewIn,
    session: AsyncSession = Depends(get_session),
):
    _require_job(await _load_opportunity(session, item_id))
    result = await service.add_interview(session, item_id, body)
    if result is None:
        raise HTTPException(404)
    return result


@router.patch("/interviews/{interview_id}", response_model=service.InterviewOut)
async def patch_interview(
    interview_id: UUID,
    body: service.InterviewIn,
    session: AsyncSession = Depends(get_session),
):
    result = await service.patch_interview(session, interview_id, body)
    if result is None:
        raise HTTPException(404)
    return result


@router.delete("/interviews/{interview_id}", status_code=204)
async def delete_interview(interview_id: UUID, session: AsyncSession = Depends(get_session)):
    if not await service.delete_interview(session, interview_id):
        raise HTTPException(404)


def _prune_token(preview) -> str:
    """Onizleme ile uygulama arasinda bag: veri degisirse token da degisir."""
    stamp = datetime.now(UTC).strftime("%Y%m%d%H")
    payload = f"prune:{preview.days}:{preview.candidates}:{preview.protected}:{preview.archived}:{stamp}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@router.get("/opportunities/prune/preview", response_model=PrunePreviewOut)
async def prune_preview(
    days: int = Query(90, ge=7, le=3650),
    session: AsyncSession = Depends(get_session),
):
    """Dry-run: ne silinir, ne korunur, tahmini ne kadar yer bosalir.

    Silme yalnizca bu onizlemeden alinan `confirm_token` ile yapilir; boylece
    tek tikla geri alinamaz veri kaybi olmaz (Faz 2.3).
    """
    preview = await service.prune_preview(session, days=days)
    return PrunePreviewOut(
        candidates=preview.candidates,
        protected=preview.protected,
        archived=preview.archived,
        estimated_bytes=preview.estimated_bytes,
        days=preview.days,
        confirm_token=_prune_token(preview),
    )


@router.post("/opportunities/prune", response_model=PruneResultOut)
async def prune_opportunities(
    days: int = Query(90, ge=7, le=3650),
    confirm_token: str = Query(..., min_length=8, max_length=64),
    session: AsyncSession = Depends(get_session),
):
    """Onaylanmis silme: yalnizca sahipsiz ham ilanlar gider, event uretilir."""
    preview = await service.prune_preview(session, days=days)
    if confirm_token != _prune_token(preview):
        raise HTTPException(
            409,
            "Önizleme bayatladı: önce /opportunities/prune/preview ile yeniden onay alın",
        )
    result = await service.prune_stale_opportunities(session, days=days)
    return PruneResultOut(**result)


# Kaynak/jobhunter uclari (sources*, sync*, jobhunter) sources_router'da.
# include_router() bu FastAPI surumunde lazy _IncludedRouter sarmali uretir ve
# route.path erisimini kiran testlerle uyumsuzdur; rotalari dogrudan ekliyoruz.
router.routes.extend(sources_router.routes)
