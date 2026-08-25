"""Medya cycle/consumption ilerleme kurallari: cycle yonetimi, consumption, unit upsert."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import create_entity, touch_entity
from app.core.events import log_event
from app.core.models import Entity
from app.modules.media.models import MediaConsumption, MediaCycle, MediaItem, MediaUnit
from app.modules.media.schemas import (
    MediaConsumptionIn,
    MediaConsumptionOut,
    MediaCycleOut,
    MediaCycleStart,
    MediaUnitUpsert,
    UnitUpsertResult,
)

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
class MediaConflictError(ValueError):
    pass


class MediaCommandError(ValueError):
    pass


def _number(value: Decimal | int | float | None) -> float | None:
    return float(value) if value is not None else None


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


def _canonical_consumption_request(data: MediaConsumptionIn) -> dict[str, object]:
    return data.model_dump(mode="json", exclude_none=False)


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
