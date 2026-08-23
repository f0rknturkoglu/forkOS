from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import Integer, and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import create_entity
from app.core.events import log_event
from app.core.models import Entity, Event
from app.core.time import local_datetime, local_day_bounds
from app.modules.pomodoro.models import PomodoroSession
from app.modules.review.models import Review
from app.modules.review.schemas import ReviewIn, ReviewOut, ReviewPreview
from app.modules.study.models import StudyArea, StudyTopic
from app.modules.todo import service as todo_service
from app.modules.todo.models import Todo
from app.modules.todo.schemas import PlanSlotIn, TodoIn, TodoUpdate


def period_bounds(kind: str, start: date) -> tuple[date, date]:
    if kind == "daily":
        return start, start + timedelta(days=1)
    if kind != "weekly":
        raise ValueError("review kind daily veya weekly olmali")
    monday = start - timedelta(days=start.weekday())
    return monday, monday + timedelta(days=7)


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


async def preview(session: AsyncSession, kind: str, period_start: date) -> ReviewPreview:
    start, end = period_bounds(kind, period_start)
    start_dt, end_dt = local_day_bounds(start)[0], local_day_bounds(end)[0]
    minutes_expr = Event.payload["minutes"].astext.cast(Integer)
    topic_expr = Event.payload["topic"].astext
    routine_title_expr = case(
        (Event.verb == "habit.checked", Event.payload["habit"].astext),
        else_=Event.payload["title"].astext,
    )
    focus = (
        await session.execute(
            select(
                func.coalesce(func.sum(minutes_expr), 0),
                func.count(),
            ).where(
                Event.verb == "pomodoro.completed",
                Event.occurred_at >= start_dt,
                Event.occurred_at < end_dt,
            )
        )
    ).one()
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
        "focus": {"minutes": int(focus[0]), "sessions": int(focus[1]), "interrupted": interrupted},
        "topics": [
            {"topic": topic or "Genel", "minutes": int(minutes or 0)}
            for topic, minutes in topic_rows
        ],
        "habits": {title: int(count) for title, count in routine_rows if title},
        "capture": {
            "bookmarks": await _event_count(session, "bookmark.saved", start_dt, end_dt),
            "rss_read": await _event_count(session, "rss.item_read", start_dt, end_dt),
        },
        "applications": {
            "discovered": await _event_count(session, "opportunity.items_added", start_dt, end_dt),
            "updated": await _event_count(session, "opportunity.updated", start_dt, end_dt),
        },
        "study": {"minutes_by_area": {area: int(minutes or 0) for area, minutes in study_rows}},
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
    return ReviewPreview(
        kind=kind, period_start=start, period_end=end, stats=stats, unfinished_todos=unfinished
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
    await _apply_decisions(session, data.decisions, snap.period_end)
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
        stats=snap.stats,
        decisions=data.decisions,
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


async def _apply_decisions(session: AsyncSession, decisions: dict, next_start: date) -> None:
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
    for item in decisions.get("priorities", [])[:3]:
        title = item if isinstance(item, str) else item.get("title", "")
        if not title:
            continue
        todo = await todo_service.create(session, TodoIn(title=title, priority=3), commit=False)
        await todo_service.schedule(
            session, PlanSlotIn(entity_id=todo.id, day=next_start), commit=False
        )


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
