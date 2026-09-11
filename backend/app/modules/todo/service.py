from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import tags as tag_svc
from app.core.entity import create_entity, touch_entity
from app.core.events import log_event
from app.core.links import link
from app.core.models import Entity, Link
from app.core.time import local_today
from app.modules import DeadlineRow
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


def _todo_out(todo: Todo, title: str, tags: list[str] | None = None,
              context: dict | None = None) -> TodoOut:
    """`context`: proje/kilometre tasi/alt gorev sayilari (bkz. `_context_for`).

    Ayri parametre cunku tek kayit okurken bunlari toplamak gereksiz;
    liste uclarinda ise N+1 kacinmak icin TOPLU hesaplanip buraya verilir.
    """
    extra = context or {}
    return TodoOut(id=todo.id, title=title, description=todo.description,
                   priority=todo.priority, status=todo.status, due_at=todo.due_at,
                   reminder_at=todo.reminder_at, completed_at=todo.completed_at,
                   parent_id=todo.parent_id, position=todo.position,
                   tags=tags or [], recur=todo.recur, milestone_id=todo.milestone_id,
                   **extra)


async def _context_for(session: AsyncSession, todos: list[Todo]) -> dict[uuid.UUID, dict]:
    """Gorevlerin proje / kilometre tasi / alt gorev bilgisini TOPLU okur."""
    if not todos:
        return {}
    ids = [todo.id for todo in todos]
    out: dict[uuid.UUID, dict] = {todo.id: {} for todo in todos}

    # Proje: link(from=todo, to=project, 'belongs_to')
    rows = (
        await session.execute(
            select(Link.from_id, Entity.id, Entity.title)
            .join(Entity, Entity.id == Link.to_id)
            .where(Link.from_id.in_(ids), Link.relation == "belongs_to",
                   Entity.type == "project")
        )
    ).all()
    for todo_id, project_id, project_title in rows:
        out[todo_id]["project_id"] = project_id
        out[todo_id]["project_title"] = project_title

    # Ogrenme kaynagi: learning topic -> todo olustururken yazilan
    # todo --prepares_for--> study_topic bagi. Gorev listesindeki baslik bu
    # sayede N+1 sorgu olmadan asil konu agacina geri donebilir.
    learning_rows = (
        await session.execute(
            select(Link.from_id, Entity.id, Entity.title)
            .join(Entity, Entity.id == Link.to_id)
            .where(
                Link.from_id.in_(ids),
                Link.relation == "prepares_for",
                Entity.type == "study_topic",
            )
        )
    ).all()
    for todo_id, topic_id, topic_title in learning_rows:
        out[todo_id]["learning_topic_id"] = topic_id
        out[todo_id]["learning_topic_title"] = topic_title

    milestone_ids = [todo.milestone_id for todo in todos if todo.milestone_id]
    if milestone_ids:
        # Yerel import: project.service zaten todo.service'i cagiriyor, modul
        # duzeyinde almak dongusel import yapiyor.
        from app.modules.project.models import Milestone

        titles = dict(
            (
                await session.execute(
                    select(Milestone.id, Milestone.title).where(Milestone.id.in_(milestone_ids))
                )
            ).all()
        )
        for todo in todos:
            if todo.milestone_id in titles:
                out[todo.id]["milestone_title"] = titles[todo.milestone_id]

    # Alt gorevler: parent_id bu gorevleri gosterenler.
    counts = (
        await session.execute(
            select(
                Todo.parent_id,
                func.count(Todo.id),
                func.count(Todo.id).filter(Todo.status == "done"),
            )
            .where(Todo.parent_id.in_(ids))
            .group_by(Todo.parent_id)
        )
    ).all()
    for parent_id, total, done in counts:
        out[parent_id]["subtask_total"] = int(total)
        out[parent_id]["subtask_done"] = int(done)

    # Plan: tek sorguda tum gorevlerin gelecek slotlarini cek, en yakin gunu
    # sec. Gecmis slotlar DONMEZ -- plan bilgisi gelecege donuktur, dune
    # planlanan gorev bugun "planli" rozetini hak etmez. Bir gorevin birden
    # fazla gunu varsa en yakin gelecek gorunur (o gunun akisi asil odaktir).
    plan_rows = (
        await session.execute(
            select(PlanSlot.entity_id, PlanSlot.day, PlanSlot.start_min)
            .where(PlanSlot.entity_id.in_(ids), PlanSlot.day >= local_today())
            .order_by(PlanSlot.day)
        )
    ).all()
    nearest: dict[uuid.UUID, tuple[date, int | None]] = {}
    for entity_id, day, start_min in plan_rows:
        if entity_id not in nearest:
            nearest[entity_id] = (day, start_min)
    for todo_id, (day, start_min) in nearest.items():
        out[todo_id]["planned_day"] = day
        out[todo_id]["planned_start_min"] = start_min

    return out


def _next_due(current: datetime, recur: str) -> datetime:
    """Rutinin bir sonraki tarihi.

    weekdays: cumartesi/pazar atlanir -- hafta ici rutinleri hafta sonuna
    dusmesin. monthly ayni gun sayisini korur; ayin 31'i olmayan aylarda
    ay sonuna kayar (relativedelta bagimliligi eklemeye degmez).
    """
    if recur == "daily":
        return current + timedelta(days=1)
    if recur == "weekdays":
        nxt = current + timedelta(days=1)
        while nxt.weekday() >= 5:
            nxt += timedelta(days=1)
        return nxt
    if recur == "weekly":
        return current + timedelta(days=7)
    if recur == "monthly":
        year, month = divmod(current.month, 12)
        year, month = current.year + year, month + 1
        last_day = [31, 29 if year % 4 == 0 and (year % 100 or not year % 400) else 28,
                    31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
        return current.replace(year=year, month=month, day=min(current.day, last_day))
    return current + timedelta(days=1)


async def _resolve_context(
    session: AsyncSession, *, parent_id: uuid.UUID | None,
    project_id: uuid.UUID | None, milestone_id: uuid.UUID | None,
) -> tuple[uuid.UUID | None, uuid.UUID | None]:
    inherited_project = None
    inherited_milestone = None
    if parent_id:
        parent = await session.get(Todo, parent_id)
        if parent is None:
            raise ValueError("ust gorev bulunamadi")
        inherited_projects = (await session.execute(
            select(Link.to_id).join(Entity, Entity.id == Link.to_id).where(
                Link.from_id == parent_id, Link.relation == "belongs_to",
                Entity.type == "project",
            )
        )).scalars().all()
        if len(inherited_projects) > 1:
            raise ValueError("ust gorev birden fazla projeye bagli")
        inherited_project = inherited_projects[0] if inherited_projects else None
        inherited_milestone = parent.milestone_id
    if project_id and inherited_project and project_id != inherited_project:
        raise ValueError("alt gorev farkli projeye baglanamaz")
    if milestone_id and inherited_milestone and milestone_id != inherited_milestone:
        raise ValueError("alt gorev farkli kilometre tasina baglanamaz")
    resolved_project = project_id or inherited_project
    resolved_milestone = milestone_id or inherited_milestone
    if resolved_project:
        entity = await session.get(Entity, resolved_project)
        if entity is None or entity.type != "project":
            raise ValueError("proje bulunamadi")
    if resolved_milestone:
        from app.modules.project.models import Milestone

        milestone = await session.get(Milestone, resolved_milestone)
        if milestone is None:
            raise ValueError("kilometre tasi bulunamadi")
        if resolved_project and milestone.project_id != resolved_project:
            raise ValueError("kilometre tasi bu projeye ait degil")
        resolved_project = resolved_project or milestone.project_id
    return resolved_project, resolved_milestone


async def _copy_project_links(
    session: AsyncSession, source_id: uuid.UUID, target_id: uuid.UUID
) -> list[uuid.UUID]:
    project_ids = list((await session.execute(
        select(Link.to_id).join(Entity, Entity.id == Link.to_id).where(
            Link.from_id == source_id, Link.relation == "belongs_to",
            Entity.type == "project",
        )
    )).scalars())
    for project_id in project_ids:
        await link(session, target_id, project_id, "belongs_to")
    return project_ids


async def create(
    session: AsyncSession, data: TodoIn, *, commit: bool = True,
    search_text: str | None = None,
) -> TodoOut:
    """Tek gorev olusturma siniri (Faz 17): tum context adapter'lari buraya
    delege eder; kendi iliskisini ayni transaction'da yazar.

    `search_text`: varsayilan `data.description`; GitHub issue gibi
    adaptorler arama metnini govdeden ayri tutmak isterse verir.
    """
    if data.status not in STATUSES:
        raise ValueError("gecersiz todo durumu")
    project_id, milestone_id = await _resolve_context(
        session,
        parent_id=data.parent_id,
        project_id=data.project_id,
        milestone_id=data.milestone_id,
    )
    entity = await create_entity(session, type=Todo.ENTITY_TYPE, title=data.title.strip(),
                                 search_text=search_text if search_text is not None
                                 else (data.description or ""))
    todo = Todo(id=entity.id, description=data.description, priority=data.priority,
                status=data.status, due_at=data.due_at, reminder_at=data.reminder_at,
                parent_id=data.parent_id, position=data.position, recur=data.recur,
                milestone_id=milestone_id)
    session.add(todo)
    if project_id:
        await link(session, todo.id, project_id, "belongs_to")
    if data.tags:
        await tag_svc.add_tags(session, entity.id, data.tags)
    await log_event(session, verb="todo.created", entity_id=entity.id, entity_type="todo",
                    payload={"priority": data.priority,
                             "due_at": data.due_at.isoformat() if data.due_at else None})
    if data.plan_day is not None:
        # Tek istekte atomik: gorev + plan ayni transaction'da yazilir
        # (review/service.py:251'deki desen). schedule() kendi event'ini atar
        # (plan.scheduled); todo.created ikisi de kalir (kural 3).
        await schedule(session, PlanSlotIn(entity_id=todo.id, day=data.plan_day), commit=False)
    if commit:
        await session.commit()
    else:
        await session.flush()
    context = await _context_for(session, [todo])
    return _todo_out(todo, entity.title, data.tags, context.get(todo.id))


async def list_todos(session: AsyncSession, *, status: str | None = None,
                     due_before: datetime | None = None, priority: int | None = None,
                     include_undated: bool = False, completed_after: datetime | None = None,
                     recur_only: bool = False, limit: int = 100) -> list[TodoOut]:
    """`include_undated`: due_before verildiginde tarihsiz gorevleri de al.

    Bugun paneli bunu ister -- tarih girmeden eklenen bir gorev aksi halde
    hicbir zaman "bugunun gorevleri" listesine dusmuyordu.

    `completed_after`: o andan sonra TAMAMLANANLARI getir. Bugun panelinde
    "bugun ne bitirdim" listesi bunu kullanir; due_before ile birlikte
    verildiginde ikisi OR'lanir (bugun yapilacaklar + bugun bitenler).
    """
    stmt = (select(Todo, Entity.title).join(Entity, Entity.id == Todo.id)
            .where(Entity.archived_at.is_(None))
            .order_by(Todo.status, Todo.due_at.asc().nullslast(), Todo.position, Entity.created_at)
            .limit(limit))
    if status:
        stmt = stmt.where(Todo.status == status)
    if due_before:
        window = Todo.due_at <= due_before
        if include_undated:
            window = or_(window, Todo.due_at.is_(None))
        if completed_after is not None:
            window = or_(window, Todo.completed_at >= completed_after)
        stmt = stmt.where(window)
    elif completed_after is not None:
        stmt = stmt.where(Todo.completed_at >= completed_after)
    if priority is not None:
        stmt = stmt.where(Todo.priority == priority)
    if recur_only:
        stmt = stmt.where(Todo.recur.is_not(None))
    rows = (await session.execute(stmt)).all()
    todos = [todo for todo, _ in rows]
    tag_map = await tag_svc.tags_for(session, [todo.id for todo in todos])
    context = await _context_for(session, todos)
    return [_todo_out(todo, title, tag_map.get(todo.id, []), context.get(todo.id))
            for todo, title in rows]


async def get(session: AsyncSession, todo_id: uuid.UUID) -> TodoOut | None:
    row = (await session.execute(select(Todo, Entity.title).join(Entity, Entity.id == Todo.id)
                                 .where(Todo.id == todo_id))).first()
    if row is None:
        return None
    tag_map = await tag_svc.tags_for(session, [row[0].id])
    context = await _context_for(session, [row[0]])
    return _todo_out(row[0], row[1], tag_map.get(row[0].id, []), context.get(row[0].id))


async def update(session: AsyncSession, todo_id: uuid.UUID, data: TodoUpdate, *,
                 commit: bool = True) -> TodoOut | None:
    todo = await session.get(Todo, todo_id)
    entity = await session.get(Entity, todo_id)
    if todo is None or entity is None:
        return None
    values = data.model_dump(exclude_unset=True)
    title = values.pop("title", None)
    # tags bir kolon degil, entity_tag uzerinden duruyor.
    new_tags = values.pop("tags", None)
    # Bos metin "rutini kaldir" demek; None ise alan hic degismez.
    if values.get("recur") == "":
        values["recur"] = None
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
    if new_tags is not None:
        await tag_svc.set_tags(session, todo_id, new_tags)
    if todo.status == "done" and previous_status != "done":
        todo.completed_at = datetime.now(UTC)
        await _log_completed(session, todo, entity.title)
        await _spawn_next_occurrence(session, todo)
    elif todo.status == "dropped" and previous_status != "dropped":
        await log_event(session, verb="todo.dropped", entity_id=todo_id,
                        entity_type="todo", payload={})
    if commit:
        await session.commit()
    else:
        await session.flush()
    tag_map = await tag_svc.tags_for(session, [todo.id])
    context = await _context_for(session, [todo])
    return _todo_out(todo, entity.title if title is None else title.strip(),
                     tag_map.get(todo.id, []), context.get(todo.id))


async def _log_completed(session: AsyncSession, todo: Todo, title: str) -> None:
    now = datetime.now(UTC)
    overdue = bool(todo.due_at and todo.due_at < now)
    await log_event(session, verb="todo.completed", entity_id=todo.id, entity_type="todo",
                    payload={"title": title, "priority": todo.priority,
                             "was_overdue": overdue, "recur": todo.recur})


async def complete(session: AsyncSession, todo_id: uuid.UUID) -> TodoOut | None:
    todo = await session.get(Todo, todo_id)
    entity = await session.get(Entity, todo_id)
    if todo is None or entity is None:
        return None
    if todo.status != "done":
        todo.status = "done"
        todo.completed_at = datetime.now(UTC)
        await touch_entity(session, todo_id)
        await _log_completed(session, todo, entity.title)
        await _spawn_next_occurrence(session, todo)
        await session.commit()
    tag_map = await tag_svc.tags_for(session, [todo.id])
    context = await _context_for(session, [todo])
    return _todo_out(todo, entity.title, tag_map.get(todo.id, []), context.get(todo.id))


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


async def carry_over(session: AsyncSession, day: date, target: date) -> int:
    """Bir gunun ACIK todo slotlarini hedef gune tasir (Faz 33).

    Tek transaction: tum tasima ya olur ya olmaz. Tamamlanmis/dropped
    gorevlerin slotlari TASINMAZ. Hedef gunde ayni entity icin slot
    zaten varsa eski slot dusurulur (yeni gun kazanir). `plan.carried_over`
    event'i yazilir.
    """
    slots = list((await session.execute(
        select(PlanSlot).where(PlanSlot.day == day)
    )).scalars())
    moved = 0
    for slot in slots:
        todo = await session.get(Todo, slot.entity_id)
        if todo is None or todo.status not in ("open", "doing"):
            continue
        existing = (await session.execute(
            select(PlanSlot).where(
                PlanSlot.entity_id == slot.entity_id, PlanSlot.day == target
            )
        )).scalar_one_or_none()
        if existing is not None:
            # Hedef gunde zaten planli: eski slot gereksiz, yeni gun kazanir.
            await session.delete(slot)
        else:
            slot.day = target
        await log_event(
            session, verb="plan.carried_over", entity_id=slot.entity_id,
            entity_type="todo",
            payload={"from": day.isoformat(), "to": target.isoformat()},
        )
        moved += 1
    await session.commit()
    return moved


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
    previous = {
        "day": slot.day,
        "start_min": slot.start_min,
        "duration_min": slot.duration_min,
        "note": slot.note,
        "position": slot.position,
    }
    values = data.model_dump(exclude_unset=True)
    for key, value in values.items():
        setattr(slot, key, value)
    entity = await session.get(Entity, slot.entity_id)
    if any(previous[key] != getattr(slot, key) for key in values):
        await log_event(
            session,
            verb="plan.rescheduled",
            entity_id=slot.entity_id,
            entity_type=entity.type if entity else None,
            payload={
                "slot_id": str(slot.id),
                "from": previous["day"].isoformat(),
                "to": slot.day.isoformat(),
                "start_min": slot.start_min,
                "duration_min": slot.duration_min,
            },
        )
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
    entity = await session.get(Entity, slot.entity_id)
    await log_event(
        session,
        verb="plan.unscheduled",
        entity_id=slot.entity_id,
        entity_type=entity.type if entity else None,
        payload={"slot_id": str(slot.id), "day": slot.day.isoformat()},
    )
    await session.delete(slot)
    await session.commit()
    return True


async def deadline_provider(session: AsyncSession) -> list[DeadlineRow]:
    """Son tarihli acik gorevler (kural 16 -- deadline_v yerine)."""
    from app.core.deadlines import rows_with_titles

    # ScalarResult TEK gezinmelidir: ayni sonucu iki kez gezmek ikinci turda
    # bos doner (kayitlar sessizce /api/deadlines disinda kalirdi).
    todos = list((await session.execute(
        select(Todo).where(
            Todo.status.in_(("open", "doing")),
            Todo.due_at.is_not(None),
        )
    )).scalars())
    ids = [t.id for t in todos]
    due = {t.id: t.due_at for t in todos}
    prio = {t.id: t.priority for t in todos}
    return await rows_with_titles(
        session, type_="todo", module="todo", ids=ids,
        due_at=due, priority=prio,
    )


async def _spawn_next_occurrence(session: AsyncSession, done: Todo) -> None:
    """Rutin gorev tamamlaninca bir sonrakini olusturur.

    Kopya degil YENI kayit: tamamlanan gorev gecmiste kalir, seri kopmaz ve
    "bu rutini kac kez yaptim" sorusu event'lerden cevaplanabilir.
    Tekrar uretimi engellemek icin ayni gun/ayni kaynak zaten varsa atlanir.
    """
    if not done.recur:
        return

    origin = done.recur_origin_id or done.id
    base = done.due_at or datetime.now(UTC)
    next_due = _next_due(base, done.recur)
    now = datetime.now(UTC)
    while next_due <= now:
        next_due = _next_due(next_due, done.recur)

    already = (
        await session.execute(
            select(Todo.id).where(
                Todo.recur_origin_id == origin,
                Todo.status.in_(("open", "doing")),
            )
        )
    ).first()
    if already is not None:
        return

    entity = await session.get(Entity, done.id)
    title = entity.title if entity else "Rutin"
    new_entity = await create_entity(
        session, type=Todo.ENTITY_TYPE, title=title, search_text=done.description or ""
    )
    session.add(
        Todo(
            id=new_entity.id,
            description=done.description,
            priority=done.priority,
            status="open",
            due_at=next_due,
            parent_id=done.parent_id,
            position=done.position,
            recur=done.recur,
            recur_origin_id=origin,
            milestone_id=done.milestone_id,
        )
    )
    await _copy_project_links(session, done.id, new_entity.id)
    tag_map = await tag_svc.tags_for(session, [done.id])
    if tag_map.get(done.id):
        await tag_svc.add_tags(session, new_entity.id, tag_map[done.id])
    await log_event(
        session,
        verb="todo.created",
        entity_id=new_entity.id,
        entity_type="todo",
        payload={"recur": done.recur, "due_at": next_due.isoformat(), "from_routine": True},
    )
