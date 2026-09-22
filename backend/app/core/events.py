"""Activity log. Append-only."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from sqlalchemy import Numeric, Text, and_, case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity, Event


async def log_event(
    session: AsyncSession, *, verb: str,
    entity_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    payload: dict | None = None,
) -> Event:
    """Ornek: await log_event(s, verb="bookmark.saved", entity_id=b.id,
                              entity_type="bookmark", payload={"collection": "inbox"})"""
    event = Event(verb=verb, entity_id=entity_id, entity_type=entity_type,
                  payload=payload or {})
    session.add(event)
    return event


#: Akis filtre kimlikleri. "all" filtre yok demektir; "alerts" bir ALAN degil
#: dikkat eksenidir (her alandan cikabilir).
ActivityFilterId = Literal[
    "all", "tasks", "focus", "learning", "reading", "career", "system", "alerts",
]

#: Hareket akisi filtreleri: "bu kayit hangi alandan geldi?"
#:
#: Emek haritasinin kategorileri (contributions.KINDS) BASKA bir soruyu
#: yanitlar ("bugun insan eliyle is yapildi mi?"): ikisi tek eslemeye
#: zorlanmaz, cunku bir kayit haritada sayilmadan da bir alana ait olabilir
#: (or. todo.created) ve sayilan bir kayit alan disi da kalabilir.
#:
#: Filtreler AYRIKTIR ve kanonik fiil defterini (registry.all_event_verbs)
#: TAM kapsar; yeni fiil ekleyen modul onu buraya da yazar
#: (bkz. tests/test_activity_filters.py::test_filters_partition_the_verb_ledger).
#: "system" bir kullanici alani degildir: kendi filtresi olmayan kayitlarin
#: (makine kosumu, kaynak, ayar, yedek, finans, proje) evidir.
ACTIVITY_FILTERS: dict[str, tuple[str, ...]] = {
    "tasks": (
        "plan.carried_over", "plan.rescheduled", "plan.scheduled", "plan.unscheduled",
        "todo.completed", "todo.created", "todo.dropped", "todo.rescheduled",
        "calendar.plan_pushed",
    ),
    "focus": (
        "pomodoro.completed", "pomodoro.deleted", "pomodoro.interrupted",
    ),
    "learning": (
        "course.completed", "course.created", "course.deleted", "course.progressed",
        "course.reopened", "course.started", "flashcard.card_added", "flashcard.deck_created",
        "flashcard.imported", "flashcard.reviewed", "learning.imported", "learning.resource_added",
        "learning.resource_completed", "learning.resource_deleted", "learning.resource_reopened",
        "learning.resource_updated",
        "study.area_archived", "study.area_created", "study.area_deleted", "study.area_reopened",
        "study.confidence_changed", "study.mastery_changed", "study.reviewed", "study.topic_completed",
        "study.topic_created", "study.topic_deleted", "study.topic_moved", "study.topic_renamed",
        "study.topic_reopened", "study.topic_started", "review.completed", "review.note_updated",
    ),
    "reading": (
        "bookmark.deleted", "bookmark.favorited", "bookmark.highlighted", "bookmark.moved",
        "bookmark.read", "bookmark.saved", "bookmark.scrolled",
        "media.collection_created", "media.collection_deleted", "media.collection_item_added",
        "media.collection_item_removed", "media.collection_updated",
        "media.consumed", "media.cycle_completed", "media.cycle_reopened", "media.cycle_started",
        "media.item_added", "media.item_deleted", "media.item_restored", "media.item_trashed",
        "media.item_updated", "media.progress_corrected", "media.session_logged",
        "note.archive_restored", "note.archived", "note.attachment_added", "note.attachment_deleted",
        "note.created", "note.deleted", "note.folder_created", "note.folder_deleted",
        "note.folder_updated", "note.moved", "note.pinned", "note.restored",
        "note.source_linked", "note.trashed", "note.updated",
        "rss.feed_added", "rss.feed_disabled", "rss.feed_failed", "rss.feed_removed",
        "rss.item_read", "rss.item_saved", "rss.items_added", "rss.marked_all_read",
        "rss.pruned",
    ),
    "career": (
        "career_connections.imported", "career_story.archived", "career_story.created",
        "career_story.updated", "document.created", "document.deleted",
        "opportunity.created", "opportunity.deleted", "opportunity.duplicates_merged",
        "opportunity.evaluated", "opportunity.evaluation_updated", "opportunity.interview_added",
        "opportunity.interview_deleted", "opportunity.interview_updated", "opportunity.items_added",
        "opportunity.pruned", "opportunity.requirement_added",
        "opportunity.requirement_document_bound", "opportunity.restored",
        "opportunity.source_reopened", "opportunity.source_status_changed",
        "opportunity.status_changed", "opportunity.trashed", "opportunity.updated",
    ),
    "system": (
        "backup.created", "backup.drive_uploaded", "backup.drive_upload_failed", "backup.restored",
        "calendar.synced", "document.synced",
        "expense.created", "expense.deleted", "github.commit", "income.created", "income.deleted",
        "link.created", "media.artwork_pruned", "media.release_discovered", "media.sync_completed",
        "media.sync_empty", "media.sync_failed",
        "project.created", "project.deleted", "project.milestone_added",
        "project.milestone_deleted", "project.milestone_updated", "project.updated",
        "recurring.paid", "recurring_payment.created", "recurring_payment.deleted",
        "settings.reset", "settings.updated",
        "source.failing", "source.stalled",
        "source_sync.completed", "source_sync.queued", "source_sync.sources_added",
        "source_sync.started",
        "system.automation_profile", "system.maintenance", "system.refresh.completed",
        "system.refresh.started",
    ),
}

#: Uyari = kullanicinin mudahale etmesi gereken kayit. TEK kural burasi:
#: `filter=alerts` sorgusu da satir bayragi (is_alert) da buradan uretilir.
ALERT_VERBS: tuple[str, ...] = (
    "source.stalled",
    "source.failing",
    "rss.feed_failed",
    "rss.feed_disabled",
    "media.sync_failed",
    "media.sync_empty",
    "backup.drive_upload_failed",
)

#: Basarili gorunen ama hata tasiyan kosum: payload.errors > 0.
ALERT_ERROR_VERB = "source_sync.completed"


def _positive(value: object) -> bool:
    try:
        return float(value) > 0  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False


def is_alert(verb: str, payload: dict | None = None) -> bool:
    """Uyari mi? Saf Python kurali -- SQL karsiligi `_alert_clause`."""
    if verb in ALERT_VERBS:
        return True
    if verb == ALERT_ERROR_VERB:
        return _positive((payload or {}).get("errors"))
    return False


def _alert_clause():
    """`is_alert`in SQL karsiligi: ayni kural, ayni satirlar.

    `payload.errors` JSONB'de her zaman sayi olmayabilir; CASE kisa devre
    yapar, metin uzerinde numeric cast patlamaz.
    """
    errors = Event.payload["errors"]
    return or_(
        Event.verb.in_(ALERT_VERBS),
        and_(
            Event.verb == ALERT_ERROR_VERB,
            case(
                (func.jsonb_typeof(errors) == "number", cast(errors.astext, Numeric) > 0),
                else_=False,
            ),
        ),
    )


async def recent_events(
    session: AsyncSession, *, limit: int = 50, offset: int = 0,
    since: datetime | None = None, verbs: list[str] | None = None,
    filter: ActivityFilterId | None = None, q: str | None = None,
) -> list[Event]:
    """Hareket akisi. Sira deterministik (occurred_at, id) -- offset'le sayfalama
    ayni kaydi iki kez gostermesin.

    `filter` ACTIVITY_FILTERS anahtarlarindan biri, "alerts" (uyarilar) ya da
    "all"/None (filtresiz). Uyari suzmesi SUNUCUDA yapilir: istemci ilk
    sayfayi suzerse pencere disindaki uyarilar gorunmez.
    """
    stmt = select(Event).order_by(Event.occurred_at.desc(), Event.id.desc())
    if since is not None:
        stmt = stmt.where(Event.occurred_at >= since)
    if verbs:
        stmt = stmt.where(Event.verb.in_(verbs))
    if filter == "alerts":
        stmt = stmt.where(_alert_clause())
    elif filter and filter != "all":
        stmt = stmt.where(Event.verb.in_(ACTIVITY_FILTERS[filter]))
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Event.verb.ilike(pattern),
                cast(Event.payload, Text).ilike(pattern),
                Entity.title.ilike(pattern),
            )
        ).outerjoin(Entity, Entity.id == Event.entity_id)
    stmt = stmt.offset(max(0, offset)).limit(limit)
    return list((await session.execute(stmt)).scalars())
