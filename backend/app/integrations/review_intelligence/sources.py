"""H5 sınırlı kanonik kaynak okumaları (§111).

Bu modül yalnızca OKUR ve sınırlar: muhakeme yok, yazma yok. Her okuma
deterministik sıralıdır ve tavanları `+1 nöbetçi` ile dürüstçe ölçer (§139).

Kaynak politikası:

  - **Anlamlı hareket** `contributions.COUNTED_VERBS`'tir: worker gürültüsü
    (feed çekimi, kaynak senkronu, sağlık kayıtları) kullanıcı emeği SAYILMAZ.
  - **Proje hareketi** kanonik Event geçmişinden hesaplanır:
    `Project.last_activity_at` yalnızca GitHub senkronunda yazıldığı için
    genel proje hareketini temsil ETMEZ; üçüncü bir zaman damgası uydurulmaz.
  - **Son tarihler** `core.deadlines.collect_deadlines` ile toplanır: ikinci bir
    son tarih kaydı KURULMAZ.
  - **Günlük notlar** `10 Daily/YYYY-MM-DD.md` yolundan, H0 güvenlik
    primitifleriyle okunur; eksik not hata değildir.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import registry as registry_svc
from app.core.contributions import COUNTED_VERBS
from app.core.deadlines import collect_deadlines
from app.core.models import Entity, Event, Link, Notification
from app.core.time import local_day_bounds, local_today, local_zone
from app.integrations.review_intelligence.models import (
    MAX_H5_DAILY_NOTE_CHARS,
    MAX_H5_DAILY_NOTES,
    MAX_H5_EVENTS_SCAN,
    MAX_H5_PERIOD_DAYS,
    ReviewIntelligenceError,
)
from app.modules.opportunity.models import Opportunity
from app.modules.project.models import Milestone, Project
from app.modules.rss.models import Feed, FeedItem
from app.modules.todo.models import PlanSlot, Todo

#: Süreklilik çapası aranırken geriye bakılan sınır (gün). Çapa daha eski
#: olabilir ama TARAMA sınırsız olamaz (§23).
CONTINUITY_ANCHOR_LOOKBACK_DAYS = 120

#: Günlük not kökü (constants.DAILY_ROOT ile aynı ağaç).
DAILY_ROOT = "10 Daily"


# ---------------------------------------------------------------------------
# Zaman yardımcıları
# ---------------------------------------------------------------------------


def parse_aware(value: str | None, label: str) -> datetime | None:
    """Saat dilimi ZORUNLU ISO-8601 (§22). Naif damga reddedilir."""
    if value is None or not str(value).strip():
        return None
    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text)
    except (ValueError, TypeError) as exc:
        raise ReviewIntelligenceError(
            "INVALID_TIME_RANGE", f"'{label}' is not a valid ISO-8601 timestamp"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ReviewIntelligenceError(
            "INVALID_TIME_RANGE",
            f"'{label}' must include a timezone offset (e.g. +03:00 or Z)",
        )
    return parsed


def parse_reference_date(value: str | None) -> date | None:
    if value is None or not str(value).strip():
        return None
    try:
        return date.fromisoformat(str(value).strip())
    except (ValueError, TypeError) as exc:
        raise ReviewIntelligenceError(
            "INVALID_REFERENCE_DATE", "'reference_date' must be YYYY-MM-DD"
        ) from exc


@dataclass(frozen=True)
class ResolvedPeriod:
    """Çözülmüş dönem + dürüstlük bayrakları (§47).

    `start_day`/`end_day` YEREL takvim günleridir. UTC damgasının `.date()`'i
    kullanılamaz: `Europe/Istanbul` (+03) için gün başlangıcı bir önceki UTC
    gününe düşer ve günlük not yolları bir gün kayardı.
    """

    start: datetime
    end: datetime
    start_day: date
    end_day: date
    days: int
    partial: bool
    comparable: bool
    reference_date: date | None = None


def day_bounds(day: date) -> tuple[datetime, datetime]:
    start, end = local_day_bounds(day)
    return start, end


def resolve_period(
    *,
    mode: str,
    since: datetime | None,
    until: datetime | None,
    reference_date: date | None,
    now: datetime | None = None,
) -> ResolvedPeriod:
    """Moda göre dönemi belirler; özel dönemlerde 31 gün tavanı uygular (§23)."""
    moment = now or datetime.now(UTC)

    if mode == "daily_close":
        day = reference_date or local_today()
        start, end = day_bounds(day)
        partial = end > moment
        return ResolvedPeriod(
            start, end, day, day + timedelta(days=1), 1, partial, not partial, day
        )

    if mode == "weekly_review":
        anchor_day = reference_date or local_today()
        monday = anchor_day - timedelta(days=anchor_day.weekday())
        start, _ = day_bounds(monday)
        _, end = day_bounds(monday + timedelta(days=6))
        partial = end > moment
        return ResolvedPeriod(
            start, end, monday, monday + timedelta(days=7), 7, partial, not partial, anchor_day
        )

    if mode == "period_delta":
        if since is None:
            raise ReviewIntelligenceError(
                "INVALID_ARGUMENT", "mode 'period_delta' requires 'since'"
            )
        start = since
        end = until or moment
        if end <= start:
            raise ReviewIntelligenceError("INVALID_TIME_RANGE", "'since' must be before 'until'")
        days = (end - start).days
        if days > MAX_H5_PERIOD_DAYS:
            raise ReviewIntelligenceError(
                "PERIOD_TOO_LARGE", f"period must be at most {MAX_H5_PERIOD_DAYS} days"
            )
        partial = until is None
        return ResolvedPeriod(
            start,
            end,
            start.astimezone(local_zone()).date(),
            end.astimezone(local_zone()).date(),
            max(days, 1),
            partial,
            not partial,
            reference_date,
        )

    if mode == "consolidation_review":
        if since is not None:
            start = since
            end = until or moment
            days = (end - start).days
            if days > MAX_H5_PERIOD_DAYS:
                raise ReviewIntelligenceError(
                    "PERIOD_TOO_LARGE", f"period must be at most {MAX_H5_PERIOD_DAYS} days"
                )
            partial = until is None
            return ResolvedPeriod(
                start,
                end,
                start.astimezone(local_zone()).date(),
                end.astimezone(local_zone()).date(),
                max(days, 1),
                partial,
                not partial,
                reference_date,
            )
        anchor_day = reference_date or local_today()
        monday = anchor_day - timedelta(days=anchor_day.weekday())
        start, _ = day_bounds(monday)
        return ResolvedPeriod(
            start,
            moment,
            monday,
            moment.astimezone(local_zone()).date(),
            max((moment - start).days, 1),
            True,
            False,
            reference_date,
        )

    # continuity: çapa ayrıca çözülür; burada yalnızca emniyet penceresi.
    end = until or moment
    start = since or (end - timedelta(days=CONTINUITY_ANCHOR_LOOKBACK_DAYS))
    if end <= start:
        raise ReviewIntelligenceError("INVALID_TIME_RANGE", "'since' must be before 'until'")
    days = (end - start).days
    if days > CONTINUITY_ANCHOR_LOOKBACK_DAYS:
        start = end - timedelta(days=CONTINUITY_ANCHOR_LOOKBACK_DAYS)
        days = CONTINUITY_ANCHOR_LOOKBACK_DAYS
    partial = since is None or until is None
    return ResolvedPeriod(
        start,
        end,
        start.astimezone(local_zone()).date(),
        end.astimezone(local_zone()).date(),
        max(days, 1),
        partial,
        False,
        reference_date,
    )


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _bounded(text: str | None, limit: int) -> tuple[str, bool]:
    value = (text or "").strip()
    if len(value) <= limit:
        return value, False
    return value[:limit], True


# ---------------------------------------------------------------------------
# Event / anlamlı hareket
# ---------------------------------------------------------------------------


async def meaningful_events(
    session: AsyncSession,
    *,
    start: datetime,
    end: datetime,
    limit: int = MAX_H5_EVENTS_SCAN,
) -> tuple[list[dict[str, Any]], bool]:
    """Sayılan (insan) fiilleri döner. `+1 nöbetçi` ile kesme dürüstçe ölçülür."""
    stmt = (
        select(Event, Entity.title, Entity.type)
        .outerjoin(Entity, Entity.id == Event.entity_id)
        .where(
            Event.verb.in_(COUNTED_VERBS),
            Event.occurred_at >= start,
            Event.occurred_at < end,
        )
        .order_by(Event.occurred_at.desc(), Event.id.desc())
        .limit(limit + 1)
    )
    rows = list((await session.execute(stmt)).all())
    truncated = len(rows) > limit
    events = [
        {
            "id": event.id,
            "verb": event.verb,
            "occurred_at": event.occurred_at,
            "entity_id": str(event.entity_id) if event.entity_id else None,
            "entity_type": entity_type or event.entity_type,
            "title": title or "",
            "payload": event.payload or {},
        }
        for event, title, entity_type in rows[:limit]
    ]
    return events, truncated


async def last_meaningful_event(
    session: AsyncSession, *, before: datetime | None = None
) -> dict[str, Any] | None:
    """Son ANLAMLI insan hareketi (§24) — keyfî 'en son Event' DEĞİL."""
    stmt = select(Event, Entity.title, Entity.type).outerjoin(Entity, Entity.id == Event.entity_id)
    stmt = stmt.where(Event.verb.in_(COUNTED_VERBS))
    if before is not None:
        stmt = stmt.where(Event.occurred_at < before)
    stmt = stmt.order_by(Event.occurred_at.desc(), Event.id.desc()).limit(1)
    row = (await session.execute(stmt)).first()
    if row is None:
        return None
    event, title, entity_type = row
    return {
        "id": event.id,
        "verb": event.verb,
        "occurred_at": event.occurred_at,
        "entity_id": str(event.entity_id) if event.entity_id else None,
        "entity_type": entity_type or event.entity_type,
        "title": title or "",
        "payload": event.payload or {},
    }


async def last_meaningful_event_for_entities(
    session: AsyncSession, *, entity_ids: list[uuid.UUID], before: datetime | None = None
) -> dict[str, Any] | None:
    """Belirli entity'ler (ve bağlı görevleri) için son anlamlı hareket (§26)."""
    if not entity_ids:
        return None
    linked_todos = select(Link.from_id).where(
        Link.to_id.in_(entity_ids), Link.relation == "belongs_to"
    )
    stmt = (
        select(Event, Entity.title, Entity.type)
        .outerjoin(Entity, Entity.id == Event.entity_id)
        .where(
            Event.verb.in_(COUNTED_VERBS),
            or_(Event.entity_id.in_(entity_ids), Event.entity_id.in_(linked_todos)),
        )
        .order_by(Event.occurred_at.desc(), Event.id.desc())
        .limit(1)
    )
    if before is not None:
        stmt = stmt.where(Event.occurred_at < before)
    row = (await session.execute(stmt)).first()
    if row is None:
        return None
    event, title, entity_type = row
    return {
        "id": event.id,
        "verb": event.verb,
        "occurred_at": event.occurred_at,
        "entity_id": str(event.entity_id) if event.entity_id else None,
        "entity_type": entity_type or event.entity_type,
        "title": title or "",
        "payload": event.payload or {},
    }


# ---------------------------------------------------------------------------
# Todo / plan / son tarih
# ---------------------------------------------------------------------------


async def scoped_events(
    session: AsyncSession,
    *,
    entity_ids: list[uuid.UUID],
    start: datetime,
    end: datetime,
    limit: int,
    verbs: tuple[str, ...] | None = None,
) -> tuple[list[dict[str, Any]], bool]:
    """Belirli entity'lere (ve `belongs_to` bağlı görevlerine) kapsanmış olaylar (§50).

    Yeni bir grafik gezinmesi KURULMAZ: yalnızca kanonik `link` tablosunun
    `belongs_to` kenarı kullanılır.
    """
    if not entity_ids:
        return [], False
    linked = select(Link.from_id).where(Link.to_id.in_(entity_ids), Link.relation == "belongs_to")
    stmt = (
        select(Event, Entity.title, Entity.type)
        .outerjoin(Entity, Entity.id == Event.entity_id)
        .where(
            Event.occurred_at >= start,
            Event.occurred_at < end,
            or_(Event.entity_id.in_(entity_ids), Event.entity_id.in_(linked)),
        )
        .order_by(Event.occurred_at.desc(), Event.id.desc())
        .limit(limit + 1)
    )
    if verbs:
        stmt = stmt.where(Event.verb.in_(verbs))
    rows = list((await session.execute(stmt)).all())
    truncated = len(rows) > limit
    events = [
        {
            "id": event.id,
            "verb": event.verb,
            "occurred_at": event.occurred_at,
            "entity_id": str(event.entity_id) if event.entity_id else None,
            "entity_type": entity_type or event.entity_type,
            "title": title or "",
            "payload": event.payload or {},
        }
        for event, title, entity_type in rows[:limit]
    ]
    return events, truncated


async def todo_statuses(
    session: AsyncSession, *, todo_ids: list[uuid.UUID]
) -> dict[str, dict[str, Any]]:
    """Öncelik makbuzlarını DOĞRULAMAK için gerçek Todo durumları (§45)."""
    if not todo_ids:
        return {}
    rows = (
        await session.execute(
            select(Todo.id, Entity.title, Todo.status, Todo.due_at)
            .join(Entity, Entity.id == Todo.id)
            .where(Todo.id.in_(todo_ids))
        )
    ).all()
    return {
        str(todo_id): {
            "id": str(todo_id),
            "title": title or "",
            "status": status,
            "due_at": _iso(due_at),
        }
        for todo_id, title, status, due_at in rows
    }


async def open_todos(session: AsyncSession, *, limit: int) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            select(Todo.id, Entity.title, Todo.status, Todo.priority, Todo.due_at)
            .join(Entity, Entity.id == Todo.id)
            .where(Todo.status.in_(("open", "doing")), Entity.archived_at.is_(None))
            .order_by(Todo.priority.desc(), Todo.due_at.asc().nulls_last(), Todo.id.asc())
            .limit(limit)
        )
    ).all()
    return [
        {
            "id": str(todo_id),
            "title": title or "",
            "status": status,
            "priority": priority,
            "due_at": _iso(due_at),
        }
        for todo_id, title, status, priority, due_at in rows
    ]


async def newly_overdue_todos(
    session: AsyncSession, *, start: datetime, end: datetime, limit: int
) -> list[dict[str, Any]]:
    """Çapa ile şimdi arasında SON TARİHİ GEÇEN ve hâlâ açık görevler (§32)."""
    rows = (
        await session.execute(
            select(Todo.id, Entity.title, Todo.due_at, Todo.status)
            .join(Entity, Entity.id == Todo.id)
            .where(
                Todo.status.in_(("open", "doing")),
                Todo.due_at.is_not(None),
                Todo.due_at >= start,
                Todo.due_at < end,
            )
            .order_by(Todo.due_at.asc(), Todo.id.asc())
            .limit(limit)
        )
    ).all()
    return [
        {
            "id": str(todo_id),
            "title": title or "",
            "due_at": _iso(due_at),
            "status": status,
        }
        for todo_id, title, due_at, status in rows
    ]


async def passed_plan_open_tasks(
    session: AsyncSession, *, now: datetime, limit: int
) -> list[dict[str, Any]]:
    """Planlanan zamanı GEÇMİŞ ama görevi hâlâ açık olan planlar (§36)."""
    today = now.astimezone(local_zone()).date()
    rows = (
        await session.execute(
            select(PlanSlot.id, PlanSlot.entity_id, PlanSlot.day, PlanSlot.start_min, Entity.title)
            .join(Todo, Todo.id == PlanSlot.entity_id)
            .join(Entity, Entity.id == Todo.id)
            .where(
                Todo.status.in_(("open", "doing")),
                or_(
                    PlanSlot.day < today,
                    (PlanSlot.day == today) & (PlanSlot.start_min.is_not(None)),
                ),
            )
            .order_by(PlanSlot.day.asc(), PlanSlot.start_min.asc().nulls_last(), PlanSlot.id.asc())
            .limit(limit)
        )
    ).all()

    results: list[dict[str, Any]] = []
    for slot_id, entity_id, day, start_min, title in rows:
        if day == today and start_min is not None:
            slot_start = datetime.combine(
                day, time(hour=min(start_min // 60, 23)), tzinfo=local_zone()
            )
            if slot_start >= now:
                continue
        results.append(
            {
                "plan_slot_id": str(slot_id),
                "todo_id": str(entity_id),
                "title": title or "",
                "day": day.isoformat(),
                "start_min": start_min,
            }
        )
    return results


async def upcoming_deadlines(
    session: AsyncSession, *, now: datetime, days: int, limit: int
) -> tuple[list[dict[str, Any]], bool]:
    """Kanonik son tarih toplayıcısını kullanır (§31) — ikinci kayıt YOK."""
    rows = await collect_deadlines(session, limit=limit + 1)
    results: list[dict[str, Any]] = []
    horizon = now + timedelta(days=days)
    for row in rows:
        due = row.get("due_at")
        if due is None:
            continue
        if hasattr(due, "tzinfo") and due.tzinfo is None:
            due = due.replace(tzinfo=UTC)
        if due < now or due > horizon:
            continue
        remaining = (due - now).total_seconds()
        results.append(
            {
                "entity_id": str(row.get("entity_id")) if row.get("entity_id") else None,
                "type": row.get("type"),
                "title": row.get("title") or "",
                "due_at": _iso(due),
                "module": row.get("module"),
                "sub_kind": row.get("sub_kind"),
                "priority": row.get("priority"),
                "remaining_days": int(remaining // 86400),
                "remaining_seconds": int(remaining),
            }
        )
    results.sort(key=lambda item: (item["due_at"] or "", item["entity_id"] or ""))
    return results[:limit], len(rows) > limit


# ---------------------------------------------------------------------------
# RSS / bildirim / fırsat
# ---------------------------------------------------------------------------


async def rss_accumulation(
    session: AsyncSession, *, anchor: datetime, now: datetime, top_sources: int = 5
) -> dict[str, Any]:
    """Okunmamış birikimi (§33) — başlık dökümü DEĞİL, sayı + sınırlı kırılım."""
    new_unread = int(
        (
            await session.execute(
                select(func.count())
                .select_from(FeedItem)
                .where(
                    FeedItem.fetched_at >= anchor,
                    FeedItem.fetched_at < now,
                    FeedItem.read_at.is_(None),
                )
            )
        ).scalar_one()
    )
    total_unread = int(
        (
            await session.execute(
                select(func.count()).select_from(FeedItem).where(FeedItem.read_at.is_(None))
            )
        ).scalar_one()
    )
    breakdown_rows = (
        await session.execute(
            select(Entity.title, func.count())
            .select_from(FeedItem)
            .join(Feed, Feed.id == FeedItem.feed_id)
            .join(Entity, Entity.id == Feed.id)
            .where(
                FeedItem.fetched_at >= anchor, FeedItem.fetched_at < now, FeedItem.read_at.is_(None)
            )
            .group_by(Entity.title)
            .order_by(func.count().desc(), Entity.title.asc())
            .limit(top_sources)
        )
    ).all()
    return {
        "new_unread_since_anchor": new_unread,
        "current_unread_total": total_unread,
        "top_sources": [
            {"source": title or "", "count": int(count)} for title, count in breakdown_rows
        ],
    }


async def important_notifications(
    session: AsyncSession, *, start: datetime, end: datetime, limit: int
) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            select(Notification.id, Notification.title, Notification.body, Notification.created_at)
            .where(Notification.created_at >= start, Notification.created_at < end)
            .order_by(
                Notification.importance.desc(),
                Notification.created_at.desc(),
                Notification.id.desc(),
            )
            .limit(limit)
        )
    ).all()
    return [
        {
            "id": int(notification_id),
            "title": title or "",
            "body": (body or "")[:200],
            "created_at": _iso(created_at),
        }
        for notification_id, title, body, created_at in rows
    ]


async def opportunity_changes(
    session: AsyncSession, *, start: datetime, end: datetime, limit: int
) -> list[dict[str, Any]]:
    """Dönemde KEŞFEDİLEN fırsatlar (§34) — kazıma YOK, mevcut durum okunur."""
    rows = (
        await session.execute(
            select(
                Opportunity.id,
                Entity.title,
                Opportunity.kind,
                Opportunity.status,
                Opportunity.organization,
                Opportunity.deadline_at,
                Opportunity.found_at,
            )
            .join(Entity, Entity.id == Opportunity.id)
            .where(
                Opportunity.found_at >= start,
                Opportunity.found_at < end,
                Opportunity.trashed_at.is_(None),
            )
            .order_by(Opportunity.found_at.desc(), Opportunity.id.asc())
            .limit(limit)
        )
    ).all()
    return [
        {
            "id": str(opportunity_id),
            "title": title or "",
            "kind": kind,
            "status": status,
            "organization": organization,
            "deadline_at": _iso(deadline_at),
            "found_at": _iso(found_at),
        }
        for opportunity_id, title, kind, status, organization, deadline_at, found_at in rows
    ]


# ---------------------------------------------------------------------------
# Projeler
# ---------------------------------------------------------------------------


async def active_projects(session: AsyncSession, *, limit: int) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            select(
                Project.id,
                Entity.title,
                Project.status,
                Project.next_action,
                Project.stack,
                Project.github_repo,
                Entity.updated_at,
            )
            .join(Entity, Entity.id == Project.id)
            .where(Project.status != "completed", Entity.archived_at.is_(None))
            .order_by(Project.position.asc(), Entity.title.asc())
            .limit(limit)
        )
    ).all()
    return [
        {
            "id": str(project_id),
            "title": title or "",
            "status": status,
            "next_action": (next_action or "").strip(),
            "stack": stack or [],
            "github_repo": github_repo,
            "entity_updated_at": _iso(updated_at),
        }
        for project_id, title, status, next_action, stack, github_repo, updated_at in rows
    ]


async def project_last_activity(
    session: AsyncSession, *, project_ids: list[uuid.UUID]
) -> dict[str, datetime]:
    """Proje başına son ANLAMLI hareket (§69).

    `Project.last_activity_at` yalnızca GitHub senkronunda yazıldığı için genel
    proje hareketini temsil etmez; kanonik Event geçmişi (sayılan fiiller)
    kullanılır. Üçüncü bir zaman damgası ÜRETİLMEZ.
    """
    if not project_ids:
        return {}
    rows = (
        await session.execute(
            select(Event.entity_id, func.max(Event.occurred_at))
            .where(Event.entity_id.in_(project_ids), Event.verb.in_(COUNTED_VERBS))
            .group_by(Event.entity_id)
        )
    ).all()
    result: dict[str, datetime] = {
        str(entity_id): occurred_at for entity_id, occurred_at in rows if entity_id is not None
    }

    # Projeye bağlı görevlerin hareketi de projenin hareketidir (belongs_to).
    linked = (
        await session.execute(
            select(Link.to_id, func.max(Event.occurred_at))
            .select_from(Link)
            .join(Event, Event.entity_id == Link.from_id)
            .where(
                Link.to_id.in_(project_ids),
                Link.relation == "belongs_to",
                Event.verb.in_(COUNTED_VERBS),
            )
            .group_by(Link.to_id)
        )
    ).all()
    for project_id, occurred_at in linked:
        key = str(project_id)
        if occurred_at is not None and (key not in result or occurred_at > result[key]):
            result[key] = occurred_at
    return result


async def overdue_milestones(
    session: AsyncSession, *, now: datetime, limit: int
) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            select(Milestone.id, Milestone.project_id, Milestone.title, Milestone.due_at)
            .where(
                Milestone.due_at.is_not(None),
                Milestone.due_at < now,
                Milestone.completed_at.is_(None),
            )
            .order_by(Milestone.due_at.asc(), Milestone.id.asc())
            .limit(limit)
        )
    ).all()
    return [
        {
            "id": str(milestone_id),
            "project_id": str(project_id),
            "title": title or "",
            "due_at": _iso(due_at),
        }
        for milestone_id, project_id, title, due_at in rows
    ]


async def overdue_todos_for_project(
    session: AsyncSession, *, project_id: uuid.UUID, now: datetime, limit: int
) -> list[dict[str, Any]]:
    linked = select(Link.from_id).where(Link.to_id == project_id, Link.relation == "belongs_to")
    rows = (
        await session.execute(
            select(Todo.id, Entity.title, Todo.due_at)
            .join(Entity, Entity.id == Todo.id)
            .where(
                Todo.id.in_(linked),
                Todo.status.in_(("open", "doing")),
                Todo.due_at.is_not(None),
                Todo.due_at < now,
            )
            .order_by(Todo.due_at.asc(), Todo.id.asc())
            .limit(limit)
        )
    ).all()
    return [
        {"id": str(todo_id), "title": title or "", "due_at": _iso(due_at)}
        for todo_id, title, due_at in rows
    ]


# ---------------------------------------------------------------------------
# Review
# ---------------------------------------------------------------------------


async def previous_review(
    session: AsyncSession, *, kind: str | None, before: date
) -> dict[str, Any] | None:
    """Dönemi `before`'dan ÖNCE başlayan EN YENİ kabul edilmiş review (§145).

    `kind=None` tür ayrımı yapmaz: süreklilik çapası HERHANGİ bir review'ı
    kabul eder (§26), haftalık karşılaştırma ise aynı türü ister.
    """
    from app.modules.review.models import Review

    statement = select(Review).where(Review.period_start < before)
    if kind is not None:
        statement = statement.where(Review.kind == kind)
    row = (
        await session.execute(statement.order_by(Review.period_start.desc()).limit(1))
    ).scalar_one_or_none()
    if row is None:
        return None
    return {
        "id": str(row.id),
        "kind": row.kind,
        "period_start": row.period_start.isoformat(),
        "period_end": row.period_end.isoformat(),
        "stats": row.stats or {},
        "decisions": row.decisions or {},
        "note": row.note,
    }


async def todo_title_index(session: AsyncSession, *, limit: int) -> dict[str, str]:
    """Normalize başlık → todo_id (§66: yalnızca TAM eşleşme kanıt sayılır)."""
    from app.integrations.review_intelligence.policy import normalize_for_identity

    rows = (
        await session.execute(
            select(Todo.id, Entity.title)
            .join(Entity, Entity.id == Todo.id)
            .where(Entity.archived_at.is_(None))
            .order_by(Todo.id.asc())
            .limit(limit)
        )
    ).all()
    index: dict[str, str] = {}
    for todo_id, title in rows:
        key = normalize_for_identity(title or "")
        if key and key not in index:
            index[key] = str(todo_id)
    return index


# ---------------------------------------------------------------------------
# Vault / Sıcak Hafıza
# ---------------------------------------------------------------------------


def vault_root() -> Path | None:
    from app.integrations.obsidian.vault import vault_context

    root, _name = vault_context()
    if root is None or not root.is_dir():
        return None
    return root


def daily_note_ref(day: date) -> str:
    return f"{DAILY_ROOT}/{day.isoformat()}.md"


def read_daily_note(day: date) -> dict[str, Any] | None:
    """Günlük notu sınırlı biçimde okur; eksik not HATA DEĞİLDİR (§86).

    Kaynak referansı satır aralığı taşır: `vault:10 Daily/….md:L1-L40`.
    """
    from app.integrations.obsidian import evidence as vault_ev

    root = vault_root()
    if root is None:
        return None
    rel_path = daily_note_ref(day)
    lines = vault_ev.read_note_lines(root, rel_path)
    if lines is None:
        return None
    body = "\n".join(lines)
    excerpt, truncated = _bounded(body, MAX_H5_DAILY_NOTE_CHARS)
    included_lines = excerpt.count("\n") + 1 if excerpt else 0
    return {
        "day": day.isoformat(),
        "relative_path": rel_path,
        "ref": f"vault:{rel_path}:L1-L{max(included_lines, 1)}",
        "excerpt": excerpt,
        "truncated": truncated,
    }


def daily_note_days(period_start: date, period_end: date) -> list[date]:
    """Dönemdeki günler (günlük not beklentisi) — en fazla 7 gün (§87)."""
    days: list[date] = []
    current = period_start
    while current < period_end and len(days) < MAX_H5_DAILY_NOTES:
        days.append(current)
        current += timedelta(days=1)
    return days


def managed_note_meta(entity_id: uuid.UUID) -> dict[str, Any] | None:
    """Yönetilen notun taze çözümü (§73/§130) — yol DB'den OKUNMAZ."""
    from app.integrations.obsidian.service import VaultConflictError, resolve_managed_item

    root = vault_root()
    if root is None:
        return None
    try:
        item = resolve_managed_item(entity_id)
    except VaultConflictError:
        return {
            "state": "conflict",
            "relative_path": None,
            "forkos_id": str(entity_id),
            "mtime": None,
            "age_days": None,
        }
    if item is None:
        return None
    path = root / item.relative_path
    mtime = None
    age_days = None
    try:
        stat = path.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
        age_days = max((datetime.now(UTC) - mtime).days, 0)
    except OSError:
        mtime = None
    return {
        "state": "available",
        "relative_path": item.relative_path,
        "forkos_id": item.forkos_id,
        "title": item.title,
        "mtime": _iso(mtime),
        "age_days": age_days,
    }


def active_hot_memories() -> list[dict[str, Any]]:
    """Yalnızca TAM dedupe için okunur (§80/§81) — tarihsel kanıt DEĞİLDİR."""
    from app.integrations.obsidian.hot_memory import MEMORY_ROOT, scan_memories

    root = vault_root()
    if root is None:
        return []
    directory = root / MEMORY_ROOT
    if not directory.is_dir():
        return []
    snapshot = scan_memories(directory)
    return [
        {
            "memory_id": record.memory_id,
            "title": record.title,
            "text": record.text,
            "status": record.status,
            "ref": f"hot_memory:{record.memory_id}",
        }
        for record in snapshot.items
    ]


def entity_route(entity_type: str, entity_id: str) -> str:
    spec = registry_svc.type_spec(entity_type)
    if spec and spec.route:
        return spec.route.replace("{id}", entity_id)
    return f"/{entity_type}s/{entity_id}"


_UUID_RE = re.compile(r"^[0-9a-fA-F-]{36}$")


def parse_focus_entity(value: str | None) -> uuid.UUID | None:
    if value is None or not str(value).strip():
        return None
    text = str(value).strip()
    if not _UUID_RE.match(text):
        raise ReviewIntelligenceError("INVALID_FOCUS_ENTITY", "focus_entity_id must be a UUID")
    try:
        return uuid.UUID(text)
    except (ValueError, AttributeError) as exc:
        raise ReviewIntelligenceError(
            "INVALID_FOCUS_ENTITY", "focus_entity_id must be a UUID"
        ) from exc


async def load_entity(session: AsyncSession, entity_id: uuid.UUID) -> dict[str, Any] | None:
    row = (await session.execute(select(Entity).where(Entity.id == entity_id))).scalar_one_or_none()
    if row is None:
        return None
    return {
        "id": str(row.id),
        "type": row.type,
        "title": row.title,
        "archived_at": _iso(row.archived_at),
        "updated_at": _iso(row.updated_at),
        "route": entity_route(row.type, str(row.id)),
    }


async def sealed_episode_items(
    session: AsyncSession,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Mühürlenmiş epizodik oturum maddelerini döner (ref: episode:<id>, episode_item:<id>)."""
    from app.modules.agent_episode.models import (
        AgentSessionEpisode,
        AgentSessionEpisodeItem,
        AgentSessionEpisodeTurn,
    )

    query = (
        select(AgentSessionEpisodeItem, AgentSessionEpisode, AgentSessionEpisodeTurn)
        .join(AgentSessionEpisode, AgentSessionEpisodeItem.episode_id == AgentSessionEpisode.id)
        .outerjoin(
            AgentSessionEpisodeTurn,
            AgentSessionEpisodeItem.episode_turn_id == AgentSessionEpisodeTurn.id,
        )
        .where(AgentSessionEpisode.status.in_(("sealed", "sealed_degraded")))
    )
    if start is not None:
        query = query.where(AgentSessionEpisodeItem.created_at >= start)
    if end is not None:
        query = query.where(AgentSessionEpisodeItem.created_at <= end)
    query = query.order_by(
        AgentSessionEpisodeItem.created_at.desc(), AgentSessionEpisodeItem.id.desc()
    ).limit(limit)

    result = await session.execute(query)
    items: list[dict[str, Any]] = []
    for item_row, ep_row, turn_row in result.all():
        items.append(
            {
                "episode_id": ep_row.id,
                "episode_ref": f"episode:{ep_row.id}",
                "item_id": item_row.id,
                "ref": f"episode_item:{item_row.id}",
                "kind": item_row.kind,
                "text": item_row.text,
                "source_role": item_row.source_role,
                "evidence_digest": item_row.evidence_digest,
                "semantic_memory_eligible": (
                    turn_row.semantic_memory_eligible if turn_row is not None else False
                ),
                "scope_ambiguous": "SCOPE_AMBIGUOUS" in (ep_row.degraded_reasons or []),
                "scope_project": ep_row.scope_project,
                "created_at": _iso(item_row.created_at),
            }
        )
    return items


__all__ = [
    "CONTINUITY_ANCHOR_LOOKBACK_DAYS",
    "DAILY_ROOT",
    "ResolvedPeriod",
    "active_hot_memories",
    "active_projects",
    "daily_note_days",
    "daily_note_ref",
    "important_notifications",
    "last_meaningful_event",
    "last_meaningful_event_for_entities",
    "load_entity",
    "managed_note_meta",
    "meaningful_events",
    "newly_overdue_todos",
    "open_todos",
    "opportunity_changes",
    "overdue_milestones",
    "overdue_todos_for_project",
    "parse_aware",
    "parse_focus_entity",
    "parse_reference_date",
    "passed_plan_open_tasks",
    "previous_review",
    "project_last_activity",
    "read_daily_note",
    "resolve_period",
    "rss_accumulation",
    "scoped_events",
    "sealed_episode_items",
    "todo_statuses",
    "todo_title_index",
    "upcoming_deadlines",
    "vault_root",
]
