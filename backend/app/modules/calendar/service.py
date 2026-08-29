from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.entity import archive_entity, create_entity, touch_entity
from app.core.events import log_event
from app.core.models import Entity
from app.core.time import local_datetime, local_today
from app.integrations.gcal import list_events, parse_google_time, upsert_event
from app.integrations.google_auth import access_token
from app.integrations.models import OAuthToken
from app.modules import DeadlineRow
from app.modules.calendar.models import ExternalEvent
from app.modules.todo.models import PlanSlot


async def events(session: AsyncSession, from_at: datetime, to_at: datetime) -> list[dict]:
    external_rows = (
        await session.execute(
            select(ExternalEvent, Entity.title)
            .join(Entity, Entity.id == ExternalEvent.id)
            .where(
                Entity.archived_at.is_(None),
                ExternalEvent.starts_at < to_at,
                ExternalEvent.ends_at > from_at,
            )
            .order_by(ExternalEvent.starts_at)
        )
    ).all()
    slot_rows = (
        await session.execute(
            select(PlanSlot, Entity.title, Entity.type)
            .join(Entity, Entity.id == PlanSlot.entity_id)
            .where(PlanSlot.day >= local_today(from_at), PlanSlot.day <= local_today(to_at))
            .order_by(PlanSlot.day, PlanSlot.start_min.nulls_last(), PlanSlot.position)
        )
    ).all()
    result = [
        {
            "id": str(item.id),
            "source": "google",
            "title": title,
            "starts_at": item.starts_at,
            "ends_at": item.ends_at,
            "all_day": item.all_day,
            "location": item.location,
            "url": item.url,
            "read_only": True,
        }
        for item, title in external_rows
    ]
    for slot, title, entity_type in slot_rows:
        minute = slot.start_min or 0
        starts_at = local_datetime(slot.day, minute)
        result.append(
            {
                "id": str(slot.id),
                "source": "plan",
                "title": title,
                "entity_id": str(slot.entity_id),
                "entity_type": entity_type,
                "starts_at": starts_at,
                "ends_at": starts_at + timedelta(minutes=slot.duration_min or 30),
                "all_day": slot.start_min is None,
                "note": slot.note,
                "google_event_id": slot.google_event_id,
                "read_only": False,
            }
        )
    return sorted(result, key=lambda item: item["starts_at"])


async def sync_google(session: AsyncSession) -> int:
    token_row = await session.get(OAuthToken, "google")
    if token_row is None:
        raise RuntimeError("Google bağlı değil")
    token = await access_token(session)
    try:
        raw_events, next_token = await list_events(token, sync_token=token_row.sync_token)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code != 410 or not token_row.sync_token:
            raise
        token_row.sync_token = None
        raw_events, next_token = await list_events(token)

    now = datetime.now(UTC)
    changed = 0
    for raw in raw_events:
        external_id = raw.get("id")
        if not external_id:
            continue
        existing = (
            await session.execute(
                select(ExternalEvent).where(
                    ExternalEvent.provider == "google",
                    ExternalEvent.external_id == external_id,
                )
            )
        ).scalar_one_or_none()
        if raw.get("status") == "cancelled":
            if existing is not None:
                await archive_entity(session, existing.id)
                changed += 1
            continue
        if not raw.get("start"):
            continue
        starts_at, all_day = parse_google_time(raw["start"])
        ends_at = parse_google_time(raw["end"])[0] if raw.get("end") else None
        title = raw.get("summary") or "Başlıksız etkinlik"
        if existing is None:
            entity = await create_entity(
                session, type="external_event", title=title, search_text=raw.get("location", "")
            )
            existing = ExternalEvent(id=entity.id, provider="google", external_id=external_id)
            session.add(existing)
        else:
            await touch_entity(
                session, existing.id, title=title, search_text=raw.get("location", "")
            )
            entity = await session.get(Entity, existing.id)
            if entity:
                entity.archived_at = None
        existing.calendar_id = raw.get("organizer", {}).get("email")
        existing.starts_at = starts_at
        existing.ends_at = ends_at
        existing.all_day = all_day
        existing.location = raw.get("location")
        existing.url = raw.get("htmlLink")
        existing.synced_at = now
        changed += 1
    token_row.sync_token = next_token or token_row.sync_token
    await log_event(
        session,
        verb="calendar.synced",
        entity_type="external_event",
        payload={"count": changed, "incremental": bool(token_row.sync_token)},
    )
    await session.commit()
    return changed


async def push_slot(session: AsyncSession, slot_id: uuid.UUID) -> dict | None:
    row = (
        await session.execute(
            select(PlanSlot, Entity.title)
            .join(Entity, Entity.id == PlanSlot.entity_id)
            .where(PlanSlot.id == slot_id)
        )
    ).first()
    if row is None:
        return None
    slot, title = row
    token = await access_token(session)
    minute = slot.start_min or 9 * 60
    starts_at = local_datetime(slot.day, minute)
    payload = {
        "summary": title,
        "description": slot.note or "forkOS plan slot",
        # Timezone backend config'inden (Faz 14) -- sabit string yok.
        "start": {"dateTime": starts_at.isoformat(), "timeZone": settings.timezone},
        "end": {
            "dateTime": (starts_at + timedelta(minutes=slot.duration_min or 30)).isoformat(),
            "timeZone": settings.timezone,
        },
    }
    result = await upsert_event(token, payload, slot.google_event_id)
    slot.google_event_id = result["id"]
    await log_event(
        session,
        verb="calendar.plan_pushed",
        entity_id=slot.entity_id,
        payload={"slot_id": str(slot.id), "google_event_id": slot.google_event_id},
    )
    await session.commit()
    return {
        "slot_id": slot.id,
        "google_event_id": slot.google_event_id,
        "url": result.get("htmlLink"),
    }


async def deadline_provider(session: AsyncSession) -> list[DeadlineRow]:
    """Bugun + 3 gun icindeki takvim olaylari (kural 16)."""
    from datetime import timedelta

    from app.core.deadlines import rows_with_titles
    from app.modules.calendar.models import ExternalEvent

    now = datetime.now(UTC)
    events = (await session.execute(
        select(ExternalEvent).where(
            ExternalEvent.starts_at >= now,
            ExternalEvent.starts_at <= now + timedelta(days=3),
        )
    )).scalars()
    ids = [e.id for e in events]
    due = {e.id: e.starts_at for e in events}
    return await rows_with_titles(
        session, type_="external_event", module="calendar",
        ids=ids, due_at=due, priority={e: 1 for e in ids},
    )
