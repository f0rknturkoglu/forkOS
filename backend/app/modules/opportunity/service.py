"""Opportunity core: firsat CRUD, kaynak ingesti ve deadline merdiveni."""

from __future__ import annotations

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
from app.core.models import Entity, Link
from app.core.notifications import notify

# Application CRM -- service.py uzerinden dogrudan import edenler bu isimleri korur.
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
    transition_status,
    upsert_application,
)
from app.modules.opportunity.models import (
    Application,
    Opportunity,
    OpportunityRequirement,
)
from app.modules.opportunity.schemas import (
    OpportunityIn,
    OpportunityOut,
    OpportunityPatch,
    RequirementIn,
    SkillMatchOut,
)
from app.modules.opportunity.taxonomy import classify_job

TECH_KEYWORDS = (
    "python", "javascript", "typescript", "c#", ".net", "java", "go", "golang",
    "rust", "c++", "ruby", "php", "swift", "kotlin", "sql", "postgresql",
    "mysql", "mongodb", "redis", "elasticsearch", "kafka", "rabbitmq",
    "react", "vue", "angular", "next.js", "node.js", "django", "fastapi",
    "flask", "spring", "docker", "kubernetes", "aws", "azure", "gcp",
    "terraform", "graphql", "rest", "ci/cd", "git", "linux",
    "pytorch", "langchain", "faiss", "rag", "yolo", "opencv",
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


def _out(row: tuple[Opportunity, str], *, include_raw: bool = True) -> OpportunityOut:
    o, title = row
    # Skor raw'in icinde duruyor; listede raw'i tasimadan yalnizca sayiyi
    # cikariyoruz, cunku kart siralamasi ve elemesi buna dayaniyor.
    forkjob = (o.raw or {}).get("forkjob") or {}
    score = forkjob.get("score")
    # forkjob'in to_row() ciktisinda reasons JSON metni olarak duruyor;
    # dict bekleyen sema icin cozuyoruz. Bozuksa alan bos gecer.
    reasons = forkjob.get("reasons")
    if isinstance(reasons, str):
        try:
            reasons = json.loads(reasons)
        except ValueError:
            reasons = None
    if not isinstance(reasons, dict):
        reasons = None
    return OpportunityOut(
        id=o.id,
        title=title,
        kind=o.kind,
        category=o.category,
        organization=o.organization,
        url=o.url,
        status=o.status,
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
        score=score if isinstance(score, (int, float)) else None,
        score_reasons=reasons if include_raw else None,
        notes=o.notes,
        trashed_at=o.trashed_at,
        trashed_from_status=o.trashed_from_status,
        country=o.country,
        region=o.region,
        follow_up_at=o.follow_up_at,
        rejection_reason=o.rejection_reason,
        skill_match=_calculate_skill_match(o, title, reasons),
    )


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
        Opportunity.trashed_at.is_not(None)
        if trashed_only
        else Opportunity.trashed_at.is_(None)
    )
    if status:
        stmt = stmt.where(Opportunity.status == status)
    if kind:
        stmt = stmt.where(Opportunity.kind == kind)
    stmt = stmt.limit(limit)
    rows = (await session.execute(stmt)).all()
    outs = [_out(row, include_raw=False) for row in rows]
    if not outs:
        return outs
    # Belge ters-bağları: DocumentsPage "bu belge hangi başvurularda kullanılıyor"
    # için /opportunities listesini istemcide filtreler. Listeye join eklemek
    # yerine iki hafif sorguyla dolduruyoruz (1:1 application + gereksinimler).
    app_rows = (
        await session.execute(
            select(Application.opportunity_id, Application.cv_document_id)
            .where(Application.opportunity_id.in_([row[0].id for row in rows]))
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


async def trash_opportunity(
    session: AsyncSession, item_id: uuid.UUID
) -> OpportunityOut | None:
    item = await session.get(Opportunity, item_id)
    if item is None:
        return None
    if item.trashed_at is None:
        item.trashed_from_status = item.status
        item.status = "trashed"
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


async def restore_opportunity(
    session: AsyncSession, item_id: uuid.UUID
) -> OpportunityOut | None:
    item = await session.get(Opportunity, item_id)
    if item is None:
        return None
    if item.trashed_at is not None:
        restored_status = item.trashed_from_status or "discovered"
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
        if data.kind == "job"
        else None,
        organization=data.organization,
        url=str(data.url) if data.url else None,
        status=data.status,
        priority=data.priority,
        found_at=now,
        published_at=None,
        deadline_at=data.deadline_at,
        applied_at=now if data.status == "applied" else None,
        location=data.location,
        remote=data.remote,
        compensation=data.compensation,
        source="manual",
        raw={},
        notes=data.notes,
    )
    session.add(item)
    await log_event(
        session,
        verb="opportunity.created",
        entity_id=item.id,
        entity_type="opportunity",
        payload={"kind": item.kind, "status": item.status},
    )
    await session.commit()
    return (await list_opportunities(session))[0] if False else _out((item, data.title))


async def patch(
    session: AsyncSession, item_id: uuid.UUID, data: OpportunityPatch
) -> OpportunityOut | None:
    item = await session.get(Opportunity, item_id)
    if item is None:
        return None
    changes = data.model_dump(exclude_unset=True)
    title = changes.pop("title", None)
    old_status = item.status
    next_status = changes.pop("status", None)
    # Durum degisikligi her zaman akistan gecer: gecmis + event yazilir.
    if next_status is not None and next_status != old_status:
        _validate_transition(old_status, next_status)
        await _record_status_change(session, item, next_status, note=None)
        item.status = next_status
    for key, value in changes.items():
        setattr(item, key, value)
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
        await session.execute(
            select(cluster)
            .where(cluster.is_not(None))
            .group_by(cluster)
            .having(func.count() > 1)
        )
    ).scalars().all()
    safe_groups = merged_groups = removed_rows = skipped_groups = 0
    for cluster_key in keys:
        rows = list(
            (
                await session.execute(
                    select(Opportunity).where(cluster == cluster_key)
                )
            ).scalars().all()
        )
        ids = [row.id for row in rows]
        related_count = (
            await session.execute(
                select(func.count()).select_from(Link).where(
                    or_(Link.from_id.in_(ids), Link.to_id.in_(ids))
                )
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


async def ingest_jobs(session: AsyncSession, jobs: list[Any], source_label: str) -> int:
    """forkjob Job nesnelerini forkOS entity/opportunity kayıtlarına çevirir."""
    if not jobs:
        return 0
    added = 0

    # Toplu on-yukleme: N+1 sorgu yerine batch lookup ile var olan kayitlari tek seferde al
    external_ids = [
        str(j.external_id or getattr(j, "job_id", None))
        for j in jobs
        if (getattr(j, "external_id", None) or getattr(j, "job_id", None))
    ]
    existing_by_ext: dict[str, Opportunity] = {}
    if external_ids:
        ext_rows = (
            await session.execute(
                select(Opportunity).where(
                    Opportunity.source == source_label,
                    Opportunity.external_id.in_(external_ids),
                )
            )
        ).scalars().all()
        existing_by_ext = {o.external_id: o for o in ext_rows if o.external_id}

    urls = [j.url for j in jobs if getattr(j, "url", None)]
    existing_by_url: dict[str, Opportunity] = {}
    if urls:
        url_rows = (
            await session.execute(
                select(Opportunity).where(Opportunity.url.in_(urls))
            )
        ).scalars().all()
        existing_by_url = {o.url: o for o in url_rows if o.url}

    for job in jobs:
        external_id = job.external_id or getattr(job, "job_id", None)
        existing = existing_by_ext.get(str(external_id)) if external_id else None
        raw = job.to_row()
        forkjob = raw.get("forkjob", raw)
        published_at = getattr(job, "published_at", None)
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
            else None
        )
        cluster_key = forkjob.get("cluster_key")
        cluster_matches: list[Opportunity] = []
        if cluster_key:
            cluster_matches = list(
                (
                    await session.execute(
                        select(Opportunity).where(
                            Opportunity.raw["forkjob"]["cluster_key"].astext == cluster_key
                        )
                    )
                ).scalars().all()
            )
        if cluster_matches:
            canonical = canonical_cluster(cluster_matches)
            _merge_cluster_sources(canonical, cluster_matches, source_label)
            if existing is not None:
                existing.raw = raw if existing is canonical else existing.raw
                existing.category = category
                existing.published_at = published_at
            continue
        if existing:
            existing.raw = raw
            existing.category = category
            existing.published_at = published_at
            if existing.country is None and forkjob.get("country"):
                existing.country = forkjob.get("country")
            if existing.region is None and forkjob.get("region"):
                existing.region = forkjob.get("region")
            continue
        # Ikinci savunma: ayni URL farkli kaynaktan geliyorsa birlestir.
        if job.url:
            by_url = existing_by_url.get(job.url)
            if by_url is not None and by_url.source != source_label:
                sources = list(by_url.raw.get("sources", [by_url.source]))
                if source_label not in sources:
                    sources.append(source_label)
                by_url.raw = {**by_url.raw, "sources": sources}
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
        new_opp = Opportunity(
            id=entity.id,
            kind=getattr(job, "kind", "job"),
            category=category,
            organization=job.company,
            url=job.url,
            status="discovered",
            priority=priority,
            found_at=datetime.now(UTC),
            published_at=published_at,
            location=job.location,
            remote=job.work_mode.value,
            compensation=job.salary,
            source=source_label,
            external_id=external_id,
            raw=raw,
            country=forkjob.get("country"),
            region=forkjob.get("region"),
        )
        session.add(new_opp)
        if external_id:
            existing_by_ext[str(external_id)] = new_opp
        if job.url:
            existing_by_url[job.url] = new_opp
        added += 1
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
            dedup_key=f"digest:{source_label}:{datetime.now(UTC).date()}",
        )
    return added


async def prune_stale_opportunities(
    session: AsyncSession, *, days: int = 90
) -> int:
    """Son `days` gundur bulunan, status='discovered' olan ve trashed_at null olan ilgilenilmemis ilanlari budar."""
    cutoff = datetime.now(UTC) - timedelta(days=days)
    stale_ids = list(
        (
            await session.execute(
                select(Opportunity.id).where(
                    Opportunity.status == "discovered",
                    Opportunity.trashed_at.is_(None),
                    Opportunity.found_at < cutoff,
                )
            )
        ).scalars().all()
    )
    if not stale_ids:
        return 0
    for item_id in stale_ids:
        await delete_entity(session, item_id)
    await session.commit()
    return len(stale_ids)


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
            .join(Entity, Entity.id == Opportunity.id)
            .where(
                Opportunity.follow_up_at.is_not(None),
                Opportunity.follow_up_at >= now,
                Opportunity.follow_up_at < now + timedelta(days=31),
                Opportunity.status.not_in(list(TERMINAL_STATUSES)),
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
