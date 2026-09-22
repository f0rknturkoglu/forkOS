from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import Integer, and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import create_entity, touch_entity
from app.core.events import log_event
from app.core.models import Entity, Event
from app.core.time import local_datetime, local_day_bounds, local_zone
from app.modules.flashcard.models import FlashcardDeck
from app.modules.learning.models import StudyArea, StudyTopic
from app.modules.pomodoro.models import PomodoroSession
from app.modules.review.models import Review
from app.modules.review.schemas import CompletedTodo, ReviewIn, ReviewOut, ReviewPreview
from app.modules.todo import service as todo_service
from app.modules.todo.models import Todo
from app.modules.todo.schemas import PlanSlotIn, TodoIn, TodoUpdate


def period_bounds(kind: str, start: date) -> tuple[date, date]:
    if kind == "daily":
        return start, start + timedelta(days=1)
    if kind == "weekly":
        monday = start - timedelta(days=start.weekday())
        return monday, monday + timedelta(days=7)
    if kind == "monthly":
        month = start.replace(day=1)
        return month, (month.replace(year=month.year + 1, month=1) if month.month == 12 else month.replace(month=month.month + 1))
    if kind == "yearly":
        year = start.replace(month=1, day=1)
        return year, year.replace(year=year.year + 1)
    raise ValueError("review kind daily, weekly, monthly veya yearly olmali")


async def _event_count(session: AsyncSession, verb: str, start: datetime, end: datetime) -> int:
    return int(
        (
            await session.execute(
                select(func.count())
                .select_from(Event)
                .where(Event.verb == verb, Event.occurred_at >= start, Event.occurred_at < end)
            )
        ).scalar_one()
    )


#: Tamamlanan görev satırı üst sınırı — preview ve H5 aynı pencereyi görür.
COMPLETED_TODO_LIMIT = 100


async def completed_todo_rows(
    session: AsyncSession, kind: str, period_start: date
) -> list[dict[str, Any]]:
    """Dönemde TAMAMLANAN görevler — kanıtı append-only Event'tir (H5.1).

    `event_id` kanonik destek referansıdır: Todo/Entity sonradan silinse bile
    `todo.completed` Event'ı kalır (`event.entity_id` → NULL). HTTP sözleşmesi
    (`ReviewPreview.completed_todos`) DEĞİŞMEZ; alan yalnızca çağırana döner.
    """
    start, end = period_bounds(kind, period_start)
    start_dt, end_dt = local_day_bounds(start)[0], local_day_bounds(end)[0]
    rows = (
        await session.execute(
            select(
                Event.id,
                Event.entity_id,
                Event.payload["title"].astext,
                Event.occurred_at,
            )
            .where(
                Event.verb == "todo.completed",
                Event.occurred_at >= start_dt,
                Event.occurred_at < end_dt,
            )
            .order_by(Event.occurred_at.desc())
            .limit(COMPLETED_TODO_LIMIT)
        )
    ).all()
    return [
        {
            "event_id": str(event_id),
            "id": str(entity_id) if entity_id else None,
            "title": title or "Görev",
            "completed_at": occurred_at.isoformat(),
        }
        for event_id, entity_id, title, occurred_at in rows
    ]


async def preview(session: AsyncSession, kind: str, period_start: date) -> ReviewPreview:
    start, end = period_bounds(kind, period_start)
    start_dt, end_dt = local_day_bounds(start)[0], local_day_bounds(end)[0]
    minutes_expr = Event.payload["minutes"].astext.cast(Integer)
    topic_expr = Event.payload["topic"].astext
    # Tarihsel veri dalı: habit.checked event'leri Faz 1'de habit modulu
    # kaldirilmasina ragmen event tablosunda DURUYOR (append-only, kural 3).
    # Bu dal onlari rutin sayiminda tutar -- kaldirilirsa gecmis haftalarin
    # ozet rakami degisir. Yeni kayitlar todo.recur uzerinden gelir.
    routine_title_expr = case(
        (Event.verb == "habit.checked", Event.payload["habit"].astext),
        else_=Event.payload["title"].astext,
    )
    focus_rows = (
        await session.execute(
            select(Event.occurred_at, minutes_expr).where(
                Event.verb == "pomodoro.completed",
                Event.occurred_at >= start_dt,
                Event.occurred_at < end_dt,
            )
        )
    ).all()
    focus_by_day: dict[date, int] = {}
    focus_minutes: list[int] = []
    for occurred_at, raw_minutes in focus_rows:
        minutes = int(raw_minutes or 0)
        focus_minutes.append(minutes)
        day = occurred_at.astimezone(local_zone()).date()
        focus_by_day[day] = focus_by_day.get(day, 0) + minutes
    best_focus = max(focus_by_day.items(), key=lambda item: item[1], default=(None, 0))
    interrupted = await _event_count(session, "pomodoro.interrupted", start_dt, end_dt)
    topic_rows = (
        await session.execute(
            select(
                topic_expr,
                func.sum(minutes_expr),
            )
            .where(
                Event.verb == "pomodoro.completed",
                Event.occurred_at >= start_dt,
                Event.occurred_at < end_dt,
            )
            .group_by(topic_expr)
            .order_by(func.sum(minutes_expr).desc())
        )
    ).all()
    routine_rows = (
        await session.execute(
            select(routine_title_expr, func.count())
            .select_from(Event)
            .outerjoin(Todo, Todo.id == Event.entity_id)
            .where(
                or_(
                    Event.verb == "habit.checked",
                    and_(
                        Event.verb == "todo.completed",
                        or_(Event.payload["recur"].astext.is_not(None), Todo.recur.is_not(None)),
                    ),
                ),
                Event.occurred_at >= start_dt,
                Event.occurred_at < end_dt,
            )
            .group_by(routine_title_expr)
        )
    ).all()
    study_rows = (
        await session.execute(
            select(Entity.title, func.coalesce(func.sum(PomodoroSession.actual_min), 0))
            .select_from(PomodoroSession)
            .join(StudyTopic, StudyTopic.id == PomodoroSession.context_entity_id)
            .join(StudyArea, StudyArea.id == StudyTopic.area_id)
            .join(Entity, Entity.id == StudyArea.id)
            .where(
                PomodoroSession.kind == "focus",
                PomodoroSession.ended_at.is_not(None),
                PomodoroSession.started_at >= start_dt,
                PomodoroSession.started_at < end_dt,
            )
            .group_by(Entity.title)
            .order_by(func.sum(PomodoroSession.actual_min).desc())
        )
    ).all()
    deck_expr = Event.payload["deck_id"].astext
    flashcard_rows = (
        await session.execute(
            select(deck_expr, func.count())
            .where(
                Event.verb == "flashcard.reviewed",
                Event.occurred_at >= start_dt,
                Event.occurred_at < end_dt,
            )
            .group_by(deck_expr)
        )
    ).all()
    # Payload'daki deck_id -> deste adi; deste silinmisse anahtar duser.
    deck_ids = [deck_id for deck_id, _ in flashcard_rows if deck_id]
    deck_titles: dict[str, str] = {}
    if deck_ids:
        deck_titles = {
            str(deck_id): title
            for deck_id, title in (
                await session.execute(
                    select(FlashcardDeck.id, Entity.title)
                    .join(Entity, Entity.id == FlashcardDeck.id)
                    .where(FlashcardDeck.id.in_([uuid.UUID(value) for value in deck_ids]))
                )
            ).all()
        }
    # --- Kariyer metrikleri (Faz 5) -----------------------------------
    # Kaynak: application_history (durum gecisleri) + opportunity.
    # Oran YOK: kucuk orneklemde yuzde yanilticidir; haftalik degerlendirme
    # yalnizca guvenilir HAM sayilari tasir.
    from app.modules.opportunity import lifecycle as opportunity_lifecycle
    from app.modules.opportunity.models import ApplicationHistory, Opportunity

    history_rows = (
        await session.execute(
            select(ApplicationHistory.to_status, func.count())
            .where(
                ApplicationHistory.at >= start_dt,
                ApplicationHistory.at < end_dt,
            )
            .group_by(ApplicationHistory.to_status)
        )
    ).all()
    transitions = {status: int(count) for status, count in history_rows}
    discovered_now = int(
        (
            await session.execute(
                select(func.count())
                .select_from(Opportunity)
                .where(
                    Opportunity.found_at >= start_dt,
                    Opportunity.found_at < end_dt,
                    Opportunity.trashed_at.is_(None),
                    Opportunity.source_status == "active",
                )
            )
        ).scalar_one()
    )
    upcoming_deadlines = int(
        (
            await session.execute(
                select(func.count())
                .select_from(Opportunity)
                .where(
                    Opportunity.deadline_at.is_not(None),
                    Opportunity.deadline_at >= datetime.now(UTC),
                    Opportunity.deadline_at < datetime.now(UTC) + timedelta(days=7),
                    Opportunity.trashed_at.is_(None),
                    Opportunity.status.in_(sorted(opportunity_lifecycle.ACTIVE_DISCOVERY_STATUSES)),
                )
            )
        ).scalar_one()
    )
    career_prep = await _event_count(session, "career_story.created", start_dt, end_dt) + (
        await _event_count(session, "career_story.updated", start_dt, end_dt)
    )

    repo_expr = Event.payload["repo"].astext
    github_rows = (
        await session.execute(
            select(repo_expr, func.count())
            .where(
                Event.verb == "github.commit",
                Event.occurred_at >= start_dt,
                Event.occurred_at < end_dt,
            )
            .group_by(repo_expr)
        )
    ).all()
    overdue = int(
        (
            await session.execute(
                select(func.count())
                .select_from(Todo)
                .where(Todo.status.in_(("open", "doing")), Todo.due_at < datetime.now(UTC))
            )
        ).scalar_one()
    )
    unfinished_rows = (
        await session.execute(
            select(Todo.id, Entity.title, Todo.priority, Todo.due_at)
            .join(Entity, Entity.id == Todo.id)
            .where(Todo.status.in_(("open", "doing")))
            .order_by(Todo.priority.desc(), Todo.due_at.asc().nullslast())
        )
    ).all()
    stats = {
        "todos": {
            "completed": await _event_count(session, "todo.completed", start_dt, end_dt),
            "created": await _event_count(session, "todo.created", start_dt, end_dt),
            "dropped": await _event_count(session, "todo.dropped", start_dt, end_dt),
            "overdue_now": overdue,
        },
        "focus": {
            "minutes": sum(focus_minutes),
            "sessions": len(focus_rows),
            "interrupted": interrupted,
            "active_days": len(focus_by_day),
            "best_day": best_focus[0],
            "best_day_minutes": best_focus[1],
            "longest_session": max(focus_minutes, default=0),
        },
        "topics": [
            {"topic": topic or "Genel", "minutes": int(minutes or 0)}
            for topic, minutes in topic_rows
        ],
        "habits": {title: int(count) for title, count in routine_rows if title},
        "capture": {
            "bookmarks": await _event_count(session, "bookmark.saved", start_dt, end_dt),
            "rss_read": await _event_count(session, "rss.item_read", start_dt, end_dt),
            "notes": await _event_count(session, "note.created", start_dt, end_dt),
        },
        "applications": {
            # Kesfedilen GUNCEL ilan: kaynakta hala gorunen yeni kayitlar.
            "discovered": discovered_now,
            "shortlisted": transitions.get("shortlisted", 0),
            "prepared": transitions.get("preparing", 0),
            "applied": transitions.get("applied", 0),
            "interview": transitions.get("interview", 0),
            "offer": transitions.get("offer", 0) + transitions.get("accepted", 0),
            "rejected": transitions.get("rejected", 0),
            "upcoming_deadlines": upcoming_deadlines,
            "career_prep": career_prep,
        },
        "study": {"minutes_by_area": {area: int(minutes or 0) for area, minutes in study_rows}},
        "flashcards": {
            "reviewed": sum(int(count) for _, count in flashcard_rows),
            "decks": {
                deck_titles.get(deck_id, "Deste"): int(count)
                for deck_id, count in flashcard_rows
            },
        },
        "github": {
            "commits": sum(int(count) for _, count in github_rows),
            "repos": {repo: int(count) for repo, count in github_rows if repo},
        },
    }
    unfinished = [
        {
            "id": str(row.id),
            "title": row.title,
            "priority": row.priority,
            "due_at": row.due_at.isoformat() if row.due_at else None,
        }
        for row in unfinished_rows
    ]
    completed = [
        CompletedTodo(id=item["id"], title=item["title"], completed_at=item["completed_at"])
        for item in await completed_todo_rows(session, kind, period_start)
    ]
    return ReviewPreview(
        kind=kind,
        period_start=start,
        period_end=end,
        stats=stats,
        unfinished_todos=unfinished,
        completed_todos=completed,
    )


async def create(session: AsyncSession, data: ReviewIn) -> ReviewOut:
    snap = await preview(session, data.kind, data.period_start)
    existing = (
        await session.execute(
            select(Review).where(Review.kind == data.kind, Review.period_start == snap.period_start)
        )
    ).scalar_one_or_none()
    if existing:
        raise RuntimeError("bu donem icin review zaten var")
    receipts = await _apply_decisions(session, data.decisions, snap.period_end)
    entity = await create_entity(
        session,
        type=Review.ENTITY_TYPE,
        title=f"{data.kind.title()} review · {snap.period_start}",
        search_text=data.note or "",
    )
    review = Review(
        id=entity.id,
        kind=data.kind,
        period_start=snap.period_start,
        period_end=snap.period_end,
        stats=snap.stats.model_dump(mode="json"),
        # Makbuz, kararlarin urettigi GERCEK kayitlarin kanitidir: istemci
        # gonderdigi `_receipts` varsa EZILIR, cunku tek kaynak sunucudur.
        decisions={**data.decisions, "_receipts": receipts},
        note=data.note,
    )
    session.add(review)
    await log_event(
        session,
        verb="review.completed",
        entity_id=entity.id,
        entity_type="review",
        payload={"kind": data.kind, "period_start": snap.period_start.isoformat()},
    )
    await session.commit()
    return _out(review)


async def _apply_decisions(
    session: AsyncSession, decisions: dict, next_start: date
) -> dict[str, list[dict[str, Any]]]:
    """Kararlari uygular ve urettigi kayitlarin makbuzunu dondurur.

    Makbuz olmadan "oncelik olusturuldu" iddiasi dogrulanamaz: Todo id'si
    sunucuda uretilir, istemci yalnizca basligi bilir. Bu yuzden donen kayit
    `Review.decisions["_receipts"]` altina yazilir. Simdilik yalnizca
    oncelikler makbuz tasir; diger kararlar mevcut kayitlari degistirir.
    """
    for raw_id in decisions.get("drop", []):
        await todo_service.update(
            session, uuid.UUID(str(raw_id)), TodoUpdate(status="dropped"), commit=False
        )
    for raw_id in decisions.get("carry_over", []):
        todo_id = uuid.UUID(str(raw_id))
        await todo_service.schedule(
            session, PlanSlotIn(entity_id=todo_id, day=next_start), commit=False
        )
    for item in decisions.get("reschedule", []):
        todo_id = uuid.UUID(str(item["id"]))
        day = date.fromisoformat(item.get("day", next_start.isoformat()))
        await todo_service.update(
            session,
            todo_id,
            TodoUpdate(due_at=local_datetime(day, 17 * 60)),
            commit=False,
        )
        await todo_service.schedule(session, PlanSlotIn(entity_id=todo_id, day=day), commit=False)
    receipts: list[dict[str, Any]] = []
    for item in decisions.get("priorities", [])[:3]:
        title = item if isinstance(item, str) else item.get("title", "")
        if not title:
            continue
        todo = await todo_service.create(session, TodoIn(title=title, priority=3), commit=False)
        await todo_service.schedule(
            session, PlanSlotIn(entity_id=todo.id, day=next_start), commit=False
        )
        receipts.append(
            {
                "title": title,
                "todo_id": str(todo.id),
                "scheduled_day": next_start.isoformat(),
            }
        )
    return {"priorities": receipts}


def _out(review: Review) -> ReviewOut:
    return ReviewOut(
        id=review.id,
        kind=review.kind,
        period_start=review.period_start,
        period_end=review.period_end,
        stats=review.stats,
        decisions=review.decisions,
        note=review.note,
    )


async def list_reviews(session: AsyncSession, kind: str | None, limit: int) -> list[ReviewOut]:
    stmt = select(Review).order_by(Review.period_start.desc()).limit(limit)
    if kind:
        stmt = stmt.where(Review.kind == kind)
    return [_out(item) for item in (await session.execute(stmt)).scalars()]


async def update_note(session: AsyncSession, review_id: uuid.UUID, note: str | None) -> ReviewOut | None:
    review = await session.get(Review, review_id)
    if review is None:
        return None
    review.note = note
    await touch_entity(session, review_id, search_text=note or "")
    await log_event(session, verb="review.note_updated", entity_id=review_id,
                    entity_type="review", payload={"kind": review.kind})
    await session.commit()
    return _out(review)
