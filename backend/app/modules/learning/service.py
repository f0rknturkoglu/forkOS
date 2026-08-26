from sqlalchemy import select

from app.core import tags as tag_svc
from app.core.entity import create_entity, delete_entity, touch_entity
from app.core.events import log_event
from app.core.models import Entity
from app.core.time import local_today
from app.modules.bookmark.models import Bookmark
from app.modules.bookmark.service import _to_out
from app.modules.learning.models import Course


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
