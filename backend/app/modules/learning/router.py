from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.learning import service
from app.modules.learning.models import Course
from app.modules.learning.schemas import (
    AreaIn,
    CourseIn,
    CoursePatch,
    ResourceIn,
    ResourcePatch,
    TopicImportIn,
    TopicImportOut,
    TopicIn,
    TopicPatch,
    TopicTodoIn,
)

router = APIRouter(tags=["learning"])


@router.get("/courses")
async def courses(s: AsyncSession = Depends(get_session)):
    return await service.list_items(s, Course)


@router.post("/courses", status_code=201)
async def add_course(b: CourseIn, s: AsyncSession = Depends(get_session)):
    return await service.create_item(s, Course, b)


@router.patch("/courses/{id}")
async def patch_course(id: UUID, b: CoursePatch, s: AsyncSession = Depends(get_session)):
    r = await service.patch_item(s, Course, id, b)
    if not r:
        raise HTTPException(404)
    return r


@router.delete("/courses/{id}", status_code=204)
async def delete_course(id: UUID, session: AsyncSession = Depends(get_session)):
    if not await service.delete_item(session, Course, id):
        raise HTTPException(404)

# Calisma alanlari / konulari (Faz 12: eski study modulu burada).
# Yollar DEGISMEDI: /study/* aynen calisir.


@router.get("/study/areas")
async def areas(session: AsyncSession = Depends(get_session)):
    return await service.list_areas(session)


@router.post("/study/areas", status_code=201)
async def add_area(body: AreaIn, session: AsyncSession = Depends(get_session)):
    return await service.create_area(session, body)


@router.get("/study/topics")
async def topics(area_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.tree(session, area_id)


@router.post("/study/topics", status_code=201)
async def add_topic(body: TopicIn, session: AsyncSession = Depends(get_session)):
    return await service.create_topic(session, body)


@router.get("/study/topics/{topic_id}")
async def topic(topic_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await service.get_topic(session, topic_id)
    if result is None:
        raise HTTPException(404)
    return result


@router.patch("/study/topics/{topic_id}")
async def patch_topic(
    topic_id: UUID, body: TopicPatch, session: AsyncSession = Depends(get_session)
):
    result = await service.patch_topic(session, topic_id, body)
    if result is None:
        raise HTTPException(404)
    return result


@router.get("/study/topics/{topic_id}/stats")
async def stats(topic_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.topic_stats(session, topic_id)


@router.get("/study/stale")
async def stale(days: int = 21, session: AsyncSession = Depends(get_session)):
    return await service.stale(session, days)


@router.delete("/study/topics/{topic_id}", status_code=204)
async def delete_topic(topic_id: UUID, session: AsyncSession = Depends(get_session)):
    if not await service.delete_topic(session, topic_id):
        raise HTTPException(404, "konu bulunamadi")


@router.delete("/study/areas/{area_id}", status_code=204)
async def delete_area(area_id: UUID, session: AsyncSession = Depends(get_session)):
     if not await service.delete_area(session, area_id):
         raise HTTPException(404, "alan bulunamadi")


@router.post("/study/topics/{topic_id}/todos", status_code=201)
async def create_topic_todo(
    topic_id: UUID,
    body: TopicTodoIn | None = None,
    session: AsyncSession = Depends(get_session),
):
    """Konudan gorev + `prepares_for` bagini tek istekte uretir (Faz 17).

    Govde ortak TodoIn sozlesmesidir (Faz 31): "bugune al" tercihi
    plan_day olarak buradan gelir; title/description konudan sabit kalir.
    """
    try:
        return await service.create_todo_for_topic(session, topic_id, body)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


# Kaynaklar: konunun altindaki URL/materyal listesi. Tamamlananlar konunun
# ilerlemesini uretir (service.topic_progress).


@router.get("/study/topics/{topic_id}/resources")
async def topic_resources(topic_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.list_resources(session, topic_id)


@router.post("/study/topics/{topic_id}/resources", status_code=201)
async def add_resource(
    topic_id: UUID, body: ResourceIn, session: AsyncSession = Depends(get_session)
):
    try:
        return await service.create_resource(session, topic_id, body)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/study/topics/{topic_id}/progress")
async def topic_progress(topic_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.topic_progress(session, topic_id)


@router.patch("/learning/resources/{resource_id}")
async def patch_resource(
    resource_id: UUID, body: ResourcePatch, session: AsyncSession = Depends(get_session)
):
    result = await service.patch_resource(session, resource_id, body)
    if result is None:
        raise HTTPException(404, "kaynak bulunamadi")
    return result


@router.delete("/learning/resources/{resource_id}", status_code=204)
async def delete_resource(resource_id: UUID, session: AsyncSession = Depends(get_session)):
    if not await service.delete_resource(session, resource_id):
        raise HTTPException(404, "kaynak bulunamadi")


@router.post("/study/import", response_model=TopicImportOut, status_code=201)
async def import_topics(body: TopicImportIn, session: AsyncSession = Depends(get_session)):
    """Konu agacini JSON'dan kurar (disarida uretilmis olabilir).

    Yeniden yuklenebilir: ayni baslik ayni ebeveyn altinda eslesir, kopya
    olusmaz. Var olan konulari SILMEZ -- ekler ve gunceller.
    """
    try:
        return await service.import_topics(session, body)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
