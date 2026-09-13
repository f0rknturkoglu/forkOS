"""Opportunity kaynak/jobhunter senkron uclari (sources*, jobhunter, sync*)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import runs as runs_service
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
from app.sources.base import (
    SourceClass,
    env_flag,
    is_general_refresh_source,
    is_opt_in,
    order_by_class,
    source_class,
    source_estimated_seconds,
    source_timeout_seconds,
)
from app.sources.forkjob_core.config import load_config
from app.sources.forkjob_core.linkedin_profiles import LinkedInProfile, LinkedInProfiles
from app.sources.forkjob_core.scrapers.base import (
    ScraperConfig,
    cache_stats,
    clear_cache,
    prune_cache,
)
from app.sources.forkjob_port import forkjob_sources

router = APIRouter(tags=["opportunities"])


class SourceRefreshIn(BaseModel):
    """Bos govde = genel yenileme (critical + normal; opt-in HARIC)."""

    source_ids: list[str] | None = None
    kind: Literal["job", "announcement"] | None = None
    #: critical = yalnizca resmi/hizli kaynaklar; general = opt-in/yavas
    #: kaynaklar haric (varsayilan); full = katalogun tamami.
    mode: Literal["critical", "general", "full"] = "general"


class SourceRefreshResult(SourceRefreshOut):
    estimated_seconds: int = 0
    mode: str = "general"


class CachePruneIn(BaseModel):
    max_bytes: int | None = None
    max_age_seconds: int | None = None


class CacheClearIn(BaseModel):
    confirm: bool = False


def _catalog_sources() -> list:
    return [*forkjob_sources(include_opt_in=True), *ANNOUNCEMENT_SOURCES]


@router.get("/sources/runs")
async def source_runs(session: AsyncSession = Depends(get_session)):
    rows = list(
        (
            await session.execute(
                select(SourceRun).order_by(SourceRun.started_at.desc()).limit(100)
            )
        ).scalars()
    )
    return [
        {
            "id": run.id,
            "source": run.source,
            "status": run.status,
            "items_found": run.items_found,
            "error": runs_service.error_message_of(run),
            "error_kind": runs_service.error_kind_of(run),
            "batch_id": run.batch_id,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
        }
        for run in rows
    ]


@router.get("/sources/catalog")
async def source_catalog(session: AsyncSession = Depends(get_session)):
    """Kaynak katalogu: sinif, tahmini sure ve devre kesici durumu."""
    sources = _catalog_sources()
    states = await runs_service.circuit_states(session, [source.id for source in sources])
    return [
        {
            "id": source.id,
            "interval_minutes": source.interval_minutes,
            "kind": "announcement" if source in ANNOUNCEMENT_SOURCES else "job",
            #: Portalin katalog kategorisi (startup/regional/...) — LayerB portal
            #: kayitlarinda tanimli; ATS/duyuru kaynaklarinda yoktur.
            "category": getattr(source, "category", None),
            #: Yenileme sirasi / timeout / kapanma bekleme sinifi.
            "class": source_class(source).value,
            "estimated_seconds": source_estimated_seconds(source),
            "timeout_seconds": source_timeout_seconds(source),
            "opt_in": is_opt_in(source),
            "circuit_open": states.get(source.id, {}).get("open", False),
            "consecutive_failures": states.get(source.id, {}).get("consecutive_failures", 0),
        }
        for source in sources
    ]


@router.get("/sources/coverage")
async def source_coverage(session: AsyncSession = Depends(get_session)):
    """Kaynak kapsam matrisi: hangi kurumu takip ediyoruz, hangisi eksik?

    Her satir bir kaynaktir; resmi/ikincil ayrimi, son basarili kosu, son yeni
    icerik, ortalama yayin araligi ve ust uste bos kosu sayisi tek yerde durur.
    """
    sources = _catalog_sources()
    ids = [source.id for source in sources]
    recent = (
        await session.execute(
            select(
                SourceRun.source,
                SourceRun.status,
                SourceRun.started_at,
                SourceRun.items_found,
                SourceRun.error,
                SourceRun.error_kind,
                func.row_number()
                .over(partition_by=SourceRun.source, order_by=SourceRun.started_at.desc())
                .label("rank"),
            ).where(SourceRun.source.in_(ids))
        )
    ).all()
    history: dict[str, list] = {source.id: [] for source in sources}
    for row in recent:
        if row.rank > 50:
            continue
        history.setdefault(row.source, []).append(row)

    states = await runs_service.circuit_states(session, ids)
    rows = []
    for source in sources:
        runs = history.get(source.id, [])
        last = runs[0] if runs else None
        ok_runs = [run for run in runs if run.status == "ok"]
        with_content = [run for run in ok_runs if run.items_found > 0]
        gaps = [
            (with_content[index].started_at - with_content[index + 1].started_at).total_seconds()
            / 86400
            for index in range(len(with_content) - 1)
        ]
        consecutive_empty = 0
        for run in runs:
            if run.status == "empty":
                consecutive_empty += 1
            else:
                break
        state = states.get(source.id, {})
        rows.append(
            {
                "source": source.id,
                "kind": "announcement" if source in ANNOUNCEMENT_SOURCES else "job",
                "class": source_class(source).value,
                "category": getattr(source, "category", None),
                #: Resmi kaynak mi, ikincil/aggregator mu? Adapter bilmiyorsa null.
                "official": getattr(source, "official", None),
                "url": getattr(source, "url", None) or getattr(source, "homepage", None),
                "parser_version": getattr(source, "parser_version", None),
                "last_status": last.status if last else None,
                "last_run_at": last.started_at if last else None,
                "last_success_at": ok_runs[0].started_at if ok_runs else None,
                "last_new_content_at": with_content[0].started_at if with_content else None,
                "avg_publish_interval_days": (
                    round(sum(gaps) / len(gaps), 1) if gaps else None
                ),
                "consecutive_empty": consecutive_empty,
                "last_error": (last.error if last and last.status == "error" else None),
                "last_error_kind": (
                    runs_service.error_kind_of(last) if last and last.status == "error" else None
                ),
                "circuit_open": state.get("open", False),
                "consecutive_failures": state.get("consecutive_failures", 0),
                "tracked": True,
            }
        )
    return rows


@router.get("/sources/sync", response_model=SourceSyncStatusOut)
async def sync_status(
    background: BackgroundTasks,
    scope: Literal["opportunity", "media"] = "opportunity",
    session: AsyncSession = Depends(get_session),
):
    """Aktif manuel batch ve kaynak bazli kesin ilerleme.

    Okuma ayni zamanda uzlastirir: worker kapaliyken terk edilmis sahiplikler
    geri alinir ve kuyruk bos kalmasin diye (taze bir drain yoksa) arka planda
    tuketim devralinir. Boylece batch asla sonsuza kadar `running` kalmaz.
    """
    from app.worker.jobs import (
        batch_waiting_too_long,
        drain_is_alive,
        drain_source_sync_batches,
        reclaim_stale_source_runs,
    )

    await reclaim_stale_source_runs(session)
    await session.commit()
    status = await sync_service.current_status(session, scope=scope)
    if (
        status["active"] is not None
        and batch_waiting_too_long(status["active"])
        and not await drain_is_alive(session)
    ):
        background.add_task(drain_source_sync_batches)
    return status


@router.get("/sources/sync/history", response_model=list[SourceSyncBatchOut])
async def sync_history(
    background: BackgroundTasks,
    limit: int = 10,
    scope: Literal["opportunity", "media"] = "opportunity",
    session: AsyncSession = Depends(get_session),
):
    from app.worker.jobs import (
        batch_waiting_too_long,
        drain_is_alive,
        drain_source_sync_batches,
        reclaim_stale_source_runs,
    )

    await reclaim_stale_source_runs(session)
    await session.commit()
    active = await sync_service.current_status(session, scope=scope)
    if (
        active["active"] is not None
        and batch_waiting_too_long(active["active"])
        and not await drain_is_alive(session)
    ):
        background.add_task(drain_source_sync_batches)
    return await sync_service.history(session, min(limit, 50), scope=scope)


@router.post("/sources/refresh", response_model=SourceRefreshResult)
async def refresh_sources(
    body: SourceRefreshIn,
    background: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """Secmeli ya da toplu cekim.

    source_ids verilirse yalnizca onlar (kullanici ne sectiyse, opt-in dahil);
    aksi halde `mode`: `critical` yalnizca resmi/hizli kaynaklari, `general`
    (varsayilan) opt-in/yavas kaynaklar haric tumunu, `full` ise katalogun
    tamamini kosar. Her durumda critical -> normal -> slow_optin sirasi
    korunur. API yalnizca kalici batch olusturur; cekimi API arka plan gorevi
    tuketir; worker acikken ayni kalici kuyrugu paylasir.
    """
    from app.worker.jobs import drain_source_sync_batches, reclaim_stale_source_runs

    catalog = {source.id: source for source in _catalog_sources()}
    announcement_ids = {source.id for source in ANNOUNCEMENT_SOURCES}

    if body.source_ids:
        unknown = [item for item in body.source_ids if item not in catalog]
        if unknown:
            raise HTTPException(404, f"kaynak bulunamadı: {', '.join(unknown[:5])}")
        # Secili kaynaklarda da sinif sirasi korunur: kritik kaynaklar once.
        selected = order_by_class([catalog[item] for item in dict.fromkeys(body.source_ids)])
    else:
        pool = list(catalog.values())
        if body.kind:
            pool = [
                source
                for source in pool
                if ("announcement" if source.id in announcement_ids else "job") == body.kind
            ]
        if body.mode == "critical":
            pool = [source for source in pool if source_class(source) is SourceClass.CRITICAL]
        elif body.mode == "general":
            pool = [source for source in pool if is_general_refresh_source(source)]
        selected = order_by_class(pool)

    ids = [source.id for source in selected]
    if not ids:
        return {
            "batch_id": None,
            "queued": 0,
            "total_sources": 0,
            "estimated_seconds": 0,
            "mode": body.mode,
        }

    await reclaim_stale_source_runs(session)
    batch, newly_queued = await sync_service.create_or_extend_batch(session, ids)
    await session.commit()
    background.add_task(drain_source_sync_batches)
    estimated = sum(
        source_estimated_seconds(catalog[source_id])
        for source_id in batch.source_ids
        if source_id in catalog
    )
    return {
        "batch_id": str(batch.id),
        "queued": len(newly_queued),
        "total_sources": batch.total_sources,
        "estimated_seconds": estimated,
        "mode": body.mode,
    }


@router.post("/sources/{source_id:path}/refresh")
async def refresh_source(
    source_id: str,
    background: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    from app.worker.jobs import drain_source_sync_batches, reclaim_stale_source_runs

    try:
        catalog = {source.id for source in _catalog_sources()}
        if source_id not in catalog:
            raise KeyError(source_id)
        await reclaim_stale_source_runs(session)
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
# Scraper HTTP cache — disk istatistigi, budama ve temizleme
#
# Temizlik YALNIZCA diski hedefler; PostgreSQL satirlarina ASLA dokunmaz.


@router.get("/sources/cache")
async def source_cache_stats():
    """Ozet: boyut, dosya sayisi, en eski kayit, host basina kullanim."""
    return cache_stats(ScraperConfig())


@router.post("/sources/cache/prune")
async def source_cache_prune(body: CachePruneIn):
    """TTL ve butce sinirlarina gore buda; sinir verilmezse config varsayilani."""
    return prune_cache(
        ScraperConfig(), max_bytes=body.max_bytes, max_age_seconds=body.max_age_seconds
    )


@router.post("/sources/cache/clear")
async def source_cache_clear(body: CacheClearIn):
    """On-disk scraper onbellegini temizle; acik onay ister."""
    if not body.confirm:
        raise HTTPException(400, "onbellek temizlemek icin confirm=true gerekli")
    return clear_cache(ScraperConfig())


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
    _validate_scoring_payload(body)

    _JOBHUNTER_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    header = "# forkjob scoring & balance -- forkOS ayarlar panelinden yonetilir.\n\n"
    payload = header + yaml.safe_dump(body, sort_keys=False, allow_unicode=True, width=100)
    previous = _JOBHUNTER_CONFIG.read_text(encoding="utf-8") if _JOBHUNTER_CONFIG.exists() else None
    _JOBHUNTER_CONFIG.write_text(payload, encoding="utf-8")
    try:
        reloaded = load_config(_JOBHUNTER_CONFIG)
    except Exception as exc:  # noqa: BLE001 - bozuk config CALISAN ayari bozmamali
        if previous is None:
            _JOBHUNTER_CONFIG.unlink(missing_ok=True)
        else:
            _JOBHUNTER_CONFIG.write_text(previous, encoding="utf-8")
        raise HTTPException(422, f"skorlama ayarı yüklenemedi: {type(exc).__name__}") from exc
    forkjob_port.SCORING = reloaded
    return {"ok": True}


#: Govdede sayisal olmasi gereken skorlama alanlari.
_SCORING_NUMERIC_FIELDS = (
    "base",
    "skill_max",
    "skill_title_multiplier",
    "role_mismatch_penalty",
    "role_description_relief",
    "level_bonus",
    "level_description_factor",
    "visa_bonus",
    "visa_penalty",
    "spanish_requirement_penalty",
    "english_working_bonus",
    "tr_relocation_penalty",
    "freshness_grace_days",
    "freshness_penalty_per_day",
    "freshness_max_penalty",
    "kill_score",
    "score_cap",
    "score_floor",
)


def _validate_scoring_payload(body: dict) -> None:
    """Skorlama govdesini dogrula; gecersizse 422 yukseltir.

    Dogrulama YAZMADAN ONCE yapilir: eskiden her govde oldugu gibi diske
    yaziliyor ve sicak yukleniyordu; tek bir hatali alan calisan skorlamayi
    bozabiliyordu (ve `config.yaml` bozuk kaliyordu).
    """
    scoring = body["scoring"]

    def number(container: dict, key: str) -> float | None:
        value = container.get(key)
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise HTTPException(422, f"scoring.{key} sayı olmalı")
        if value != value or value in (float("inf"), float("-inf")):
            raise HTTPException(422, f"scoring.{key} sonlu bir sayı olmalı")
        return float(value)

    for key in _SCORING_NUMERIC_FIELDS:
        number(scoring, key)

    floor = number(scoring, "score_floor")
    cap = number(scoring, "score_cap")
    if floor is not None and cap is not None and floor > cap:
        raise HTTPException(422, "scoring.score_floor, score_cap'ten büyük olamaz")
    kill = number(scoring, "kill_score")
    if kill is not None and floor is not None and cap is not None and not floor <= kill <= cap:
        raise HTTPException(422, "scoring.kill_score skor aralığının dışında")

    skills = scoring.get("skills")
    if skills is not None:
        if not isinstance(skills, list):
            raise HTTPException(422, "scoring.skills liste olmalı")
        for entry in skills:
            if not isinstance(entry, dict) or not str(entry.get("name", "")).strip():
                raise HTTPException(422, "her beceri en az 'name' ister")
            if not isinstance(entry.get("points"), (int, float)) or isinstance(
                entry.get("points"), bool
            ):
                raise HTTPException(422, "beceri puanı sayı olmalı")

    balance = body.get("balance")
    if balance is not None:
        if not isinstance(balance, dict):
            raise HTTPException(422, "balance objesi gerekli")
        quotas = balance.get("quotas")
        if quotas is not None:
            if not isinstance(quotas, dict) or not quotas:
                raise HTTPException(422, "balance.quotas boş olamaz")
            for key, value in quotas.items():
                if not str(key).strip() or isinstance(value, bool) or not isinstance(value, int):
                    raise HTTPException(422, "balance.quotas anahtar/sayı çiftleri istiyor")
                if value < 0:
                    raise HTTPException(422, "balance.quotas negatif olamaz")


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
    """LinkedIn direct/proxy ayarlarinin gercek durumu.

    `allow_direct` bir guvenlik anahtaridir: yalnizca ortam degiskeni acikca
    acarsa true olur (bkz. `env_flag`). Yanlis yazilmis `linkein_allow_direct`
    alani eski istemciler icin ayni degerle korunur.
    """
    allow_direct = env_flag(
        next(
            (
                os.environ[name]
                for name in ("FORKJOB_LINKEDIN_ALLOW_DIRECT", "LINKEDIN_ALLOW_DIRECT")
                if name in os.environ
            ),
            None,
        ),
        default=False,
    )
    proxies_file = next(
        (
            os.environ[name]
            for name in ("FORKJOB_LINKEDIN_PROXIES_FILE", "LINKEDIN_PROXIES_FILE")
            if os.environ.get(name)
        ),
        "",
    )
    return {
        "linkedin_allow_direct": allow_direct,
        "proxies_file": proxies_file,
        #: Kullanimdan kalkti; yazim hatasiyla uretilen alan geriye uyumluluk
        #: icin ayni degeri tasir. Yeni kod `linkedin_allow_direct` okumali.
        "linkein_allow_direct": allow_direct,
    }
