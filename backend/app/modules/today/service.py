from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.models import Entity, Link
from app.core.time import local_zone
from app.modules.calendar.models import ExternalEvent
from app.modules.finance.models import RecurringPayment
from app.modules.flashcard.models import FlashcardCard, FlashcardDeck
from app.modules.media.models import MediaItem
from app.modules.opportunity.models import Interview, Opportunity
from app.modules.project.models import Project
from app.modules.rss.models import Feed, FeedItem
from app.modules.system.models import Setting
from app.modules.today.schemas import AgendaRow, TodayAgendaOut
from app.modules.todo.models import PlanSlot, Todo


def _bounds(day: date) -> tuple[datetime, datetime]:
    zone = local_zone()
    start = datetime.combine(day, time.min, tzinfo=zone)
    return start.astimezone(UTC), (start + timedelta(days=1)).astimezone(UTC)


def _planned_start(day: date, minute: int) -> datetime:
    zone = local_zone()
    return datetime.combine(
        day, time(hour=minute // 60, minute=minute % 60), tzinfo=zone
    )


def _todo_row(
    todo: Todo,
    title: str,
    slot: PlanSlot | None = None,
    *,
    context_only: bool = False,
    project_title: str | None = None,
) -> AgendaRow:
    completed = todo.status == "done"
    source = "planned" if slot else "routine" if todo.recur else "due"
    return AgendaRow(
        kind="todo",
        source=source,
        id=todo.id,
        slot_id=slot.id if slot else None,
        title=title,
        completed=completed,
        action=None if completed or context_only else "complete_todo",
        read_only=completed or context_only,
        context_only=context_only,
        starts_at=(
            _planned_start(slot.day, slot.start_min)
            if slot is not None and slot.start_min is not None
            else None
        ),
        duration_min=slot.duration_min if slot else None,
        parent_id=todo.parent_id,
        project_title=project_title,
        recur=todo.recur,
    )


def _nest(
    rows: list[AgendaRow],
    parents: dict[uuid.UUID, tuple[Todo, str]],
    project_titles: dict[uuid.UUID, str],
) -> list[AgendaRow]:
    by_id = {row.id: row for row in rows}
    roots: list[AgendaRow] = []
    for row in rows:
        if row.parent_id is None:
            roots.append(row)
            continue
        parent = by_id.get(row.parent_id)
        if parent is None and row.parent_id in parents:
            todo, title = parents[row.parent_id]
            parent = _todo_row(
                todo, title, context_only=True, project_title=project_titles.get(todo.id)
            )
            by_id[parent.id] = parent
            roots.append(parent)
        if parent is None:
            roots.append(row)
        else:
            parent.children.append(row)
    return roots


async def _project_context(
    session: AsyncSession, todo_ids: list[uuid.UUID]
) -> tuple[dict[uuid.UUID, str], dict[uuid.UUID, uuid.UUID]]:
    if not todo_ids:
        return {}, {}
    ProjectEntity = aliased(Entity, name="agenda_project_entity")
    rows = (await session.execute(
        select(Link.from_id, Link.to_id, ProjectEntity.title)
        .join(Project, Project.id == Link.to_id)
        .join(ProjectEntity, ProjectEntity.id == Project.id)
        .where(
            Link.from_id.in_(todo_ids),
            Link.relation == "belongs_to",
            Project.status == "active",
            ProjectEntity.archived_at.is_(None),
        )
    )).all()
    return (
        {todo_id: title for todo_id, _, title in rows},
        {todo_id: project_id for todo_id, project_id, _ in rows},
    )


def _rss_row(item: FeedItem, title: str, feed_title: str, slot: PlanSlot | None = None,
             *, source: str = "suggestion") -> AgendaRow:
    completed = item.read_at is not None
    return AgendaRow(
        kind="rss",
        source=source,
        id=item.id,
        slot_id=slot.id if slot else None,
        title=title,
        completed=completed,
        action=None if completed or slot is None else "mark_rss_read",
        read_only=completed,
        starts_at=(
            _planned_start(slot.day, slot.start_min)
            if slot is not None and slot.start_min is not None
            else None
        ),
        duration_min=slot.duration_min if slot else None,
        feed_title=feed_title,
        url=item.url,
    )


_MEASURE_LABELS = {
    "item": "öğe",
    "episode": "bölüm",
    "chapter": "bölüm",
    "page": "sayfa",
    "minute": "dk",
    "hour": "saat",
    "track": "parça",
}


def _display_number(value) -> str:
    decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
    rendered = format(decimal_value, "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def _media_progress_label(item: MediaItem) -> str:
    measure = _MEASURE_LABELS.get(item.progress_measure or "", item.progress_measure or "")
    progress = _display_number(item.progress) if item.progress is not None else None
    total = _display_number(item.total) if item.total is not None else None
    if progress is not None and total is not None:
        detail = f"{progress} / {total}"
    elif progress is not None:
        detail = progress
    elif total is not None:
        detail = f"0 / {total}"
    else:
        detail = ""
    if detail and measure:
        detail = f"{detail} {measure}"
    if item.status == "completed":
        return f"Tamamlandı · {detail}" if detail else "Tamamlandı"
    return detail or "Henüz başlanmadı"


def _media_cover(item: MediaItem) -> str | None:
    if not item.cover_path:
        return item.cover_url
    if item.cover_path.startswith("/api/media/assets/"):
        return item.cover_path
    return f"/api/media/assets/{item.cover_path.rsplit('/', 1)[-1]}"


def _media_row(
    item: MediaItem,
    title: str,
    slot: PlanSlot | None = None,
    *,
    source: str = "suggestion",
) -> AgendaRow:
    completed = item.status == "completed"
    interactive = item.status in {"planned", "in_progress", "paused"}
    return AgendaRow(
        kind="media",
        source=source,
        id=item.id,
        slot_id=slot.id if slot else None,
        title=title,
        completed=completed,
        action="log_media" if interactive else None,
        read_only=not interactive,
        starts_at=(
            _planned_start(slot.day, slot.start_min)
            if slot is not None and slot.start_min is not None
            else None
        ),
        duration_min=slot.duration_min if slot else None,
        media_kind=item.kind,
        media_status=item.status,
        progress_label=_media_progress_label(item),
        cover_url=_media_cover(item),
    )


async def agenda(session: AsyncSession, day: date) -> TodayAgendaOut:
    start, end = _bounds(day)
    external_rows = (await session.execute(
        select(ExternalEvent, Entity.title)
        .join(Entity, Entity.id == ExternalEvent.id)
        .where(
            Entity.archived_at.is_(None),
            ExternalEvent.starts_at < end,
            ExternalEvent.ends_at > start,
        )
        .order_by(ExternalEvent.starts_at)
    )).all()
    slots = list((await session.execute(
        select(PlanSlot).where(PlanSlot.day == day).order_by(
            PlanSlot.start_min.asc().nullslast(), PlanSlot.position
        )
    )).scalars())
    slot_by_entity = {slot.entity_id: slot for slot in slots}
    planned_ids = list(slot_by_entity)

    relevant = or_(
        Todo.id.in_(planned_ids),
        and_(
            Todo.status.in_(("open", "doing")),
            or_(Todo.due_at < end, and_(Todo.recur.is_not(None), Todo.due_at.is_(None))),
        ),
        and_(Todo.status == "done", Todo.completed_at >= start, Todo.completed_at < end),
    )
    rows = (await session.execute(
        select(Todo, Entity.title)
        .join(Entity, Entity.id == Todo.id)
        .where(Entity.archived_at.is_(None), relevant)
        .order_by(Todo.due_at.asc().nullslast(), Todo.priority.desc(), Entity.created_at)
    )).all()

    candidate_rows = (await session.execute(
        select(Todo, Entity.title, Entity.created_at)
        .join(Entity, Entity.id == Todo.id)
        .where(
            Entity.archived_at.is_(None),
            Todo.status.in_(("open", "doing")),
            Todo.parent_id.is_(None),
            # Rutinler yalniz vadeleri gelen gunun akimina girer. Gelecek
            # occurrence normal gorev onerisi olarak bugune geri sizmaz.
            Todo.recur.is_(None),
        )
    )).all()
    all_todo_ids = list({todo.id for todo, *_ in rows + candidate_rows} | {
        parent_id for todo, *_ in rows if (parent_id := todo.parent_id)
    })
    project_titles, project_ids = await _project_context(session, all_todo_ids)

    parent_ids = {todo.parent_id for todo, _ in rows if todo.parent_id}
    parents: dict[uuid.UUID, tuple[Todo, str]] = {}
    if parent_ids:
        parent_rows = (await session.execute(
            select(Todo, Entity.title).join(Entity, Entity.id == Todo.id)
            .where(Todo.id.in_(parent_ids), Entity.archived_at.is_(None))
        )).all()
        parents = {todo.id: (todo, title) for todo, title in parent_rows}

    timed = [
        AgendaRow(
            kind="calendar",
            source="calendar",
            id=event.id,
            title=title,
            read_only=True,
            starts_at=event.starts_at,
            duration_min=(
                max(1, int((event.ends_at - event.starts_at).total_seconds() // 60))
                if event.ends_at else None
            ),
            url=event.url,
        )
        for event, title in external_rows
    ]
    checklist: list[AgendaRow] = []
    completed: list[AgendaRow] = []
    for todo, title in rows:
        row = _todo_row(
            todo, title, slot_by_entity.get(todo.id), project_title=project_titles.get(todo.id)
        )
        if row.completed:
            completed.append(row)
        elif row.starts_at is not None:
            timed.append(row)
        else:
            checklist.append(row)

    FeedEntity = aliased(Entity, name="agenda_feed_entity")
    rss_slot_ids = [
        slot.entity_id for slot in slots
        if slot.entity_id not in {todo.id for todo, _ in rows}
    ]
    rss_rows = []
    if rss_slot_ids:
        rss_rows = (await session.execute(
            select(FeedItem, Entity.title, FeedEntity.title)
            .join(Entity, Entity.id == FeedItem.id)
            .join(Feed, Feed.id == FeedItem.feed_id)
            .join(FeedEntity, FeedEntity.id == Feed.id)
            .where(FeedItem.id.in_(rss_slot_ids), Entity.archived_at.is_(None))
        )).all()
    handled_ids = {todo.id for todo, _ in rows}
    for item, title, feed_title in rss_rows:
        handled_ids.add(item.id)
        row = _rss_row(item, title, feed_title, slot_by_entity[item.id], source="planned")
        if row.completed:
            completed.append(row)
        elif row.starts_at is not None:
            timed.append(row)
        else:
            checklist.append(row)

    media_slot_ids = [
        slot.entity_id for slot in slots if slot.entity_id not in handled_ids
    ]
    media_rows = []
    if media_slot_ids:
        media_rows = (await session.execute(
            select(MediaItem, Entity.title)
            .join(Entity, Entity.id == MediaItem.id)
            .where(MediaItem.id.in_(media_slot_ids), Entity.archived_at.is_(None))
        )).all()
    media_by_id = {item.id: (item, title) for item, title in media_rows}
    for media_id in media_slot_ids:
        if media_id not in media_by_id:
            continue
        item, title = media_by_id[media_id]
        handled_ids.add(item.id)
        row = _media_row(item, title, slot_by_entity[item.id], source="planned")
        if row.completed:
            completed.append(row)
        elif row.starts_at is not None:
            timed.append(row)
        else:
            checklist.append(row)

    generic_ids = [slot.entity_id for slot in slots if slot.entity_id not in handled_ids]
    if generic_ids:
        generic_titles = {
            eid: (title, etype)
            for eid, title, etype in (await session.execute(
                select(Entity.id, Entity.title, Entity.type).where(
                    Entity.id.in_(generic_ids), Entity.archived_at.is_(None)
                )
            )).all()
        }
        for entity_id in generic_ids:
            if entity_id not in generic_titles:
                continue
            slot = slot_by_entity[entity_id]
            etype = generic_titles[entity_id][1]
            kind = "study" if etype in ("study_topic", "study_area") else (
                "pomodoro" if etype == "pomodoro_session" else "calendar"
            )
            row = AgendaRow(
                kind=kind,
                source="planned",
                id=entity_id,
                slot_id=slot.id,
                title=generic_titles[entity_id][0],
                read_only=True,
                starts_at=(
                    _planned_start(slot.day, slot.start_min)
                    if slot.start_min is not None else None
                ),
                duration_min=slot.duration_min,
            )
            (timed if row.starts_at is not None else checklist).append(row)

    # Firsat son tarihleri (bugun + yarin) ve bugun vadesi gelen odemeler.
    deadline_end = end + timedelta(days=1)
    opps = (await session.execute(
        select(Opportunity, Entity.title)
        .join(Entity, Entity.id == Opportunity.id)
        .where(
            Entity.archived_at.is_(None),
            Opportunity.deadline_at.is_not(None),
            Opportunity.deadline_at < deadline_end,
            Opportunity.status.in_(
                ("discovered", "considering", "preparing", "applied", "interview", "offer")
            ),
        )
        .order_by(Opportunity.deadline_at)
    )).all()
    for opp, title in opps:
        row = AgendaRow(
            kind="opportunity",
            source="due",
            id=opp.id,
            title=title,
            read_only=True,
            starts_at=opp.deadline_at,
            url=opp.url,
        )
        (timed if row.starts_at is not None else checklist).append(row)

    # Bugunun mulakatlari -- saatli satir olarak.
    interviews = (await session.execute(
        select(Interview, Entity.title)
        .join(Opportunity, Opportunity.id == Interview.opportunity_id)
        .join(Entity, Entity.id == Opportunity.id)
        .where(
            Interview.scheduled_at.is_not(None),
            Interview.scheduled_at >= start,
            Interview.scheduled_at < end,
        )
        .order_by(Interview.scheduled_at)
    )).all()
    for interview, title in interviews:
        timed.append(AgendaRow(
            kind="interview",
            source="due",
            id=interview.id,
            title=f"Görüşme: {title}",
            read_only=True,
            starts_at=interview.scheduled_at,
            duration_min=interview.duration_min,
        ))

    # Bugun vadesi gelen tekrarlayan odemeler.
    payments = (await session.execute(
        select(RecurringPayment, Entity.title)
        .join(Entity, Entity.id == RecurringPayment.id)
        .where(
            Entity.archived_at.is_(None),
            RecurringPayment.active.is_(True),
            RecurringPayment.next_due_at.is_not(None),
            RecurringPayment.next_due_at >= start,
            RecurringPayment.next_due_at < end,
        )
        .order_by(RecurringPayment.next_due_at)
    )).all()
    for payment, title in payments:
        checklist.append(AgendaRow(
            kind="payment",
            source="due",
            id=payment.id,
            title=title,
            read_only=True,
            starts_at=payment.next_due_at,
            url=None,
        ))

    auto_setting = await session.get(Setting, "today.auto_suggestions")
    auto_suggestions = True if auto_setting is None else bool(auto_setting.value)
    todo_suggestions: list[AgendaRow] = []
    rss_suggestions: list[AgendaRow] = []
    flashcard_suggestions: list[AgendaRow] = []
    # Bu liste bir tavsiye degil, devam eden mevcut medya durumudur. Additive
    # sozlesme icin suggestions altinda kalir ama otomatik tavsiye ayarindan etkilenmez.
    continue_media = (await session.execute(
        select(MediaItem, Entity.title)
        .join(Entity, Entity.id == MediaItem.id)
        .where(MediaItem.status == "in_progress", Entity.archived_at.is_(None))
        .order_by(Entity.updated_at.desc(), MediaItem.id.desc())
        .limit(4)
    )).all()
    media_suggestions = [
        _media_row(item, title) for item, title in continue_media
    ]
    if auto_suggestions:
        # Yalniz cocugu bugune dusen ust gorev de akista context basligi olarak
        # bulunur; ayni ust gorevi onerilerde ikinci kez gostermeyelim.
        excluded = handled_ids | {todo.id for todo, _ in rows} | parent_ids
        candidates = [row for row in candidate_rows if row[0].id not in excluded]
        candidates.sort(key=lambda row: (
            -row[0].priority,
            row[0].due_at or datetime.max.replace(tzinfo=UTC),
            row[2],
        ))
        selected: list[tuple[Todo, str, datetime]] = []
        seen_projects: set[uuid.UUID] = set()
        for candidate in candidates:
            project_id = project_ids.get(candidate[0].id)
            if project_id is not None and project_id not in seen_projects:
                selected.append(candidate)
                seen_projects.add(project_id)
            if len(selected) == 4:
                break
        if len(selected) < 4:
            selected_ids = {row[0].id for row in selected}
            selected.extend(
                row for row in candidates if row[0].id not in selected_ids
            )
        todo_suggestions = [
            _todo_row(todo, title, project_title=project_titles.get(todo.id)).model_copy(
                update={"source": "suggestion", "action": None}
            )
            for todo, title, _ in selected[:4]
        ]

        since = datetime.now(UTC) - timedelta(hours=24)
        recent_rss = (await session.execute(
            select(FeedItem, Entity.title, FeedEntity.title)
            .join(Entity, Entity.id == FeedItem.id)
            .join(Feed, Feed.id == FeedItem.feed_id)
            .join(FeedEntity, FeedEntity.id == Feed.id)
            .where(
                FeedItem.read_at.is_(None),
                Entity.archived_at.is_(None),
                func.coalesce(FeedItem.published_at, FeedItem.fetched_at) >= since,
                FeedItem.id.not_in(handled_ids),
            )
            .order_by(func.coalesce(FeedItem.published_at, FeedItem.fetched_at).desc())
            .limit(4)
        )).all()
        rss_suggestions = [
            _rss_row(item, title, feed_title) for item, title, feed_title in recent_rss
        ]

        # Vadesi gelmis kart desteleri: tekrar etmezsen birikim buyur.
        due_decks = (
            await session.execute(
                select(FlashcardDeck.id, Entity.title, func.count())
                .select_from(FlashcardCard)
                .join(FlashcardDeck, FlashcardDeck.id == FlashcardCard.deck_id)
                .join(Entity, Entity.id == FlashcardDeck.id)
                .where(
                    FlashcardCard.suspended.is_(False),
                    or_(
                        FlashcardCard.due_at <= datetime.now(UTC),
                        FlashcardCard.due_at.is_(None),
                    ),
                )
                .group_by(FlashcardDeck.id, Entity.title)
                .order_by(func.count().desc())
                .limit(3)
            )
        ).all()
        flashcard_suggestions = [
            AgendaRow(
                kind="flashcard",
                source="suggestion",
                id=deck_id,
                title=title,
                # Kart oturumu sayfada surer: satir tiklanabilir bir baglanti.
                read_only=True,
            )
            for deck_id, title, _ in due_decks
        ]

    timed.sort(key=lambda row: row.starts_at or datetime.max.replace(tzinfo=UTC))

    return TodayAgendaOut(
        day=day,
        auto_suggestions=auto_suggestions,
        timed=_nest(timed, parents, project_titles),
        checklist=_nest(checklist, parents, project_titles),
        completed=_nest(completed, parents, project_titles),
        suggestions={
            "todos": todo_suggestions,
            "rss": rss_suggestions,
            "media": media_suggestions,
            "flashcards": flashcard_suggestions,
        },
    )
