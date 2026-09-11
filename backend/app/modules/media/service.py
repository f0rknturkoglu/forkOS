"""Medya domain is mantigi: item CRUD ve cikis noktalari (dashboard, stats, deadline)."""

from __future__ import annotations

import base64
import binascii
import json
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.entity import (
    archive_entity,
    create_entity,
    delete_entity,
    restore_entity,
    touch_entity,
)
from app.core.events import log_event
from app.core.models import Entity, Link
from app.core.time import local_day_bounds, local_end_of_day, local_today, local_zone
from app.modules import DeadlineRow
from app.modules.media.artwork import (  # noqa: F401 (re-export: router service.X ile erisir)
    ArtworkError,
    ArtworkStore,
    artwork_stats,
    cache_artwork,
    prune_artwork,
)
from app.modules.media.collections import (  # noqa: F401 (re-export: router service.X ile erisir)
    _cover_asset_url,
    _to_collection_out,
    add_collection_item,
    collection_detail,
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
    MediaBusiestDayOut,
    MediaConsumptionIn,
    MediaConsumptionPageOut,
    MediaConversionOut,
    MediaCycleOut,
    MediaDashboardOut,
    MediaDetailOut,
    MediaItemIn,
    MediaItemOut,
    MediaItemUpdate,
    MediaRecentConsumptionOut,
    MediaStats,
    MediaUnitOut,
    MediaUpcomingOut,
    MediaUpcomingPageOut,
)
from app.modules.media.search import (  # noqa: F401 (re-export: router service.X ile erisir)
    _item_search_text,
    _search_text,
    _to_item_out,
    list_items,
    provider_registry,
    search_all_metadata,
)
from app.modules.system.models import Setting

#: Detay ekraninda gosterilen en yeni tuketim sayisi (tamami alt uc ile sayfalanir).
_DETAIL_CONSUMPTIONS = 20
#: `media.upcoming_days` ayari yoksa kullanilan pencere.
_DEFAULT_UPCOMING_DAYS = 30


def _encode_offset(offset: int) -> str:
    raw = json.dumps({"offset": offset}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_offset(cursor: str | None) -> int:
    """Offset imlecini cozer; bozuk imlec ilk sayfayi doner.

    Tuketim ve koleksiyon uclarinda router MediaCommandError'i yakalamiyor
    (imza donuk), bu yuzden cozulemeyen imlec 500 yerine sayfa basindan baslar.
    """
    if not cursor:
        return 0
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        value = json.loads(base64.urlsafe_b64decode(padded).decode())
        offset = int(value["offset"])
        return offset if offset >= 0 else 0
    except (
        binascii.Error,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        UnicodeDecodeError,
        ValueError,
    ):
        return 0


async def _upcoming_days(session: AsyncSession) -> int:
    setting = await session.get(Setting, "media.upcoming_days")
    if setting is None or setting.value is None:
        return _DEFAULT_UPCOMING_DAYS
    try:
        return int(setting.value)
    except (TypeError, ValueError):
        return _DEFAULT_UPCOMING_DAYS


def _range_start(range_: str) -> datetime | None:
    """Istatistik penceresi baslangici: Europe/Istanbul gun basi (UTC).

    `week`/`month`/`year` takvim basi (pomodoro ile ayni kural), `90d` yuvarlanan
    pencere, `all` sinirsiz.
    """
    if range_ == "all":
        return None
    today = local_today()
    if range_ == "week":
        day = today - timedelta(days=today.weekday())
    elif range_ == "month":
        day = today.replace(day=1)
    elif range_ == "90d":
        day = today - timedelta(days=89)
    elif range_ == "year":
        day = today.replace(month=1, day=1)
    else:
        raise ValueError(f"Gecersiz media araligi: {range_}")
    return local_day_bounds(day)[0]


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
                .order_by(MediaConsumption.occurred_at.desc(), MediaConsumption.id.desc())
                .limit(_DETAIL_CONSUMPTIONS)
            )
        ).scalars()
    )
    consumption_count = int(
        (
            await session.execute(
                select(func.count())
                .select_from(MediaConsumption)
                .where(MediaConsumption.media_id == item_id)
            )
        ).scalar_one()
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
    # sync.py service'i import eder; donguyu onlemek icin fonksiyon icinde alinir.
    from app.modules.media.sync import item_sync_state

    return MediaDetailOut(
        item=item,
        units=roots,
        cycles=[MediaCycleOut.model_validate(cycle) for cycle in cycles],
        consumptions=[_to_consumption_out(row) for row in consumptions],
        collections=[_to_collection_out(*row) for row in collection_rows],
        consumption_count=consumption_count,
        sync=await item_sync_state(session, item_id),
    )


async def list_consumptions(
    session: AsyncSession,
    item_id: uuid.UUID,
    *,
    limit: int = 50,
    cursor: str | None = None,
) -> MediaConsumptionPageOut:
    """Tuketim gecmisi: en yeni once, offset tabanli imlecle sayfalanir."""
    total = int(
        (
            await session.execute(
                select(func.count())
                .select_from(MediaConsumption)
                .where(MediaConsumption.media_id == item_id)
            )
        ).scalar_one()
    )
    offset = _decode_offset(cursor)
    rows = list(
        (
            await session.execute(
                select(MediaConsumption)
                .where(MediaConsumption.media_id == item_id)
                .order_by(
                    MediaConsumption.occurred_at.desc(),
                    MediaConsumption.id.desc(),
                )
                .offset(offset)
                .limit(limit)
            )
        ).scalars()
    )
    return MediaConsumptionPageOut(
        items=[_to_consumption_out(row) for row in rows],
        total=total,
        next_cursor=_encode_offset(offset + limit) if offset + len(rows) < total else None,
    )


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


async def list_upcoming(
    session: AsyncSession,
    *,
    days: int | None = None,
    kind: str | None = None,
    provider: str | None = None,
) -> MediaUpcomingPageOut:
    """Yaklasan yayinlar: unit release_at + item release_date birlikte.

    Ayni medya icin pencerede unit satiri varsa item satiri dusurulur
    (daha spesifik kaynak kazanir, duplicate yok). Item release_date bir
    `date`; Europe/Istanbul gun sonuna (23:59:59) oturtulur.
    """
    window_days = await _upcoming_days(session) if days is None else days
    now = datetime.now(UTC)
    end = now + timedelta(days=window_days)
    unit_entity = aliased(Entity)
    item_entity = aliased(Entity)

    unit_stmt = (
        select(MediaUnit, MediaItem, unit_entity.title, item_entity.title)
        .join(unit_entity, unit_entity.id == MediaUnit.id)
        .join(MediaItem, MediaItem.id == MediaUnit.media_id)
        .join(item_entity, item_entity.id == MediaItem.id)
        .where(
            MediaUnit.release_at.is_not(None),
            MediaUnit.release_at >= now,
            MediaUnit.release_at <= end,
            item_entity.archived_at.is_(None),
        )
        .order_by(MediaUnit.release_at.asc(), MediaUnit.id.asc())
    )
    if kind:
        unit_stmt = unit_stmt.where(MediaItem.kind == kind)
    if provider:
        unit_stmt = unit_stmt.where(MediaItem.provider == provider)
    unit_rows = (await session.execute(unit_stmt)).all()
    unit_media_ids = {unit.media_id for unit, *_ in unit_rows}

    item_stmt = (
        select(MediaItem, item_entity.title)
        .join(item_entity, item_entity.id == MediaItem.id)
        .where(
            MediaItem.release_date.is_not(None),
            MediaItem.release_date >= local_today(now),
            MediaItem.release_date <= local_today(end),
            item_entity.archived_at.is_(None),
        )
        .order_by(MediaItem.release_date.asc(), MediaItem.id.asc())
    )
    if kind:
        item_stmt = item_stmt.where(MediaItem.kind == kind)
    if provider:
        item_stmt = item_stmt.where(MediaItem.provider == provider)

    entries: list[tuple[datetime, MediaUpcomingOut]] = []
    for unit, item, unit_title, item_title in unit_rows:
        label = unit_title or item_title
        entries.append(
            (
                unit.release_at,
                MediaUpcomingOut(
                    entry_type="unit",
                    entity_id=unit.id,
                    media_id=unit.media_id,
                    media_title=item_title,
                    title=label,
                    kind=item.kind,
                    provider=unit.provider or item.provider,
                    release_at=unit.release_at,
                    cover_url=_cover_asset_url(unit.cover_path, unit.cover_url)
                    or _cover_asset_url(item.cover_path, item.cover_url),
                    monitored=item.monitored,
                    unit_type=unit.unit_type,
                    number=_number(unit.number),
                ),
            )
        )
    for item, item_title in (await session.execute(item_stmt)).all():
        if item.id in unit_media_ids or item.release_date is None:
            continue
        release_at = local_end_of_day(item.release_date)
        if not now <= release_at <= end:
            continue
        entries.append(
            (
                release_at,
                MediaUpcomingOut(
                    entry_type="item",
                    entity_id=item.id,
                    media_id=item.id,
                    media_title=item_title,
                    title=item_title,
                    kind=item.kind,
                    provider=item.provider,
                    release_at=release_at,
                    cover_url=_cover_asset_url(item.cover_path, item.cover_url),
                    monitored=item.monitored,
                ),
            )
        )
    entries.sort(key=lambda entry: (entry[0], str(entry[1].entity_id)))
    return MediaUpcomingPageOut(
        entries=[entry for _, entry in entries], total=len(entries)
    )


async def stats(session: AsyncSession, *, range_: str = "all") -> MediaStats:
    """Kutuphane + tuketim istatistikleri.

    `total/in_progress/completed/planned/by_kind/scored_count` arsivsiz tum
    kayitlardan (araliktan bagimsiz); tuketim alanlari `range_` penceresinden.
    """
    start = _range_start(range_)
    now = datetime.now(UTC)
    live_ids = select(Entity.id).where(Entity.archived_at.is_(None))
    finished_condition = (
        MediaItem.finished_at.is_not(None)
        if start is None
        else MediaItem.finished_at.between(start, now)
    )
    started_condition = or_(
        MediaItem.started_at.is_not(None),
        MediaItem.status.in_(("in_progress", "paused", "dropped")),
    )
    (
        total,
        in_progress,
        planned,
        completed,
        started,
        scored_count,
        average_score,
        completed_in_range,
    ) = (
        await session.execute(
            select(
                func.count(MediaItem.id),
                func.count(MediaItem.id).filter(MediaItem.status == "in_progress"),
                func.count(MediaItem.id).filter(MediaItem.status == "planned"),
                func.count(MediaItem.id).filter(MediaItem.status == "completed"),
                func.count(MediaItem.id).filter(started_condition),
                func.count(MediaItem.score),
                func.avg(MediaItem.score),
                func.count(MediaItem.id).filter(finished_condition),
            ).where(MediaItem.id.in_(live_ids))
        )
    ).one()

    by_kind: dict[str, int] = {}
    score_distribution = {str(value): 0 for value in range(1, 11)}
    for kind, score, count in (
        await session.execute(
            select(MediaItem.kind, MediaItem.score, func.count())
            .where(MediaItem.id.in_(live_ids))
            .group_by(MediaItem.kind, MediaItem.score)
        )
    ).all():
        by_kind[kind] = by_kind.get(kind, 0) + int(count)
        if score is not None and 1 <= score <= 10:
            score_distribution[str(score)] += int(count)

    consumption_filters = [MediaConsumption.media_id.in_(live_ids)]
    if start is not None:
        consumption_filters.append(MediaConsumption.occurred_at >= start)
        consumption_filters.append(MediaConsumption.occurred_at <= now)
    pomodoro_condition = MediaConsumption.meta["pomodoro_session_id"].is_not(None)
    by_measure: dict[str, float] = {}
    total_duration_min = 0
    pomodoro_minutes = 0
    for measure, amount, duration, pomodoro in (
        await session.execute(
            select(
                MediaConsumption.measure,
                func.sum(MediaConsumption.amount),
                func.sum(MediaConsumption.duration_min),
                func.sum(MediaConsumption.duration_min).filter(pomodoro_condition),
            )
            .where(*consumption_filters)
            .group_by(MediaConsumption.measure)
        )
    ).all():
        if measure is not None:
            by_measure[measure] = float(amount or 0)
        total_duration_min += int(duration or 0)
        pomodoro_minutes += int(pomodoro or 0)

    local_day = func.date_trunc(
        "day", func.timezone(str(local_zone()), MediaConsumption.occurred_at)
    ).label("day")
    day_rows = (
        await session.execute(
            select(local_day, func.count()).where(*consumption_filters).group_by(local_day)
        )
    ).all()
    busiest_day = None
    if day_rows:
        day, count = max(day_rows, key=lambda row: (row[1], row[0]))
        busiest_day = MediaBusiestDayOut(day=day.date().isoformat(), count=int(count))

    return MediaStats(
        total=total,
        in_progress=in_progress,
        completed=completed,
        planned=planned,
        by_kind=by_kind,
        by_measure=by_measure,
        total_duration_min=total_duration_min,
        pomodoro_minutes=pomodoro_minutes,
        scored_count=scored_count,
        average_score=round(float(average_score), 1) if average_score is not None else None,
        score_distribution=score_distribution,
        conversion=MediaConversionOut(
            planned=planned, started=started, completed=completed
        ),
        active_days=len(day_rows),
        busiest_day=busiest_day,
        completed_in_range=completed_in_range,
    )


async def dashboard(
    session: AsyncSession, *, range_: str = "all", recent_limit: int = 20
) -> MediaDashboardOut:
    """Istatistik sayfasi icin tek istek: ozet + devam + yaklasan + son tuketimler."""
    continue_page = await list_items(session, status="in_progress", limit=4)
    live_media_ids = select(Entity.id).where(Entity.archived_at.is_(None))
    now = datetime.now(UTC)
    upcoming_rows = (
        await session.execute(
            select(MediaUnit, Entity.title)
            .join(Entity, Entity.id == MediaUnit.id)
            .where(
                MediaUnit.release_at.is_not(None),
                MediaUnit.release_at >= now,
                MediaUnit.release_at <= now + timedelta(days=await _upcoming_days(session)),
                MediaUnit.media_id.in_(live_media_ids),
            )
            .order_by(MediaUnit.release_at)
        )
    ).all()
    return MediaDashboardOut(
        continue_items=continue_page.items,
        upcoming=[_to_unit_out(*row) for row in upcoming_rows],
        recent_consumptions=await recent_consumptions(session, limit=recent_limit),
        stats=await stats(session, range_=range_),
    )


async def deadline_provider(session: AsyncSession) -> list[DeadlineRow]:
    """Yaklasan cikislar: unit release_at (varsa) yoksa item release_date (kural 16).

    Item `release_date` bir `date`; zaman cizgisine Europe/Istanbul gun sonu
    olarak konur. Ayni medyanin unit deadline'i varsa item satiri eklenmez.
    """
    from app.core.deadlines import rows_with_titles

    # Iki kez gezilen ScalarResult ikinci turda bosalir; listele.
    units = list(
        (
            await session.execute(select(MediaUnit).where(MediaUnit.release_at.is_not(None)))
        ).scalars()
    )
    unit_due = {unit.id: unit.release_at for unit in units}
    unit_media_ids = {unit.media_id for unit in units}
    items = list(
        (
            await session.execute(select(MediaItem).where(MediaItem.release_date.is_not(None)))
        ).scalars()
    )
    item_due = {
        item.id: local_end_of_day(item.release_date)
        for item in items
        if item.release_date is not None and item.id not in unit_media_ids
    }
    item_ids = list(item_due)
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


async def recent_consumptions(
    session: AsyncSession, limit: int = 10
) -> list[MediaRecentConsumptionOut]:
    """Arsivlenmemis medyanin en son tuketimleri; baslik ve tur birlikte."""
    live_ids = select(Entity.id).where(Entity.archived_at.is_(None))
    rows = (
        await session.execute(
            select(MediaConsumption, MediaItem.kind, Entity.title)
            .join(MediaItem, MediaItem.id == MediaConsumption.media_id)
            .join(Entity, Entity.id == MediaConsumption.media_id)
            .where(MediaConsumption.media_id.in_(live_ids))
            .order_by(MediaConsumption.occurred_at.desc())
            .limit(limit)
        )
    ).all()
    return [
        MediaRecentConsumptionOut(
            id=consumption.id,
            media_id=consumption.media_id,
            title=title,
            kind=kind,
            action=consumption.action,
            measure=consumption.measure,
            amount=_number(consumption.amount),
            progress_after=_number(consumption.progress_after),
            occurred_at=consumption.occurred_at,
            duration_min=consumption.duration_min,
        )
        for consumption, kind, title in rows
    ]