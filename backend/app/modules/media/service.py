"""Medya domain is mantigi ve aggregate ilerleme kurallari."""
from __future__ import annotations

import base64
import json
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
from sqlalchemy import func, or_, select
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
from app.modules.media.models import (
    MEDIA_COLLECTION_ITEM_RELATION,
    MediaCollection,
    MediaConsumption,
    MediaCycle,
    MediaItem,
    MediaUnit,
)
from app.modules.media.schemas import (
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
    ProgressValidationOut,
    UnitUpsertResult,
)
from app.modules.system.models import Setting

TIMEOUT = httpx.Timeout(20.0)
POLL_MAX = 6
SERIAL_KINDS = {"show", "anime", "manga", "podcast", "music"}
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
ANILIST_QUERY = """
query ($q: String, $t: MediaType) {
  Page(page: 1, perPage: 6) {
    media(search: $q, type: $t) {
      id
      title { romaji }
      coverImage { large }
      episodes
      chapters
      startDate { year }
    }
  }
}
"""
TMDB_IMAGE = "https://image.tmdb.org/t/p/w200"


class MediaConflictError(ValueError):
    pass


class MediaCommandError(ValueError):
    pass


def _number(value: Decimal | int | float | None) -> float | None:
    return float(value) if value is not None else None


def _provider_id(item: MediaItem) -> str | None:
    if not item.provider:
        return None
    value = (item.provider_ids or {}).get(item.provider)
    if value is None:
        value = (item.provider_ids or {}).get("provider_id")
    return str(value) if value is not None else None


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
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise MediaCommandError("Gecersiz media cursor") from exc


async def _tmdb_key(session: AsyncSession) -> str | None:
    row = await session.get(Setting, "media.tmdb_key")
    return row.value if row and row.value else None


async def _search_openlibrary(q: str) -> list[MetadataResult]:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(
            "https://openlibrary.org/search.json",
            params={
                "q": q,
                "limit": POLL_MAX,
                "fields": "key,title,author_name,first_publish_year,cover_i",
            },
        )
        response.raise_for_status()
    results = []
    for doc in response.json().get("docs", []):
        cover = doc.get("cover_i")
        results.append(
            MetadataResult(
                title=doc.get("title") or "(basliksiz)",
                subtitle=", ".join(doc.get("author_name", []) or []) or None,
                cover_url=(
                    f"https://covers.openlibrary.org/b/id/{cover}-M.jpg" if cover else None
                ),
                year=doc.get("first_publish_year"),
                metadata={"source": "openlibrary", "ol_key": doc.get("key")},
            )
        )
    return results


async def _search_anilist(q: str, kind: str) -> list[MetadataResult]:
    payload = {
        "query": ANILIST_QUERY,
        "variables": {"q": q, "t": "ANIME" if kind == "anime" else "MANGA"},
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post("https://graphql.anilist.co", json=payload)
        if response.status_code == 404:
            return []
        response.raise_for_status()
    entries = (response.json().get("data") or {}).get("Page", {}).get("media", [])
    return [
        MetadataResult(
            title=(entry.get("title") or {}).get("romaji") or "(basliksiz)",
            subtitle=(
                f"{entry.get('episodes') or entry.get('chapters')} bolum"
                if entry.get("episodes") or entry.get("chapters")
                else None
            ),
            cover_url=(entry.get("coverImage") or {}).get("large"),
            year=(entry.get("startDate") or {}).get("year"),
            metadata={"source": "anilist", "anilist_id": entry.get("id")},
        )
        for entry in entries
    ]


async def _search_tmdb(q: str, key: str, kind: str) -> list[MetadataResult]:
    results = []
    for table, media_kind in (("movie", "movie"), ("tv", "show")):
        if kind == "movie" and media_kind != "movie":
            continue
        if kind in ("show", "anime") and media_kind != "show":
            continue
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(
                f"https://api.themoviedb.org/3/search/{table}",
                params={"api_key": key, "query": q, "language": "tr-TR"},
            )
            response.raise_for_status()
        for row in response.json().get("results", [])[:3]:
            poster = row.get("poster_path")
            results.append(
                MetadataResult(
                    title=row.get("title") or row.get("name") or "(basliksiz)",
                    subtitle=row.get("release_date") or row.get("first_air_date"),
                    cover_url=TMDB_IMAGE + poster if poster else None,
                    metadata={
                        "source": "tmdb",
                        "tmdb_id": row.get("id"),
                        "tmdb_type": media_kind,
                    },
                )
            )
    return results[:POLL_MAX]


async def search_metadata(session: AsyncSession, q: str, kind: str) -> list[MetadataResult]:
    if kind == "book":
        return await _search_openlibrary(q)
    if kind in ("anime", "manga"):
        return await _search_anilist(q, kind)
    if kind in ("movie", "show"):
        key = await _tmdb_key(session)
        if not key:
            raise RuntimeError("TMDB API key yok -- Ayarlardan media.tmdb_key ekle")
        return await _search_tmdb(q, key, kind)
    return []


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
    stmt = stmt.where(
        Entity.archived_at.is_not(None) if trashed else Entity.archived_at.is_(None)
    )
    if kind:
        stmt = stmt.where(MediaItem.kind == kind)
    if status:
        stmt = stmt.where(MediaItem.status == status)
    if q:
        for token in q.split():
            pattern = f"%{token}%"
            stmt = stmt.where(
                or_(Entity.title.ilike(pattern), Entity.search_text.ilike(pattern))
            )
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
        "score": (MediaItem.score.desc().nulls_last(), Entity.updated_at.desc()),
        "progress": (MediaItem.progress.desc().nulls_last(), Entity.updated_at.desc()),
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


async def _provider_duplicate(session: AsyncSession, data: MediaItemIn) -> bool:
    if data.source != "provider" or not data.provider or not data.provider_id:
        return False
    rows = list(
        (
            await session.execute(select(MediaItem).where(MediaItem.provider == data.provider))
        ).scalars()
    )
    return any(_provider_id(row) == data.provider_id for row in rows)


async def create_item(session: AsyncSession, data: MediaItemIn) -> MediaItemOut:
    if await _provider_duplicate(session, data):
        raise MediaConflictError("Bu provider kaydi kutuphanede zaten var")
    provider_ids = dict(data.provider_ids)
    if data.provider and data.provider_id:
        provider_ids[data.provider] = data.provider_id
    title = data.title.strip()
    entity = await create_entity(
        session,
        type=MediaItem.ENTITY_TYPE,
        title=title,
        search_text=_search_text(data),
    )
    item = MediaItem(
        id=entity.id,
        kind=data.kind,
        status=data.status,
        progress=data.progress,
        total=data.total,
        score=data.score,
        notes=data.notes,
        started_at=data.started_at,
        finished_at=data.finished_at,
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
        provider_ids=provider_ids,
        cover_url=data.cover_url,
        cover_path=data.cover_path,
        backdrop_url=data.backdrop_url,
        backdrop_path=data.backdrop_path,
        last_synced_at=data.last_synced_at,
    )
    session.add(item)
    await log_event(
        session,
        verb="media.item_added",
        entity_id=item.id,
        entity_type="media_item",
        payload={"kind": item.kind, "status": item.status, "title": title},
    )
    await session.commit()
    return _to_item_out(item, entity)


async def update_item(
    session: AsyncSession, item_id: uuid.UUID, data: MediaItemUpdate
) -> MediaItemOut | None:
    item = await session.get(MediaItem, item_id)
    entity = await session.get(Entity, item_id)
    if item is None or entity is None:
        return None
    changes = data.model_dump(exclude_unset=True)
    title = changes.pop("title", None)
    for key, value in changes.items():
        setattr(item, key, value)
    if item.status == "completed" and item.finished_at is None:
        item.finished_at = datetime.now(UTC)
    if item.status != "completed" and "status" in changes:
        item.finished_at = None
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
        payload={"title": title or entity.title, "kind": item.kind, "changes": list(changes)},
    )
    await session.commit()
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
            (
                await session.execute(select(model.id).where(model.media_id == item_id))
            ).scalars()
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
    ordinal = int(
        (
            await session.execute(
                select(func.coalesce(func.max(MediaCycle.ordinal), 0)).where(
                    MediaCycle.media_id == item.id
                )
            )
        ).scalar_one()
    ) + 1
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
    item = await session.get(MediaItem, item_id)
    if item is None:
        return None
    cycle = await _start_cycle(session, item, data, commit=True)
    return MediaCycleOut.model_validate(cycle)


async def _unit_completed(
    session: AsyncSession, item_id: uuid.UUID, unit_id: uuid.UUID
) -> bool:
    action = (
        await session.execute(
            select(MediaConsumption.action)
            .where(
                MediaConsumption.media_id == item_id,
                MediaConsumption.unit_id == unit_id,
                MediaConsumption.action.in_(("complete_unit", "uncomplete_unit")),
            )
            .order_by(MediaConsumption.occurred_at.desc(), MediaConsumption.created_at.desc())
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


async def consume(
    session: AsyncSession, item_id: uuid.UUID, data: MediaConsumptionIn
) -> MediaConsumptionOut | None:
    replay = (
        await session.execute(
            select(MediaConsumption).where(MediaConsumption.client_uuid == data.client_uuid)
        )
    ).scalar_one_or_none()
    if replay is not None:
        return _to_consumption_out(replay)
    item = await session.get(MediaItem, item_id)
    if item is None:
        return None
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
        already_completed = await _unit_completed(session, item_id, unit.id)
        amount = 0.0 if already_completed else float(unit.progress_total or 1)
        progress_after = current + amount
    elif data.action == "uncomplete_unit":
        already_completed = await _unit_completed(session, item_id, unit.id)
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
        meta={},
    )
    session.add(consumption)
    completed = data.action == "finish" or (
        item.total is not None and progress_after >= float(item.total)
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
    await session.commit()
    return _to_consumption_out(consumption)


async def upsert_unit(
    session: AsyncSession, item_id: uuid.UUID, data: MediaUnitUpsert
) -> UnitUpsertResult:
    item = await session.get(MediaItem, item_id)
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
    if existing is None and data.number is not None:
        existing = (
            await session.execute(
                select(MediaUnit).where(
                    MediaUnit.media_id == item_id,
                    MediaUnit.unit_type == data.unit_type,
                    MediaUnit.number == data.number,
                )
            )
        ).scalar_one_or_none()
    if existing is not None:
        values = data.model_dump(exclude={"title"}, exclude_unset=True)
        for key, value in values.items():
            setattr(existing, key, value)
        await touch_entity(session, existing.id, title=data.title)
        await session.commit()
        return UnitUpsertResult(id=existing.id, created=False)
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
    unit = MediaUnit(id=entity.id, media_id=item_id, **data.model_dump(exclude={"title"}))
    session.add(unit)
    await session.flush()
    reopened = False
    now = datetime.now(UTC)
    if (
        item.kind in SERIAL_KINDS
        and item.monitored
        and item.status == "completed"
        and unit.release_at is not None
        and unit.release_at <= now
    ):
        latest = (
            await session.execute(
                select(MediaCycle)
                .where(MediaCycle.media_id == item_id)
                .order_by(MediaCycle.ordinal.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if latest and latest.status == "completed":
            latest.last_caught_up_at = latest.completed_at or now
            latest.completed_at = None
            latest.status = "active"
            item.status = "in_progress"
            item.finished_at = None
            reopened = True
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
    await session.commit()
    return UnitUpsertResult(id=unit.id, created=True, cycle_reopened=reopened)


async def list_collections(session: AsyncSession) -> list[MediaCollectionOut]:
    rows = (
        await session.execute(
            select(MediaCollection, Entity.title)
            .join(Entity, Entity.id == MediaCollection.id)
            .order_by(MediaCollection.position, Entity.title)
        )
    ).all()
    return [_to_collection_out(*row) for row in rows]


async def create_collection(
    session: AsyncSession, data: MediaCollectionIn
) -> MediaCollectionOut:
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
    rows = (
        await session.execute(
            select(MediaUnit, Entity.title)
            .join(Entity, Entity.id == MediaUnit.id)
            .where(
                MediaUnit.release_at >= now,
                MediaUnit.release_at <= now + timedelta(days=days),
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
    recent = list(
        (
            await session.execute(
                select(MediaConsumption)
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
                .order_by(
                    MediaConsumption.occurred_at.desc(), MediaConsumption.created_at.desc()
                )
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
