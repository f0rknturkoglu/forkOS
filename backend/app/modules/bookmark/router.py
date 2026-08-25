from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.bookmark import service
from app.modules.bookmark.models import COLLECTIONS, READ_STATUSES
from app.modules.bookmark.schemas import (
    BookmarkOut,
    BookmarkStats,
    BookmarkUpdate,
    CaptureIn,
    CaptureResult,
)

router = APIRouter(tags=["bookmark"])


def _check_collection(collection: str) -> None:
    if collection not in COLLECTIONS:
        raise HTTPException(422, f"collection su olmali: {COLLECTIONS}")


@router.post("/capture", response_model=CaptureResult, status_code=201)
async def capture(body: CaptureIn, session: AsyncSession = Depends(get_session)):
    """Extension ve quick capture giris noktasi. Idempotent (client_uuid).

    Ayni URL ikinci kez gelirse 409 DEGIL, 201 + duplicate=true doner --
    extension popup'i "zaten kayitli, tasimak ister misin?" gosterir.
    """
    _check_collection(body.collection)

    bookmark, replayed, prior = await service.capture(session, body)
    if replayed:
        return CaptureResult(id=bookmark.id, duplicate=True, existing_id=bookmark.id,
                             collection=bookmark.collection)
    return CaptureResult(id=bookmark.id, duplicate=prior is not None,
                         existing_id=prior.id if prior else None,
                         collection=bookmark.collection)


@router.get("/bookmarks", response_model=list[BookmarkOut])
async def list_bookmarks(
    collection: str | None = None,
    read_status: str | None = None,
    favorite: bool | None = None,
    source: str | None = None,
    q: str | None = None,
    tag: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    return await service.list_bookmarks(
        session, collection=collection, read_status=read_status, favorite=favorite,
        source=source, q=q, tag=tag, limit=limit, offset=offset,
    )


@router.get("/bookmarks/stats", response_model=BookmarkStats)
async def bookmark_stats(session: AsyncSession = Depends(get_session)):
    return await service.stats(session)


@router.get("/bookmarks/{bookmark_id}", response_model=BookmarkOut)
async def get_bookmark(bookmark_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    bookmark = await service.get(session, bookmark_id)
    if bookmark is None:
        raise HTTPException(404)
    return bookmark


@router.patch("/bookmarks/{bookmark_id}", response_model=BookmarkOut)
async def update_bookmark(
    bookmark_id: uuid.UUID,
    body: BookmarkUpdate,
    session: AsyncSession = Depends(get_session),
):
    if body.collection is not None:
        _check_collection(body.collection)
    if body.read_status is not None and body.read_status not in READ_STATUSES:
        raise HTTPException(422, f"read_status su olmali: {READ_STATUSES}")
    if await service.update(session, bookmark_id, body) is None:
        raise HTTPException(404)
    return await service.get(session, bookmark_id)


@router.patch("/bookmarks/{bookmark_id}/collection", response_model=BookmarkOut)
async def move_bookmark(
    bookmark_id: uuid.UUID,
    collection: str = Query(...),
    session: AsyncSession = Depends(get_session),
):
    """Surukle-birak buraya duser: tek UPDATE, link ve event kopmaz."""
    _check_collection(collection)
    if await service.move(session, bookmark_id, collection) is None:
        raise HTTPException(404)
    return await service.get(session, bookmark_id)


@router.delete("/bookmarks/{bookmark_id}", status_code=204)
async def delete_bookmark(bookmark_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    if not await service.delete(session, bookmark_id):
        raise HTTPException(404)
