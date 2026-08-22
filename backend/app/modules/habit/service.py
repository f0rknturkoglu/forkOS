from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import create_entity, touch_entity
from app.core.events import log_event
from app.core.models import Entity
from app.modules.habit.models import Habit, HabitLog
from app.modules.habit.schemas import HabitCheck, HabitGridEntry, HabitIn, HabitOut, HabitUpdate


async def _logs_by_habit(session: AsyncSession, ids: list[uuid.UUID], start: date) -> dict:
    rows = (await session.execute(select(HabitLog).where(
        HabitLog.habit_id.in_(ids), HabitLog.day >= start, HabitLog.done.is_(True)))).scalars()
    result: dict[uuid.UUID, set[date]] = {item: set() for item in ids}
    for row in rows:
        result[row.habit_id].add(row.day)
    return result


def _streak(days: set[date]) -> int:
    """Bugunden (ya da dunden) geriye kesintisiz gun sayisi.

    Bugun henuz isaretlenmemis olabilir -- gun bitmedi; o yuzden seri dunden
    sayilir. Yoksa her sabah "seri bozuldu" gorunurdu.
    """
    cursor, count = date.today(), 0
    if cursor not in days:
        cursor -= timedelta(days=1)
    while cursor in days:
        count += 1
        cursor -= timedelta(days=1)
    return count


def _best_streak(days: set[date]) -> int:
    """En uzun kesintisiz seri -- gecmisin tamami taranir."""
    if not days:
        return 0
    best = current = 1
    ordered = sorted(days)
    for previous, day in zip(ordered, ordered[1:], strict=False):
        current = current + 1 if (day - previous).days == 1 else 1
        best = max(best, current)
    return best


def _week_done(days: set[date]) -> int:
    """Bu haftanin (pazartesiden bugune) isaretli gun sayisi."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return sum(1 for day in days if monday <= day <= today)


async def list_habits(session: AsyncSession, active: bool | None = True) -> list[HabitOut]:
    stmt = select(Habit, Entity.title).join(Entity, Entity.id == Habit.id).order_by(Habit.position)
    if active is not None:
        stmt = stmt.where(Habit.active.is_(active))
    rows = (await session.execute(stmt)).all()
    logs = await _logs_by_habit(
        session, [h.id for h, _ in rows], date.today() - timedelta(days=365))
    return [HabitOut(id=h.id, title=title, cadence=h.cadence,
                     target_per_week=h.target_per_week, color=h.color, active=h.active,
                     position=h.position, done_today=date.today() in logs[h.id],
                     streak=_streak(logs[h.id]), best_streak=_best_streak(logs[h.id]),
                     week_done=_week_done(logs[h.id])) for h, title in rows]


async def create(session: AsyncSession, data: HabitIn) -> HabitOut:
    if data.cadence not in {"daily", "weekly"}:
        raise ValueError("gecersiz cadence")
    entity = await create_entity(session, type=Habit.ENTITY_TYPE, title=data.title.strip())
    habit = Habit(id=entity.id, cadence=data.cadence, target_per_week=data.target_per_week,
                  color=data.color, position=data.position)
    session.add(habit)
    await session.commit()
    return HabitOut(id=habit.id, title=entity.title, cadence=habit.cadence,
                    target_per_week=habit.target_per_week, color=habit.color,
                    active=habit.active, position=habit.position)


async def update(session: AsyncSession, habit_id: uuid.UUID, data: HabitUpdate) -> HabitOut | None:
    habit = await session.get(Habit, habit_id)
    entity = await session.get(Entity, habit_id)
    if habit is None or entity is None:
        return None
    values = data.model_dump(exclude_unset=True)
    title = values.pop("title", None)
    for key, value in values.items():
        setattr(habit, key, value)
    await touch_entity(session, habit_id, title=title.strip() if title else None)
    await session.commit()
    return HabitOut(id=habit.id, title=title.strip() if title else entity.title,
                    cadence=habit.cadence, target_per_week=habit.target_per_week,
                    color=habit.color, active=habit.active, position=habit.position)


async def check(session: AsyncSession, habit_id: uuid.UUID, data: HabitCheck) -> HabitOut | None:
    habit = await session.get(Habit, habit_id)
    entity = await session.get(Entity, habit_id)
    if habit is None or entity is None:
        return None
    stmt = insert(HabitLog).values(habit_id=habit_id, day=data.day, done=data.done, note=data.note)
    await session.execute(stmt.on_conflict_do_update(
        index_elements=[HabitLog.habit_id, HabitLog.day],
        set_={"done": data.done, "note": data.note}))
    if data.done:
        await log_event(session, verb="habit.checked", entity_id=habit_id, entity_type="habit",
                        payload={"habit": entity.title, "day": data.day.isoformat()})
    await session.commit()
    items = await list_habits(session, active=None)
    return next(item for item in items if item.id == habit_id)


async def grid(session: AsyncSession, weeks: int) -> list[HabitGridEntry]:
    start = date.today() - timedelta(days=weeks * 7 - 1)
    rows = (await session.execute(
        select(HabitLog, Entity.title).join(Entity, Entity.id == HabitLog.habit_id)
        .where(HabitLog.day >= start).order_by(HabitLog.day)
    )).all()
    return [HabitGridEntry(habit_id=log.habit_id, title=title, day=log.day,
                           done=log.done, note=log.note) for log, title in rows]


async def delete(session: AsyncSession, habit_id: uuid.UUID) -> bool:
    """entity satirini siler -- habit ve habit_log cascade ile gider."""
    entity = await session.get(Entity, habit_id)
    if entity is None:
        return False
    title = entity.title
    await session.delete(entity)
    await log_event(session, verb="habit.deleted", entity_type="habit",
                    payload={"title": title})
    await session.commit()
    return True
