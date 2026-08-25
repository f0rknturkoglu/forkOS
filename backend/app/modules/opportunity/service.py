from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import create_entity, delete_entity, touch_entity
from app.core.events import log_event
from app.core.models import Entity
from app.core.notifications import notify
from app.modules.document.models import Document
from app.modules.opportunity.models import (
    Application,
    ApplicationHistory,
    Interview,
    Opportunity,
    OpportunityRequirement,
)
from app.modules.opportunity.schemas import (
    ApplicationIn,
    ApplicationOut,
    ApplyIn,
    FollowupOut,
    FunnelOut,
    FunnelRow,
    HistoryOut,
    InterviewIn,
    InterviewOut,
    OpportunityIn,
    OpportunityOut,
    OpportunityPatch,
    RequirementIn,
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
        organization=o.organization,
        url=o.url,
        status=o.status,
        priority=o.priority,
        found_at=o.found_at,
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
    return [_out(row, include_raw=False) for row in (await session.execute(stmt)).all()]


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
        organization=data.organization,
        url=str(data.url) if data.url else None,
        status=data.status,
        priority=data.priority,
        found_at=now,
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
        _record_status_change(session, item, next_status, note=None)
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


async def ingest_jobs(session: AsyncSession, jobs: list[Any], source_label: str) -> int:
    """forkjob Job nesnelerini forkOS entity/opportunity kayıtlarına çevirir."""
    added = 0
    for job in jobs:
        external_id = job.external_id or job.job_id
        existing = (
            await session.execute(
                select(Opportunity).where(
                    Opportunity.source == source_label, Opportunity.external_id == external_id
                )
            )
        ).scalar_one_or_none()
        raw = job.to_row()
        forkjob = raw.get("forkjob", raw)
        cluster_key = forkjob.get("cluster_key")
        duplicate = None
        if cluster_key:
            duplicate = (
                await session.execute(
                    select(Opportunity).where(
                        Opportunity.raw["forkjob"]["cluster_key"].astext == cluster_key
                    )
                )
            ).scalar_one_or_none()
        if duplicate is not None and duplicate.source != source_label:
            sources = list(duplicate.raw.get("sources", [duplicate.source]))
            if source_label not in sources:
                sources.append(source_label)
            duplicate.raw = {**duplicate.raw, "sources": sources}
            continue
        if existing:
            existing.raw = raw
            if existing.country is None and forkjob.get("country"):
                existing.country = forkjob.get("country")
            if existing.region is None and forkjob.get("region"):
                existing.region = forkjob.get("region")
            continue
        # Ikinci savunma: ayni URL farkli kaynaktan geliyorsa birlestir.
        if job.url:
            by_url = (await session.execute(
                select(Opportunity).where(Opportunity.url == job.url)
            )).scalar_one_or_none()
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
        session.add(
            Opportunity(
                id=entity.id,
                kind=getattr(job, "kind", "job"),
                organization=job.company,
                url=job.url,
                status="discovered",
                priority=priority,
                found_at=getattr(job, "published_at", None) or datetime.now(UTC),
                location=job.location,
                remote=job.work_mode.value,
                compensation=job.salary,
                source=source_label,
                external_id=external_id,
                raw=raw,
                country=forkjob.get("country"),
                region=forkjob.get("region"),
            )
        )
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


async def deadline_ladder(session: AsyncSession) -> int:
    rows = (
        (
            await session.execute(
                text(
                    "select entity_id, title, due_at from deadline_v "
                    "where due_at >= now() and due_at < now() + interval '31 days'"
                )
            )
        )
        .mappings()
        .all()
    )
    created = 0
    now = datetime.now(UTC)
    for row in rows:
        days = (row["due_at"] - now).days
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
# ═════════════════════════════════════════════════════════════════════

STATUS_FLOW = [
    "discovered", "considering", "preparing", "applied",
    "interview", "offer", "accepted", "rejected", "withdrawn", "closed",
]
TERMINAL_STATUSES = {"accepted", "rejected", "closed"}

# Hangi durumdan hangilerine gecilebilir (tek yonlu merdiven + geri cekilme).
_TRANSITIONS: dict[str, set[str]] = {
    "discovered": {"considering", "preparing", "applied", "rejected", "withdrawn", "closed"},
    "considering": {"discovered", "preparing", "applied", "rejected", "withdrawn", "closed"},
    "preparing": {"considering", "applied", "rejected", "withdrawn", "closed"},
    "applied": {"interview", "offer", "rejected", "withdrawn", "closed", "preparing"},
    "interview": {"applied", "offer", "rejected", "withdrawn", "closed"},
    "offer": {"accepted", "rejected", "withdrawn", "closed"},
    "accepted": set(),
    "rejected": set(),
    "withdrawn": {"discovered"},
    "closed": set(),
}
REJECTION_REASONS = [
    "maas uyumsuz", "ilan kapandi", "uyum yetersiz",
    "cevap alinamadi", "pozisyon dolduruldu", "diger",
]


def _validate_transition(from_status: str, to_status: str) -> None:
    allowed = _TRANSITIONS.get(from_status, set())
    if to_status not in allowed:
        raise ValueError(f"{from_status} -> {to_status} gecisi gecersiz")


def _record_status_change(
    session: AsyncSession, item: Opportunity, to_status: str, *, note: str | None = None,
) -> None:
    """Gecis gecmisini ve event i yazar; item.status henuz degismemistir."""
    session.add(ApplicationHistory(
        id=uuid.uuid4(), opportunity_id=item.id,
        from_status=item.status, to_status=to_status, note=note,
    ))
    log_event(
        session, verb="opportunity.status_changed", entity_id=item.id,
        entity_type="opportunity",
        payload={"from": item.status, "to": to_status, "note": note},
    )


async def transition_status(
    session: AsyncSession, item_id: uuid.UUID, *,
    to: str, note: str | None = None, rejection_reason: str | None = None,
) -> OpportunityOut | None:
    item = await session.get(Opportunity, item_id)
    if item is None:
        return None
    if item.trashed_at is not None:
        raise ValueError("cop durumundaki kayit gecis kabul etmez")
    _validate_transition(item.status, to)
    if to == "rejected" and rejection_reason:
        item.rejection_reason = rejection_reason
    if to == "applied" and item.applied_at is None:
        item.applied_at = datetime.now(UTC)
    if to in TERMINAL_STATUSES:
        item.follow_up_at = None
    _record_status_change(session, item, to, note=note)
    item.status = to
    await touch_entity(session, item.id)
    await session.commit()
    row = (
        await session.execute(
            select(Opportunity, Entity.title).join(Entity).where(Opportunity.id == item_id)
        )
    ).one()
    return _out(row)



async def get_application(
    session: AsyncSession, item_id: uuid.UUID,
) -> ApplicationOut | None:
    app = await session.get(Application, item_id)
    if app is None:
        return None
    return ApplicationOut(
        opportunity_id=app.opportunity_id, cv_document_id=app.cv_document_id,
        cv_title=app.cv_title, cv_modified_at=app.cv_modified_at,
        cover_letter=app.cover_letter, company_research=app.company_research,
        salary_expectation=app.salary_expectation,
        posting_snapshot=app.posting_snapshot or {}, note=app.note,
        created_at=app.created_at, updated_at=app.updated_at,
    )


def _snapshot_posting(item: Opportunity) -> dict[str, Any]:
    """Basvuru anindaki ilan hali; sonraki degisikliklerden etkilenmez."""
    fk = (item.raw or {}).get("forkjob") or {}
    return {
        "url": item.url,
        "organization": item.organization,
        "location": item.location,
        "remote": item.remote,
        "compensation": item.compensation,
        "found_at": item.found_at.isoformat() if item.found_at else None,
        "description": fk.get("description") or (item.raw or {}).get("description") or "",
    }


async def apply(
    session: AsyncSession, item_id: uuid.UUID, data: ApplyIn,
) -> OpportunityOut | None:
    """Basvuru: durum applied olur; ilk kayitta snapshot + CV kunyesi saklanir."""
    if await session.get(Opportunity, item_id) is None:
        return None
    doc = None
    doc_title = None
    if data.cv_document_id is not None:
        row = (
            await session.execute(
                select(Document, Entity.title)
                .join(Entity, Entity.id == Document.id)
                .where(Document.id == data.cv_document_id)
            )
        ).first()
        if row is not None:
            doc, doc_title = row

    app = await session.get(Application, item_id)
    if app is None:
        item = await session.get(Opportunity, item_id)
        app = Application(
            opportunity_id=item_id,
            posting_snapshot=_snapshot_posting(item),
        )
        session.add(app)
    if doc is not None:
        app.cv_document_id = data.cv_document_id
        app.cv_title = doc_title
        app.cv_modified_at = doc.drive_modified_at
    for key in ("cover_letter", "company_research", "salary_expectation", "note"):
        value = getattr(data, key)
        if value is not None:
            setattr(app, key, value)
    app.updated_at = datetime.now(UTC)

    item = await session.get(Opportunity, item_id)
    if item.status != "applied":
        _validate_transition(item.status, "applied")
        if item.applied_at is None:
            item.applied_at = datetime.now(UTC)
        _record_status_change(session, item, "applied")
        item.status = "applied"
    await session.commit()
    row = (
        await session.execute(
            select(Opportunity, Entity.title).join(Entity).where(Opportunity.id == item_id)
        )
    ).one()
    return _out(row)


async def upsert_application(
    session: AsyncSession, item_id: uuid.UUID, data: ApplicationIn,
) -> ApplicationOut | None:
    if await session.get(Opportunity, item_id) is None:
        return None
    app = await session.get(Application, item_id)
    if app is None:
        app = Application(opportunity_id=item_id)
        session.add(app)
    if data.cv_document_id is not None:
        row = (
            await session.execute(
                select(Document, Entity.title)
                .join(Entity, Entity.id == Document.id)
                .where(Document.id == data.cv_document_id)
            )
        ).first()
        if row is not None:
            doc, doc_title = row
            app.cv_document_id = data.cv_document_id
            app.cv_title = doc_title
            app.cv_modified_at = doc.drive_modified_at
    for key in ("cover_letter", "company_research", "salary_expectation", "note"):
        value = getattr(data, key)
        if value is not None:
            setattr(app, key, value)
    app.updated_at = datetime.now(UTC)
    await session.commit()
    return await get_application(session, item_id)


async def list_history(session: AsyncSession, item_id: uuid.UUID) -> list[HistoryOut]:
    rows = (
        await session.execute(
            select(ApplicationHistory)
            .where(ApplicationHistory.opportunity_id == item_id)
            .order_by(ApplicationHistory.at.desc())
        )
    )
    return [
        HistoryOut(id=r.id, from_status=r.from_status, to_status=r.to_status,
                   at=r.at, note=r.note)
        for r in rows.scalars()
    ]


async def list_interviews(session: AsyncSession, item_id: uuid.UUID) -> list[InterviewOut]:
    rows = (
        await session.execute(
            select(Interview)
            .where(Interview.opportunity_id == item_id)
            .order_by(Interview.scheduled_at.asc().nulls_last(), Interview.position)
        )
    )
    return [
        InterviewOut(id=r.id, opportunity_id=r.opportunity_id, stage=r.stage, mode=r.mode,
                     scheduled_at=r.scheduled_at, duration_min=r.duration_min,
                     notes=r.notes, outcome=r.outcome, position=r.position)
        for r in rows.scalars()
    ]


async def add_interview(
    session: AsyncSession, item_id: uuid.UUID, data: InterviewIn,
) -> InterviewOut | None:
    if await session.get(Opportunity, item_id) is None:
        return None
    position = 1 + len(list((await session.execute(
        select(Interview.id).where(Interview.opportunity_id == item_id)
    )).scalars()))
    row = Interview(opportunity_id=item_id, position=position, **data.model_dump())
    session.add(row)
    await log_event(session, verb="opportunity.interview_added", entity_id=item_id,
                    entity_type="opportunity", payload={"stage": data.stage})
    await session.commit()
    return InterviewOut(id=row.id, opportunity_id=item_id, stage=row.stage, mode=row.mode,
                        scheduled_at=row.scheduled_at, duration_min=row.duration_min,
                        notes=row.notes, outcome=row.outcome, position=row.position)


async def patch_interview(
    session: AsyncSession, interview_id: uuid.UUID, data: InterviewIn,
) -> InterviewOut | None:
    row = await session.get(Interview, interview_id)
    if row is None:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    await session.commit()
    return InterviewOut(id=row.id, opportunity_id=row.opportunity_id, stage=row.stage,
                        mode=row.mode, scheduled_at=row.scheduled_at,
                        duration_min=row.duration_min, notes=row.notes,
                        outcome=row.outcome, position=row.position)


async def delete_interview(session: AsyncSession, interview_id: uuid.UUID) -> bool:
    row = await session.get(Interview, interview_id)
    if row is None:
        return False
    await session.delete(row)
    await session.commit()
    return True



async def funnel(session: AsyncSession) -> FunnelOut:
    rows = (
        await session.execute(
            select(Opportunity.status, func.count()).group_by(Opportunity.status)
        )
    ).all()
    counts = {status: count for status, count in rows}
    by_status = [
        FunnelRow(status=status, count=counts.get(status, 0)) for status in STATUS_FLOW
    ]
    total = sum(counts.values())

    def ratio(lower: str, upper: str) -> float | None:
        base = counts.get(lower, 0)
        return round(counts.get(upper, 0) / base * 100, 1) if base else None

    conversions = {
        "applied_to_interview": ratio("applied", "interview"),
        "interview_to_offer": ratio("interview", "offer"),
        "offer_to_accepted": ratio("offer", "accepted"),
        "applied_to_rejected": ratio("applied", "rejected"),
        "applied_total": counts.get("applied", 0),
    }
    reason_rows = (
        await session.execute(
            select(Opportunity.rejection_reason, func.count())
            .where(Opportunity.status == "rejected", Opportunity.rejection_reason.is_not(None))
            .group_by(Opportunity.rejection_reason)
            .order_by(func.count().desc())
        )
    ).all()
    return FunnelOut(
        total=total, by_status=by_status, conversions=conversions,
        rejection_reasons=[
            {"reason": reason or "belirsiz", "count": count} for reason, count in reason_rows
        ],
    )


async def list_followups(
    session: AsyncSession, *, days: int = 30,
) -> list[FollowupOut]:
    cutoff = datetime.now(UTC) + timedelta(days=days)
    rows = (
        await session.execute(
            select(Opportunity, Entity.title)
            .join(Entity, Entity.id == Opportunity.id)
            .where(
                Opportunity.follow_up_at.is_not(None),
                Opportunity.follow_up_at <= cutoff,
                Opportunity.status.not_in(list(TERMINAL_STATUSES)),
                Opportunity.trashed_at.is_(None),
            )
            .order_by(Opportunity.follow_up_at)
        )
    ).all()
    return [
        FollowupOut(id=o.id, title=title, status=o.status,
                    follow_up_at=o.follow_up_at, note=o.notes)
        for o, title in rows
    ]