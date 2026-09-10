"""Opportunity kaynak/jobhunter senkron uclari (sources*, jobhunter, sync*)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import SourceRun
from app.db import get_session
from app.modules.opportunity import sync as sync_service
from app.modules.opportunity.schemas import (
    SourceRefreshOut,
    SourceSyncBatchOut,
    SourceSyncStatusOut,
)
from app.sources import forkjob_port
from app.sources.announcements import SOURCES as ANNOUNCEMENT_SOURCES
from app.sources.forkjob_core.config import load_config
from app.sources.forkjob_core.linkedin_profiles import LinkedInProfile, LinkedInProfiles
from app.sources.forkjob_port import forkjob_sources

router = APIRouter(tags=["opportunities"])


class SourceRefreshIn(BaseModel):
    """Bos govde = katalogun tamami."""

    source_ids: list[str] | None = None
    kind: Literal["job", "announcement"] | None = None


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
            #: Portalin katalog kategorisi (startup/regional/...) — LayerB portal
            #: kayitlarinda tanimli; ATS/duyuru kaynaklarinda yoktur.
            "category": getattr(source, "category", None),
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
    body: SourceRefreshIn,
    background: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """Secmeli ya da toplu cekim.

    source_ids verilirse yalnizca onlar; kind verilirse o turun tamami; ikisi
    de bossa katalogun hepsi. API yalnızca kalıcı batch oluşturur; çekimi
    API arka plan görevi tüketir; worker açıkken aynı kalıcı kuyruğu paylaşır.
    """
    from app.worker.jobs import drain_source_sync_batches

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
    background.add_task(drain_source_sync_batches)
    return {
        "batch_id": str(batch.id),
        "queued": len(newly_queued),
        "total_sources": batch.total_sources,
    }


@router.post("/sources/{source_id:path}/refresh")
async def refresh_source(
    source_id: str,
    background: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    from app.worker.jobs import drain_source_sync_batches

    try:
        catalog = {
            source.id for source in [*forkjob_sources(include_opt_in=True), *ANNOUNCEMENT_SOURCES]
        }
        if source_id not in catalog:
            raise KeyError(source_id)
        batch, newly_queued = await sync_service.create_or_extend_batch(session, [source_id])
        await session.commit()
        if not newly_queued:
            background.add_task(drain_source_sync_batches)
            return {"source": source_id, "added": 0, "batch_id": str(batch.id)}
    except KeyError as exc:
        raise HTTPException(404, "kaynak bulunamadı") from exc
    background.add_task(drain_source_sync_batches)
    return {"source": source_id, "added": 0, "batch_id": str(batch.id)}


# ═════════════════════════════════════════════════════════════════════
# Jobhunter ayarlari — uyum profili (scoring), LinkedIn, ortam


_JOBHUNTER_CONFIG = Path("config.yaml")


def _scoring_payload(cfg) -> dict:
    sc, bc = cfg.scoring, cfg.balance
    return {
        "scoring": {
            "base": sc.base,
            "skills": [
                {"name": s.name, "points": s.points, "aliases": s.aliases} for s in sc.skills
            ],
            "skill_max": sc.skill_max,
            "skill_title_multiplier": sc.skill_title_multiplier,
            "role_terms": sc.role_terms,
            "role_mismatch_penalty": sc.role_mismatch_penalty,
            "role_description_relief": sc.role_description_relief,
            "level_words": sc.level_words,
            "level_bonus": sc.level_bonus,
            "level_description_factor": sc.level_description_factor,
            "seniority_tiers": [
                {"label": t.label, "penalty": t.penalty, "words": t.words}
                for t in sc.seniority_tiers
            ],
            "seniority_title_only": sc.seniority_title_only,
            "visa_bonus": sc.visa_bonus,
            "visa_penalty": sc.visa_penalty,
            "visa_eu_only": sc.visa_eu_only,
            "spanish_requirement_penalty": sc.spanish_requirement_penalty,
            "english_working_bonus": sc.english_working_bonus,
            "experience_bands": [
                {"max_years": b.max_years, "delta": b.delta, "label": b.label}
                for b in sc.experience_bands
            ],
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
