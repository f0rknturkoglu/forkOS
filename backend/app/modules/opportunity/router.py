import os
from pathlib import Path
from typing import Literal
from uuid import UUID

import yaml
from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import log_event
from app.core.links import link
from app.core.models import Entity, Link, SourceRun
from app.db import get_session
from app.modules.opportunity import service
from app.modules.opportunity import sync as sync_service
from app.modules.opportunity.models import Opportunity, OpportunityRequirement
from app.modules.opportunity.schemas import (
    DeadlineOut,
    OpportunityIn,
    OpportunityOut,
    OpportunityPatch,
    RequirementIn,
    SourceRefreshOut,
    SourceSyncBatchOut,
       SourceSyncStatusOut,
    TransitionIn,
)
from app.modules.todo import service as todo_service
from app.modules.todo.models import Todo
from app.modules.todo.schemas import TodoIn, TodoOut
from app.sources import forkjob_port
from app.sources.announcements import SOURCES as ANNOUNCEMENT_SOURCES
from app.sources.forkjob_core.config import load_config
from app.sources.forkjob_core.linkedin_profiles import LinkedInProfile, LinkedInProfiles
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


@router.get("/deadlines", response_model=list[DeadlineOut])
async def deadlines(session: AsyncSession = Depends(get_session)):
    rows = (
        (await session.execute(text("select * from deadline_v order by due_at limit 200")))
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]


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
async def sync_status(
    scope: Literal["opportunity", "media"] = "opportunity",
    session: AsyncSession = Depends(get_session),
):
    """Aktif manuel batch ve kaynak bazli kesin ilerleme."""
    return await sync_service.current_status(session, scope=scope)


@router.get("/sources/sync/history", response_model=list[SourceSyncBatchOut])
async def sync_history(
    limit: int = 10,
    scope: Literal["opportunity", "media"] = "opportunity",
    session: AsyncSession = Depends(get_session),
):
    return await sync_service.history(session, min(limit, 50), scope=scope)


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

# ═════════════════════════════════════════════════════════════════════
# Jobhunter ayarlari — uyum profili (scoring), LinkedIn, ortam
# ═════════════════════════════════════════════════════════════════════

_JOBHUNTER_CONFIG = Path("config.yaml")


def _scoring_payload(cfg) -> dict:
    sc, bc = cfg.scoring, cfg.balance
    return {
        "scoring": {
            "base": sc.base,
            "skills": [{"name": s.name, "points": s.points, "aliases": s.aliases}
                         for s in sc.skills],
            "skill_max": sc.skill_max,
            "skill_title_multiplier": sc.skill_title_multiplier,
            "role_terms": sc.role_terms,
            "role_mismatch_penalty": sc.role_mismatch_penalty,
            "role_description_relief": sc.role_description_relief,
            "level_words": sc.level_words,
            "level_bonus": sc.level_bonus,
            "level_description_factor": sc.level_description_factor,
            "seniority_tiers": [{"label": t.label, "penalty": t.penalty, "words": t.words}
                                  for t in sc.seniority_tiers],
            "seniority_title_only": sc.seniority_title_only,
            "visa_bonus": sc.visa_bonus,
            "visa_penalty": sc.visa_penalty,
            "visa_eu_only": sc.visa_eu_only,
            "spanish_requirement_penalty": sc.spanish_requirement_penalty,
            "english_working_bonus": sc.english_working_bonus,
            "experience_bands": [{"max_years": b.max_years, "delta": b.delta, "label": b.label}
                                   for b in sc.experience_bands],
            "tr_office_cities": sc.tr_office_cities,
            "tr_relocation_penalty": sc.tr_relocation_penalty,
            "freshness_grace_days": sc.freshness_grace_days,
            "freshness_penalty_per_day": sc.freshness_penalty_per_day,
            "freshness_max_penalty": sc.freshness_max_penalty,
            "freshness_factors": sc.freshness_factors,
            "kill_words": sc.kill_words,
            "kill_score": sc.kill_score,
            "score_cap": sc.score_cap,
            "score_floor": sc.score_floor,
        },
        "balance": {
            "quotas": bc.quotas,
            "quota_min_score": bc.quota_min_score,
            "interleave": bc.interleave,
            "floor": bc.floor,
            "allow_overflow": bc.allow_overflow,
        },
    }


@router.get("/sources/jobhunter/config")
async def jobhunter_config():
    cfg = load_config(_JOBHUNTER_CONFIG)
    return _scoring_payload(cfg)


@router.put("/sources/jobhunter/config")
async def jobhunter_config_update(body: dict):
    """Uyum profili ve dengeler. config.yaml a yazilir ve SICAK yuklenir.

    Yeni skorlar bir sonraki senkron turunda gecerli olur (forkjob_port.SCORING
    aninda guncellenir).
    """
    if not isinstance(body.get("scoring"), dict):
        raise HTTPException(422, "scoring objesi gerekli")
    _JOBHUNTER_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    header = "# forkjob scoring & balance -- forkOS ayarlar panelinden yonetilir.\n\n"
    _JOBHUNTER_CONFIG.write_text(
        header + yaml.safe_dump(body, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )
    forkjob_port.SCORING = load_config(_JOBHUNTER_CONFIG)
    return {"ok": True}


@router.get("/sources/jobhunter/linkedin-profiles")
async def jobhunter_linkedin_profiles():
    return [p.to_dict() for p in LinkedInProfiles.load()]


@router.put("/sources/jobhunter/linkedin-profiles")
async def jobhunter_linkedin_profiles_save(body: list = Body(...)):
    """Kullanici LinkedIn arama profillerinin tamami -- atomik YAML yazimi."""
    if not isinstance(body, list):
        raise HTTPException(422, "liste bekleniyor")
    parsed: list[LinkedInProfile] = []
    for entry in body:
        if not isinstance(entry, dict) or not str(entry.get("term", "")).strip():
            raise HTTPException(422, "her profil en az 'term' ister")
        parsed.append(LinkedInProfile.from_dict(entry))
    collection = LinkedInProfiles()
    collection.profiles = parsed
    collection.save()
    return {"saved": len(parsed)}


@router.get("/sources/jobhunter/env")
async def jobhunter_env():
    return {
        "linkein_allow_direct": os.environ.get("LINKEDIN_ALLOW_DIRECT", ""),
        "proxies_file": os.environ.get("FORKJOB_LINKEDIN_PROXIES_FILE", ""),
    }


# ═════════════════════════════════════════════════════════════════════
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
