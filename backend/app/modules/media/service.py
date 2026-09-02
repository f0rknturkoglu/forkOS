"""Medya domain is mantigi: item CRUD ve cikis noktalari (dashboard, stats, deadline)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import (
    archive_entity,
    create_entity,
    delete_entity,
    restore_entity,
    touch_entity,
)
from app.core.events import log_event
from app.core.models import Entity, Link
from app.modules import DeadlineRow
from app.modules.media.collections import (  # noqa: F401 (re-export: router service.X ile erisir)
    _to_collection_out,
    add_collection_item,
    create_collection,
    delete_collection,
    list_collections,
    remove_collection_item,
    update_collection,
)
from app.modules.media.models import (
    MEDIA_COLLECTION_ITEM_RELATION,
    MediaCollection,
    MediaConsumption,
    MediaCycle,
    MediaItem,
    MediaUnit,
)
from app.modules.media.progress import (  # noqa: F401 (re-export: router service.X ile erisir)
    DEFAULT_MEASURE,
    MediaCommandError,
    MediaConflictError,
    _consume_locked,
    _number,
    _synchronize_status,
    _to_consumption_out,
    consume,
    list_cycles,
    start_cycle,
    upsert_unit,
    upsert_unit_in_transaction,
)
from app.modules.media.providers.base import (
    canonical_provider_id,
    provider_identity_candidates,
)
from app.modules.media.schemas import (
    MediaConsumptionIn,
    MediaConsumptionOut,
    MediaCycleOut,
    MediaDashboardOut,
    MediaDetailOut,
    MediaItemIn,
    MediaItemOut,
    MediaItemUpdate,
    MediaStats,
    MediaUnitOut,
)
from app.modules.media.search import (  # noqa: F401 (re-export: router service.X ile erisir)
    _item_search_text,
    _search_text,
    _to_item_out,
    list_items,
    provider_registry,
    search_all_metadata,
)


def _to_unit_out(unit: MediaUnit, title: str) -> MediaUnitOut:
    return MediaUnitOut(
        id=unit.id,
        media_id=unit.media_id,
        parent_id=unit.parent_id,
        title=title,
        unit_type=unit.unit_type,
        number=_number(unit.number),
        duration_min=unit.duration_min,
        release_at=unit.release_at,
        progress_total=_number(unit.progress_total),
        progress_measure=unit.progress_measure,
        provider=unit.provider,
        provider_id=unit.provider_id,
        provider_ids=unit.provider_ids or {},
        cover_url=unit.cover_url,
        cover_path=unit.cover_path,
        meta=unit.meta or {},
        created_at=unit.created_at,
        updated_at=unit.updated_at,
    )


async def get_item(session: AsyncSession, item_id: uuid.UUID) -> MediaItemOut | None:
    row = (
        await session.execute(
            select(MediaItem, Entity)
            .join(Entity, Entity.id == MediaItem.id)
            .where(MediaItem.id == item_id)
        )
    ).first()
    return _to_item_out(*row) if row else None


async def get_detail(session: AsyncSession, item_id: uuid.UUID) -> MediaDetailOut | None:
    item = await get_item(session, item_id)
    if item is None:
        return None
    unit_rows = (
        await session.execute(
            select(MediaUnit, Entity.title)
            .join(Entity, Entity.id == MediaUnit.id)
            .where(MediaUnit.media_id == item_id)
            .order_by(MediaUnit.number.asc().nulls_last(), Entity.created_at)
        )
    ).all()
    nodes = {unit.id: _to_unit_out(unit, title) for unit, title in unit_rows}
    roots = []
    for unit, _title in unit_rows:
        if unit.parent_id and unit.parent_id in nodes:
            nodes[unit.parent_id].children.append(nodes[unit.id])
        else:
            roots.append(nodes[unit.id])
    cycles = list(
        (
            await session.execute(
                select(MediaCycle)
                .where(MediaCycle.media_id == item_id)
                .order_by(MediaCycle.ordinal.desc())
            )
        ).scalars()
    )
    consumptions = list(
        (
            await session.execute(
                select(MediaConsumption)
                .where(MediaConsumption.media_id == item_id)
                .order_by(MediaConsumption.occurred_at.desc(), MediaConsumption.created_at.desc())
            )
        ).scalars()
    )
    collection_rows = (
        await session.execute(
            select(MediaCollection, Entity.title)
            .join(Entity, Entity.id == MediaCollection.id)
            .join(
                Link,
                (Link.from_id == MediaCollection.id)
                & (Link.to_id == item_id)
                & (Link.relation == MEDIA_COLLECTION_ITEM_RELATION),
            )
            .order_by(MediaCollection.position, Entity.title)
        )
    ).all()
    return MediaDetailOut(
        item=item,
        units=roots,
        cycles=[MediaCycleOut.model_validate(cycle) for cycle in cycles],
        consumptions=[_to_consumption_out(row) for row in consumptions],
        collections=[_to_collection_out(*row) for row in collection_rows],
    )


async def list_consumptions(session: AsyncSession, item_id: uuid.UUID) -> list[MediaConsumptionOut]:
    rows = list(
        (
            await session.execute(
                select(MediaConsumption)
                .where(MediaConsumption.media_id == item_id)
                .order_by(
                    MediaConsumption.occurred_at.desc(),
                    MediaConsumption.created_at.desc(),
                    MediaConsumption.id.desc(),
                )
            )
        ).scalars()
    )
    return [_to_consumption_out(row) for row in rows]


async def _provider_duplicate(session: AsyncSession, data: MediaItemIn) -> bool:
    if data.source != "provider" or not data.provider or not data.provider_id:
        return False
    filters = [
        MediaItem.provider == data.provider,
        MediaItem.provider_id.in_(
            provider_identity_candidates(data.provider, data.kind, data.provider_id)
        ),
    ]
    if data.provider == "tmdb":
        filters.append(MediaItem.kind == data.kind)
    return (
        await session.execute(
            select(MediaItem.id).where(*filters)
        )
    ).scalar_one_or_none() is not None


async def create_item(session: AsyncSession, data: MediaItemIn) -> MediaItemOut:
    normalized_provider_id = canonical_provider_id(data.provider, data.kind, data.provider_id)
    if normalized_provider_id != data.provider_id:
        data = data.model_copy(update={"provider_id": normalized_provider_id})
    if await _provider_duplicate(session, data):
        raise MediaConflictError("Bu provider kaydi kutuphanede zaten var")
    provider_ids = dict(data.provider_ids)
    if data.provider and data.provider_id:
        provider_ids[data.provider] = provider_identity_candidates(
            data.provider, data.kind, data.provider_id
        )[-1]
    title = data.title.strip()
    requested_status = data.status
    entity = await create_entity(
        session,
        type=MediaItem.ENTITY_TYPE,
        title=title,
        search_text=_search_text(data),
    )
    item = MediaItem(
        id=entity.id,
        kind=data.kind,
        status="planned",
        progress=(
            0
            if requested_status != "planned" or (data.progress and data.progress > 0)
            else data.progress
        ),
        total=data.total,
        score=data.score,
        notes=data.notes,
        started_at=data.started_at,
        finished_at=data.finished_at if requested_status == "planned" else None,
        meta=data.meta,
        summary=data.summary,
        release_date=data.release_date,
        progress_measure=data.progress_measure or DEFAULT_MEASURE[data.kind],
        review=data.review,
        favorite=data.favorite,
        owned=data.owned,
        ownership=data.ownership,
        monitored=data.monitored,
        provider=data.provider,
        provider_id=data.provider_id,
        provider_ids=provider_ids,
        cover_url=data.cover_url,
        cover_path=data.cover_path,
        backdrop_url=data.backdrop_url,
        backdrop_path=data.backdrop_path,
        last_synced_at=data.last_synced_at,
    )
    session.add(item)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise MediaConflictError("Bu provider kaydi kutuphanede zaten var") from exc
    await log_event(
        session,
        verb="media.item_added",
        entity_id=item.id,
        entity_type="media_item",
        payload={"kind": item.kind, "status": requested_status, "title": title},
    )
    if data.progress and data.progress > 0:
        await _consume_locked(
            session,
            item,
            MediaConsumptionIn(
                client_uuid=uuid.uuid4(),
                action="set",
                measure=data.progress_measure or DEFAULT_MEASURE[data.kind],
                progress_after=data.progress,
                occurred_at=data.started_at,
                note="initial progress",
            ),
            complete_when_total=requested_status == "planned",
        )
    if requested_status == "completed":
        await _consume_locked(
            session,
            item,
            MediaConsumptionIn(
                client_uuid=uuid.uuid4(),
                action="finish",
                occurred_at=data.finished_at,
                note="initial completion",
            ),
        )
    elif requested_status != "planned":
        await _synchronize_status(session, item, requested_status)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise MediaConflictError("Bu provider kaydi kutuphanede zaten var") from exc
    result = await get_item(session, item.id)
    if result is None:
        raise RuntimeError("Olusturulan medya kaydi okunamadi")
    return result


async def update_item(
    session: AsyncSession, item_id: uuid.UUID, data: MediaItemUpdate
) -> MediaItemOut | None:
    item = (
        await session.execute(select(MediaItem).where(MediaItem.id == item_id).with_for_update())
    ).scalar_one_or_none()
    entity = await session.get(Entity, item_id)
    if item is None or entity is None:
        return None
    changes = data.model_dump(exclude_unset=True)
    title = changes.pop("title", None)
    status = changes.pop("status", None)
    target_provider = changes.get("provider", item.provider)
    target_provider_id = changes.get("provider_id", item.provider_id)
    target_kind = changes.get("kind", item.kind)
    target_provider_id = canonical_provider_id(
        target_provider, target_kind, target_provider_id
    )
    if target_provider_id is not None:
        changes["provider_id"] = target_provider_id
    if bool(target_provider) != bool(target_provider_id):
        raise MediaCommandError("Provider kimligi provider ve provider_id birlikte gerektirir")
    if target_provider and target_provider_id:
        duplicate_filters = [
            MediaItem.provider == target_provider,
            MediaItem.provider_id.in_(
                provider_identity_candidates(
                    target_provider, target_kind, target_provider_id
                )
            ),
            MediaItem.id != item_id,
        ]
        if target_provider == "tmdb":
            duplicate_filters.append(MediaItem.kind == target_kind)
        duplicate = (
            await session.execute(
                select(MediaItem.id).where(*duplicate_filters)
            )
        ).scalar_one_or_none()
        if duplicate is not None:
            raise MediaConflictError("Bu provider kaydi kutuphanede zaten var")
    for key, value in changes.items():
        setattr(item, key, value)
    if target_provider and target_provider_id:
        provider_ids = dict(item.provider_ids or {})
        provider_ids[target_provider] = provider_identity_candidates(
            target_provider, target_kind, target_provider_id
        )[-1]
        item.provider_ids = provider_ids
    if status is not None:
        await _synchronize_status(session, item, status)
    await touch_entity(
        session,
        item.id,
        title=title.strip() if title else None,
        search_text=_item_search_text(item),
    )
    await log_event(
        session,
        verb="media.item_updated",
        entity_id=item.id,
        entity_type="media_item",
        payload={
            "title": title or entity.title,
            "kind": item.kind,
            "changes": [*changes, *(["status"] if status is not None else [])],
        },
    )
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise MediaConflictError("Bu provider kaydi kutuphanede zaten var") from exc
    return await get_item(session, item.id)


async def trash_item(session: AsyncSession, item_id: uuid.UUID) -> MediaItemOut | None:
    item = await session.get(MediaItem, item_id)
    entity = await session.get(Entity, item_id)
    if item is None or entity is None:
        return None
    if entity.archived_at is None:
        await archive_entity(session, item_id)
        await log_event(
            session,
            verb="media.item_trashed",
            entity_id=item_id,
            entity_type="media_item",
            payload={"title": entity.title, "kind": item.kind},
        )
        await session.commit()
    return await get_item(session, item_id)


async def restore_item(session: AsyncSession, item_id: uuid.UUID) -> MediaItemOut | None:
    item = await session.get(MediaItem, item_id)
    entity = await session.get(Entity, item_id)
    if item is None or entity is None:
        return None
    if entity.archived_at is not None:
        await restore_entity(session, item_id)
        await log_event(
            session,
            verb="media.item_restored",
            entity_id=item_id,
            entity_type="media_item",
            payload={"title": entity.title, "kind": item.kind},
        )
        await session.commit()
    return await get_item(session, item_id)


async def permanent_delete_item(session: AsyncSession, item_id: uuid.UUID) -> bool:
    item = await session.get(MediaItem, item_id)
    entity = await session.get(Entity, item_id)
    if item is None or entity is None:
        return False
    if entity.archived_at is None:
        raise MediaConflictError("Medya kalici silinmeden once cope tasinmali")
    title, kind = entity.title, item.kind
    await log_event(
        session,
        verb="media.item_deleted",
        entity_id=item_id,
        entity_type="media_item",
        payload={"item_id": str(item_id), "title": title, "kind": kind},
    )
    await session.flush()
    for model in (MediaConsumption, MediaCycle, MediaUnit):
        child_ids = list(
            (await session.execute(select(model.id).where(model.media_id == item_id))).scalars()
        )
        for child_id in child_ids:
            await delete_entity(session, child_id)
        await session.flush()
    await delete_entity(session, item_id)
    await session.commit()
    return True


async def upcoming_units(session: AsyncSession, days: int = 30) -> list[MediaUnitOut]:
    now = datetime.now(UTC)
    live_media_ids = select(Entity.id).where(Entity.archived_at.is_(None))
    rows = (
        await session.execute(
            select(MediaUnit, Entity.title)
            .join(Entity, Entity.id == MediaUnit.id)
            .where(
                MediaUnit.release_at >= now,
                MediaUnit.release_at <= now + timedelta(days=days),
                MediaUnit.media_id.in_(live_media_ids),
            )
            .order_by(MediaUnit.release_at)
        )
    ).all()
    return [_to_unit_out(*row) for row in rows]


async def stats(session: AsyncSession) -> MediaStats:
    live_ids = select(Entity.id).where(Entity.archived_at.is_(None))
    by_kind = dict(
        (
            await session.execute(
                select(MediaItem.kind, func.count())
                .where(MediaItem.id.in_(live_ids))
                .group_by(MediaItem.kind)
            )
        ).all()
    )
    by_status = dict(
        (
            await session.execute(
                select(MediaItem.status, func.count())
                .where(MediaItem.id.in_(live_ids))
                .group_by(MediaItem.status)
            )
        ).all()
    )
    duration = int(
        (
            await session.execute(
                select(func.coalesce(func.sum(MediaConsumption.duration_min), 0)).where(
                    MediaConsumption.media_id.in_(live_ids)
                )
            )
        ).scalar_one()
    )
    score_count, average_score = (
        await session.execute(
            select(func.count(MediaItem.score), func.avg(MediaItem.score)).where(
                MediaItem.id.in_(live_ids), MediaItem.score.is_not(None)
            )
        )
    ).one()
    return MediaStats(
        total=sum(by_kind.values()),
        in_progress=by_status.get("in_progress", 0),
        completed=by_status.get("completed", 0),
        planned=by_status.get("planned", 0),
        by_kind=by_kind,
        total_duration_min=duration,
        scored_count=score_count,
        average_score=float(average_score) if average_score is not None else None,
    )


async def dashboard(session: AsyncSession) -> MediaDashboardOut:
    continue_page = await list_items(session, status="in_progress", limit=4)
    live_media_ids = select(Entity.id).where(Entity.archived_at.is_(None))
    recent = list(
        (
            await session.execute(
                select(MediaConsumption)
                .where(MediaConsumption.media_id.in_(live_media_ids))
                .order_by(MediaConsumption.occurred_at.desc())
                .limit(12)
            )
        ).scalars()
    )
    return MediaDashboardOut(
        continue_items=continue_page.items,
        upcoming=await upcoming_units(session),
        recent_consumptions=[_to_consumption_out(row) for row in recent],
        stats=await stats(session),
    )


async def deadline_provider(session: AsyncSession) -> list[DeadlineRow]:
    """Yaklasan cikislar: unit release_at (varsa) yoksa item release_date (kural 16)."""
    from app.core.deadlines import rows_with_titles
    from app.modules.media.models import MediaItem, MediaUnit

    items = (await session.execute(
        select(MediaItem).where(MediaItem.release_date.is_not(None))
    )).scalars()
    item_due = {i.id: i.release_date for i in items}
    item_ids = list(item_due)
    units = (await session.execute(
        select(MediaUnit).where(MediaUnit.release_at.is_not(None))
    )).scalars()
    unit_due = {u.id: u.release_at for u in units}
    unit_ids = list(unit_due)
    rows = await rows_with_titles(
        session, type_="media_item", module="media",
        ids=item_ids, due_at=item_due, priority={i: 1 for i in item_ids},
    )
    rows += await rows_with_titles(
        session, type_="media_unit", module="media",
        ids=unit_ids, due_at=unit_due, priority={i: 1 for i in unit_ids},
    )
    return rows