"""Opportunity core: firsat CRUD, kaynak ingesti ve deadline merdiveni."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, or_, select
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
from app.modules.opportunity.models import (
    Application,
    Interview,
    Opportunity,
    OpportunityRequirement,
    OpportunitySourceObservation,
)
from app.modules.opportunity.schemas import (
    OpportunityEvaluationOut,
    OpportunityIn,
    OpportunityOut,
    OpportunityPatch,
    RequirementIn,
    SkillMatchOut,
)
from app.modules.opportunity.taxonomy import classify_job

TECH_KEYWORDS = (
    "python",
    "javascript",
    "typescript",
    "c#",
    ".net",
    "java",
    "go",
    "golang",
    "rust",
    "c++",
    "ruby",
    "php",
    "swift",
    "kotlin",
    "sql",
    "postgresql",
    "mysql",
    "mongodb",
    "redis",
    "elasticsearch",
    "kafka",
    "rabbitmq",
    "react",
    "vue",
    "angular",
    "next.js",
    "node.js",
    "django",
    "fastapi",
    "flask",
    "spring",
    "docker",
    "kubernetes",
    "aws",
    "azure",
    "gcp",
    "terraform",
    "graphql",
    "rest",
    "ci/cd",
    "git",
    "linux",
    "pytorch",
    "langchain",
    "faiss",
    "rag",
    "yolo",
    "opencv",
)


def _calculate_skill_match(
    o: Opportunity, title: str, reasons: dict | None
) -> SkillMatchOut | None:
    if o.kind != "job":
        return None
    matched: list[str] = []
    if isinstance(reasons, dict):
        skills = reasons.get("skills")
        if isinstance(skills, dict):
            for k in skills:
                name = str(k).strip().lower()
                if name and name not in matched:
                    matched.append(name)
        elif isinstance(skills, list):
            for s in skills:
                if isinstance(s, dict) and "name" in s:
                    name = str(s["name"]).strip().lower()
                    if name and name not in matched:
                        matched.append(name)
                elif isinstance(s, str):
                    name = s.strip().lower()
                    if name and name not in matched:
                        matched.append(name)

    forkjob = (o.raw or {}).get("forkjob") or {}
    description = str(forkjob.get("description") or o.notes or "").lower()
    full_text = f"{title.lower()} {description}"

    missing: list[str] = []
    matched_set = {m.lower() for m in matched}
    for tech in TECH_KEYWORDS:
        if tech in matched_set:
            continue
        # Cogu ilanda teknoloji listesinin yalnizca birkac uyesi bulunur.
        # Bu ucuz kontrol, uzun metni her anahtar icin regex ile taramayi onler.
        if tech not in full_text:
            continue
        if tech.startswith("."):
            pattern = rf"(?:^|\W){re.escape(tech)}(?:\b|\W)"
        else:
            pattern = rf"(?:\b|\W){re.escape(tech)}(?:\b|\W)"
        if re.search(pattern, full_text):
            missing.append(tech)

    total = len(matched) + len(missing)
    if total == 0:
        return None
    ratio = round(len(matched) / total, 2)
    return SkillMatchOut(
        match_ratio=ratio,
        matched=matched,
        missing=missing[:8],
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


def _skill_match_ratio(opportunity: Opportunity, title: str) -> float | None:
    match = _calculate_skill_match(opportunity, title, _score_reasons(opportunity.raw))
    if match is not None:
        return match.match_ratio
    return 0.0 if opportunity.kind == "job" else None


def _out(
    row: tuple[Opportunity, str],
    *,
    include_raw: bool = True,
    #: `Application` ORM kaydi veya `ApplicationOut` semasi olabilir; ikisi de
    #: status/status_changed_at tasir.
    application: Any = None,
) -> OpportunityOut:
    from app.modules.opportunity import lifecycle

    o, title = row
    # Skor kanonik kolondan okunur; raw yalnizca aciklama (reasons) tasir.
    reasons = _score_reasons(o.raw) if include_raw else None
    evaluation = None
    if o.evaluation:
        try:
            evaluation = OpportunityEvaluationOut.model_validate(o.evaluation)
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
        profile_match_ratio=o.skill_match_ratio,
        skill_match=_calculate_skill_match(o, title, _score_reasons(o.raw)),
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
    outs = [_out(row, include_raw=False) for row in rows]
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


async def delete_opportunity(session: AsyncSession, item_id: uuid.UUID) -> bool:
    row = (
        await session.execute(
            select(Opportunity, Entity.title).join(Entity).where(Opportunity.id == item_id)
        )
    ).first()
    if row is None:
        return False
    item, title = row
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


async def create(session: AsyncSession, data: OpportunityIn) -> OpportunityOut:
    from app.modules.opportunity import lifecycle

    entity = await create_entity(
        session,
        type="opportunity",
        title=data.title,
        search_text=" ".join(
            filter(None, [data.organization, str(data.url or ""), data.location, data.notes])
        ),
    )
    now = datetime.now(UTC)
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
        published_at=None,
        deadline_at=data.deadline_at,
        location=data.location,
        remote=data.remote,
        compensation=data.compensation,
        source="manual",
        raw={},
        notes=data.notes,
        last_seen_at=now,
    )
    item.skill_match_ratio = _skill_match_ratio(item, data.title)
    session.add(item)
    await log_event(
        session,
        verb="opportunity.created",
        entity_id=item.id,
        entity_type="opportunity",
        payload={"kind": item.kind, "status": item.status},
    )
    await session.commit()
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
    old_status = item.status
    next_status = changes.pop("status", None)
    # Durum degisikligi her zaman akistan gecer: gecmis + event yazilir.
    if next_status is not None and next_status != old_status:
        lifecycle.validate_discovery_transition(item.kind, old_status, next_status)
        await _record_discovery_change(session, item, next_status)
        item.status = next_status
    for key, value in changes.items():
        setattr(item, key, value)
    item.skill_match_ratio = _skill_match_ratio(item, title or current_title)
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
        "guide_url": payload.get("guide_url") if isinstance(payload.get("guide_url"), str) else None,
        "apply_url": payload.get("apply_url") if isinstance(payload.get("apply_url"), str) else None,
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


def _refresh_opportunity(
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
    opportunity.raw = raw
    opportunity.category = category
    opportunity.published_at = published_at
    opportunity.deadline_at = deadline_at
    opportunity.skill_match_ratio = _skill_match_ratio(opportunity, job.title)
    score = forkjob.get("score")
    if isinstance(score, (int, float)):
        opportunity.score = float(score)
        opportunity.score_source = "forkjob-rules"
        opportunity.score_computed_at = now
    if forkjob.get("country") and not opportunity.country:
        opportunity.country = forkjob.get("country")
    if forkjob.get("region") and not opportunity.region:
        opportunity.region = forkjob.get("region")
    if job.company:
        opportunity.organization = job.company
    if job.url:
        opportunity.url = job.url
    if job.location:
        opportunity.location = job.location
    if forkjob.get("work_mode"):
        opportunity.remote = str(forkjob["work_mode"])
    elif getattr(job, "work_mode", None) is not None:
        opportunity.remote = job.work_mode.value
    if job.salary:
        opportunity.compensation = job.salary
    opportunity.last_seen_at = now
    opportunity.source_status = "active"
    opportunity.missing_since = None
    opportunity.closed_at = None
    # Duyuru alanlari kaynak sahipli; tazelenir. Kullanici alanlarina dokunulmaz.
    for key, value in _announcement_columns(raw).items():
        if value is not None and value != []:
            setattr(opportunity, key, value)


async def ingest_jobs(session: AsyncSession, jobs: list[Any], source_label: str) -> int:
    """forkjob Job nesnelerini forkOS entity/opportunity kayitlarina cevirir.

    Kayit basina SORGU YOK: external_id, url ve cluster_key lookup'lari tek
    seferde toplu yapilir; gozlemler de toplu okunur/yazilir (Faz 6.3).
    """
    if not jobs:
        return 0
    added = 0
    now = datetime.now(UTC)

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
    cluster_keys = [fk.get("cluster_key") for _job, _raw, fk in rows_by_job if fk.get("cluster_key")]

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

    existing_by_url: dict[str, Opportunity] = {}
    if urls:
        existing_by_url = {
            row.url: row
            for row in (
                await session.execute(select(Opportunity).where(Opportunity.url.in_(urls)))
            )
            .scalars()
            .all()
            if row.url
        }

    # cluster_key lookup'i kayit basina degil, tek sorguda (eski N+1 buradaydi).
    existing_by_cluster: dict[str, list[Opportunity]] = {}
    if cluster_keys:
        cluster_expr = Opportunity.raw["forkjob"]["cluster_key"].astext
        for row in (
            (
                await session.execute(
                    select(Opportunity).where(cluster_expr.in_(cluster_keys))
                )
            )
            .scalars()
            .all()
        ):
            key = ((row.raw or {}).get("forkjob") or {}).get("cluster_key")
            if key:
                existing_by_cluster.setdefault(str(key), []).append(row)

    touched: list[Opportunity] = []
    for job, raw, forkjob in rows_by_job:
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

        cluster_key = forkjob.get("cluster_key")
        cluster_matches = existing_by_cluster.get(str(cluster_key), []) if cluster_key else []
        if cluster_matches:
            canonical = canonical_cluster(cluster_matches)
            _merge_cluster_sources(canonical, cluster_matches, source_label)
            _refresh_opportunity(
                canonical,
                job=job,
                raw=raw if canonical.source == source_label else canonical.raw,
                forkjob=forkjob,
                category=category,
                published_at=published_at,
                deadline_at=deadline_at,
                source_label=source_label,
                now=now,
            )
            touched.append(canonical)
            continue

        existing = existing_by_ext.get(str(external_id)) if external_id else None
        if existing is None and job.url:
            existing = existing_by_url.get(job.url)
        if existing is not None:
            if existing.source != source_label and job.url and existing_by_url.get(job.url) is existing:
                sources = list((existing.raw or {}).get("sources", [existing.source]))
                if source_label not in sources:
                    sources.append(source_label)
                existing.raw = {**(existing.raw or {}), "sources": sources}
            _refresh_opportunity(
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
        new_opp.skill_match_ratio = _skill_match_ratio(new_opp, job.title)
        session.add(new_opp)
        if external_id:
            existing_by_ext[str(external_id)] = new_opp
        if job.url:
            existing_by_url[job.url] = new_opp
        touched.append(new_opp)
        added += 1

    # Gozlemler icin kimlikler: create_entity flush ettigi icin hazir.
    await session.flush()
    await _link_announcement_hierarchy(
        session,
        rows_by_job=rows_by_job,
        touched=touched,
        source_label=source_label,
    )
    observation_cache = await _load_observations(
        session, [row.id for row in touched], source_label
    )
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


async def sweep_missing_opportunities(
    session: AsyncSession,
    *,
    source_label: str,
    seen_opportunity_ids: list[uuid.UUID],
    grace_days: int = 3,
    now: datetime | None = None,
) -> dict[str, int]:
    """Kaynakta gorunmeyen ilanlari kademeli kapatir (kayit basina sorgu yok).

    Hemen kapatmaz: once ``missing``, grace sonrasi ``likely_closed``, bir tur
    daha sonra ``closed``. Kaynakta tekrar gorunurse ``ingest_jobs`` yeniden acar.
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
    missing = likely_closed = closed = 0
    for row in rows:
        if row.opportunity_id in seen:
            continue
        if row.source_status == "active":
            row.source_status = "missing"
            row.source_removed_at = moment
            missing += 1
        elif row.source_status == "missing":
            since = row.source_removed_at or row.last_seen_at
            if (moment - since).days >= grace_days:
                row.source_status = "likely_closed"
                likely_closed += 1
        elif row.source_status == "likely_closed":
            since = row.source_removed_at or row.last_seen_at
            if (moment - since).days >= grace_days * 2:
                row.source_status = "closed"
                closed += 1
        else:
            continue
        opportunity = await session.get(Opportunity, row.opportunity_id)
        if opportunity is None:
            continue
        opportunity.source_status = row.source_status
        if row.source_status == "missing":
            opportunity.missing_since = opportunity.missing_since or moment
        elif row.source_status == "closed":
            opportunity.closed_at = moment
            if opportunity.status in {"discovered", "shortlisted"}:
                await _record_discovery_change(session, opportunity, "closed")
                opportunity.status = "closed"
        if row.source_status != "active":
            await log_event(
                session,
                verb="opportunity.source_status_changed",
                entity_id=opportunity.id,
                entity_type="opportunity",
                payload={"source": source_label, "status": row.source_status},
            )
    if missing or likely_closed or closed:
        await session.commit()
    return {"missing": missing, "likely_closed": likely_closed, "closed": closed}


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
    """Eski ilanlarin CV oran cache'ini kucuk transaction'larla tamamla."""
    updated = 0
    while True:
        rows = list(
            (
                await session.execute(
                    select(Opportunity, Entity.title)
                    .join(Entity, Entity.id == Opportunity.id)
                    .where(
                        Opportunity.kind == "job",
                        Opportunity.skill_match_ratio.is_(None),
                    )
                    .order_by(Opportunity.id)
                    .limit(batch_size)
                )
            ).all()
        )
        if not rows:
            return updated
        for opportunity, title in rows:
            opportunity.skill_match_ratio = _skill_match_ratio(opportunity, title)
        updated += len(rows)
        await session.commit()


@dataclass(frozen=True)
class PrunePreview:
    """Silme onizlemesi -- kullaniciya ikinci onaydan once gosterilir."""

    candidates: int = 0
    protected: int = 0
    archived: int = 0
    estimated_bytes: int = 0
    days: int = 90

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


async def _prune_candidates(session: AsyncSession, *, days: int) -> tuple[list[uuid.UUID], int, int]:
    """(silinebilir id'ler, korunan sayisi, arsivlenen sayisi)."""
    cutoff = datetime.now(UTC) - timedelta(days=days)
    stale_filter = (
        func.coalesce(Opportunity.found_at, Opportunity.published_at) < cutoff,
        Opportunity.trashed_at.is_(None),
    )
    # Kullanici ilgisi olan her kayit korunur: basvuru, gorusme, gereksinim,
    # not, yer imi ya da herhangi bir entity link'i.
    linked_ids = select(Link.from_id).union(select(Link.to_id))
    user_touched = (
        select(Application.opportunity_id)
        .union(
            select(Interview.opportunity_id),
            select(OpportunityRequirement.opportunity_id),
            linked_ids,
        )
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
    )


async def prune_stale_opportunities(session: AsyncSession, *, days: int = 90) -> dict[str, int]:
    """Yalnizca sahipsiz, hic islenmemis ham ilanlari siler.

    Basvurusu, notu, yer imi, iliskisi, gorevi, gorusmesi, gereksinimi veya
    belgesi olan kayitlar korunur (Faz 2.3). Her kosu event uretir.
    """
    candidates, protected, archived = await _prune_candidates(session, days=days)
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


async def deadline_ladder(session: AsyncSession) -> int:
    from app.core.deadlines import collect_deadlines

    rows = await collect_deadlines(session)
    created = 0
    now = datetime.now(UTC)
    for row in rows:
        due = row["due_at"]
        if due < now:
            continue
        days = (due - now).days
        rung = next((n for n in (30, 14, 7, 3, 1) if days <= n), None)
        if rung is None:
            continue
        await notify(
            session,
            kind="deadline",
            title=f"{row['title']} — {days} gün kaldı",
            body="Yaklaşan son tarih",
            entity_id=row["entity_id"],
            importance=3 if days <= 3 else 2,
            dedup_key=f"deadline:{row['entity_id']}:{rung}",
        )
        created += 1
    # Follow-up tarihleri de ayni merdivene girer (takip hatirlatmasi).
    follow_rows = (
        await session.execute(
            select(Opportunity, Entity.title)
            .join(Application, Application.opportunity_id == Opportunity.id)
            .join(Entity, Entity.id == Opportunity.id)
            .where(
                Opportunity.follow_up_at.is_not(None),
                Opportunity.follow_up_at >= now,
                Opportunity.follow_up_at < now + timedelta(days=31),
                Application.status.not_in(list(lifecycle.APPLICATION_TERMINAL)),
                Opportunity.trashed_at.is_(None),
            )
        )
    ).all()
    for opportunity, entity_title in follow_rows:
        days = (opportunity.follow_up_at - now).days
        rung = next((n for n in (14, 7, 3, 1) if days <= n), None)
        if rung is None:
            continue
        await notify(
            session,
            kind="followup",
            title=f"{entity_title} — {days} gün sonra takip",
            body="Başvuru takip tarihi yaklaşıyor",
            entity_id=opportunity.id,
            importance=3 if days <= 3 else 2,
            dedup_key=f"followup:{opportunity.id}:{rung}",
        )
        created += 1
    await session.commit()
    return created


# ═════════════════════════════════════════════════════════════════════
# Application CRM — basvuru akisi, gecmis, gorusme, takip, funnel
