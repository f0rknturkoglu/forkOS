from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.media import service
from app.modules.media.models import KINDS, STATUSES
from app.modules.media.schemas import (
    MediaItemIn,
    MediaItemOut,
    MediaItemUpdate,
    MediaStats,
    MetadataResult,
)

router = APIRouter(tags=["media"])


def _check_kind(kind: str) -> None:
    if kind not in KINDS:
        raise HTTPException(422, f"kind su olmali: {KINDS}")


def _check_status(status: str) -> None:
    if status not in STATUSES:
        raise HTTPException(422, f"status su olmali: {STATUSES}")


@router.get("/media", response_model=list[MediaItemOut])
async def list_media(
    kind: str | None = None,
    status: str | None = None,
    q: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    return await service.list_items(session, kind=kind, status=status, q=q)


@router.get("/media/stats", response_model=MediaStats)
async def media_stats(session: AsyncSession = Depends(get_session)):
    return await service.stats(session)


@router.get("/media/search", response_model=list[MetadataResult])
async def search_metadata(
    q: str = Query(min_length=2),
    kind: str = Query(...),
    session: AsyncSession = Depends(get_session),
):
    """Metadata hizmetlerinde ara (OpenLibrary / AniList / TMDB). Yalnizca OKUMA."""
    _check_kind(kind)
    try:
        return await service.search_metadata(session, q, kind)
    except RuntimeError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/media", response_model=MediaItemOut, status_code=201)
async def create_media(body: MediaItemIn, session: AsyncSession = Depends(get_session)):
    return await service.create_item(session, body)


@router.patch("/media/{item_id}", response_model=MediaItemOut)
async def update_media(
    item_id: uuid.UUID, body: MediaItemUpdate, session: AsyncSession = Depends(get_session),
):
    if body.status is not None:
        _check_status(body.status)
    item = await service.update_item(session, item_id, body)
    if item is None:
        raise HTTPException(404)
    return item


@router.delete("/media/{item_id}", status_code=204)
async def delete_media(item_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    if not await service.delete_item(session, item_id):
        raise HTTPException(404)
