"""Medya domain is mantigi ve aggregate ilerleme kurallari."""

from __future__ import annotations

import asyncio
import base64
import binascii
import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, or_, select
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
from app.core.links import link, unlink
from app.core.models import Entity, EntityTag, Link, Tag
from app.modules import DeadlineRow
from app.modules.media.models import (
    MEDIA_COLLECTION_ITEM_RELATION,
    MediaCollection,
    MediaConsumption,
    MediaCycle,
    MediaItem,
    MediaUnit,
)
from app.modules.media.providers.base import (
    MediaProvider,
    ProviderResult,
    canonical_provider_id,
    provider_identity_candidates,
)
from app.modules.media.providers.registry import ProviderRegistry
from app.modules.media.schemas import (
    GlobalMetadataSearchOut,
    MediaCollectionIn,
    MediaCollectionOut,
    MediaCollectionUpdate,
    MediaConsumptionIn,
    MediaConsumptionOut,
    MediaCycleOut,
    MediaCycleStart,
    MediaDashboardOut,
    MediaDetailOut,
    MediaItemIn,
    MediaItemOut,
    MediaItemUpdate,
    MediaPageOut,
    MediaStats,
    MediaUnitOut,
    MediaUnitUpsert,
    MetadataResult,
    MetadataSearchWarning,
    ProgressValidationOut,
    UnitUpsertResult,
)
from app.modules.system.models import Setting

SERIAL_KINDS = {"show", "anime", "manga", "podcast", "music"}
RELEASE_PENDING_META_KEY = "_forkos_release_pending"
DEFAULT_MEASURE = {
    "movie": "item",
    "show": "episode",
    "anime": "episode",
    "manga": "chapter",
    "book": "page",
    "audiobook": "minute",
    "podcast": "episode",
    "music": "track",
    "game": "hour",
}
REQUEST_FINGERPRINT_KEY = "_request_fingerprint"
logger = logging.getLogger(__name__)


class MediaConflictError(ValueError):
    pass


class MediaCommandError(ValueError):
    pass


def _number(value: Decimal | int | float | None) -> float | None:
    return float(value) if value is not None else None


def _provider_id(item: MediaItem) -> str | None:
    return item.provider_id


def _to_item_out(item: MediaItem, entity: Entity) -> MediaItemOut:
    return MediaItemOut(
        id=item.id,
        title=entity.title,
        kind=item.kind,
        status=item.status,
        progress=_number(item.progress),
        total=_number(item.total),
        score=item.score,
        notes=item.notes,
        started_at=item.started_at,
        finished_at=item.finished_at,
        meta=item.meta or {},
        summary=item.summary,
        release_date=item.release_date,
        progress_measure=item.progress_measure,
        review=item.review,
        favorite=item.favorite,
        owned=item.owned,
        ownership=item.ownership or {},
        monitored=item.monitored,
        provider=item.provider,
        provider_id=_provider_id(item),
        provider_ids=item.provider_ids or {},
        cover_url=item.cover_url,
        cover_path=item.cover_path,
        backdrop_url=item.backdrop_url,
        backdrop_path=item.backdrop_path,
        last_synced_at=item.last_synced_at,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        archived_at=entity.archived_at,
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


def _to_consumption_out(row: MediaConsumption) -> MediaConsumptionOut:
    return MediaConsumptionOut(
        id=row.id,
        media_id=row.media_id,
        cycle_id=row.cycle_id,
        unit_id=row.unit_id,
        client_uuid=row.client_uuid,
        action=row.action,
        measure=row.measure,
        amount=_number(row.amount),
        progress_after=_number(row.progress_after),
        occurred_at=row.occurred_at,
        duration_min=row.duration_min,
        note=row.note,
        meta=row.meta or {},
        created_at=row.created_at,
    )


def _to_collection_out(collection: MediaCollection, title: str) -> MediaCollectionOut:
    return MediaCollectionOut(
        id=collection.id,
        title=title,
        description=collection.description,
        color=collection.color,
        position=collection.position,
        created_at=collection.created_at,
        updated_at=collection.updated_at,
    )


def _canonical_consumption_request(data: MediaConsumptionIn) -> dict[str, object]:
    return data.model_dump(mode="json", exclude_none=False)


def _search_text(data: MediaItemIn | MediaItemUpdate) -> str:
    values = [
        getattr(data, "summary", None),
        getattr(data, "notes", None),
        getattr(data, "review", None),
    ]
    meta = getattr(data, "meta", None)
    if meta:
        values.append(json.dumps(meta, ensure_ascii=False, sort_keys=True))
    return " ".join(value for value in values if value)


def _item_search_text(item: MediaItem) -> str:
    values = [item.summary, item.notes, item.review]
    if item.meta:
        values.append(json.dumps(item.meta, ensure_ascii=False, sort_keys=True))
    return " ".join(value for value in values if value)


def _encode_cursor(offset: int) -> str:
    raw = json.dumps({"offset": offset}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        value = json.loads(base64.urlsafe_b64decode(padded).decode())
        offset = int(value["offset"])
        if offset < 0:
            raise ValueError
        return offset
    except (
        binascii.Error,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        UnicodeDecodeError,
        ValueError,
    ) as exc:
        raise MediaCommandError("Gecersiz media cursor") from exc


async def provider_registry(session: AsyncSession) -> ProviderRegistry:
    keys = (
        "media.tmdb_key",
        "media.google_books_key",
        "media.igdb_client_id",
        "media.igdb_client_secret",
    )
    rows = list((await session.execute(select(Setting).where(Setting.key.in_(keys)))).scalars())
    return ProviderRegistry.from_settings({row.key: row.value for row in rows})


def _metadata_result(row: ProviderResult, kind: str) -> MetadataResult:
    return MetadataResult(
        kind=kind,
        provider=row.provider,
        provider_id=row.provider_id,
        title=row.title,
        subtitle=row.subtitle,
        year=row.year,
        summary=row.summary,
        total=row.total,
        progress_measure=row.progress_measure,
        cover=row.cover_url,
        backdrop=row.backdrop_url,
        cover_url=row.cover_url,
        backdrop_url=row.backdrop_url,
        provider_ids=row.provider_ids,
        meta=row.meta,
        metadata={
            **row.meta,
            "provider": row.provider,
            "provider_id": row.provider_id,
            "provider_ids": row.provider_ids,
        },
    )


async def search_metadata(
    session: AsyncSession, q: str, kind: str, *, provider_id: str | None = None
) -> list[MetadataResult]:
    registry = await provider_registry(session)
    provider = registry.by_id(provider_id, kind=kind) if provider_id else registry.for_kind(kind)
    if provider is None or not provider.ready:
        missing = provider.missing_settings if provider else ()
        suffix = f": {', '.join(missing)}" if missing else ""
        raise RuntimeError(f"{kind} için hazır provider yok{suffix}")
    results = await provider.search(q)
    return [_metadata_result(row, kind) for row in results]


async def search_all_metadata(session: AsyncSession, q: str) -> GlobalMetadataSearchOut:
    registry = await provider_registry(session)
    providers: list[tuple[str, MediaProvider]] = [
        variant
        for variants in registry.provider_groups().values()
        for variant in variants
    ]
    ready: list[tuple[str, MediaProvider]] = []
    warnings: list[MetadataSearchWarning] = []

    for kind, provider in providers:
        if provider.ready:
            ready.append((kind, provider))
            continue
        missing = ", ".join(provider.missing_settings)
        suffix = f": {missing}" if missing else ""
        warnings.append(
            MetadataSearchWarning(
                provider=provider.id,
                kind=kind,
                message=f"{kind} için provider hazır değil{suffix}",
            )
        )

    outcomes = await asyncio.gather(
        *(provider.search(q) for _, provider in ready), return_exceptions=True
    )
    results: list[MetadataResult] = []
    seen: set[tuple[str, str]] = set()
    for (kind, provider), outcome in zip(ready, outcomes, strict=True):
        if isinstance(outcome, BaseException):
            logger.warning(
                "Media provider search failed (kind=%s provider=%s error_type=%s)",
                kind,
                provider.id,
                type(outcome).__name__,
            )
            warnings.append(
                MetadataSearchWarning(
                    provider=provider.id,
                    kind=kind,
                    message="Provider araması başarısız",
                )
            )
            continue
        for row in outcome:
            result = _metadata_result(row, kind)
            key = (result.provider, result.provider_id)
            if key not in seen:
                seen.add(key)
                results.append(result)

    return GlobalMetadataSearchOut(results=results, warnings=warnings)


async def list_items(
    session: AsyncSession,
    *,
    kind: str | None = None,
    status: str | None = None,
    q: str | None = None,
    collection_id: uuid.UUID | None = None,
    tag: str | None = None,
    owned: bool | None = None,
    monitored: bool | None = None,
    trashed: bool = False,
    sort: str = "updated",
    cursor: str | None = None,
    limit: int = 48,
) -> MediaPageOut:
    stmt = select(MediaItem, Entity).join(Entity, Entity.id == MediaItem.id)
    stmt = stmt.where(Entity.archived_at.is_not(None) if trashed else Entity.archived_at.is_(None))
    if kind:
        stmt = stmt.where(MediaItem.kind == kind)
    if status:
        stmt = stmt.where(MediaItem.status == status)
    if q:
        for token in q.split():
            pattern = f"%{token}%"
            stmt = stmt.where(or_(Entity.title.ilike(pattern), Entity.search_text.ilike(pattern)))
    if collection_id:
        stmt = stmt.join(
            Link,
            (Link.to_id == MediaItem.id)
            & (Link.from_id == collection_id)
            & (Link.relation == MEDIA_COLLECTION_ITEM_RELATION),
        )
    if tag:
        stmt = stmt.join(EntityTag, EntityTag.entity_id == MediaItem.id).join(
            Tag, (Tag.id == EntityTag.tag_id) & (func.lower(Tag.name) == tag.lower())
        )
    if owned is not None:
        stmt = stmt.where(MediaItem.owned.is_(owned))
    if monitored is not None:
        stmt = stmt.where(MediaItem.monitored.is_(monitored))
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = int((await session.execute(count_stmt)).scalar_one())
    orders = {
        "updated": (Entity.updated_at.desc(), MediaItem.id.desc()),
        "created": (Entity.created_at.desc(), MediaItem.id.desc()),
        "title": (func.lower(Entity.title).asc(), MediaItem.id.asc()),
        "score": (
            MediaItem.score.desc().nulls_last(),
            Entity.updated_at.desc(),
            Entity.id.desc(),
        ),
        "progress": (
            MediaItem.progress.desc().nulls_last(),
            Entity.updated_at.desc(),
            Entity.id.desc(),
        ),
    }
    if sort not in orders:
        raise MediaCommandError("Gecersiz media siralamasi")
    offset = _decode_cursor(cursor)
    rows = (await session.execute(stmt.order_by(*orders[sort]).offset(offset).limit(limit))).all()
    next_cursor = _encode_cursor(offset + limit) if offset + len(rows) < total else None
    return MediaPageOut(
        items=[_to_item_out(item, entity) for item, entity in rows],
        total=total,
        next_cursor=next_cursor,
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


async def list_cycles(session: AsyncSession, item_id: uuid.UUID) -> list[MediaCycleOut]:
    rows = list(
        (
            await session.execute(
                select(MediaCycle)
                .where(MediaCycle.media_id == item_id)
                .order_by(MediaCycle.ordinal.desc())
            )
        ).scalars()
    )
    return [MediaCycleOut.model_validate(row) for row in rows]


async def _open_cycle(session: AsyncSession, item_id: uuid.UUID) -> MediaCycle | None:
    return (
        await session.execute(
            select(MediaCycle).where(
                MediaCycle.media_id == item_id,
                MediaCycle.completed_at.is_(None),
                MediaCycle.status.in_(("active", "paused")),
            )
        )
    ).scalar_one_or_none()


async def _start_cycle(
    session: AsyncSession,
    item: MediaItem,
    data: MediaCycleStart,
    *,
    commit: bool,
) -> MediaCycle:
    if await _open_cycle(session, item.id):
        raise MediaConflictError("Medya icin acik bir tur zaten var")
    ordinal = (
        int(
            (
                await session.execute(
                    select(func.coalesce(func.max(MediaCycle.ordinal), 0)).where(
                        MediaCycle.media_id == item.id
                    )
                )
            ).scalar_one()
        )
        + 1
    )
    started_at = data.started_at or datetime.now(UTC)
    entity = await create_entity(
        session,
        type=MediaCycle.ENTITY_TYPE,
        title=f"{item.kind} cycle {ordinal}",
        search_text="",
    )
    cycle = MediaCycle(
        id=entity.id,
        media_id=item.id,
        ordinal=ordinal,
        status="active",
        started_at=started_at,
        notes=data.notes,
    )
    session.add(cycle)
    if ordinal > 1:
        item.progress = 0
        item.finished_at = None
    item.status = "in_progress"
    item.started_at = item.started_at or started_at
    await touch_entity(session, item.id)
    await log_event(
        session,
        verb="media.cycle_started",
        entity_id=item.id,
        entity_type="media_item",
        payload={"cycle_id": str(cycle.id), "ordinal": ordinal, "kind": item.kind},
    )
    if commit:
        await session.commit()
    else:
        await session.flush()
    return cycle


async def start_cycle(
    session: AsyncSession, item_id: uuid.UUID, data: MediaCycleStart
) -> MediaCycleOut | None:
    item = (
        await session.execute(select(MediaItem).where(MediaItem.id == item_id).with_for_update())
    ).scalar_one_or_none()
    if item is None:
        return None
    try:
        cycle = await _start_cycle(session, item, data, commit=True)
        return MediaCycleOut.model_validate(cycle)
    except IntegrityError as exc:
        await session.rollback()
        raise MediaConflictError("Medya icin acik bir tur zaten var") from exc


async def _unit_completed(session: AsyncSession, cycle_id: uuid.UUID, unit_id: uuid.UUID) -> bool:
    action = (
        await session.execute(
            select(MediaConsumption.action)
            .where(
                MediaConsumption.cycle_id == cycle_id,
                MediaConsumption.unit_id == unit_id,
                MediaConsumption.action.in_(("complete_unit", "uncomplete_unit")),
            )
            .order_by(MediaConsumption.created_at.desc(), MediaConsumption.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return action == "complete_unit"


async def _complete_cycle(
    session: AsyncSession, item: MediaItem, cycle: MediaCycle, now: datetime
) -> None:
    if cycle.status != "completed":
        cycle.status = "completed"
        cycle.completed_at = now
        item.status = "completed"
        item.finished_at = now
        await log_event(
            session,
            verb="media.cycle_completed",
            entity_id=item.id,
            entity_type="media_item",
            payload={"cycle_id": str(cycle.id), "ordinal": cycle.ordinal, "kind": item.kind},
        )


async def _synchronize_status(session: AsyncSession, item: MediaItem, status: str) -> None:
    cycle = await _open_cycle(session, item.id)
    if status == "completed" and item.status == "completed" and cycle is None:
        return
    if status == "planned":
        if cycle is not None:
            raise MediaConflictError("Acik tur varken medya planned durumuna alinamaz")
        item.status = status
        item.finished_at = None
        return
    if status in {"in_progress", "paused", "dropped"} and cycle is None:
        cycle = await _start_cycle(session, item, MediaCycleStart(), commit=False)
    if status == "completed":
        if cycle is None:
            cycle = await _start_cycle(session, item, MediaCycleStart(), commit=False)
        await _complete_cycle(session, item, cycle, datetime.now(UTC))
        return
    if status == "in_progress":
        cycle.status = "active"
        cycle.completed_at = None
        item.finished_at = None
    elif status == "paused":
        cycle.status = "paused"
        cycle.completed_at = None
        item.finished_at = None
    elif status == "dropped":
        cycle.status = "dropped"
        cycle.completed_at = datetime.now(UTC)
        item.finished_at = None
    item.status = status


async def _consume_locked(
    session: AsyncSession,
    item: MediaItem,
    data: MediaConsumptionIn,
    *,
    complete_when_total: bool = True,
) -> MediaConsumption:
    item_id = item.id
    unit = None
    if data.unit_id:
        unit = await session.get(MediaUnit, data.unit_id)
        if unit is None or unit.media_id != item_id:
            raise MediaCommandError("Unit bu medya kaydina ait degil")
    if data.action in ("complete_unit", "uncomplete_unit") and unit is None:
        raise MediaCommandError("Bu komut icin unit_id gerekli")
    if (
        data.action == "complete_unit"
        and unit
        and unit.release_at
        and unit.release_at > datetime.now(UTC)
    ):
        raise MediaConflictError("Gelecekte yayinlanacak unit tamamlanamaz")
    cycle = await _open_cycle(session, item_id)
    if cycle is None:
        cycle = await _start_cycle(session, item, MediaCycleStart(), commit=False)
    now = data.occurred_at or datetime.now(UTC)
    current = float(item.progress or 0)
    measure = data.measure or (unit.progress_measure if unit else None)
    measure = measure or item.progress_measure or DEFAULT_MEASURE[item.kind]
    amount = 0.0
    progress_after = current
    if data.action == "quick":
        if item.kind == "movie" and data.amount is None:
            target = float(item.total or 1)
            item.total = target
            amount = max(0.0, target - current)
        else:
            amount = 1.0 if data.amount is None else data.amount
        if amount <= 0:
            raise MediaCommandError("quick amount pozitif olmali")
        progress_after = current + amount
    elif data.action == "set":
        if data.progress_after is None or data.progress_after < 0:
            raise MediaCommandError("set icin negatif olmayan progress_after gerekli")
        progress_after = data.progress_after
        amount = progress_after - current
    elif data.action == "complete_unit":
        already_completed = await _unit_completed(session, cycle.id, unit.id)
        amount = 0.0 if already_completed else float(unit.progress_total or 1)
        progress_after = current + amount
    elif data.action == "uncomplete_unit":
        already_completed = await _unit_completed(session, cycle.id, unit.id)
        amount = -float(unit.progress_total or 1) if already_completed else 0.0
        progress_after = max(0.0, current + amount)
    elif data.action == "finish":
        target = data.progress_after if data.progress_after is not None else _number(item.total)
        target = max(current, 1.0) if target is None else target
        if target < 0:
            raise MediaCommandError("finish progress negatif olamaz")
        item.total = target
        progress_after = target
        amount = max(0.0, progress_after - current)
    item.progress = progress_after
    consumption_entity = await create_entity(
        session,
        type=MediaConsumption.ENTITY_TYPE,
        title=f"{item.kind} {data.action}",
        search_text=data.note or "",
    )
    consumption = MediaConsumption(
        id=consumption_entity.id,
        media_id=item.id,
        cycle_id=cycle.id,
        unit_id=unit.id if unit else None,
        client_uuid=data.client_uuid,
        action=data.action,
        measure=measure,
        amount=amount,
        progress_after=progress_after,
        occurred_at=now,
        duration_min=data.duration_min,
        note=data.note,
        meta={
            **data.meta,
            REQUEST_FINGERPRINT_KEY: _canonical_consumption_request(data),
        },
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(consumption)
    completed = data.action == "finish" or (
        complete_when_total and item.total is not None and progress_after >= float(item.total)
    )
    if completed:
        await _complete_cycle(session, item, cycle, now)
    if data.action in ("set", "uncomplete_unit"):
        await log_event(
            session,
            verb="media.progress_corrected",
            entity_id=item.id,
            entity_type="media_item",
            payload={
                "action": data.action,
                "amount": amount,
                "progress_after": progress_after,
                "kind": item.kind,
            },
        )
    elif amount > 0:
        await log_event(
            session,
            verb="media.consumed",
            entity_id=item.id,
            entity_type="media_item",
            payload={
                "action": data.action,
                "measure": measure,
                "amount": amount,
                "duration_min": data.duration_min,
                "kind": item.kind,
            },
        )
    await touch_entity(session, item.id)
    await session.flush()
    return consumption


def _same_optional_number(stored: Decimal | None, requested: float | None) -> bool:
    if stored is None or requested is None:
        return stored is None and requested is None
    return abs(float(stored) - requested) < 0.001


def _compatible_replay(
    replay: MediaConsumption, item_id: uuid.UUID, data: MediaConsumptionIn
) -> bool:
    if replay.media_id != item_id or replay.action != data.action or replay.unit_id != data.unit_id:
        return False
    fingerprint = (replay.meta or {}).get(REQUEST_FINGERPRINT_KEY)
    if fingerprint is not None:
        return fingerprint == _canonical_consumption_request(data)
    if replay.duration_min != data.duration_min or replay.note != data.note:
        return False
    if "occurred_at" in data.model_fields_set and replay.occurred_at != data.occurred_at:
        return False
    if data.meta:
        return False
    if "measure" in data.model_fields_set and replay.measure != data.measure:
        return False
    for field in ("amount", "progress_after"):
        if field in data.model_fields_set and not _same_optional_number(
            getattr(replay, field), getattr(data, field)
        ):
            return False
    return True


def _replay_or_conflict(
    replay: MediaConsumption, item_id: uuid.UUID, data: MediaConsumptionIn
) -> MediaConsumptionOut:
    if not _compatible_replay(replay, item_id, data):
        raise MediaConflictError("client_uuid farkli bir media veya komut icin kullanilmis")
    return _to_consumption_out(replay)


async def consume(
    session: AsyncSession, item_id: uuid.UUID, data: MediaConsumptionIn
) -> MediaConsumptionOut | None:
    item = (
        await session.execute(select(MediaItem).where(MediaItem.id == item_id).with_for_update())
    ).scalar_one_or_none()
    if item is None:
        return None
    replay = (
        await session.execute(
            select(MediaConsumption).where(MediaConsumption.client_uuid == data.client_uuid)
        )
    ).scalar_one_or_none()
    if replay is not None:
        return _replay_or_conflict(replay, item_id, data)
    try:
        consumption = await _consume_locked(session, item, data)
        await session.commit()
        return _to_consumption_out(consumption)
    except IntegrityError:
        await session.rollback()
        replay = (
            await session.execute(
                select(MediaConsumption).where(MediaConsumption.client_uuid == data.client_uuid)
            )
        ).scalar_one_or_none()
        if replay is not None:
            return _replay_or_conflict(replay, item_id, data)
        raise


async def _reopen_for_release_transition(
    session: AsyncSession,
    item: MediaItem,
    unit: MediaUnit,
) -> bool:
    now = datetime.now(UTC)
    pending = bool((unit.meta or {}).get(RELEASE_PENDING_META_KEY))
    if not pending or unit.release_at is None or unit.release_at > now:
        return False
    # A release is consumed once even when there is no completed cycle to reopen.
    unit.meta = {**(unit.meta or {}), RELEASE_PENDING_META_KEY: False}
    if (
        item.kind not in SERIAL_KINDS
        or not item.monitored
        or item.status != "completed"
    ):
        return False
    latest = (
        await session.execute(
            select(MediaCycle)
            .where(MediaCycle.media_id == item.id)
            .order_by(MediaCycle.ordinal.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if latest is None or latest.status != "completed":
        return False
    if latest.completed_at is None or unit.release_at <= latest.completed_at:
        return False
    latest.last_caught_up_at = latest.completed_at or now
    latest.completed_at = None
    latest.status = "active"
    item.status = "in_progress"
    item.finished_at = None
    await log_event(
        session,
        verb="media.cycle_reopened",
        entity_id=item.id,
        entity_type="media_item",
        payload={
            "cycle_id": str(latest.id),
            "unit_id": str(unit.id),
            "checkpoint": _number(item.progress),
            "kind": item.kind,
        },
    )
    return True


async def upsert_unit_in_transaction(
    session: AsyncSession, item_id: uuid.UUID, data: MediaUnitUpsert
) -> UnitUpsertResult:
    item = (
        await session.execute(
            select(MediaItem).where(MediaItem.id == item_id).with_for_update()
        )
    ).scalar_one_or_none()
    if item is None:
        raise MediaCommandError("Medya bulunamadi")
    existing = None
    if data.provider and data.provider_id:
        existing = (
            await session.execute(
                select(MediaUnit).where(
                    MediaUnit.media_id == item_id,
                    MediaUnit.provider == data.provider,
                    MediaUnit.provider_id == data.provider_id,
                )
            )
        ).scalar_one_or_none()
    if (
        existing is None
        and not (data.provider and data.provider_id)
        and data.number is not None
    ):
        existing = (
            await session.execute(
                select(MediaUnit).where(
                    MediaUnit.media_id == item_id,
                    MediaUnit.unit_type == data.unit_type,
                    MediaUnit.number == data.number,
                    MediaUnit.parent_id == data.parent_id,
                )
            )
        ).scalar_one_or_none()
    if existing is not None:
        previous_release_at = existing.release_at
        entity = await session.get(Entity, existing.id)
        changed = entity is not None and entity.title != data.title
        values = data.model_dump(exclude={"title"}, exclude_unset=True)
        if "meta" in values and RELEASE_PENDING_META_KEY in (existing.meta or {}):
            values["meta"] = {
                **values["meta"],
                RELEASE_PENDING_META_KEY: existing.meta[RELEASE_PENDING_META_KEY],
            }
        for key, value in values.items():
            if key == "cover_path" and value is None and existing.cover_path:
                continue
            changed = changed or getattr(existing, key) != value
            setattr(existing, key, value)
        now = datetime.now(UTC)
        if (
            existing.release_at is not None
            and existing.release_at > now
            and (previous_release_at is None or previous_release_at <= now)
        ):
            existing.meta = {
                **(existing.meta or {}),
                RELEASE_PENDING_META_KEY: True,
            }
            changed = True
        await touch_entity(session, existing.id, title=data.title)
        await session.flush()
        pending_before = bool((existing.meta or {}).get(RELEASE_PENDING_META_KEY))
        reopened = await _reopen_for_release_transition(session, item, existing)
        release_processed = pending_before and not bool(
            (existing.meta or {}).get(RELEASE_PENDING_META_KEY)
        )
        return UnitUpsertResult(
            id=existing.id,
            created=False,
            changed=changed or release_processed,
            cycle_reopened=reopened,
        )
    if data.parent_id:
        parent = await session.get(MediaUnit, data.parent_id)
        if parent is None or parent.media_id != item_id:
            raise MediaCommandError("Parent unit bu medya kaydina ait degil")
    entity = await create_entity(
        session,
        type=MediaUnit.ENTITY_TYPE,
        title=data.title.strip(),
        search_text=json.dumps(data.meta, ensure_ascii=False),
    )
    values = data.model_dump(exclude={"title"})
    if data.release_at is not None and data.release_at > datetime.now(UTC):
        values["meta"] = {
            **values["meta"],
            RELEASE_PENDING_META_KEY: True,
        }
    unit = MediaUnit(id=entity.id, media_id=item_id, **values)
    session.add(unit)
    await session.flush()
    if unit.release_at is not None:
        unit.meta = {**(unit.meta or {}), RELEASE_PENDING_META_KEY: True}
    reopened = await _reopen_for_release_transition(session, item, unit)
    return UnitUpsertResult(
        id=unit.id,
        created=True,
        changed=True,
        cycle_reopened=reopened,
    )


async def upsert_unit(
    session: AsyncSession, item_id: uuid.UUID, data: MediaUnitUpsert
) -> UnitUpsertResult:
    try:
        result = await upsert_unit_in_transaction(session, item_id, data)
        await session.commit()
        return result
    except Exception:
        await session.rollback()
        raise


async def list_collections(session: AsyncSession) -> list[MediaCollectionOut]:
    rows = (
        await session.execute(
            select(MediaCollection, Entity.title)
            .join(Entity, Entity.id == MediaCollection.id)
            .order_by(MediaCollection.position, Entity.title)
        )
    ).all()
    return [_to_collection_out(*row) for row in rows]


async def create_collection(session: AsyncSession, data: MediaCollectionIn) -> MediaCollectionOut:
    entity = await create_entity(
        session,
        type=MediaCollection.ENTITY_TYPE,
        title=data.title.strip(),
        search_text=data.description or "",
    )
    collection = MediaCollection(
        id=entity.id,
        description=data.description,
        color=data.color,
        position=data.position,
    )
    session.add(collection)
    await log_event(
        session,
        verb="media.collection_created",
        entity_id=collection.id,
        entity_type="media_collection",
        payload={"title": entity.title},
    )
    await session.commit()
    return _to_collection_out(collection, entity.title)


async def update_collection(
    session: AsyncSession, collection_id: uuid.UUID, data: MediaCollectionUpdate
) -> MediaCollectionOut | None:
    collection = await session.get(MediaCollection, collection_id)
    entity = await session.get(Entity, collection_id)
    if collection is None or entity is None:
        return None
    changes = data.model_dump(exclude_unset=True)
    title = changes.pop("title", None)
    for key, value in changes.items():
        setattr(collection, key, value)
    await touch_entity(
        session,
        collection_id,
        title=title.strip() if title else None,
        search_text=collection.description or "",
    )
    await log_event(
        session,
        verb="media.collection_updated",
        entity_id=collection_id,
        entity_type="media_collection",
        payload={"title": title or entity.title, "changes": list(changes)},
    )
    await session.commit()
    return _to_collection_out(collection, title or entity.title)


async def delete_collection(session: AsyncSession, collection_id: uuid.UUID) -> bool:
    collection = await session.get(MediaCollection, collection_id)
    entity = await session.get(Entity, collection_id)
    if collection is None or entity is None:
        return False
    await log_event(
        session,
        verb="media.collection_deleted",
        entity_id=collection_id,
        entity_type="media_collection",
        payload={"collection_id": str(collection_id), "title": entity.title},
    )
    await session.flush()
    await delete_entity(session, collection_id)
    await session.commit()
    return True


async def add_collection_item(
    session: AsyncSession, collection_id: uuid.UUID, item_id: uuid.UUID
) -> bool | None:
    collection = await session.get(MediaCollection, collection_id)
    item = await session.get(MediaItem, item_id)
    if collection is None or item is None:
        return None
    exists = (
        await session.execute(
            select(Link.id).where(
                Link.from_id == collection_id,
                Link.to_id == item_id,
                Link.relation == MEDIA_COLLECTION_ITEM_RELATION,
            )
        )
    ).scalar_one_or_none()
    if exists is None:
        await link(session, collection_id, item_id, MEDIA_COLLECTION_ITEM_RELATION)
        await log_event(
            session,
            verb="media.collection_item_added",
            entity_id=item_id,
            entity_type="media_item",
            payload={"collection_id": str(collection_id)},
        )
        await session.commit()
        return True
    return False


async def remove_collection_item(
    session: AsyncSession, collection_id: uuid.UUID, item_id: uuid.UUID
) -> bool | None:
    if await session.get(MediaCollection, collection_id) is None:
        return None
    if await session.get(MediaItem, item_id) is None:
        return None
    exists = (
        await session.execute(
            select(Link.id).where(
                Link.from_id == collection_id,
                Link.to_id == item_id,
                Link.relation == MEDIA_COLLECTION_ITEM_RELATION,
            )
        )
    ).scalar_one_or_none()
    if exists is not None:
        await unlink(session, collection_id, item_id, MEDIA_COLLECTION_ITEM_RELATION)
        await log_event(
            session,
            verb="media.collection_item_removed",
            entity_id=item_id,
            entity_type="media_item",
            payload={"collection_id": str(collection_id)},
        )
        await session.commit()
        return True
    return False


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


async def validate_progress(
    session: AsyncSession, item_id: uuid.UUID, *, rebuild: bool = False
) -> ProgressValidationOut:
    item = await session.get(MediaItem, item_id)
    if item is None:
        raise MediaCommandError("Medya bulunamadi")
    latest_cycle_id = (
        await session.execute(
            select(MediaCycle.id)
            .where(MediaCycle.media_id == item_id)
            .order_by(MediaCycle.ordinal.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    expected = 0.0
    if latest_cycle_id:
        progress_after = (
            await session.execute(
                select(MediaConsumption.progress_after)
                .where(MediaConsumption.cycle_id == latest_cycle_id)
                .order_by(MediaConsumption.created_at.desc(), MediaConsumption.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        expected = float(progress_after or 0)
    actual = float(item.progress or 0)
    valid = abs(actual - expected) < 0.001
    if rebuild and not valid:
        item.progress = expected
        await touch_entity(session, item.id)
        await session.commit()
    return ProgressValidationOut(valid=valid, actual=actual, expected=expected)


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
