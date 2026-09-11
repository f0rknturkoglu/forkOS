from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.media import service
from app.modules.media import sync as media_sync
from app.modules.media.artwork import ArtworkStore
from app.modules.media.models import KINDS, STATUSES
from app.modules.media.schemas import (
    GlobalMetadataSearchOut,
    MediaArtworkPruneOut,
    MediaArtworkStatsOut,
    MediaCollectionDetailOut,
    MediaCollectionIn,
    MediaCollectionOut,
    MediaCollectionUpdate,
    MediaConsumptionIn,
    MediaConsumptionOut,
    MediaConsumptionPageOut,
    MediaCycleOut,
    MediaCycleStart,
    MediaDashboardOut,
    MediaDetailOut,
    MediaItemIn,
    MediaItemOut,
    MediaItemUpdate,
    MediaPageOut,
    MediaProviderStatusOut,
    MediaStats,
    MediaSyncBatchOut,
    MediaSyncIdleOut,
    MediaUpcomingPageOut,
)

router = APIRouter(tags=["media"])


def _check_kind(kind: str) -> None:
    if kind not in KINDS:
        raise HTTPException(422, f"kind su olmali: {KINDS}")


def _check_status(status: str) -> None:
    if status not in STATUSES:
        raise HTTPException(422, f"status su olmali: {STATUSES}")


def _command_error(exc: ValueError) -> HTTPException:
    status = 409 if isinstance(exc, service.MediaConflictError) else 422
    return HTTPException(status, str(exc))


@router.get("/media", response_model=MediaPageOut)
async def list_media(
    kind: str | None = None,
    status: str | None = None,
    q: str | None = None,
    collection_id: uuid.UUID | None = None,
    tag: str | None = None,
    owned: bool | None = None,
    favorite: bool | None = None,
    monitored: bool | None = None,
    provider: str | None = None,
    trashed: bool = False,
    sort: Literal["updated", "created", "title", "score", "progress", "relevance"] = "updated",
    cursor: str | None = None,
    limit: int = Query(48, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    if kind:
        _check_kind(kind)
    if status:
        _check_status(status)
    try:
        return await service.list_items(
            session,
            kind=kind,
            status=status,
            q=q,
            collection_id=collection_id,
            tag=tag,
            owned=owned,
            favorite=favorite,
            monitored=monitored,
            provider=provider,
            trashed=trashed,
            sort=sort,
            cursor=cursor,
            limit=limit,
        )
    except service.MediaCommandError as exc:
        raise _command_error(exc) from exc


@router.get("/media/stats", response_model=MediaStats)
async def media_stats(
    range_: Literal["week", "month", "90d", "year", "all"] = Query("all", alias="range"),
    session: AsyncSession = Depends(get_session),
):
    return await service.stats(session, range_=range_)


@router.get("/media/dashboard", response_model=MediaDashboardOut)
async def media_dashboard(
    range_: Literal["week", "month", "90d", "year", "all"] = Query("all", alias="range"),
    recent_limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """Istatistik ekraninin tek istegi (ozet + devam + yaklasan + son tuketimler)."""
    return await service.dashboard(session, range_=range_, recent_limit=recent_limit)


@router.get("/media/upcoming", response_model=MediaUpcomingPageOut)
async def media_upcoming(
    days: int | None = Query(None, ge=1, le=365),
    kind: str | None = None,
    provider: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    if kind:
        _check_kind(kind)
    return await service.list_upcoming(session, days=days, kind=kind, provider=provider)


@router.get("/media/search/global", response_model=GlobalMetadataSearchOut)
async def search_all_metadata(
    q: str = Query(min_length=2),
    kind: str | None = None,
    provider: str | None = None,
    limit: int = Query(6, ge=1, le=20),
    session: AsyncSession = Depends(get_session),
):
    if kind:
        _check_kind(kind)
    try:
        return await service.search_all_metadata(session, q, kind=kind, provider=provider, limit=limit)
    except service.MediaCommandError as exc:
        raise _command_error(exc) from exc


@router.get("/media/providers", response_model=list[MediaProviderStatusOut])
async def media_providers(session: AsyncSession = Depends(get_session)):
    return await media_sync.provider_statuses(session)


@router.post("/media/sync", response_model=MediaSyncBatchOut | MediaSyncIdleOut)
async def queue_media_sync(
    background: BackgroundTasks,
    provider: str | None = None,
    item_id: uuid.UUID | None = None,
    session: AsyncSession = Depends(get_session),
):
    from app.worker.jobs import drain_source_sync_batches

    try:
        batch = await media_sync.queue_sync(session, provider_id=provider, item_id=item_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if batch is None:
        return {
            "scope": "media",
            "status": "idle",
            "source_ids": [],
            "total_sources": 0,
        }
    background.add_task(drain_source_sync_batches)
    return batch


@router.get("/media/assets/{asset_name}")
async def media_asset(asset_name: str):
    path = ArtworkStore().resolve(asset_name)
    if path is None:
        raise HTTPException(404)
    return FileResponse(
        path,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@router.get("/media/artwork/stats", response_model=MediaArtworkStatsOut)
async def media_artwork_stats():
    return await service.artwork_stats()


@router.post("/media/artwork/prune", response_model=MediaArtworkPruneOut)
async def media_artwork_prune(session: AsyncSession = Depends(get_session)):
    return await service.prune_artwork(session)


@router.get("/media/artwork/proxy")
async def media_artwork_proxy(url: str = Query(min_length=8)):
    """Uzak saglayici gorselini yerel onbellege alip sunar (local-only gizlilik)."""
    try:
        path = await service.cache_artwork(url)
    except service.MediaCommandError as exc:
        raise _command_error(exc) from exc
    if path is None:
        raise HTTPException(404)
    return FileResponse(
        path,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@router.get("/media/collections", response_model=list[MediaCollectionOut])
async def collections(session: AsyncSession = Depends(get_session)):
    return await service.list_collections(session)


@router.get("/media/collections/{collection_id}", response_model=MediaCollectionDetailOut)
async def collection_detail(
    collection_id: uuid.UUID,
    q: str | None = None,
    sort: Literal["updated", "created", "title", "score", "progress"] = "updated",
    cursor: str | None = None,
    limit: int = Query(48, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    result = await service.collection_detail(
        session, collection_id, q=q, sort=sort, cursor=cursor, limit=limit
    )
    if result is None:
        raise HTTPException(404)
    return result


@router.post("/media/collections", response_model=MediaCollectionOut, status_code=201)
async def create_collection(body: MediaCollectionIn, session: AsyncSession = Depends(get_session)):
    return await service.create_collection(session, body)


@router.patch("/media/collections/{collection_id}", response_model=MediaCollectionOut)
async def update_collection(
    collection_id: uuid.UUID,
    body: MediaCollectionUpdate,
    session: AsyncSession = Depends(get_session),
):
    result = await service.update_collection(session, collection_id, body)
    if result is None:
        raise HTTPException(404)
    return result


@router.delete("/media/collections/{collection_id}", status_code=204)
async def delete_collection(collection_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    if not await service.delete_collection(session, collection_id):
        raise HTTPException(404)
    return Response(status_code=204)


@router.post("/media/collections/{collection_id}/items/{item_id}", status_code=204)
async def add_collection_item(
    collection_id: uuid.UUID,
    item_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await service.add_collection_item(session, collection_id, item_id)
    if result is None:
        raise HTTPException(404)
    if result is False:
        raise HTTPException(409, "Kayit zaten bu koleksiyonda")
    return Response(status_code=204)


@router.delete("/media/collections/{collection_id}/items/{item_id}", status_code=204)
async def remove_collection_item(
    collection_id: uuid.UUID,
    item_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    if await service.remove_collection_item(session, collection_id, item_id) is None:
        raise HTTPException(404)
    return Response(status_code=204)


@router.post("/media", response_model=MediaItemOut, status_code=201)
async def create_media(body: MediaItemIn, session: AsyncSession = Depends(get_session)):
    try:
        return await service.create_item(session, body)
    except service.MediaConflictError as exc:
        raise _command_error(exc) from exc


@router.get("/media/{item_id}", response_model=MediaDetailOut)
async def media_detail(item_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    result = await service.get_detail(session, item_id)
    if result is None:
        raise HTTPException(404)
    return result


@router.patch("/media/{item_id}", response_model=MediaItemOut)
async def update_media(
    item_id: uuid.UUID,
    body: MediaItemUpdate,
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await service.update_item(session, item_id, body)
    except (service.MediaConflictError, service.MediaCommandError) as exc:
        raise _command_error(exc) from exc
    if result is None:
        raise HTTPException(404)
    return result


@router.delete("/media/{item_id}/permanent", status_code=204)
async def permanent_delete_media(item_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    try:
        if not await service.permanent_delete_item(session, item_id):
            raise HTTPException(404)
    except service.MediaConflictError as exc:
        raise _command_error(exc) from exc
    return Response(status_code=204)


@router.delete("/media/{item_id}", response_model=MediaItemOut)
async def trash_media(item_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    result = await service.trash_item(session, item_id)
    if result is None:
        raise HTTPException(404)
    return result


@router.post("/media/{item_id}/restore", response_model=MediaItemOut)
async def restore_media(item_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    result = await service.restore_item(session, item_id)
    if result is None:
        raise HTTPException(404)
    return result


@router.get("/media/{item_id}/cycles", response_model=list[MediaCycleOut])
async def media_cycles(item_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    if await service.get_item(session, item_id) is None:
        raise HTTPException(404)
    return await service.list_cycles(session, item_id)


@router.post("/media/{item_id}/cycles", response_model=MediaCycleOut, status_code=201)
async def start_media_cycle(
    item_id: uuid.UUID,
    body: MediaCycleStart,
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await service.start_cycle(session, item_id, body)
    except service.MediaConflictError as exc:
        raise _command_error(exc) from exc
    if result is None:
        raise HTTPException(404)
    return result


@router.post(
    "/media/{item_id}/consumptions",
    response_model=MediaConsumptionOut,
    status_code=201,
)
async def consume_media(
    item_id: uuid.UUID,
    body: MediaConsumptionIn,
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await service.consume(session, item_id, body)
    except (service.MediaConflictError, service.MediaCommandError) as exc:
        raise _command_error(exc) from exc
    if result is None:
        raise HTTPException(404)
    return result


@router.get("/media/{item_id}/consumptions", response_model=MediaConsumptionPageOut)
async def media_consumptions(
    item_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    if await service.get_item(session, item_id) is None:
        raise HTTPException(404)
    return await service.list_consumptions(session, item_id, limit=limit, cursor=cursor)
