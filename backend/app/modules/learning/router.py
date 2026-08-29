from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.learning import service
from app.modules.learning.models import Course
from app.modules.learning.schemas import AreaIn, CourseIn, CoursePatch, TopicIn, TopicPatch

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


@router.get("/learning/queue")
async def queue(kind: str | None = None, s: AsyncSession = Depends(get_session)):
    return await service.queue(s, kind)


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
async def create_topic_todo(topic_id: UUID, session: AsyncSession = Depends(get_session)):
     """Konudan gorev + `prepares_for` bagini tek istekte uretir (Faz 17)."""
     try:
         return await service.create_todo_for_topic(session, topic_id)
     except ValueError as exc:
         raise HTTPException(400, str(exc)) from exc
