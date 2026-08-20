from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import create_entity, touch_entity
from app.core.events import log_event
from app.core.models import Entity
from app.modules.todo.models import PlanSlot, Todo
from app.modules.todo.schemas import (
    PlanSlotIn,
    PlanSlotOut,
    PlanSlotUpdate,
    TodoIn,
    TodoOut,
    TodoUpdate,
)

STATUSES = {"open", "doing", "done", "dropped"}


def _todo_out(todo: Todo, title: str) -> TodoOut:
    return TodoOut(id=todo.id, title=title, description=todo.description,
                   priority=todo.priority, status=todo.status, due_at=todo.due_at,
                   reminder_at=todo.reminder_at, completed_at=todo.completed_at,
                   parent_id=todo.parent_id, position=todo.position)


async def create(session: AsyncSession, data: TodoIn, *, commit: bool = True) -> TodoOut:
    if data.status not in STATUSES:
        raise ValueError("gecersiz todo durumu")
    entity = await create_entity(session, type=Todo.ENTITY_TYPE, title=data.title.strip(),
                                 search_text=data.description or "")
    todo = Todo(id=entity.id, description=data.description, priority=data.priority,
                status=data.status, due_at=data.due_at, reminder_at=data.reminder_at,
                parent_id=data.parent_id, position=data.position)
    session.add(todo)
    await log_event(session, verb="todo.created", entity_id=entity.id, entity_type="todo",
                    payload={"priority": data.priority,
                             "due_at": data.due_at.isoformat() if data.due_at else None})
    if commit:
        await session.commit()
    else:
        await session.flush()
    return _todo_out(todo, entity.title)


async def list_todos(session: AsyncSession, *, status: str | None = None,
                     due_before: datetime | None = None, priority: int | None = None,
                     limit: int = 100) -> list[TodoOut]:
    stmt = (select(Todo, Entity.title).join(Entity, Entity.id == Todo.id)
            .where(Entity.archived_at.is_(None))
            .order_by(Todo.status, Todo.due_at.asc().nullslast(), Todo.position, Entity.created_at)
            .limit(limit))
    if status:
        stmt = stmt.where(Todo.status == status)
    if due_before:
        stmt = stmt.where(Todo.due_at <= due_before)
    if priority is not None:
        stmt = stmt.where(Todo.priority == priority)
    return [_todo_out(todo, title) for todo, title in (await session.execute(stmt)).all()]


async def get(session: AsyncSession, todo_id: uuid.UUID) -> TodoOut | None:
    row = (await session.execute(select(Todo, Entity.title).join(Entity, Entity.id == Todo.id)
                                 .where(Todo.id == todo_id))).first()
    return _todo_out(*row) if row else None


async def update(session: AsyncSession, todo_id: uuid.UUID, data: TodoUpdate, *,
                 commit: bool = True) -> TodoOut | None:
    todo = await session.get(Todo, todo_id)
    entity = await session.get(Entity, todo_id)
    if todo is None or entity is None:
        return None
    values = data.model_dump(exclude_unset=True)
    title = values.pop("title", None)
    previous_due = todo.due_at
    previous_status = todo.status
    if "status" in values and values["status"] not in STATUSES:
        raise ValueError("gecersiz todo durumu")
    for key, value in values.items():
        setattr(todo, key, value)
    if title is not None or "description" in values:
        await touch_entity(session, todo_id, title=title.strip() if title else None,
                           search_text=todo.description or "")
    else:
        await touch_entity(session, todo_id)
    if "due_at" in values and previous_due != todo.due_at:
        await log_event(session, verb="todo.rescheduled", entity_id=todo_id,
                        entity_type="todo", payload={
                            "from": previous_due.isoformat() if previous_due else None,
                            "to": todo.due_at.isoformat() if todo.due_at else None})
    if todo.status == "done" and previous_status != "done":
        todo.completed_at = datetime.now(UTC)
        await _log_completed(session, todo)
    elif todo.status == "dropped" and previous_status != "dropped":
        await log_event(session, verb="todo.dropped", entity_id=todo_id,
                        entity_type="todo", payload={})
    if commit:
        await session.commit()
    else:
        await session.flush()
    return _todo_out(todo, entity.title if title is None else title.strip())


async def _log_completed(session: AsyncSession, todo: Todo) -> None:
    now = datetime.now(UTC)
    overdue = bool(todo.due_at and todo.due_at < now)
    await log_event(session, verb="todo.completed", entity_id=todo.id, entity_type="todo",
                    payload={"priority": todo.priority, "was_overdue": overdue})


async def complete(session: AsyncSession, todo_id: uuid.UUID) -> TodoOut | None:
    todo = await session.get(Todo, todo_id)
    entity = await session.get(Entity, todo_id)
    if todo is None or entity is None:
        return None
    if todo.status != "done":
        todo.status = "done"
        todo.completed_at = datetime.now(UTC)
        await touch_entity(session, todo_id)
        await _log_completed(session, todo)
        await session.commit()
    return _todo_out(todo, entity.title)


async def delete(session: AsyncSession, todo_id: uuid.UUID) -> bool:
    entity = await session.get(Entity, todo_id)
    if entity is None:
        return False
    await session.delete(entity)
    await session.commit()
    return True


def week_bounds(week: date) -> tuple[date, date]:
    start = week - timedelta(days=week.weekday())
    return start, start + timedelta(days=7)


async def list_plan(session: AsyncSession, week: date) -> list[PlanSlotOut]:
    start, end = week_bounds(week)
    rows = (await session.execute(
        select(PlanSlot, Entity.type, Entity.title).join(Entity, Entity.id == PlanSlot.entity_id)
        .where(PlanSlot.day >= start, PlanSlot.day < end)
        .order_by(PlanSlot.day, PlanSlot.start_min.asc().nullslast(), PlanSlot.position)
    )).all()
    return [PlanSlotOut(id=s.id, entity_id=s.entity_id, entity_type=typ, title=title,
                        day=s.day, start_min=s.start_min, duration_min=s.duration_min,
                        note=s.note, position=s.position) for s, typ, title in rows]


async def schedule(session: AsyncSession, data: PlanSlotIn, *, commit: bool = True) -> PlanSlotOut:
    entity = await session.get(Entity, data.entity_id)
    if entity is None:
        raise ValueError("entity bulunamadi")
    existing = (await session.execute(select(PlanSlot).where(
        PlanSlot.entity_id == data.entity_id, PlanSlot.day == data.day))).scalar_one_or_none()
    slot = existing or PlanSlot(entity_id=data.entity_id, day=data.day)
    for key, value in data.model_dump(exclude={"entity_id", "day"}).items():
        setattr(slot, key, value)
    slot.day = data.day
    session.add(slot)
    await session.flush()
    await log_event(session, verb="plan.scheduled", entity_id=data.entity_id,
                    entity_type=entity.type,
                    payload={"day": data.day.isoformat(), "duration_min": data.duration_min})
    if commit:
        await session.commit()
    else:
        await session.flush()
    return PlanSlotOut(id=slot.id, entity_id=slot.entity_id, entity_type=entity.type,
                       title=entity.title, day=slot.day, start_min=slot.start_min,
                       duration_min=slot.duration_min, note=slot.note, position=slot.position)


async def update_slot(session: AsyncSession, slot_id: uuid.UUID,
                      data: PlanSlotUpdate) -> PlanSlotOut | None:
    slot = await session.get(PlanSlot, slot_id)
    if slot is None:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(slot, key, value)
    entity = await session.get(Entity, slot.entity_id)
    await session.commit()
    return PlanSlotOut(id=slot.id, entity_id=slot.entity_id,
                       entity_type=entity.type if entity else "unknown",
                       title=entity.title if entity else "", day=slot.day,
                       start_min=slot.start_min, duration_min=slot.duration_min,
                       note=slot.note, position=slot.position)


async def delete_slot(session: AsyncSession, slot_id: uuid.UUID) -> bool:
    slot = await session.get(PlanSlot, slot_id)
    if slot is None:
        return False
    await session.delete(slot)
    await session.commit()
    return True


async def today_count(session: AsyncSession) -> int:
    return int((await session.execute(select(func.count()).select_from(Todo).where(
        Todo.status.in_(("open", "doing")),
        func.date(Todo.due_at) == date.today()))).scalar_one())
