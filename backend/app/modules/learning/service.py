from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import tags as tag_svc
from app.core.entity import create_entity, delete_entity, touch_entity
from app.core.events import log_event
from app.core.links import link
from app.core.models import Entity
from app.core.time import local_today
from app.modules.bookmark.models import Bookmark
from app.modules.bookmark.service import _to_out
from app.modules.learning.models import Course, StudyArea, StudyTopic
from app.modules.learning.schemas import AreaIn, TopicIn, TopicPatch


async def create_todo_for_topic(session: AsyncSession, topic_id: UUID):
    """Konudan gorev uretir + `prepares_for` bagini TEK transaction'da yazar
    (Faz 17): gorev olusup bag kurulamazsa yari yazilmis kayit kalmaz.
    Todo servisi ana sinirdir; bu adaptor yalnizca kendi iliskisini ekler.
    """
    from app.modules.todo import service as todo_service
    from app.modules.todo.schemas import TodoIn

    topic = await session.get(StudyTopic, topic_id)
    if topic is None:
        raise ValueError("konu bulunamadi")
    title = (
        await session.execute(select(Entity.title).where(Entity.id == topic_id))
    ).scalar_one()
    todo = await todo_service.create(
        session,
        TodoIn(title=title, description="çalışma konusu"),
        commit=False,
    )
    await link(session, todo.id, topic_id, "prepares_for")
    await session.commit()
    return todo


async def create_item(session, model, data):
    values = data.model_dump()
    title = values.pop("title")
    entity = await create_entity(
        session, type=model.ENTITY_TYPE, title=title, search_text=str(values)
    )
    item = model(id=entity.id, **values)
    session.add(item)
    await session.commit()
    return await out(session, item)


async def out(session, item):
    title = (await session.execute(select(Entity.title).where(Entity.id == item.id))).scalar_one()
    return {
        "id": item.id,
        "title": title,
        **{c.name: getattr(item, c.name) for c in item.__table__.columns if c.name != "id"},
    }


async def list_items(session, model):
    items = list(
        (
            await session.execute(select(model).join(Entity).order_by(Entity.updated_at.desc()))
        ).scalars()
    )
    return [await out(session, item) for item in items]


async def patch_item(session, model, item_id, data):
    item = await session.get(model, item_id)
    if not item:
        return None
    values = data.model_dump(exclude_unset=True)
    title = values.pop("title", None)
    old_progress = getattr(item, "progress_pct", None)
    old_status = item.status
    for key, value in values.items():
        setattr(item, key, value)
    await touch_entity(session, item.id, title=title)
    if model is Course and item.progress_pct != old_progress:
        await log_event(
            session,
            verb="course.progressed",
            entity_id=item.id,
            entity_type="course",
            payload={"from_pct": old_progress, "to_pct": item.progress_pct},
        )
    if model is Course and item.status == "done" and old_status != "done":
        item.completed_at = local_today()
        await log_event(
            session, verb="course.completed", entity_id=item.id, entity_type="course", payload={}
        )
    await session.commit()
    return await out(session, item)


async def queue(session, kind=None):
    stmt = (
        select(Bookmark, Entity.title)
        .join(Entity)
        .where(Bookmark.collection == "learning")
        .order_by(Bookmark.saved_at.desc())
    )
    if kind:
        stmt = stmt.where(Bookmark.queue_kind == kind)
    rows = (await session.execute(stmt)).all()
    tags = await tag_svc.tags_for(session, [b.id for b, _ in rows])
    return [_to_out(b, t, tags.get(b.id, [])) for b, t in rows]


async def delete_item(session, model, item_id) -> bool:
    """Kitabi/kursu siler. `event` kalir -- append-only (kural 3)."""
    if await session.get(model, item_id) is None:
        return False
    entity = await session.get(Entity, item_id)
    title = entity.title if entity else ""
    if not await delete_entity(session, item_id):
        return False
    await log_event(session, verb=f"{model.ENTITY_TYPE}.deleted",
                    entity_type=model.ENTITY_TYPE, payload={"title": title})
    await session.commit()
    return True


# ---------------------------------------------------------------------------
# Calisma alanlari / konulari (Faz 12: study modulu learning'e tasindi).
# ---------------------------------------------------------------------------


async def create_area(session: AsyncSession, data: AreaIn):
    entity = await create_entity(session, type="study_area", title=data.title)
    area = StudyArea(id=entity.id, color=data.color, active=True, position=data.position)
    session.add(area)
    await session.commit()
    return {
        "id": area.id,
        "title": data.title,
        "color": area.color,
        "active": area.active,
        "position": area.position,
    }


async def list_areas(session: AsyncSession):
    rows = (
        await session.execute(
            select(StudyArea, Entity.title).join(Entity).order_by(StudyArea.position)
        )
    ).all()
    return [
        {"id": a.id, "title": title, "color": a.color, "active": a.active, "position": a.position}
        for a, title in rows
    ]


async def create_topic(session: AsyncSession, data: TopicIn):
    entity = await create_entity(session, type="study_topic", title=data.title)
    topic = StudyTopic(id=entity.id, **data.model_dump(exclude={"title"}))
    session.add(topic)
    await session.commit()
    return await topic_out(session, topic)


async def topic_out(session: AsyncSession, topic: StudyTopic):
    title = (await session.execute(select(Entity.title).where(Entity.id == topic.id))).scalar_one()
    return {
        "id": topic.id,
        "title": title,
        "area_id": topic.area_id,
        "parent_id": topic.parent_id,
        "status": topic.status,
        "confidence": topic.confidence,
        "target_min": topic.target_min,
        "position": topic.position,
        "last_studied_at": topic.last_studied_at,
    }


async def tree(session: AsyncSession, area_id: UUID):
    topics = list(
        (
            await session.execute(
                select(StudyTopic)
                .where(StudyTopic.area_id == area_id)
                .order_by(StudyTopic.position)
            )
        ).scalars()
    )
    rows = [await topic_out(session, topic) for topic in topics]
    by_parent: dict[UUID | None, list[dict]] = {}
    for row in rows:
        by_parent.setdefault(row["parent_id"], []).append(row)

    def attach(parent):
        return [{**row, "children": attach(row["id"])} for row in by_parent.get(parent, [])]

    return attach(None)


async def patch_topic(session: AsyncSession, topic_id: UUID, data: TopicPatch):
    topic = await session.get(StudyTopic, topic_id)
    if not topic:
        return None
    values = data.model_dump(exclude_unset=True)
    title = values.pop("title", None)
    old_status, old_confidence = topic.status, topic.confidence
    for key, value in values.items():
        setattr(topic, key, value)
    await touch_entity(session, topic.id, title=title)
    if topic.confidence != old_confidence:
        await log_event(
            session,
            verb="study.confidence_changed",
            entity_id=topic.id,
            entity_type="study_topic",
            payload={"from": old_confidence, "to": topic.confidence},
        )
    if topic.status == "done" and old_status != "done":
        stats = await topic_stats(session, topic.id)
        await log_event(
            session,
            verb="study.topic_completed",
            entity_id=topic.id,
            entity_type="study_topic",
            payload={"total_minutes": stats["minutes"]},
        )
    await session.commit()
    return await topic_out(session, topic)


async def topic_stats(session: AsyncSession, topic_id: UUID):
    row = (
        (
            await session.execute(
                text("""with recursive subtree as (
      select id from study_topic where id=:id union all
      select t.id from study_topic t join subtree s on t.parent_id=s.id)
      select coalesce(sum(p.actual_min),0) minutes, count(p.id) sessions
      from pomodoro_session p where p.context_entity_id in (select id from subtree)
      and p.kind='focus' and p.ended_at is not null"""),
                {"id": topic_id},
            )
        )
        .mappings()
        .one()
    )
    return dict(row)


async def stale(session: AsyncSession, days: int):
    cutoff = datetime.now(UTC) - timedelta(days=days)
    rows = (
        await session.execute(
            select(StudyTopic, Entity.title)
            .join(Entity)
            .where((StudyTopic.last_studied_at.is_(None)) | (StudyTopic.last_studied_at < cutoff))
            .order_by(StudyTopic.last_studied_at.asc().nullsfirst())
            .limit(20)
        )
    ).all()
    return [await topic_out(session, topic) for topic, _ in rows]


async def delete_topic(session: AsyncSession, topic_id: UUID) -> bool:
    """Konuyu (ve alt konularini) siler. `event` kalir -- append-only."""
    topic = await session.get(StudyTopic, topic_id)
    if topic is None:
        return False
    entity = await session.get(Entity, topic_id)
    title = entity.title if entity else ""
    if not await delete_entity(session, topic_id):
        return False
    await log_event(session, verb="study.topic_deleted", entity_type="study_topic",
                    payload={"title": title})
    await session.commit()
    return True


async def delete_area(session: AsyncSession, area_id: UUID) -> bool:
    """Alani ve altindaki tum konulari siler."""
    area = await session.get(StudyArea, area_id)
    if area is None:
        return False
    entity = await session.get(Entity, area_id)
    title = entity.title if entity else ""
    if not await delete_entity(session, area_id):
        return False
    await log_event(session, verb="study.area_deleted", entity_type="study_area",
                    payload={"title": title})
    await session.commit()
    return True
