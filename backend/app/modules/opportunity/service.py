from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import create_entity, delete_entity, touch_entity
from app.core.events import log_event
from app.core.models import Entity
from app.core.notifications import notify
from app.modules.opportunity.models import Opportunity, OpportunityRequirement
from app.modules.opportunity.schemas import (
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
    for key, value in changes.items():
        setattr(item, key, value)
    if item.status == "applied" and old_status != "applied":
        item.applied_at = datetime.now(UTC)
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
    await session.commit()
    return created
