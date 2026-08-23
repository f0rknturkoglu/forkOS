from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.media import service
from app.modules.media import sync as media_sync
from app.modules.media.artwork import ArtworkStore
from app.modules.media.models import KINDS, STATUSES
from app.modules.media.schemas import (
    MediaCollectionIn,
    MediaCollectionOut,
    MediaCollectionUpdate,
    MediaConsumptionIn,
    MediaConsumptionOut,
    MediaCycleOut,
    MediaCycleStart,
    MediaDashboardOut,
    MediaDetailOut,
    MediaItemIn,
    MediaItemOut,
    MediaItemUpdate,
    MediaPageOut,
    MediaStats,
    MediaUnitOut,
    MetadataResult,
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
    monitored: bool | None = None,
    trashed: bool = False,
    sort: Literal["updated", "created", "title", "score", "progress"] = "updated",
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
            monitored=monitored,
            trashed=trashed,
            sort=sort,
            cursor=cursor,
            limit=limit,
        )
    except service.MediaCommandError as exc:
        raise _command_error(exc) from exc


@router.get("/media/stats", response_model=MediaStats)
async def media_stats(session: AsyncSession = Depends(get_session)):
    return await service.stats(session)


@router.get("/media/dashboard", response_model=MediaDashboardOut)
async def media_dashboard(session: AsyncSession = Depends(get_session)):
    return await service.dashboard(session)


@router.get("/media/upcoming", response_model=list[MediaUnitOut])
async def media_upcoming(
    days: int = Query(30, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
):
    return await service.upcoming_units(session, days)


@router.get("/media/search", response_model=list[MetadataResult])
async def search_metadata(
    q: str = Query(min_length=2),
    kind: str = Query(...),
    provider: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    _check_kind(kind)
    try:
        return await service.search_metadata(session, q, kind, provider_id=provider)
    except RuntimeError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/media/providers")
async def media_providers(session: AsyncSession = Depends(get_session)):
    return await media_sync.provider_statuses(session)


@router.post("/media/sync")
async def queue_media_sync(
    provider: str | None = None,
    item_id: uuid.UUID | None = None,
    session: AsyncSession = Depends(get_session),
):
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


@router.get("/media/collections", response_model=list[MediaCollectionOut])
async def collections(session: AsyncSession = Depends(get_session)):
    return await service.list_collections(session)


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
    if await service.add_collection_item(session, collection_id, item_id) is None:
        raise HTTPException(404)
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


@router.get("/media/{item_id}/consumptions", response_model=list[MediaConsumptionOut])
async def media_consumptions(item_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    if await service.get_item(session, item_id) is None:
        raise HTTPException(404)
    return await service.list_consumptions(session, item_id)
