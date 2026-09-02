from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import create_entity, delete_entity, touch_entity
from app.core.events import log_event
from app.core.links import link
from app.core.models import Entity
from app.core.time import local_today
from app.modules.learning.models import Course, LearningResource, StudyArea, StudyTopic
from app.modules.learning.schemas import AreaIn, TopicIn, TopicPatch, TopicTodoIn
from app.modules.todo.schemas import TodoIn


async def create_todo_for_topic(
    session: AsyncSession, topic_id: UUID, data: TopicTodoIn | None = None,
):
    """Konudan gorev uretir + `prepares_for` bagini TEK transaction'da yazar
    (Faz 17/31): gorev olusup bag kurulamazsa yari yazilmis kayit kalmaz.
    Todo servisi ana sinirdir; bu adaptor yalnizca kendi iliskisini ekler.
    `data`: ortak TodoIn sözleşmesi -- plan_day/priority/recur gibi alanlar
    gövdeden gelir; title/description konudan sabit kalir (bağlam korunur).
    """
    from app.modules.todo import service as todo_service

    topic = await session.get(StudyTopic, topic_id)
    if topic is None:
        raise ValueError("konu bulunamadi")
    title = (
        await session.execute(select(Entity.title).where(Entity.id == topic_id))
    ).scalar_one()
    extra = data.model_dump(exclude_unset=True) if data else {}
    todo = await todo_service.create(
        session,
        TodoIn(title=title, description="çalışma konusu", **extra),
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
    # onclause ACIK yazilir: Course'un entity'ye IKI FK'si var (id ve
    # certificate_entity_id), bu yuzden `join(Entity)` belirsiz kalip
    # AmbiguousForeignKeysError firlatiyordu (GET /courses 500).
    items = list(
        (
            await session.execute(
                select(model)
                .join(Entity, Entity.id == model.id)
                .order_by(Entity.updated_at.desc())
            )
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


async def get_topic(session: AsyncSession, topic_id: UUID):
    topic = await session.get(StudyTopic, topic_id)
    if topic is None:
        return None
    return {
        **await topic_out(session, topic),
        "children": [],
        "progress": await topic_progress(session, topic_id),
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
    progress = await progress_map(session, area_id)
    empty = {"total": 0, "done": 0, "pct": 0}
    by_parent: dict[UUID | None, list[dict]] = {}
    for row in rows:
        row["progress"] = progress.get(row["id"], empty)
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


# ---------------------------------------------------------------------------
# Kaynaklar ve ilerleme (Faz 35).
#
# Ilerleme AYRI BIR KOLONDA TUTULMAZ: tamamlanan kaynak sayisindan (alt
# konular dahil) hesaplanir. Boylece kaynak silinince/eklenince yuzde
# kendiliginden dogru kalir -- kaynakla yuzde birbirinden kayamaz.
# ---------------------------------------------------------------------------

SUBTREE_SQL = """with recursive subtree as (
    select id from study_topic where id = :id
    union all
    select t.id from study_topic t join subtree s on t.parent_id = s.id)
select id from subtree"""


async def resource_out(session: AsyncSession, item: LearningResource, title: str) -> dict:
    return {
        "id": item.id,
        "title": title,
        "topic_id": item.topic_id,
        "url": item.url,
        "kind": item.kind,
        "position": item.position,
        "completed_at": item.completed_at,
        "note": item.note,
    }


async def list_resources(session: AsyncSession, topic_id: UUID) -> list[dict]:
    rows = (
        await session.execute(
            select(LearningResource, Entity.title)
            .join(Entity, Entity.id == LearningResource.id)
            .where(LearningResource.topic_id == topic_id)
            .order_by(LearningResource.position, Entity.created_at)
        )
    ).all()
    return [await resource_out(session, item, title) for item, title in rows]


async def create_resource(session: AsyncSession, topic_id: UUID, data) -> dict:
    if await session.get(StudyTopic, topic_id) is None:
        raise ValueError("konu bulunamadi")
    values = data.model_dump()
    title = values.pop("title")
    entity = await create_entity(
        session, type=LearningResource.ENTITY_TYPE, title=title,
        search_text=" ".join(filter(None, [values.get("url"), values.get("note")])),
    )
    item = LearningResource(id=entity.id, topic_id=topic_id, **values)
    session.add(item)
    # Konu -> kaynak bagi: RelatedPanel ve graf kaynagi konunun altinda gosterir.
    await link(session, topic_id, item.id, "learns_from")
    await log_event(session, verb="learning.resource_added", entity_id=item.id,
                    entity_type=LearningResource.ENTITY_TYPE,
                    payload={"topic_id": str(topic_id), "kind": item.kind})
    await session.commit()
    return await resource_out(session, item, title)


async def patch_resource(session: AsyncSession, resource_id: UUID, data) -> dict | None:
    item = await session.get(LearningResource, resource_id)
    if item is None:
        return None
    values = data.model_dump(exclude_unset=True)
    title = values.pop("title", None)
    completed = values.pop("completed", None)
    for key, value in values.items():
        setattr(item, key, value)
    if completed is not None:
        was_done = item.completed_at is not None
        item.completed_at = datetime.now(UTC) if completed else None
        if completed != was_done:
            await log_event(
                session,
                verb="learning.resource_completed" if completed else "learning.resource_reopened",
                entity_id=item.id, entity_type=LearningResource.ENTITY_TYPE,
                payload={"topic_id": str(item.topic_id)},
            )
    await touch_entity(session, item.id, title=title)
    await session.commit()
    entity_title = (
        await session.execute(select(Entity.title).where(Entity.id == item.id))
    ).scalar_one()
    return await resource_out(session, item, entity_title)


async def delete_resource(session: AsyncSession, resource_id: UUID) -> bool:
    item = await session.get(LearningResource, resource_id)
    if item is None:
        return False
    entity = await session.get(Entity, resource_id)
    title = entity.title if entity else ""
    if not await delete_entity(session, resource_id):
        return False
    await log_event(session, verb="learning.resource_deleted",
                    entity_type=LearningResource.ENTITY_TYPE, payload={"title": title})
    await session.commit()
    return True


async def progress_map(session: AsyncSession, area_id: UUID) -> dict[UUID, dict]:
    """Alandaki her konu icin (kendi + alt agaci) kaynak sayaci.

    Tek sorguda: konu -> alt agac eslemesi, sonra kaynaklar sayilir. Agac
    basina ayri sorgu ATILMAZ (N+1 yok).
    """
    rows = (
        await session.execute(
            text("""with recursive tree as (
                select id as root, id as node from study_topic where area_id = :area
                union all
                select tr.root, t.id from study_topic t join tree tr on t.parent_id = tr.node)
            select tr.root,
                   count(r.id) as total,
                   count(r.completed_at) as done
              from tree tr left join learning_resource r on r.topic_id = tr.node
             group by tr.root"""),
            {"area": area_id},
        )
    ).all()
    return {
        root: {
            "total": total,
            "done": done,
            "pct": round(done * 100 / total) if total else 0,
        }
        for root, total, done in rows
    }


async def topic_progress(session: AsyncSession, topic_id: UUID) -> dict:
    row = (
        await session.execute(
            text("""with recursive subtree as (
                select id from study_topic where id = :id
                union all
                select t.id from study_topic t join subtree s on t.parent_id = s.id)
            select count(r.id) as total, count(r.completed_at) as done
              from learning_resource r where r.topic_id in (select id from subtree)"""),
            {"id": topic_id},
        )
    ).mappings().one()
    total, done = row["total"], row["done"]
    return {"total": total, "done": done, "pct": round(done * 100 / total) if total else 0}


# ---------------------------------------------------------------------------
# JSON ile agac ice aktarma (Faz 36).
# ---------------------------------------------------------------------------


def _norm(value: str) -> str:
    return " ".join(value.split()).casefold()


async def import_topics(session: AsyncSession, data) -> dict:
    """Konu agacini JSON'dan kurar. AYNI JSON iki kez yuklenirse kopya olmaz.

    Eslesme baslikla yapilir (ayni ebeveyn altinda, buyuk/kucuk harf ve fazla
    bosluk duyarsiz): varsa mevcut konu kullanilir, yoksa yenisi acilir.
    Boylece disarida gelistirilen bir agacin yeni surumu ustune yuklenebilir.
    Var olan konular SILINMEZ -- ice aktarma ekler ve gunceller, budamaz.
    """
    area_id = data.area_id
    if area_id is not None:
        area = await session.get(StudyArea, area_id)
        if area is None:
            raise ValueError("alan bulunamadi")
        area_title = (
            await session.execute(select(Entity.title).where(Entity.id == area_id))
        ).scalar_one()
    else:
        title = data.area.strip()
        existing = (
            await session.execute(
                select(StudyArea.id, Entity.title)
                .join(Entity, Entity.id == StudyArea.id)
                .where(func.lower(Entity.title) == title.casefold())
            )
        ).first()
        if existing is not None:
            area_id, area_title = existing
        else:
            entity = await create_entity(session, type="study_area", title=title)
            session.add(StudyArea(id=entity.id, active=True, position=0))
            await session.flush()
            area_id, area_title = entity.id, title

    # Alandaki mevcut konular: (parent, normalize baslik) -> id
    rows = (
        await session.execute(
            select(StudyTopic.id, StudyTopic.parent_id, Entity.title)
            .join(Entity, Entity.id == StudyTopic.id)
            .where(StudyTopic.area_id == area_id)
        )
    ).all()
    known: dict[tuple[UUID | None, str], UUID] = {
        (parent, _norm(title)): topic_id for topic_id, parent, title in rows
    }
    counters = {"topics_created": 0, "topics_matched": 0,
                "resources_created": 0, "resources_skipped": 0}

    async def sync_resources(topic_id: UUID, seeds: list) -> None:
        rows = (
            await session.execute(
                select(LearningResource.url, Entity.title)
                .join(Entity, Entity.id == LearningResource.id)
                .where(LearningResource.topic_id == topic_id)
            )
        ).all()
        # URL varsa kimlik URL'dir; yoksa baslik. Ayni kaynak iki kez eklenmez.
        seen = {(url or _norm(title)) for url, title in rows}
        position = len(rows)
        for seed in seeds:
            key = seed.url or _norm(seed.title)
            if key in seen:
                counters["resources_skipped"] += 1
                continue
            seen.add(key)
            entity = await create_entity(
                session, type=LearningResource.ENTITY_TYPE, title=seed.title,
                search_text=" ".join(filter(None, [seed.url, seed.note])),
            )
            session.add(
                LearningResource(
                    id=entity.id, topic_id=topic_id, url=seed.url,
                    kind=seed.kind, position=position, note=seed.note,
                )
            )
            await link(session, topic_id, entity.id, "learns_from")
            position += 1
            counters["resources_created"] += 1

    async def walk(seeds: list, parent: UUID | None) -> None:
        for position, seed in enumerate(seeds):
            key = (parent, _norm(seed.title))
            topic_id = known.get(key)
            if topic_id is None:
                entity = await create_entity(session, type="study_topic", title=seed.title)
                session.add(
                    StudyTopic(
                        id=entity.id, area_id=area_id, parent_id=parent,
                        status=seed.status, target_min=seed.target_min,
                        position=position,
                    )
                )
                await session.flush()
                topic_id = entity.id
                known[key] = topic_id
                counters["topics_created"] += 1
            else:
                counters["topics_matched"] += 1
            await sync_resources(topic_id, seed.resources)
            await walk(seed.children, topic_id)

    await walk(data.topics, None)
    await log_event(
        session, verb="learning.imported", entity_id=area_id, entity_type="study_area",
        payload={"area": area_title, **counters},
    )
    await session.commit()
    return {"area_id": area_id, "area_title": area_title, **counters}
