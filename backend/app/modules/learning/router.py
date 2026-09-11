from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.learning import service
from app.modules.learning.schemas import (
    AreaIn,
    AreaPatch,
    AttachBookmarkIn,
    CourseIn,
    CourseOut,
    CoursePatch,
    ImportPreviewOut,
    ResourceIn,
    ResourceOut,
    ResourcePatch,
    ReviewQueueOut,
    StalePageOut,
    StudyAreaOut,
    StudyStatsOut,
    StudyTopicDetailOut,
    StudyTopicLegacyNode,
    StudyTopicOut,
    StudyTreeOut,
    TopicImpactOut,
    TopicImportIn,
    TopicImportOut,
    TopicIn,
    TopicMoveIn,
    TopicPatch,
    TopicProgressOut,
    TopicReviewIn,
    TopicReviewOut,
    TopicTodoIn,
    TopicTodoOut,
)
from app.modules.learning.service import LearningCommandError, LearningNotFoundError

router = APIRouter(tags=["learning"])


def _error(exc: LearningCommandError) -> HTTPException:
    """Is kurali ihlali 422; kayit yok 404 (eski 'sessiz 0' davranisi kalkti)."""
    status = 404 if isinstance(exc, LearningNotFoundError) else 422
    return HTTPException(status, str(exc))


# ---------------------------------------------------------------------------
# Kurslar
# ---------------------------------------------------------------------------


@router.get("/courses", response_model=list[CourseOut])
async def courses(
    include_archived: bool = False,
    area_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
):
    return await service.list_courses(
        session, include_archived=include_archived, area_id=area_id
    )


@router.post("/courses", response_model=CourseOut, status_code=201)
async def add_course(body: CourseIn, session: AsyncSession = Depends(get_session)):
    try:
        return await service.create_course(session, body)
    except LearningCommandError as exc:
        raise _error(exc) from exc


@router.patch("/courses/{course_id}", response_model=CourseOut)
async def patch_course(
    course_id: UUID, body: CoursePatch, session: AsyncSession = Depends(get_session)
):
    try:
        result = await service.patch_course(session, course_id, body)
    except LearningCommandError as exc:
        raise _error(exc) from exc
    if result is None:
        raise HTTPException(404, "kurs bulunamadi")
    return result


@router.delete("/courses/{course_id}", status_code=204)
async def delete_course(course_id: UUID, session: AsyncSession = Depends(get_session)):
    if not await service.delete_course(session, course_id):
        raise HTTPException(404, "kurs bulunamadi")


# ---------------------------------------------------------------------------
# Calisma alanlari
# ---------------------------------------------------------------------------


@router.get("/study/areas", response_model=list[StudyAreaOut])
async def areas(
    include_stats: bool = False,
    session: AsyncSession = Depends(get_session),
):
    return await service.list_areas(session, include_stats=include_stats)


@router.post("/study/areas", response_model=StudyAreaOut, status_code=201)
async def add_area(body: AreaIn, session: AsyncSession = Depends(get_session)):
    return await service.create_area(session, body)


@router.get("/study/areas/{area_id}/tree", response_model=StudyTreeOut)
async def area_tree(
    area_id: UUID,
    q: str | None = Query(None, max_length=200),
    status: str | None = Query(None),
    include_resources: bool = False,
    session: AsyncSession = Depends(get_session),
):
    result = await service.area_tree(
        session, area_id, q=q, status=status, include_resources=include_resources
    )
    if result is None:
        raise HTTPException(404, "alan bulunamadi")
    return result


@router.patch("/study/areas/{area_id}", response_model=StudyAreaOut)
async def patch_area(
    area_id: UUID, body: AreaPatch, session: AsyncSession = Depends(get_session)
):
    result = await service.patch_area(session, area_id, body)
    if result is None:
        raise HTTPException(404, "alan bulunamadi")
    return result


@router.delete("/study/areas/{area_id}", status_code=204)
async def delete_area(area_id: UUID, session: AsyncSession = Depends(get_session)):
    if not await service.delete_area(session, area_id):
        raise HTTPException(404, "alan bulunamadi")


# ---------------------------------------------------------------------------
# Konular
# ---------------------------------------------------------------------------


@router.get("/study/topics", response_model=list[StudyTopicLegacyNode])
async def topics(area_id: UUID, session: AsyncSession = Depends(get_session)):
    """Alan agaci (ic ice, ESKI sekil -- yol degismedi)."""
    try:
        return await service.tree(session, area_id)
    except LearningCommandError as exc:
        raise _error(exc) from exc


@router.post("/study/topics", response_model=StudyTopicOut, status_code=201)
async def add_topic(body: TopicIn, session: AsyncSession = Depends(get_session)):
    try:
        return await service.create_topic(session, body)
    except LearningCommandError as exc:
        raise _error(exc) from exc


@router.get("/study/topics/{topic_id}", response_model=StudyTopicDetailOut)
async def topic(topic_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await service.get_topic(session, topic_id)
    if result is None:
        raise HTTPException(404, "konu bulunamadi")
    return result


@router.patch("/study/topics/{topic_id}", response_model=StudyTopicOut)
async def patch_topic(
    topic_id: UUID, body: TopicPatch, session: AsyncSession = Depends(get_session)
):
    try:
        result = await service.patch_topic(session, topic_id, body)
    except LearningCommandError as exc:
        raise _error(exc) from exc
    if result is None:
        raise HTTPException(404, "konu bulunamadi")
    return result


@router.post("/study/topics/{topic_id}/move", response_model=StudyTopicOut)
async def move_topic(
    topic_id: UUID, body: TopicMoveIn, session: AsyncSession = Depends(get_session)
):
    try:
        result = await service.move_topic(session, topic_id, body)
    except LearningCommandError as exc:
        raise _error(exc) from exc
    if result is None:
        raise HTTPException(404, "konu bulunamadi")
    return result


@router.get("/study/topics/{topic_id}/impact", response_model=TopicImpactOut)
async def topic_impact(topic_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await service.topic_impact(session, topic_id)
    if result is None:
        raise HTTPException(404, "konu bulunamadi")
    return result


@router.get("/study/topics/{topic_id}/progress", response_model=TopicProgressOut)
async def topic_progress(topic_id: UUID, session: AsyncSession = Depends(get_session)):
    try:
        return await service.topic_progress(session, topic_id)
    except LearningCommandError as exc:
        raise _error(exc) from exc


@router.delete("/study/topics/{topic_id}", status_code=204)
async def delete_topic(topic_id: UUID, session: AsyncSession = Depends(get_session)):
    if not await service.delete_topic(session, topic_id):
        raise HTTPException(404, "konu bulunamadi")


@router.post("/study/topics/{topic_id}/review", response_model=TopicReviewOut)
async def review_topic(
    topic_id: UUID, body: TopicReviewIn, session: AsyncSession = Depends(get_session)
):
    result = await service.review_topic(session, topic_id, body)
    if result is None:
        raise HTTPException(404, "konu bulunamadi")
    return result


@router.post("/study/topics/{topic_id}/todos", response_model=TopicTodoOut, status_code=201)
async def create_topic_todo(
    topic_id: UUID,
    body: TopicTodoIn | None = None,
    session: AsyncSession = Depends(get_session),
):
    """Konudan gorev + `prepares_for` bagini tek istekte uretir (Faz 17).

    Idempotent: konunun acik gorevi varsa yenisi acilmaz (`created: false`);
    `force=true` ikinci gorevi uretir. Go vde ortak TodoIn sozlesmesidir.
    """
    try:
        return await service.create_todo_for_topic(session, topic_id, body)
    except LearningCommandError as exc:
        raise _error(exc) from exc


# ---------------------------------------------------------------------------
# Tekrar / istatistik / stale
# ---------------------------------------------------------------------------


@router.get("/study/review", response_model=ReviewQueueOut)
async def review_queue(
    window: int = Query(14, ge=1, le=365),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    return await service.topic_review_queue(session, window_days=window, limit=limit)


@router.get("/study/stats", response_model=StudyStatsOut)
async def study_stats(
    range_: str = Query("week", alias="range", pattern="^(week|month|90d|year|all)$"),
    session: AsyncSession = Depends(get_session),
):
    return await service.study_stats(session, value=range_)


@router.get("/study/stale", response_model=StalePageOut)
async def stale(
    days: int = Query(service.DEFAULT_STALE_DAYS, ge=7, le=365),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    area_id: UUID | None = None,
    include_done: bool = False,
    session: AsyncSession = Depends(get_session),
):
    return await service.stale(
        session,
        days=days,
        limit=limit,
        offset=offset,
        area_id=area_id,
        include_done=include_done,
    )


# ---------------------------------------------------------------------------
# Kaynaklar
# ---------------------------------------------------------------------------


@router.get("/study/topics/{topic_id}/resources", response_model=list[ResourceOut])
async def topic_resources(topic_id: UUID, session: AsyncSession = Depends(get_session)):
    try:
        return await service.list_resources(session, topic_id)
    except LearningCommandError as exc:
        raise _error(exc) from exc


@router.post("/study/topics/{topic_id}/resources", response_model=ResourceOut, status_code=201)
async def add_resource(
    topic_id: UUID, body: ResourceIn, session: AsyncSession = Depends(get_session)
):
    try:
        return await service.create_resource(session, topic_id, body)
    except LearningCommandError as exc:
        raise _error(exc) from exc


@router.post("/study/resources/attach-bookmark", response_model=ResourceOut)
async def attach_bookmark(
    body: AttachBookmarkIn, session: AsyncSession = Depends(get_session)
):
    """Yer imini ogrenme kaynagina baglar (kopyalamaz; ayni bag idempotent)."""
    try:
        return await service.attach_bookmark(session, body.topic_id, body.bookmark_id)
    except LearningCommandError as exc:
        raise _error(exc) from exc


@router.get("/learning/resources/{resource_id}", response_model=ResourceOut)
async def get_resource(resource_id: UUID, session: AsyncSession = Depends(get_session)):
    """Tek kaynak (deep-link) + `last_opened_at` damgasi."""
    result = await service.get_resource(session, resource_id)
    if result is None:
        raise HTTPException(404, "kaynak bulunamadi")
    return result


@router.patch("/learning/resources/{resource_id}", response_model=ResourceOut)
async def patch_resource(
    resource_id: UUID, body: ResourcePatch, session: AsyncSession = Depends(get_session)
):
    try:
        result = await service.patch_resource(session, resource_id, body)
    except LearningCommandError as exc:
        raise _error(exc) from exc
    if result is None:
        raise HTTPException(404, "kaynak bulunamadi")
    return result


@router.delete("/learning/resources/{resource_id}", status_code=204)
async def delete_resource(resource_id: UUID, session: AsyncSession = Depends(get_session)):
    if not await service.delete_resource(session, resource_id):
        raise HTTPException(404, "kaynak bulunamadi")


# ---------------------------------------------------------------------------
# Ice aktarma
# ---------------------------------------------------------------------------


@router.post("/study/import/preview", response_model=ImportPreviewOut)
async def import_preview(body: TopicImportIn, session: AsyncSession = Depends(get_session)):
    """Yazmadan ne olacagini soyler (creates/updates/matches/sayaclar)."""
    try:
        return await service.import_preview(session, body)
    except LearningCommandError as exc:
        raise _error(exc) from exc


@router.post("/study/import", response_model=TopicImportOut, status_code=201)
async def import_topics(body: TopicImportIn, session: AsyncSession = Depends(get_session)):
    """Konu agacini JSON'dan kurar/gunceller (atomik: tek commit).

    Yeniden yuklenebilir: ayni baslik ayni ebeveyn altinda eslesir, kopya
    olusmaz. `prune=true` agacta olmayani SILMEZ, arsivler.
    """
    try:
        return await service.import_topics(session, body)
    except LearningCommandError as exc:
        raise _error(exc) from exc
