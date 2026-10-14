"""Opportunity core: firsat CRUD, kaynak ingesti ve deadline merdiveni."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import create_entity, delete_entity, touch_entity
from app.core.events import log_event
from app.core.links import link
from app.core.models import Entity, Link
from app.core.notifications import notify

# Application CRM -- service.py uzerinden dogrudan import edenler bu isimleri korur.
from app.modules.opportunity import lifecycle
from app.modules.opportunity.application import (  # noqa: F401 (re-export: router service.X ile erisir)
    REJECTION_REASONS,
    TERMINAL_STATUSES,
    ApplicationIn,
    ApplicationOut,
    ApplyIn,
    FollowupOut,
    FunnelOut,
    HistoryOut,
    InterviewIn,
    InterviewOut,
    _record_status_change,
    _validate_transition,
    add_interview,
    apply,
    deadline_provider,
    delete_interview,
    funnel,
    get_application,
    list_followups,
    list_history,
    list_interviews,
    patch_interview,
    timeline,
    transition_application,
    transition_status,
    upsert_application,
)
from app.modules.opportunity.candidate_context import build_candidate_career_context
from app.modules.opportunity.candidate_fit import (
    ALGORITHM as FAST_SCORE_ALGORITHM,
)
from app.modules.opportunity.candidate_fit import (
    canonical_description,
    score_canonical_opportunity,
    scoring_revision,
)
from app.modules.opportunity.candidate_match import ALGORITHM as CANDIDATE_MATCH_ALGORITHM
from app.modules.opportunity.candidate_match import apply_candidate_match
from app.modules.opportunity.identity import (
    identity_from_incoming,
    identity_from_stored,
    same_real_world_posting,
    specific_application_url,
)
from app.modules.opportunity.models import (
    Application,
    ApplicationHistory,
    Interview,
    Opportunity,
    OpportunityRequirement,
    OpportunitySourceObservation,
    OpportunitySuppression,
)
from app.modules.opportunity.schemas import (
    BulkCleanupCriteria,
    BulkCleanupExecuteIn,
    BulkCleanupExecuteOut,
    BulkCleanupPreviewOut,
    BulkCleanupProtectionBreakdown,
    OpportunityEvaluationOut,
    OpportunityIn,
    OpportunityOut,
    OpportunityPatch,
    RequirementIn,
    SkillMatchOut,
)
from app.modules.opportunity.taxonomy import classify_job
from app.sources.forkjob_core.models import canonical_url
from app.sources.forkjob_core.rich_text import merge_descriptions, source_fact


def _calculate_skill_match(
    o: Opportunity, title: str, reasons: dict | None, *, candidate_revision: str | None = None
) -> SkillMatchOut | None:
    del reasons  # Source-specific score explanations are not candidate evidence.
    if o.kind != "job" or not isinstance(o.raw, dict):
        return None
    match = o.raw.get("candidate_match")
    if not isinstance(match, dict) or match.get("algorithm") != CANDIDATE_MATCH_ALGORITHM:
        return None
    if candidate_revision is not None and match.get("candidate_revision") != candidate_revision:
        return None
    from app.modules.opportunity.intelligence import listing_fingerprint

    if match.get("listing_fingerprint") != listing_fingerprint(o, title=title):
        return None
    ratio = match.get("ratio")
    if not isinstance(ratio, (int, float)):
        return None
    return SkillMatchOut(
        match_ratio=ratio,
        matched=list(match.get("matched") or []),
        missing=list(match.get("missing") or [])[:8],
    )


def _score_reasons(raw: dict[str, Any] | None) -> dict[str, Any] | None:
    forkjob = (raw or {}).get("forkjob") or {}
    reasons = forkjob.get("reasons")
    if isinstance(reasons, str):
        try:
            reasons = json.loads(reasons)
        except ValueError:
            return None
    return reasons if isinstance(reasons, dict) else None


def _skill_match_ratio(
    opportunity: Opportunity, title: str, *, candidate_revision: str | None = None
) -> float | None:
    """Profil uyum orani; HESAPLANAMADIYSA `None`.

    Eskiden is ilanlarinda `0.0` yaziliyordu: "hic ortusme yok" ile "hic
    hesaplanmadi" ayni goruntuye dusuyor ve "Hesaplanmadi" filtresi is
    ilanlarinda asla eslesmiyordu. Artik null korunur.
    """
    match = _calculate_skill_match(opportunity, title, None, candidate_revision=candidate_revision)
    if match is None:
        return None
    return match.match_ratio


def _out(
    row: tuple[Opportunity, str],
    *,
    include_raw: bool = True,
    #: `Application` ORM kaydi veya `ApplicationOut` semasi olabilir; ikisi de
    #: status/status_changed_at tasir.
    application: Any = None,
    candidate_revision: str | None = None,
) -> OpportunityOut:
    from app.modules.opportunity import lifecycle

    o, title = row
    # Skor kanonik kolondan okunur; raw yalnizca aciklama (reasons) tasir.
    reasons = _score_reasons(o.raw) if include_raw else None
    evaluation = None
    if o.candidate_evaluation:
        try:
            evaluation = OpportunityEvaluationOut.model_validate(o.candidate_evaluation)
        except ValueError:
            # Eski/yarim kalmis bir JSON detay ucunu kirmaz; yeniden
            # degerlendirme gecerli surumlu belgeyi uretir.
            evaluation = None
    return OpportunityOut(
        id=o.id,
        title=title,
        kind=o.kind,
        category=o.category,
        organization=o.organization,
        url=o.url,
        status=o.status,
        allowed_transitions=lifecycle.allowed_discovery_transitions(o.kind, o.status),
        priority=o.priority,
        found_at=o.found_at,
        published_at=o.published_at,
        deadline_at=o.deadline_at,
        applied_at=o.applied_at,
        location=o.location,
        remote=o.remote,
        compensation=o.compensation,
        source=o.source,
        external_id=o.external_id,
        raw=o.raw if include_raw else {},
        score=o.score,
        score_source=o.score_source,
        score_computed_at=o.score_computed_at,
        score_reasons=reasons,
        notes=o.notes,
        trashed_at=o.trashed_at,
        trashed_from_status=o.trashed_from_status,
        country=o.country,
        region=o.region,
        follow_up_at=o.follow_up_at,
        rejection_reason=o.rejection_reason,
        profile_match_ratio=_skill_match_ratio(o, title, candidate_revision=candidate_revision),
        skill_match=_calculate_skill_match(o, title, None, candidate_revision=candidate_revision),
        application_status=application.status if application is not None else None,
        application_status_changed_at=(
            application.status_changed_at if application is not None else None
        ),
        allowed_application_transitions=(
            lifecycle.allowed_application_transitions(application.status)
            if application is not None
            else []
        ),
        evaluation=evaluation,
        source_status=o.source_status,
        last_seen_at=o.last_seen_at,
        closed_at=o.closed_at,
        official=o.official,
        parent_id=o.parent_id,
        stage=o.stage,
        application_start_at=o.application_start_at,
        application_end_at=o.application_end_at,
        exam_at=o.exam_at,
        result_at=o.result_at,
        guide_url=o.guide_url,
        apply_url=o.apply_url,
        quota_total=o.quota_total,
        fields=list(o.fields or []),
    )


async def attach_applications(
    session: AsyncSession,
    rows: Sequence[tuple[Opportunity, str]],
    outs: list[OpportunityOut],
) -> list[OpportunityOut]:
    """Liste cikislarina basvuru hattini tek sorguda ekler (N+1 yok)."""
    ids = [row[0].id for row in rows]
    if not ids:
        return outs
    applications = {
        app.opportunity_id: app
        for app in (
            await session.execute(select(Application).where(Application.opportunity_id.in_(ids)))
        ).scalars()
    }
    return [
        out.model_copy(
            update={
                "application_status": applications[out.id].status,
                "application_status_changed_at": applications[out.id].status_changed_at,
                "allowed_application_transitions": _allowed_application(
                    applications[out.id].status
                ),
            }
        )
        if out.id in applications
        else out
        for out in outs
    ]


def _allowed_application(status: str) -> list[str]:
    from app.modules.opportunity import lifecycle

    return lifecycle.allowed_application_transitions(status)


async def list_opportunities(
    session: AsyncSession,
    status: str | None = None,
    kind: str | None = None,
    limit: int = 200,
    trashed_only: bool = False,
) -> list[OpportunityOut]:
    stmt = (
        select(Opportunity, Entity.title)
        .join(Entity, Entity.id == Opportunity.id)
        .order_by(
            Opportunity.priority.desc(),
            Opportunity.deadline_at.nulls_last(),
            Opportunity.found_at.desc(),
        )
    )
    stmt = stmt.where(
        Opportunity.trashed_at.is_not(None) if trashed_only else Opportunity.trashed_at.is_(None)
    )
    if status:
        stmt = stmt.where(Opportunity.status == status)
    if kind:
        stmt = stmt.where(Opportunity.kind == kind)
    stmt = stmt.limit(limit)
    rows = (await session.execute(stmt)).all()
    candidate_revision = (await build_candidate_career_context(session)).revision if rows else None
    outs = [_out(row, include_raw=False, candidate_revision=candidate_revision) for row in rows]
    outs = await attach_applications(session, rows, outs)
    if not outs:
        return outs
    from app.modules.opportunity.intelligence import enrich_opportunities

    outs = await enrich_opportunities(session, rows, outs)
    # Belge ters-bağları: DocumentsPage "bu belge hangi başvurularda kullanılıyor"
    # için /opportunities listesini istemcide filtreler. Listeye join eklemek
    # yerine iki hafif sorguyla dolduruyoruz (1:1 application + gereksinimler).
    app_rows = (
        await session.execute(
            select(Application.opportunity_id, Application.cv_document_id).where(
                Application.opportunity_id.in_([row[0].id for row in rows])
            )
        )
    ).all()
    cv_docs = {opportunity_id: cv for opportunity_id, cv in app_rows}
    req_docs: dict[uuid.UUID, uuid.UUID] = {}
    for opportunity_id, document_id in (
        await session.execute(
            select(
                OpportunityRequirement.opportunity_id,
                OpportunityRequirement.document_entity_id,
            )
            .where(
                OpportunityRequirement.opportunity_id.in_([row[0].id for row in rows]),
                OpportunityRequirement.document_entity_id.is_not(None),
            )
            .order_by(OpportunityRequirement.position)
        )
    ).all():
        req_docs.setdefault(opportunity_id, document_id)
    return [
        out.model_copy(
            update={
                "cv_document_id": cv_docs.get(out.id),
                "requirement_document_id": req_docs.get(out.id),
            }
        )
        for out in outs
    ]


async def trash_opportunity(session: AsyncSession, item_id: uuid.UUID) -> OpportunityOut | None:
    from app.modules.opportunity import lifecycle

    item = await session.get(Opportunity, item_id)
    if item is None:
        return None
    if item.trashed_at is None:
        item.trashed_from_status = item.status
        # Kesif dongusunde "elendi" durumu; is basvurusu hatti bundan etkilenmez.
        if item.status != lifecycle.TRASH_STATUS:
            await _record_discovery_change(session, item, lifecycle.TRASH_STATUS)
            item.status = lifecycle.TRASH_STATUS
        item.trashed_at = datetime.now(UTC)
        await touch_entity(session, item.id)
        await log_event(
            session,
            verb="opportunity.trashed",
            entity_id=item.id,
            entity_type="opportunity",
            payload={"from_status": item.trashed_from_status},
        )
        await session.commit()
    row = (
        await session.execute(
            select(Opportunity, Entity.title).join(Entity).where(Opportunity.id == item_id)
        )
    ).one()
    return _out(row)


async def restore_opportunity(session: AsyncSession, item_id: uuid.UUID) -> OpportunityOut | None:
    from app.modules.opportunity import lifecycle

    item = await session.get(Opportunity, item_id)
    if item is None:
        return None
    if item.trashed_at is not None:
        restored_status = lifecycle.coerce_discovery_status(item.kind, item.trashed_from_status)
        if restored_status == lifecycle.TRASH_STATUS:
            restored_status = lifecycle.discovery_flow(item.kind)[0]
        await _record_discovery_change(session, item, restored_status)
        item.status = restored_status
        item.trashed_at = None
        item.trashed_from_status = None
        await touch_entity(session, item.id)
        await log_event(
            session,
            verb="opportunity.restored",
            entity_id=item.id,
            entity_type="opportunity",
            payload={"status": restored_status},
        )
        await session.commit()
    row = (
        await session.execute(
            select(Opportunity, Entity.title).join(Entity).where(Opportunity.id == item_id)
        )
    ).one()
    return _out(row)


async def _record_discovery_change(
    session: AsyncSession, item: Opportunity, to_status: str
) -> None:
    """Kesif durumu degisimini ortak gecmis/olay yolundan yazar."""
    await _record_status_change(
        session, item, to_status, from_status=item.status, scope="discovery"
    )


async def _suppress_opportunity(
    session: AsyncSession, item: Opportunity, reason: str = "deleted"
) -> None:
    """Kalıcı silinen ilanın yeniden import edilmesini önlemek için tombstone kaydı yazar."""
    canonical = canonical_url(item.url) if item.url else None
    raw = item.raw if isinstance(item.raw, dict) else {}
    forkjob = raw.get("forkjob") if isinstance(raw.get("forkjob"), dict) else {}
    cluster_key = forkjob.get("cluster_key") or raw.get("cluster_key")
    if not item.source and not canonical and not item.external_id:
        return
    sup = OpportunitySuppression(
        id=uuid.uuid4(),
        source=item.source or "unknown",
        external_id=str(item.external_id) if item.external_id else None,
        canonical_url=canonical,
        dedup_hash=str(cluster_key) if cluster_key else None,
        reason=reason,
    )
    session.add(sup)


async def delete_opportunity(session: AsyncSession, item_id: uuid.UUID) -> bool:
    row = (
        await session.execute(
            select(Opportunity, Entity.title).join(Entity).where(Opportunity.id == item_id)
        )
    ).first()
    if row is None:
        return False
    item, title = row
    await _suppress_opportunity(session, item, reason="user_deleted")
    await log_event(
        session,
        verb="opportunity.deleted",
        entity_id=item.id,
        entity_type="opportunity",
        payload={"opportunity_id": str(item.id), "title": title},
    )
    await session.flush()
    await delete_entity(session, item.id)
    await session.commit()
    return True



async def create(
    session: AsyncSession, data: OpportunityIn, *, commit: bool = True
) -> OpportunityOut:
    from app.modules.opportunity import lifecycle

    if data.client_uuid:
        from app.modules.bookmark.receipts import capture_once

        async def write():
            result = await create(
                session, data.model_copy(update={"client_uuid": None}), commit=False
            )
            return result.model_dump(mode="json")

        result, _ = await capture_once(session, data, "opportunity", write)
        return OpportunityOut.model_validate(result)

    entity = await create_entity(
        session,
        type="opportunity",
        title=data.title,
        search_text=" ".join(
            filter(None, [data.organization, str(data.url or ""), data.location, data.notes])
        ),
    )
    now = datetime.now(UTC)
    raw = dict(data.raw or {})
    item = Opportunity(
        id=entity.id,
        kind=data.kind,
        category=classify_job(data.title, data.organization, data.notes)
        if lifecycle.is_job_kind(data.kind)
        else None,
        organization=data.organization,
        url=str(data.url) if data.url else None,
        # Serbest metin durum kabul edilmez: tur bazli kume tek hakikat kaynagi.
        status=lifecycle.coerce_discovery_status(data.kind, data.status),
        priority=data.priority,
        found_at=now,
        published_at=data.published_at,
        deadline_at=data.deadline_at,
        location=data.location,
        remote=data.remote,
        compensation=data.compensation,
        source="manual",
        raw=raw,
        country=data.country,
        region=data.region,
        notes=data.notes,
        last_seen_at=now,
    )
    if lifecycle.is_job_kind(item.kind):
        score_canonical_opportunity(item, data.title, now=now)
        apply_candidate_match(item, data.title, await build_candidate_career_context(session))
    session.add(item)
    await log_event(
        session,
        verb="opportunity.created",
        entity_id=item.id,
        entity_type="opportunity",
        payload={"kind": item.kind, "status": item.status},
    )
    if commit:
        await session.commit()
    else:
        await session.flush()
    return _out((item, data.title))


async def patch(
    session: AsyncSession, item_id: uuid.UUID, data: OpportunityPatch
) -> OpportunityOut | None:
    from app.modules.opportunity import lifecycle

    item = await session.get(Opportunity, item_id)
    if item is None:
        return None
    current_title = (
        await session.execute(select(Entity.title).where(Entity.id == item_id))
    ).scalar_one()
    changes = data.model_dump(exclude_unset=True)
    title = changes.pop("title", None)
    effective_title = title if title is not None else current_title
    old_status = item.status
    next_status = changes.pop("status", None)
    # Durum degisikligi her zaman akistan gecer: gecmis + event yazilir.
    if next_status is not None and next_status != old_status:
        lifecycle.validate_discovery_transition(item.kind, old_status, next_status)
        await _record_discovery_change(session, item, next_status)
        item.status = next_status

    # Ranking ve candidate match acisindan kritik alan degisimlerini yakala
    title_changed = title is not None and title != current_title
    old_raw = dict(item.raw or {})
    old_desc = canonical_description(old_raw)

    ranking_fields = (
        "organization",
        "location",
        "remote",
        "compensation",
        "published_at",
        "country",
        "region",
    )
    field_ranking_changed = any(
        key in changes and changes[key] != getattr(item, key, None) for key in ranking_fields
    )

    raw_changed = False
    if "raw" in changes and isinstance(changes["raw"], dict):
        new_raw = {**old_raw, **changes["raw"]}
        changes["raw"] = new_raw
        raw_changed = new_raw != old_raw

    for key, value in changes.items():
        setattr(item, key, value)

    new_raw = dict(item.raw or {})
    new_desc = canonical_description(new_raw)
    desc_changed = new_desc != old_desc

    ranking_relevant_changed = title_changed or field_ranking_changed or raw_changed or desc_changed
    candidate_evidence_changed = title_changed or desc_changed

    now = datetime.now(UTC)
    if lifecycle.is_job_kind(item.kind):
        if ranking_relevant_changed:
            score_canonical_opportunity(item, effective_title, now=now)
        if candidate_evidence_changed:
            apply_candidate_match(
                item, effective_title, await build_candidate_career_context(session)
            )

    for key in ("deadline_at", "follow_up_at"):
        if isinstance(changes.get(key), datetime):
            changes[key] = changes[key].isoformat()
    await touch_entity(session, item.id, title=title)
    await log_event(
        session,
        verb="opportunity.updated",
        entity_id=item.id,
        entity_type="opportunity",
        payload={"changes": changes, "from_status": old_status},
    )
    await session.commit()
    row = (
        await session.execute(
            select(Opportunity, Entity.title).join(Entity).where(Opportunity.id == item_id)
        )
    ).one()
    return _out(row)


async def add_requirement(
    session: AsyncSession, item_id: uuid.UUID, data: RequirementIn
) -> OpportunityRequirement | None:
    if await session.get(Opportunity, item_id) is None:
        return None
    req = OpportunityRequirement(id=uuid.uuid4(), opportunity_id=item_id, **data.model_dump())
    session.add(req)
    await log_event(
        session,
        verb="opportunity.requirement_added",
        entity_id=item_id,
        entity_type="opportunity",
        payload={"name": data.name},
    )
    await session.commit()
    return req


def canonical_cluster(rows: Sequence[Opportunity]) -> Opportunity:
    """Bir duplicate kümesinin kullanıcı açısından en değerli kaydını seç."""
    if not rows:
        raise ValueError("Boş fırsat kümesinden canonical kayıt seçilemez")
    return min(
        rows,
        key=lambda row: (
            row.status == "discovered",
            row.applied_at is None,
            not bool(row.notes),
            not row.source.startswith("careerops:"),
            row.found_at,
            str(row.id),
        ),
    )


def _merge_cluster_sources(
    canonical: Opportunity, rows: Sequence[Opportunity], incoming_source: str | None = None
) -> None:
    sources: list[str] = []
    for row in rows:
        for source in (row.raw or {}).get("sources", [row.source]):
            if source and source not in sources:
                sources.append(source)
    if incoming_source and incoming_source not in sources:
        sources.append(incoming_source)
    canonical.raw = {**(canonical.raw or {}), "sources": sources}


@dataclass(frozen=True)
class DuplicateMergeSummary:
    duplicate_groups: int = 0
    safe_groups: int = 0
    merged_groups: int = 0
    removed_rows: int = 0
    skipped_groups: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


async def merge_duplicate_clusters(
    session: AsyncSession, *, dry_run: bool = True
) -> DuplicateMergeSummary:
    """Kullanıcı verisi taşımayan duplicate iş kümelerini güvenle birleştir."""
    cluster = Opportunity.raw["forkjob"]["cluster_key"].astext
    keys = (
        (
            await session.execute(
                select(cluster)
                .where(cluster.is_not(None))
                .group_by(cluster)
                .having(func.count() > 1)
            )
        )
        .scalars()
        .all()
    )
    safe_groups = merged_groups = removed_rows = skipped_groups = 0
    for cluster_key in keys:
        rows = list(
            (await session.execute(select(Opportunity).where(cluster == cluster_key)))
            .scalars()
            .all()
        )
        ids = [row.id for row in rows]
        related_count = (
            await session.execute(
                select(func.count())
                .select_from(Link)
                .where(or_(Link.from_id.in_(ids), Link.to_id.in_(ids)))
            )
        ).scalar_one()
        application_count = (
            await session.execute(
                select(func.count())
                .select_from(Application)
                .where(Application.opportunity_id.in_(ids))
            )
        ).scalar_one()
        requirement_count = (
            await session.execute(
                select(func.count())
                .select_from(OpportunityRequirement)
                .where(OpportunityRequirement.opportunity_id.in_(ids))
            )
        ).scalar_one()
        safe = (
            all(row.status == "discovered" for row in rows)
            and all(not row.notes and row.applied_at is None for row in rows)
            and all(row.trashed_at is None for row in rows)
            and related_count == 0
            and application_count == 0
            and requirement_count == 0
            and all(
                same_real_world_posting(identity_from_stored(rows[0]), identity_from_stored(row))
                for row in rows[1:]
            )
        )
        if not safe:
            skipped_groups += 1
            continue
        safe_groups += 1
        if dry_run:
            continue
        canonical = canonical_cluster(rows)
        duplicates = [row for row in rows if row.id != canonical.id]
        _merge_cluster_sources(canonical, rows)
        await log_event(
            session,
            verb="opportunity.duplicates_merged",
            entity_id=canonical.id,
            entity_type="opportunity",
            payload={
                "cluster_key": cluster_key,
                "merged_ids": [str(row.id) for row in duplicates],
            },
        )
        for duplicate in duplicates:
            await delete_entity(session, duplicate.id)
        merged_groups += 1
        removed_rows += len(duplicates)
    if not dry_run:
        await session.commit()
    return DuplicateMergeSummary(
        duplicate_groups=len(keys),
        safe_groups=safe_groups,
        merged_groups=merged_groups,
        removed_rows=removed_rows,
        skipped_groups=skipped_groups,
    )


def _parse_dt(value: Any) -> datetime | None:
    """ISO-8601 metnini datetime'a cevirir; gecersizde None doner."""
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _announcement_columns(raw: dict[str, Any]) -> dict[str, Any]:
    """`raw['announcement']` yukunu Opportunity kolonlarina cevirir.

    Duyuru kaynaklari (YLSY/OSYM/kurum) ek alanlari bu anahtar altinda tasir;
    alan yoksa kolonlar bos kalir -- tahmin edilmez.
    """
    payload = raw.get("announcement")
    if not isinstance(payload, dict):
        return {}
    official = payload.get("official")
    quota = payload.get("quota_total")
    fields = payload.get("fields")
    return {
        "official": official if isinstance(official, bool) else None,
        "stage": payload.get("stage") if isinstance(payload.get("stage"), str) else None,
        "application_start_at": _parse_dt(payload.get("application_start_at")),
        "application_end_at": _parse_dt(payload.get("application_end_at")),
        "exam_at": _parse_dt(payload.get("exam_at")),
        "result_at": _parse_dt(payload.get("result_at")),
        "guide_url": payload.get("guide_url")
        if isinstance(payload.get("guide_url"), str)
        else None,
        "apply_url": payload.get("apply_url")
        if isinstance(payload.get("apply_url"), str)
        else None,
        "quota_total": quota if isinstance(quota, int) else None,
        "fields": [str(item) for item in fields] if isinstance(fields, list) else [],
    }


def _payload_hash(raw: dict[str, Any]) -> str:
    """Icerik degisimini yakalayan hash; gozlem zamani alanlari disarida."""
    stable = {
        key: value
        for key, value in raw.items()
        if key not in {"first_seen", "last_seen", "missed_syncs", "is_open", "last_seen_at"}
    }
    return hashlib.sha256(
        json.dumps(stable, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:32]


def _cluster_keys(jobs: list[Any]) -> list[str]:
    keys: list[str] = []
    for job in jobs:
        raw = job.to_row() if hasattr(job, "to_row") else {}
        forkjob = raw.get("forkjob", raw) if isinstance(raw, dict) else {}
        key = forkjob.get("cluster_key")
        if key:
            keys.append(str(key))
    return keys


async def _load_observations(
    session: AsyncSession, opportunity_ids: list[uuid.UUID], source_label: str
) -> dict[uuid.UUID, OpportunitySourceObservation]:
    if not opportunity_ids:
        return {}
    rows = (
        await session.execute(
            select(OpportunitySourceObservation).where(
                OpportunitySourceObservation.opportunity_id.in_(opportunity_ids),
                OpportunitySourceObservation.source == source_label,
            )
        )
    ).scalars()
    return {row.opportunity_id: row for row in rows}


async def _touch_observation(
    session: AsyncSession,
    *,
    opportunity: Opportunity,
    source_label: str,
    external_id: str | None,
    url: str | None,
    payload_hash: str,
    source_published_at: datetime | None,
    now: datetime,
    cache: dict[uuid.UUID, OpportunitySourceObservation],
) -> None:
    """Kaynak gozlemini yazar; tekrar gorulen ilan yeniden acilir."""
    row = cache.get(opportunity.id)
    if row is None:
        row = OpportunitySourceObservation(
            opportunity_id=opportunity.id,
            source=source_label,
            external_id=external_id,
            canonical_url=url,
            payload_hash=payload_hash,
            source_status="active",
            first_seen_at=now,
            last_seen_at=now,
            last_successful_seen_at=now,
            source_published_at=source_published_at,
        )
        session.add(row)
        cache[opportunity.id] = row
        return
    row.external_id = external_id or row.external_id
    row.canonical_url = url or row.canonical_url
    row.payload_hash = payload_hash
    row.last_seen_at = now
    row.last_successful_seen_at = now
    row.source_published_at = source_published_at or row.source_published_at
    if row.source_status != "active":
        # Kaynakta tekrar gorundu: yeniden ac ve olayi kaydet.
        row.source_status = "active"
        row.source_removed_at = None
        await log_event(
            session,
            verb="opportunity.source_reopened",
            entity_id=opportunity.id,
            entity_type="opportunity",
            payload={"source": source_label},
        )


async def _refresh_opportunity(
    session: AsyncSession,
    opportunity: Opportunity,
    *,
    job: Any,
    raw: dict[str, Any],
    forkjob: dict[str, Any],
    category: str | None,
    published_at: datetime | None,
    deadline_at: datetime | None,
    source_label: str,
    now: datetime,
) -> None:
    """Kaynak verisiyle tazelenen alanlar. Kullanici alanlarina dokunulmaz."""
    from app.modules.opportunity import lifecycle

    # Kaynakta tekrar gorunen kayit yeniden acilir -- ama YALNIZCA kaynak
    # tarafindan kapatilmis kayitlar (`closed_at` sweep tarafindan yazilir).
    # Kullanicinin kendi kapattigi/arsivledigi kayda dokunulmaz.
    if opportunity.closed_at is not None and opportunity.status == lifecycle.source_closed_status(
        opportunity.kind
    ):
        reopened = lifecycle.source_reopen_status(opportunity.kind)
        await _record_discovery_change(session, opportunity, reopened)
        opportunity.status = reopened

    # Non-destructive raw merge (Finding 16-18)
    merged_raw = dict(opportunity.raw or {})
    incoming_authority = raw.get("source_authority") or "native"
    existing_authority = merged_raw.get("source_authority") or "native"
    existing_owner = (merged_raw.get("forkjob") or {}).get("source")
    incoming_owner = (raw.get("forkjob") or {}).get("source")
    # A source refresh can correct its own historical default-native label.
    # It cannot downgrade an employer owner or another publisher's evidence.
    if (
        incoming_authority == "meta"
        and existing_authority == "native"
        and existing_owner
        and existing_owner == incoming_owner
        and opportunity.source == source_label
    ):
        existing_authority = "meta"
        merged_raw["source_authority"] = "meta"
    authority_rank = {"meta": 0, "native": 1, "employer": 2}
    incoming_rank = authority_rank.get(incoming_authority, 1)
    existing_rank = authority_rank.get(existing_authority, 1)
    preserve_authority = incoming_rank < existing_rank
    upgrade_authority = incoming_rank > existing_rank
    if "forkjob" in raw and isinstance(raw["forkjob"], dict):
        merged_fk = dict(merged_raw.get("forkjob") or {})
        for k, v in raw["forkjob"].items():
            if (
                k == "language"
                and v is None
                and (existing_owner == incoming_owner or upgrade_authority)
                and not preserve_authority
                and not source_fact(merged_fk.get("description"), "Language")
            ):
                merged_fk[k] = (
                    None  # remove a historical UI/prose-language guess, not explicit facts
                )
            if v is not None and v != "":
                if k == "description":
                    merged_fk[k] = merge_descriptions(
                        merged_fk.get(k),
                        v,
                        prefer_existing=preserve_authority,
                        prefer_incoming=upgrade_authority,
                    )
                elif not preserve_authority or merged_fk.get(k) in (None, "", "unknown", "UNKNOWN"):
                    merged_fk[k] = v
        merged_raw["forkjob"] = merged_fk
    if "career_ops" in raw and isinstance(raw["career_ops"], dict):
        merged_raw["career_ops"] = raw["career_ops"]
    if "cluster_key" in raw and raw["cluster_key"]:
        merged_raw.setdefault("cluster_key", raw["cluster_key"])
    if raw.get("apply_url"):
        merged_raw.setdefault("apply_url", raw["apply_url"])
    if raw.get("description"):
        merged_raw["description"] = merge_descriptions(
            canonical_description(merged_raw),
            str(raw["description"]),
            prefer_existing=preserve_authority,
            prefer_incoming=upgrade_authority,
        )

    if raw.get("source_authority") and (
        not merged_raw.get("source_authority") or upgrade_authority
    ):
        merged_raw["source_authority"] = raw["source_authority"]
    existing_sources = list(merged_raw.get("sources", [opportunity.source]))
    incoming_sources = raw.get("sources") or [source_label]
    for s in incoming_sources:
        if s and s not in existing_sources:
            existing_sources.append(s)
    merged_raw["sources"] = existing_sources
    opportunity.raw = merged_raw

    same_primary_source = (
        opportunity.source == source_label and not source_label.startswith("careerops:")
    ) or upgrade_authority

    # Field-aware non-destructive updates (Finding 16)
    if category is not None and (not opportunity.category or same_primary_source):
        opportunity.category = category
    if published_at is not None and (opportunity.published_at is None or same_primary_source):
        opportunity.published_at = published_at
    if deadline_at is not None and (opportunity.deadline_at is None or same_primary_source):
        opportunity.deadline_at = deadline_at

    # Finding 19: Scoring ownership - do not erase existing score
    score = forkjob.get("score")
    if isinstance(score, (int, float)):
        opportunity.score = float(score)
        opportunity.score_source = "forkjob-rules"
        opportunity.score_computed_at = now

    if forkjob.get("country") and (not opportunity.country or same_primary_source):
        opportunity.country = forkjob.get("country")
    if forkjob.get("region") and (not opportunity.region or same_primary_source):
        opportunity.region = forkjob.get("region")
    if job.company and (not opportunity.organization or same_primary_source):
        opportunity.organization = job.company
    if job.url and (not opportunity.url or same_primary_source):
        opportunity.url = job.url
    if job.location and (not opportunity.location or same_primary_source):
        opportunity.location = job.location

    if forkjob.get("work_mode"):
        mode = str(forkjob["work_mode"])
        if (
            mode
            and mode != "unknown"
            and (not opportunity.remote or opportunity.remote == "unknown" or same_primary_source)
        ):
            opportunity.remote = mode
    elif getattr(job, "work_mode", None) is not None:
        mode_val = job.work_mode.value if hasattr(job.work_mode, "value") else str(job.work_mode)
        if mode_val and mode_val != "unknown":
            if not opportunity.remote or opportunity.remote == "unknown" or same_primary_source:
                opportunity.remote = mode_val
        elif not opportunity.remote:
            opportunity.remote = mode_val

    if job.salary and (not opportunity.compensation or same_primary_source):
        opportunity.compensation = job.salary

    # User state and richer fields stay put, but when the same discovered job
    # arrives from both engines the visible primary source is career-ops.
    if source_label.startswith("careerops:") and opportunity.source.startswith("forkjob_core:"):
        if opportunity.external_id:
            collision = (
                await session.execute(
                    select(Opportunity.id).where(
                        Opportunity.source == source_label,
                        Opportunity.external_id == opportunity.external_id,
                        Opportunity.id != opportunity.id,
                    )
                )
            ).scalar_one_or_none()
            if not collision:
                opportunity.source = source_label
        else:
            opportunity.source = source_label

    opportunity.last_seen_at = now
    opportunity.source_status = "active"
    opportunity.missing_since = None
    opportunity.closed_at = None

    # Duyuru alanlari kaynak sahipli; tazelenir. Kullanici alanlarina dokunulmaz.
    for key, value in _announcement_columns(raw).items():
        if value is not None and value != []:
            setattr(opportunity, key, value)


async def _sync_entity_titles(
    session: AsyncSession,
    *,
    rows_by_job: list[tuple[Any, dict[str, Any], dict[str, Any]]],
    touched: list[Opportunity],
) -> None:
    """Kaynak basligi degistiyse Entity basligini ve arama vektorunu senkronla.

    `_refresh_opportunity` yalnizca `opportunity` satirini tazeler; Entity
    basligi eski kalirsa guncellenmis ilan global aramada ESKI baslikla
    bulunur.
    """
    titles: dict[uuid.UUID, str] = {}
    for (job, _raw, _forkjob), opportunity in zip(rows_by_job, touched, strict=False):
        title = getattr(job, "title", None)
        if title:
            titles[opportunity.id] = str(title)
    if not titles:
        return
    current = dict(
        (
            await session.execute(
                select(Entity.id, Entity.title).where(Entity.id.in_(list(titles)))
            )
        ).all()
    )
    for entity_id, title in titles.items():
        if current.get(entity_id) == title:
            continue
        await touch_entity(session, entity_id, title=title)


async def ingest_jobs(session: AsyncSession, jobs: list[Any], source_label: str) -> int:
    """forkjob Job nesnelerini forkOS entity/opportunity kayitlarina cevirir.

    Kayit basina SORGU YOK: external_id, url ve cluster_key lookup'lari tek
    seferde toplu yapilir; gozlemler de toplu okunur/yazilir (Faz 6.3).
    """
    if not jobs:
        return 0
    added = 0
    now = datetime.now(UTC)
    candidate_context = await build_candidate_career_context(session)

    rows_by_job: list[tuple[Any, dict[str, Any], dict[str, Any]]] = []
    for job in jobs:
        raw = job.to_row()
        forkjob = raw.get("forkjob", raw) if isinstance(raw, dict) else {}
        rows_by_job.append((job, raw, forkjob))

    external_ids = [
        str(job.external_id or getattr(job, "job_id", None))
        for job, _raw, _fk in rows_by_job
        if (getattr(job, "external_id", None) or getattr(job, "job_id", None))
    ]
    urls = [job.url for job, _raw, _fk in rows_by_job if getattr(job, "url", None)]
    cluster_keys = [
        str(fk.get("cluster_key") or _raw.get("cluster_key"))
        for _job, _raw, fk in rows_by_job
        if (fk.get("cluster_key") or _raw.get("cluster_key"))
    ]

    existing_by_ext: dict[str, Opportunity] = {}
    if external_ids:
        existing_by_ext = {
            row.external_id: row
            for row in (
                await session.execute(
                    select(Opportunity).where(
                        Opportunity.source == source_label,
                        Opportunity.external_id.in_(external_ids),
                    )
                )
            )
            .scalars()
            .all()
            if row.external_id
        }

    # URL eslesmesi HEM ham hem de normalize edilmis bicimle yapilir: ayni ilan
    # `http://x/1/`, `https://x/1` ve `?utm_source=...` varyantlariyla
    # gelebiliyor ve her varyant ayri kayit aciyordu.
    canonical_urls = [canonical_url(url) for url in urls if isinstance(url, str) and url.strip()]
    existing_by_url: dict[str, Opportunity] = {}
    existing_by_canonical_url: dict[str, Opportunity] = {}
    apply_urls = [
        url
        for _job, raw, _fk in rows_by_job
        if (url := specific_application_url(raw.get("apply_url")))
    ]
    lookups = list(dict.fromkeys([*urls, *canonical_urls, *apply_urls]))
    existing_by_apply_url: dict[str, list[Opportunity]] = {}
    if lookups:
        for row in (
            await session.execute(
                select(Opportunity).where(
                    or_(
                        Opportunity.url.in_(lookups),
                        Opportunity.raw["apply_url"].astext.in_(lookups),
                    )
                )
            )
        ).scalars():
            if not row.url:
                continue
            existing_by_url.setdefault(row.url, row)
            existing_by_canonical_url.setdefault(canonical_url(row.url), row)
            if application := specific_application_url((row.raw or {}).get("apply_url")):
                existing_by_apply_url.setdefault(application, []).append(row)

    # cluster_key lookup'i kayit basina degil, tek sorguda (eski N+1 buradaydi).
    existing_by_cluster: dict[str, list[Opportunity]] = {}
    if cluster_keys:
        cluster_expr = func.coalesce(
            Opportunity.raw["forkjob"]["cluster_key"].astext,
            Opportunity.raw["cluster_key"].astext,
        )
        for row in (
            (await session.execute(select(Opportunity).where(cluster_expr.in_(cluster_keys))))
            .scalars()
            .all()
        ):
            key = ((row.raw or {}).get("forkjob") or {}).get("cluster_key") or (row.raw or {}).get(
                "cluster_key"
            )
            if key:
                existing_by_cluster.setdefault(str(key), []).append(row)

    # Kalıcı silinenlerin yeniden içeri alınmasını önle (suppression filter)
    suppressed_ext_ids: set[str] = set()
    suppressed_canonical_urls: set[str] = set()
    suppressed_clusters: set[str] = set()
    suppression_clauses = []
    if external_ids:
        suppression_clauses.append(
            and_(
                OpportunitySuppression.source == source_label,
                OpportunitySuppression.external_id.in_(external_ids),
            )
        )
    if canonical_urls:
        suppression_clauses.append(OpportunitySuppression.canonical_url.in_(canonical_urls))
    if cluster_keys:
        suppression_clauses.append(OpportunitySuppression.dedup_hash.in_(cluster_keys))

    if suppression_clauses:
        for sup in (
            (await session.execute(select(OpportunitySuppression).where(or_(*suppression_clauses))))
            .scalars()
            .all()
        ):
            if sup.external_id:
                suppressed_ext_ids.add(sup.external_id)
            if sup.canonical_url:
                suppressed_canonical_urls.add(sup.canonical_url)
            if sup.dedup_hash:
                suppressed_clusters.add(sup.dedup_hash)

    touched: list[Opportunity] = []
    for job, raw, forkjob in rows_by_job:
        ext_id_str = str(job.external_id or getattr(job, "job_id", None) or "")
        c_url = canonical_url(job.url) if job.url else None
        c_key = str(forkjob.get("cluster_key") or raw.get("cluster_key") or "")
        if (
            (ext_id_str and ext_id_str in suppressed_ext_ids)
            or (c_url and c_url in suppressed_canonical_urls)
            or (c_key and c_key in suppressed_clusters)
        ):
            continue

        external_id = job.external_id or getattr(job, "job_id", None)
        published_at = getattr(job, "published_at", None)
        deadline_at = getattr(job, "deadline_at", None)
        department = forkjob.get("department") or forkjob.get("departments")
        if isinstance(department, list):
            department = " ".join(str(value) for value in department)
        category = (
            classify_job(
                job.title,
                department if isinstance(department, str) else None,
                job.description,
            )
            if getattr(job, "kind", "job") == "job"
            else forkjob.get("category")
        )

        cluster_key = forkjob.get("cluster_key") or raw.get("cluster_key")
        cluster_matches = (
            [
                row
                for row in existing_by_cluster.get(str(cluster_key), [])
                if same_real_world_posting(
                    identity_from_stored(row),
                    identity_from_incoming(job, raw, source_label),
                )
            ]
            if cluster_key
            else []
        )
        if cluster_matches:
            canonical = canonical_cluster(cluster_matches)
            _merge_cluster_sources(canonical, cluster_matches, source_label)
            await _refresh_opportunity(
                session,
                canonical,
                job=job,
                raw=raw,
                forkjob=forkjob,
                category=category,
                published_at=published_at,
                deadline_at=deadline_at,
                source_label=source_label,
                now=now,
            )
            score_canonical_opportunity(canonical, job.title, now=now)
            apply_candidate_match(canonical, job.title, candidate_context)
            touched.append(canonical)
            continue

        existing = existing_by_ext.get(str(external_id)) if external_id else None
        if existing is None and job.url:
            existing = existing_by_url.get(job.url) or existing_by_canonical_url.get(
                canonical_url(job.url)
            )
        if existing is None:
            application = specific_application_url(raw.get("apply_url"))
            candidates = (
                list(existing_by_apply_url.get(canonical_url(job.url), [])) if job.url else []
            )
            if application:
                if linked := existing_by_canonical_url.get(application):
                    candidates.append(linked)
                candidates.extend(existing_by_apply_url.get(application, []))
            matches = {
                row.id: row
                for row in candidates
                if same_real_world_posting(
                    identity_from_stored(row), identity_from_incoming(job, raw, source_label)
                )
            }
            if len(matches) == 1:
                existing = next(iter(matches.values()))
        if existing is not None:
            if (
                existing.source != source_label
                and job.url
                and existing_by_url.get(job.url) is existing
            ):
                sources = list((existing.raw or {}).get("sources", [existing.source]))
                if source_label not in sources:
                    sources.append(source_label)
                existing.raw = {**(existing.raw or {}), "sources": sources}
            await _refresh_opportunity(
                session,
                existing,
                job=job,
                raw=raw,
                forkjob=forkjob,
                category=category,
                published_at=published_at,
                deadline_at=deadline_at,
                source_label=source_label,
                now=now,
            )
            score_canonical_opportunity(existing, job.title, now=now)
            apply_candidate_match(existing, job.title, candidate_context)
            touched.append(existing)
            continue

        entity = await create_entity(
            session,
            type="opportunity",
            title=job.title,
            search_text=" ".join(
                filter(None, [job.company, job.location, job.description, job.url])
            ),
        )
        score = forkjob.get("score")
        priority = 3 if isinstance(score, (int, float)) and score >= 50 else 2
        kind = getattr(job, "kind", "job")
        new_opp = Opportunity(
            id=entity.id,
            kind=kind,
            category=category,
            organization=job.company,
            url=job.url,
            # Kesif dongusu is ilanlarinda 'discovered', duyurularda 'new' baslar.
            status=lifecycle.coerce_discovery_status(kind, None),
            priority=priority,
            found_at=now,
            published_at=published_at,
            deadline_at=deadline_at,
            location=job.location,
            remote=job.work_mode.value,
            compensation=job.salary,
            source=source_label,
            external_id=external_id,
            raw=raw,
            country=forkjob.get("country"),
            region=forkjob.get("region"),
            score=float(score) if isinstance(score, (int, float)) else None,
            score_source="forkjob-rules" if isinstance(score, (int, float)) else None,
            score_computed_at=now if isinstance(score, (int, float)) else None,
            source_status="active",
            last_seen_at=now,
            **_announcement_columns(raw),
        )
        score_canonical_opportunity(new_opp, job.title, now=now)
        apply_candidate_match(new_opp, job.title, candidate_context)
        if new_opp.score is not None:
            new_opp.priority = 3 if new_opp.score >= 50 else 2
        session.add(new_opp)
        if external_id:
            existing_by_ext[str(external_id)] = new_opp
        if job.url:
            existing_by_url[job.url] = new_opp
            existing_by_canonical_url.setdefault(canonical_url(job.url), new_opp)
        # AYNI batch icinde kumelenmis ikinci bir kayit gelirse yeni kayit
        # acilmasin: cluster haritasi her kayittan SONRA guncellenir.
        if cluster_key:
            existing_by_cluster.setdefault(str(cluster_key), []).append(new_opp)
        touched.append(new_opp)
        added += 1

    # Gozlemler icin kimlikler: create_entity flush ettigi icin hazir.
    await session.flush()
    await _sync_entity_titles(session, rows_by_job=rows_by_job, touched=touched)
    await _link_announcement_hierarchy(
        session,
        rows_by_job=rows_by_job,
        touched=touched,
        source_label=source_label,
    )
    observation_cache = await _load_observations(session, [row.id for row in touched], source_label)
    for (job, raw, _forkjob), opportunity in zip(rows_by_job, touched, strict=False):
        await _touch_observation(
            session,
            opportunity=opportunity,
            source_label=source_label,
            external_id=str(job.external_id or getattr(job, "job_id", "") or "") or None,
            url=job.url,
            payload_hash=_payload_hash(raw),
            source_published_at=getattr(job, "published_at", None),
            now=now,
            cache=observation_cache,
        )

    if added:
        await log_event(
            session,
            verb="opportunity.items_added",
            entity_type="opportunity",
            payload={"source": source_label, "count": added},
        )
        await notify(
            session,
            kind="opportunity.digest",
            title=f"{source_label}: {added} yeni fırsat",
            body="Yeni kayıtlar Fırsatlar ekranına eklendi.",
            dedup_key=f"digest:{source_label}:{now.date()}",
        )
    return added


#: Kaynak sinifina gore kapanma bekleme suresi (gun).
_CLOSE_GRACE_DAYS = {"critical": 1, "normal": 3, "slow": 14}

#: Kaynak durumu onceligi: en IYI durum kazanir. Ayni ilan bir kaynakta
#: kaybolup digerinde duruyorsa ilan hala yayindadir; kapanma ancak TUM
#: kaynaklar ilani biraktiginda gerceklesir.
SOURCE_STATUS_PRIORITY: tuple[str, ...] = ("active", "missing", "likely_closed", "closed")


def aggregate_source_status(statuses: Iterable[str | None]) -> str:
    """Gozlem birlesiminden global kaynak durumunu turet.

    "Son calisan kaynak kazanir" DEGIL: en iyimser gozlem kazanir. Boylece
    ikinci bir kaynagin gecikmeli/kismi taramasi, aktif bir ilani kapatamaz.
    Hic gozlem yoksa kayit aktif sayilir (elle eklenen kayitlar boyledir).
    """
    known = [status for status in statuses if status in SOURCE_STATUS_PRIORITY]
    if not known:
        return SOURCE_STATUS_PRIORITY[0]
    return min(known, key=SOURCE_STATUS_PRIORITY.index)


def _next_source_status(
    row: OpportunitySourceObservation, *, moment: datetime, grace_days: int
) -> str | None:
    """Tek bir gozlem bir sonraki kademeye geciyor mu? (Yoksa ``None``.)

    Kademe: active -> missing -> likely_closed -> closed. Her kosuda en fazla
    bir adim ilerlenir; boylece gecici bir aksaklik kaydi hemen kapatmaz.
    """
    if row.source_status == "active":
        return "missing"
    since = row.source_removed_at or row.last_seen_at
    if row.source_status == "missing":
        return "likely_closed" if (moment - since).days >= grace_days else None
    if row.source_status == "likely_closed":
        return "closed" if (moment - since).days >= grace_days * 2 else None
    return None


async def sweep_missing_opportunities(
    session: AsyncSession,
    *,
    source_label: str,
    seen_opportunity_ids: list[uuid.UUID],
    grace_days: int = 3,
    now: datetime | None = None,
) -> dict[str, int]:
    """Kaynakta gorunmeyen ilanlari kademeli kapatir (kayit basina sorgu yok).

    Once YALNIZCA bu kaynagin gozlemi ilerletilir; ardindan her etkilenen
    kaydin global durumu TUM gozlemlerin birlesiminden yeniden turetilir.
    Iki kaynakli bir ilan bir kaynakta kaybolup digerinde duruyorsa global
    durum `active` kalir: kayit ne `missing` gorunur ne kapanir.

    Kapanma karari kullanici durumunu EZMEZ: yalnizca kaynak sahipli kesif
    durumu (`discovered`/`new`) kapatilir; shortlist'lenmis ya da takip edilen
    kayit kendi durumunu korur ve kayip `source_status`/`closed_at` ile temsil
    edilir.
    """
    moment = now or datetime.now(UTC)
    seen = set(seen_opportunity_ids)
    rows = list(
        (
            await session.execute(
                select(OpportunitySourceObservation).where(
                    OpportunitySourceObservation.source == source_label,
                    OpportunitySourceObservation.source_status != "closed",
                )
            )
        ).scalars()
    )
    changed: set[uuid.UUID] = set()
    for row in rows:
        if row.opportunity_id in seen:
            continue
        next_status = _next_source_status(row, moment=moment, grace_days=grace_days)
        if next_status is None:
            continue
        if next_status == "missing":
            row.source_removed_at = moment
        row.source_status = next_status
        changed.add(row.opportunity_id)

    if not changed:
        return {"missing": 0, "likely_closed": 0, "closed": 0}
    return await _sync_global_source_status(session, changed, moment=moment)


async def _sync_global_source_status(
    session: AsyncSession, opportunity_ids: set[uuid.UUID], *, moment: datetime
) -> dict[str, int]:
    """Etkilenen kayitlarin global kaynak durumunu gozlem birlesiminden turetir."""
    from app.modules.opportunity import lifecycle

    counts = {"missing": 0, "likely_closed": 0, "closed": 0}
    statuses: dict[uuid.UUID, list[str]] = {}
    for opportunity_id, status in (
        await session.execute(
            select(
                OpportunitySourceObservation.opportunity_id,
                OpportunitySourceObservation.source_status,
            ).where(OpportunitySourceObservation.opportunity_id.in_(opportunity_ids))
        )
    ).all():
        statuses.setdefault(opportunity_id, []).append(status)

    opportunities = {
        item.id: item
        for item in (
            await session.execute(select(Opportunity).where(Opportunity.id.in_(opportunity_ids)))
        ).scalars()
    }
    for opportunity_id, item in opportunities.items():
        global_status = aggregate_source_status(statuses.get(opportunity_id, []))
        if global_status == item.source_status:
            continue
        item.source_status = global_status
        if global_status == "active":
            item.missing_since = None
            item.closed_at = None
        else:
            item.missing_since = item.missing_since or moment
            if global_status == "closed":
                item.closed_at = item.closed_at or moment
                if item.status in lifecycle.SOURCE_OWNED_DISCOVERY:
                    closed_status = lifecycle.source_closed_status(item.kind)
                    await _record_discovery_change(session, item, closed_status)
                    item.status = closed_status
        await log_event(
            session,
            verb="opportunity.source_status_changed",
            entity_id=item.id,
            entity_type="opportunity",
            payload={"source": None, "status": global_status},
        )
        if global_status in counts:
            counts[global_status] += 1
    await session.commit()
    return counts


async def _link_announcement_hierarchy(
    session: AsyncSession,
    *,
    rows_by_job: list[tuple[Any, dict[str, Any], dict[str, Any]]],
    touched: list[Opportunity],
    source_label: str,
) -> None:
    """YLSY ana kilavuz/çocuk kontenjan ve düzeltme ilişkilerini kurar.

    Kaynak `external_id` ile referans verir; biz aynı kaynak içinde
    `external_id -> opportunity.id` çözerek `parent_id` ve `references`
    bağlantısını yazarız. Tek sorgu; kayıt başına arama yok.
    """
    references: list[tuple[str, str, str]] = []
    for (job, raw, _forkjob), _opportunity in zip(rows_by_job, touched, strict=False):
        payload = raw.get("announcement")
        if not isinstance(payload, dict):
            continue
        parent_external = payload.get("parent_external_id")
        corrects_external = payload.get("corrects_external_id")
        own = str(job.external_id or getattr(job, "job_id", "") or "")
        if parent_external and own:
            references.append((str(parent_external), own, "parent"))
        if corrects_external and own:
            references.append((str(corrects_external), own, "corrects"))
    if not references:
        return

    wanted = {reference[0] for reference in references} | {reference[1] for reference in references}
    known: dict[str, uuid.UUID] = {
        row.external_id: row.id
        for row in (
            await session.execute(
                select(Opportunity).where(
                    Opportunity.source == source_label,
                    Opportunity.external_id.in_(list(wanted)),
                )
            )
        )
        .scalars()
        .all()
        if row.external_id
    }
    for parent_external, child_external, kind in references:
        parent_id = known.get(parent_external)
        child_id = known.get(child_external)
        if parent_id is None or child_id is None or parent_id == child_id:
            continue
        if kind == "parent":
            child = await session.get(Opportunity, child_id)
            if child is not None and child.parent_id != parent_id:
                child.parent_id = parent_id
        else:
            await link(session, child_id, parent_id, "references")


async def backfill_skill_match_ratios(session: AsyncSession, *, batch_size: int = 500) -> int:
    """Refresh canonical scores and evidence-bound matches in bounded batches.

    NULL match values can be valid (insufficient evidence), so freshness is
    determined by version and fingerprints rather than a NULL-column loop.
    """
    from app.modules.opportunity.intelligence import listing_fingerprint

    candidate_context = await build_candidate_career_context(session)
    updated = 0
    cursor: uuid.UUID | None = None
    while True:
        statement = (
            select(Opportunity, Entity.title)
            .join(Entity, Entity.id == Opportunity.id)
            .where(Opportunity.kind == "job")
            .order_by(Opportunity.id)
            .limit(batch_size)
        )
        if cursor is not None:
            statement = statement.where(Opportunity.id > cursor)
        rows = list((await session.execute(statement)).all())
        if not rows:
            return updated
        for opportunity, title in rows:
            changed = False
            fast_meta = (opportunity.raw or {}).get("candidate_fit") or {}
            if opportunity.score_source != FAST_SCORE_ALGORITHM or (
                fast_meta.get("scoring_revision") != scoring_revision()
            ):
                score_canonical_opportunity(opportunity, title, now=datetime.now(UTC))
                changed = True
            stored = (opportunity.raw or {}).get("candidate_match")
            if not isinstance(stored, dict) or (
                stored.get("algorithm") != CANDIDATE_MATCH_ALGORITHM
                or stored.get("candidate_revision") != candidate_context.revision
                or stored.get("listing_fingerprint")
                != listing_fingerprint(opportunity, title=title)
            ):
                apply_candidate_match(opportunity, title, candidate_context)
                changed = True
            if changed:
                updated += 1
        cursor = rows[-1][0].id
        await session.commit()


@dataclass(frozen=True)
class PrunePreview:
    """Silme onizlemesi -- kullaniciya ikinci onaydan once gosterilir."""

    candidates: int = 0
    protected: int = 0
    archived: int = 0
    estimated_bytes: int = 0
    days: int = 90
    #: Silinecek TAM kimlik kumesinin deterministik ozeti. Onay token'i bunu
    #: tasir; kume onay ile silme arasinda degisirse silme reddedilir.
    candidate_digest: str = ""

    def to_dict(self) -> dict[str, int]:
        return {
            "candidates": self.candidates,
            "protected": self.protected,
            "archived": self.archived,
            "estimated_bytes": self.estimated_bytes,
            "days": self.days,
        }


async def _average_row_bytes(session: AsyncSession) -> int:
    """Bir ilanin kabaca kapladigi yer (opportunity tablosu / satir sayisi)."""
    size, count = (
        await session.execute(
            select(
                func.pg_relation_size("opportunity"),
                select(func.count()).select_from(Opportunity).scalar_subquery(),
            )
        )
    ).one()
    return int(size / count) if count else 0


async def _prune_candidates(
    session: AsyncSession, *, days: int
) -> tuple[list[uuid.UUID], int, int]:
    """(silinebilir id'ler, korunan sayisi, arsivlenen sayisi)."""
    cutoff = datetime.now(UTC) - timedelta(days=days)
    stale_filter = (
        func.coalesce(Opportunity.found_at, Opportunity.published_at) < cutoff,
        Opportunity.trashed_at.is_(None),
    )
    # Kullanici ilgisi olan her kayit korunur: basvuru, gorusme, gereksinim,
    # not, yer imi ya da herhangi bir entity link'i.
    linked_ids = select(Link.from_id).union(select(Link.to_id))
    user_touched = select(Application.opportunity_id).union(
        select(Interview.opportunity_id),
        select(OpportunityRequirement.opportunity_id),
        linked_ids,
    )
    protected = (
        await session.execute(
            select(func.count())
            .select_from(Opportunity)
            .where(
                *stale_filter,
                or_(
                    Opportunity.id.in_(user_touched),
                    Opportunity.status != "discovered",
                    Opportunity.source == "manual",
                ),
            )
        )
    ).scalar_one()

    candidate_ids = list(
        (
            await session.execute(
                select(Opportunity.id).where(
                    *stale_filter,
                    Opportunity.kind == "job",
                    Opportunity.status == "discovered",
                    Opportunity.source != "manual",
                    Opportunity.id.not_in(user_touched),
                )
            )
        )
        .scalars()
        .all()
    )
    # Reddedilmis/kapanmis gercek basvurular analitik icin arsivde tutulur.
    archived = (
        await session.execute(
            select(func.count())
            .select_from(Application)
            .join(Opportunity, Opportunity.id == Application.opportunity_id)
            .where(
                Application.status.in_(list(lifecycle.APPLICATION_TERMINAL)),
                Opportunity.trashed_at.is_(None),
            )
        )
    ).scalar_one()
    return candidate_ids, protected, archived


def candidate_digest(candidate_ids: Iterable[uuid.UUID]) -> str:
    """Aday kumesinin deterministik ozeti (sirali, kimlige bagli)."""
    joined = "|".join(sorted(str(item) for item in candidate_ids))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


async def prune_preview(session: AsyncSession, *, days: int = 90) -> PrunePreview:
    """Dry-run: ne silinir, ne korunur, tahmini ne kadar yer bosalir."""
    candidates, protected, archived = await _prune_candidates(session, days=days)
    avg_bytes = await _average_row_bytes(session)
    return PrunePreview(
        candidates=len(candidates),
        protected=protected,
        archived=archived,
        estimated_bytes=avg_bytes,
        days=days,
        candidate_digest=candidate_digest(candidates),
    )


async def prune_stale_opportunities(
    session: AsyncSession, *, days: int = 90, expected_digest: str | None = None
) -> dict[str, int]:
    """Yalnizca sahipsiz, hic islenmemis ham ilanlari siler.

    Basvurusu, notu, yer imi, iliskisi, gorevi, gorusmesi, gereksinimi veya
    belgesi olan kayitlar korunur (Faz 2.3). Her kosu event uretir.

    `expected_digest` verilirse aday kumesi SILME ANINDA yeniden hesaplanir ve
    ozet tutmuyorsa islem reddedilir: onay ile silme arasinda kume degisirse
    (TOCTOU) kullanici gormedigi kayitlar silinemez.
    """
    candidates, protected, archived = await _prune_candidates(session, days=days)
    if expected_digest is not None and candidate_digest(candidates) != expected_digest:
        raise ValueError(
            "Aday kümesi onaydan sonra değişti: önizlemeyi yenileyip yeniden onaylayın"
        )
    avg_bytes = await _average_row_bytes(session)
    for item_id in candidates:
        await delete_entity(session, item_id)
    result = {
        "pruned": len(candidates),
        "protected": protected,
        "archived": archived,
        "freed_bytes": avg_bytes,
        "days": days,
    }
    await log_event(
        session,
        verb="opportunity.pruned",
        entity_type="opportunity",
        payload=result,
    )
    await session.commit()
    return result


async def pending_follow_up_rows(session: AsyncSession) -> list[dict]:
    """Takip tarihi yaklasan basvurular — KANONIK takip kaynagi.

    Son tarih merdiveni H6'ya tasindi (`proactivity.rules`); bu fonksiyon
    yalnizca takip satirlarini uretir, boylece tek bir proaktif uretici kalir.
    """
    now = datetime.now(UTC)
    rows = (
        await session.execute(
            select(Opportunity.id, Entity.title, Opportunity.follow_up_at)
            .join(Application, Application.opportunity_id == Opportunity.id)
            .join(Entity, Entity.id == Opportunity.id)
            .where(
                Opportunity.follow_up_at.is_not(None),
                Opportunity.follow_up_at >= now,
                Opportunity.follow_up_at < now + timedelta(days=31),
                Application.status.not_in(list(lifecycle.APPLICATION_TERMINAL)),
                Opportunity.trashed_at.is_(None),
            )
            .order_by(Opportunity.follow_up_at.asc(), Opportunity.id.asc())
        )
    ).all()
    return [
        {
            "entity_id": opportunity_id,
            "type": "opportunity_follow_up",
            "title": entity_title,
            "due_at": follow_up_at,
            "module": "opportunity",
            "sub_kind": "follow_up",
            "priority": 2,
        }
        for opportunity_id, entity_title, follow_up_at in rows
    ]


# ═════════════════════════════════════════════════════════════════════
# Toplu Kalıcı İlan Temizliği & Yeniden Giriş Önleme (Suppression)
# ═════════════════════════════════════════════════════════════════════

async def _bulk_cleanup_candidates(
    session: AsyncSession, criteria: BulkCleanupCriteria
) -> tuple[list[Opportunity], list[Opportunity], dict[str, int]]:
    """(silinebilir satirlar, korunan satirlar, koruma kirilimi)"""
    if not criteria.low_score and not criteria.dismissed:
        return [], [], {
            "applied": 0, "shortlisted": 0, "interviews": 0, "manual": 0, "notes": 0, "linked": 0
        }

    # Yalnızca job / internship türleri temizlenir; resmî duyurular dahil edilmez
    kind_filter = Opportunity.kind.in_(["job", "internship"])

    score_conditions = []
    if criteria.low_score:
        score_conditions.append(and_(Opportunity.score.is_not(None), Opportunity.score >= 0, Opportunity.score <= 40))
    if criteria.dismissed:
        score_conditions.append(or_(Opportunity.score == -1, Opportunity.status == "dismissed"))

    matched_query = (
        select(Opportunity)
        .where(
            kind_filter,
            or_(*score_conditions),
            Opportunity.trashed_at.is_(None),
        )
    )
    matched_rows = list((await session.execute(matched_query)).scalars().all())
    if not matched_rows:
        return [], [], {
            "applied": 0, "shortlisted": 0, "interviews": 0, "manual": 0, "notes": 0, "linked": 0
        }

    matched_ids = [m.id for m in matched_rows]

    # Koruma alt kümeleri
    applied_ids = set(
        (await session.execute(
            select(Application.opportunity_id).where(Application.opportunity_id.in_(matched_ids))
        )).scalars().all()
    )
    history_ids = set(
        (await session.execute(
            select(ApplicationHistory.opportunity_id).where(
                ApplicationHistory.opportunity_id.in_(matched_ids),
                ApplicationHistory.scope == "application",
            )
        )).scalars().all()
    )
    all_applied = applied_ids | history_ids

    interview_ids = set(
        (await session.execute(
            select(Interview.opportunity_id).where(Interview.opportunity_id.in_(matched_ids))
        )).scalars().all()
    )

    linked_ids = set(
        (await session.execute(
            select(Link.from_id).where(Link.from_id.in_(matched_ids))
            .union(select(Link.to_id).where(Link.to_id.in_(matched_ids)))
        )).scalars().all()
    )
    req_doc_ids = set(
        (await session.execute(
            select(OpportunityRequirement.opportunity_id).where(
                OpportunityRequirement.opportunity_id.in_(matched_ids),
                OpportunityRequirement.document_entity_id.is_not(None),
            )
        )).scalars().all()
    )
    all_linked = linked_ids | req_doc_ids

    breakdown = {
        "applied": 0,
        "shortlisted": 0,
        "interviews": 0,
        "manual": 0,
        "notes": 0,
        "linked": 0,
    }

    deletable: list[Opportunity] = []
    protected: list[Opportunity] = []

    for opp in matched_rows:
        is_protected = False
        if opp.id in all_applied:
            breakdown["applied"] += 1
            is_protected = True
        if opp.status == "shortlisted":
            breakdown["shortlisted"] += 1
            is_protected = True
        if opp.id in interview_ids:
            breakdown["interviews"] += 1
            is_protected = True
        if opp.source == "manual":
            breakdown["manual"] += 1
            is_protected = True
        if opp.notes and opp.notes.strip():
            breakdown["notes"] += 1
            is_protected = True
        if opp.id in all_linked:
            breakdown["linked"] += 1
            is_protected = True

        if is_protected:
            protected.append(opp)
        else:
            deletable.append(opp)

    return deletable, protected, breakdown


async def bulk_cleanup_preview(
    session: AsyncSession, criteria: BulkCleanupCriteria
) -> BulkCleanupPreviewOut:
    """Toplu silme önizlemesi: eşleşen, korunan ve silinecek kayıt sayıları."""
    deletable, protected, breakdown = await _bulk_cleanup_candidates(session, criteria)
    return BulkCleanupPreviewOut(
        matched_total=len(deletable) + len(protected),
        protected_total=len(protected),
        deletable_total=len(deletable),
        breakdown=BulkCleanupProtectionBreakdown(**breakdown),
    )


async def bulk_cleanup_execute(
    session: AsyncSession, payload: BulkCleanupExecuteIn
) -> BulkCleanupExecuteOut:
    """Kalıcı toplu silme: kontrollü partiler halinde siler ve suppression yazar."""
    if not payload.confirm:
        raise ValueError("Kalıcı silme işlemi için açık onay (confirm=true) zorunludur.")

    criteria = BulkCleanupCriteria(low_score=payload.low_score, dismissed=payload.dismissed)
    deletable, protected, _breakdown = await _bulk_cleanup_candidates(session, criteria)

    deleted_count = 0
    suppressed_count = 0
    batch_size = 200

    for i in range(0, len(deletable), batch_size):
        batch = deletable[i : i + batch_size]
        for opp in batch:
            await _suppress_opportunity(session, opp, reason="bulk_cleanup")
            suppressed_count += 1
            await delete_entity(session, opp.id)
            deleted_count += 1

        await log_event(
            session,
            verb="opportunity.bulk_cleaned",
            entity_type="opportunity",
            payload={
                "batch_size": len(batch),
                "total_deletable": len(deletable),
                "low_score": payload.low_score,
                "dismissed": payload.dismissed,
            },
        )
        await session.flush()

    await session.commit()
    return BulkCleanupExecuteOut(
        deleted_count=deleted_count,
        skipped_count=len(protected),
        suppressed_count=suppressed_count,
    )
