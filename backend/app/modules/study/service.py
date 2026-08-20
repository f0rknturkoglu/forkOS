from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import create_entity, touch_entity
from app.core.events import log_event
from app.core.models import Entity
from app.modules.study.models import StudyArea, StudyTopic
from app.modules.study.schemas import AreaIn, TopicIn, TopicPatch


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
