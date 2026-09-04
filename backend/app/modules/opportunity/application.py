"""Opportunity application CRM: basvuru akisi, gecmis, gorusme, takip, funnel."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import touch_entity
from app.core.events import log_event
from app.core.models import Entity
from app.modules import DeadlineRow
from app.modules.document.models import Document
from app.modules.opportunity.models import (
    Application,
    ApplicationHistory,
    Interview,
    Opportunity,
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
    OpportunityOut,
)

STATUS_FLOW = [
    "discovered",
    "considering",
    "preparing",
    "applied",
    "interview",
    "offer",
    "accepted",
    "rejected",
    "withdrawn",
    "closed",
]


TERMINAL_STATUSES = {"accepted", "rejected", "closed"}


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
    "maas uyumsuz",
    "ilan kapandi",
    "uyum yetersiz",
    "cevap alinamadi",
    "pozisyon dolduruldu",
    "diger",
]


def _validate_transition(from_status: str, to_status: str) -> None:
    allowed = _TRANSITIONS.get(from_status, set())
    if to_status not in allowed:
        raise ValueError(f"{from_status} -> {to_status} gecisi gecersiz")


async def _record_status_change(
    session: AsyncSession,
    item: Opportunity,
    to_status: str,
    *,
    note: str | None = None,
) -> None:
    """Gecis gecmisini ve event i yazar; item.status henuz degismemistir."""
    session.add(
        ApplicationHistory(
            id=uuid.uuid4(),
            opportunity_id=item.id,
            from_status=item.status,
            to_status=to_status,
            note=note,
        )
    )
    await log_event(
        session,
        verb="opportunity.status_changed",
        entity_id=item.id,
        entity_type="opportunity",
        payload={"from": item.status, "to": to_status, "note": note},
    )


async def transition_status(
    session: AsyncSession,
    item_id: uuid.UUID,
    *,
    to: str,
    note: str | None = None,
    rejection_reason: str | None = None,
) -> OpportunityOut | None:
    from app.modules.opportunity.service import _out

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
    await _record_status_change(session, item, to, note=note)
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
    session: AsyncSession,
    item_id: uuid.UUID,
) -> ApplicationOut | None:
    app = await session.get(Application, item_id)
    if app is None:
        return None
    return ApplicationOut(
        opportunity_id=app.opportunity_id,
        cv_document_id=app.cv_document_id,
        cv_title=app.cv_title,
        cv_modified_at=app.cv_modified_at,
        cover_letter=app.cover_letter,
        company_research=app.company_research,
        salary_expectation=app.salary_expectation,
        posting_snapshot=app.posting_snapshot or {},
        note=app.note,
        created_at=app.created_at,
        updated_at=app.updated_at,
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
    session: AsyncSession,
    item_id: uuid.UUID,
    data: ApplyIn,
) -> OpportunityOut | None:
    """Basvuru: durum applied olur; ilk kayitta snapshot + CV kunyesi saklanir."""
    from app.modules.opportunity.service import _out

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
        await _record_status_change(session, item, "applied")
        item.status = "applied"
    await session.commit()
    row = (
        await session.execute(
            select(Opportunity, Entity.title).join(Entity).where(Opportunity.id == item_id)
        )
    ).one()
    return _out(row)


async def upsert_application(
    session: AsyncSession,
    item_id: uuid.UUID,
    data: ApplicationIn,
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
    rows = await session.execute(
        select(ApplicationHistory)
        .where(ApplicationHistory.opportunity_id == item_id)
        .order_by(ApplicationHistory.at.desc())
    )
    return [
        HistoryOut(id=r.id, from_status=r.from_status, to_status=r.to_status, at=r.at, note=r.note)
        for r in rows.scalars()
    ]


async def list_interviews(session: AsyncSession, item_id: uuid.UUID) -> list[InterviewOut]:
    rows = await session.execute(
        select(Interview)
        .where(Interview.opportunity_id == item_id)
        .order_by(Interview.scheduled_at.asc().nulls_last(), Interview.position)
    )
    return [
        InterviewOut(
            id=r.id,
            opportunity_id=r.opportunity_id,
            stage=r.stage,
            mode=r.mode,
            scheduled_at=r.scheduled_at,
            duration_min=r.duration_min,
            notes=r.notes,
            outcome=r.outcome,
            salary_stated=r.salary_stated,
            position=r.position,
        )
        for r in rows.scalars()
    ]


async def add_interview(
    session: AsyncSession,
    item_id: uuid.UUID,
    data: InterviewIn,
) -> InterviewOut | None:
    if await session.get(Opportunity, item_id) is None:
        return None
    position = 1 + len(
        list(
            (
                await session.execute(
                    select(Interview.id).where(Interview.opportunity_id == item_id)
                )
            ).scalars()
        )
    )
    row = Interview(opportunity_id=item_id, position=position, **data.model_dump())
    session.add(row)
    await log_event(
        session,
        verb="opportunity.interview_added",
        entity_id=item_id,
        entity_type="opportunity",
        payload={
            "stage": data.stage,
            "salary_stated": bool(data.salary_stated),
        },
    )
    await session.commit()
    return InterviewOut(
        id=row.id,
        opportunity_id=item_id,
        stage=row.stage,
        mode=row.mode,
        scheduled_at=row.scheduled_at,
        duration_min=row.duration_min,
        notes=row.notes,
        outcome=row.outcome,
        salary_stated=row.salary_stated,
        position=row.position,
    )


async def patch_interview(
    session: AsyncSession,
    interview_id: uuid.UUID,
    data: InterviewIn,
) -> InterviewOut | None:
    row = await session.get(Interview, interview_id)
    if row is None:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    await log_event(
        session,
        verb="opportunity.interview_updated",
        entity_id=row.opportunity_id,
        entity_type="opportunity",
        payload={"interview_id": str(row.id), "salary_stated": bool(row.salary_stated)},
    )
    await session.commit()
    return InterviewOut(
        id=row.id,
        opportunity_id=row.opportunity_id,
        stage=row.stage,
        mode=row.mode,
        scheduled_at=row.scheduled_at,
        duration_min=row.duration_min,
        notes=row.notes,
        outcome=row.outcome,
        salary_stated=row.salary_stated,
        position=row.position,
    )


async def delete_interview(session: AsyncSession, interview_id: uuid.UUID) -> bool:
    row = await session.get(Interview, interview_id)
    if row is None:
        return False
    await log_event(
        session,
        verb="opportunity.interview_deleted",
        entity_id=row.opportunity_id,
        entity_type="opportunity",
        payload={"interview_id": str(row.id)},
    )
    await session.delete(row)
    await session.commit()
    return True


async def funnel(session: AsyncSession) -> FunnelOut:
    rows = (
        await session.execute(select(Opportunity.status, func.count()).group_by(Opportunity.status))
    ).all()
    counts = {status: count for status, count in rows}
    by_status = [FunnelRow(status=status, count=counts.get(status, 0)) for status in STATUS_FLOW]
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
        total=total,
        by_status=by_status,
        conversions=conversions,
        rejection_reasons=[
            {"reason": reason or "belirsiz", "count": count} for reason, count in reason_rows
        ],
    )


async def list_followups(
    session: AsyncSession,
    *,
    days: int = 30,
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
        FollowupOut(
            id=o.id, title=title, status=o.status, follow_up_at=o.follow_up_at, note=o.notes
        )
        for o, title in rows
    ]


async def deadline_provider(session: AsyncSession) -> list[DeadlineRow]:
    """Firsat son tarihleri + mulakat saatleri (kural 16; deadline_v yerine)."""
    from app.core.deadlines import rows_with_titles
    from app.modules.opportunity.models import Interview, Opportunity

    ACTIVE = ("discovered", "considering", "preparing", "applied", "interview", "offer")
    opps = (
        await session.execute(
            select(Opportunity).where(
                Opportunity.deadline_at.is_not(None),
                Opportunity.status.in_(ACTIVE),
            )
        )
    ).scalars()
    ids = [o.id for o in opps]
    due = {o.id: o.deadline_at for o in opps}
    sub = {o.id: o.kind for o in opps}
    prio = {o.id: o.priority for o in opps}
    rows = await rows_with_titles(
        session,
        type_="opportunity",
        module="opportunity",
        ids=ids,
        due_at=due,
        sub_kind=sub,
        priority=prio,
    )

    interviews = (
        await session.execute(select(Interview).where(Interview.scheduled_at.is_not(None)))
    ).scalars()
    ids = [i.id for i in interviews]
    due = {i.id: i.scheduled_at for i in interviews}
    rows += await rows_with_titles(
        session,
        type_="opportunity",
        module="opportunity",
        ids=ids,
        due_at=due,
        priority={i: 1 for i in ids},
    )
    return rows
