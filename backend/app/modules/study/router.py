from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.study import service
from app.modules.study.schemas import AreaIn, TopicIn, TopicPatch

router = APIRouter(tags=["study"])


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
