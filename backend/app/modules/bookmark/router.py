from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.integrations.obsidian import service as obsidian_service
from app.integrations.obsidian.models import VaultItem
from app.integrations.obsidian.router import vault_http_error
from app.modules.bookmark import service
from app.modules.bookmark.models import COLLECTIONS, READ_STATUSES
from app.modules.bookmark.schemas import (
    BookmarkBulkActionIn,
    BookmarkBulkActionResult,
    BookmarkFullTextOut,
    BookmarkHighlightIn,
    BookmarkHighlightOut,
    BookmarkOut,
    BookmarkProgressUpdate,
    BookmarkStats,
    BookmarkUpdate,
    CaptureIn,
    CaptureResult,
    ConvertToTaskIn,
    CreateSourceNoteIn,
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


@router.get("/bookmarks/export")
async def export_bookmarks(session: AsyncSession = Depends(get_session)):
    """Netscape Bookmark HTML formatinda kutuphane dosyasini indirir."""
    html_content = await service.export_bookmarks(session)
    return Response(
        content=html_content,
        media_type="text/html",
        headers={"Content-Disposition": 'attachment; filename="forkos-bookmarks.html"'},
    )


@router.post("/bookmarks/import")
async def import_bookmarks(
    body: dict,
    session: AsyncSession = Depends(get_session),
):
    """Netscape HTML veya Pocket JSON formatinda yer imi yukler."""
    content = body.get("content", "")
    collection = body.get("collection", "inbox")
    if not content:
        raise HTTPException(400, "content alani gerekli")
    _check_collection(collection)
    imported = await service.import_bookmarks(session, content, default_collection=collection)
    return {"imported": imported}


@router.get("/bookmarks/{bookmark_id}", response_model=BookmarkOut)
async def get_bookmark(bookmark_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    bookmark = await service.get(session, bookmark_id)
    if bookmark is None:
        raise HTTPException(404)
    return bookmark


@router.get("/bookmarks/{bookmark_id}/fulltext", response_model=BookmarkFullTextOut)
async def get_bookmark_fulltext(
    bookmark_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    """Makalenin tam metni, temizlenmis HTML'i ve vurgulari."""
    fulltext = await service.get_full_text(session, bookmark_id)
    if fulltext is None:
        raise HTTPException(404)
    return fulltext


@router.patch("/bookmarks/{bookmark_id}/progress", response_model=BookmarkOut)
async def update_bookmark_progress(
    bookmark_id: uuid.UUID,
    body: BookmarkProgressUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Okuma yuzdesini gunceller. Yuzde >= 90 ise otomatik okundu yapilir."""
    bookmark = await service.update_progress(session, bookmark_id, body.scroll_progress)
    if bookmark is None:
        raise HTTPException(404)
    return bookmark


@router.get("/bookmarks/{bookmark_id}/highlights", response_model=list[BookmarkHighlightOut])
async def list_bookmark_highlights(
    bookmark_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    return await service.list_highlights(session, bookmark_id)


@router.post(
    "/bookmarks/{bookmark_id}/highlights",
    response_model=BookmarkHighlightOut,
    status_code=201,
)
async def add_bookmark_highlight(
    bookmark_id: uuid.UUID,
    body: BookmarkHighlightIn,
    session: AsyncSession = Depends(get_session),
):
    highlight = await service.add_highlight(session, bookmark_id, body)
    if highlight is None:
        raise HTTPException(404)
    return highlight


@router.delete("/bookmarks/{bookmark_id}/highlights/{highlight_id}", status_code=204)
async def delete_bookmark_highlight(
    bookmark_id: uuid.UUID,
    highlight_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    if not await service.delete_highlight(session, bookmark_id, highlight_id):
        raise HTTPException(404)


@router.post("/bookmarks/{bookmark_id}/highlights/{highlight_id}/convert-to-flashcard")
async def convert_highlight_to_flashcard(
    bookmark_id: uuid.UUID,
    highlight_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    try:
        card_id = await service.convert_highlight_to_flashcard(session, bookmark_id, highlight_id)
        return {"card_id": card_id}
    except ValueError as err:
        raise HTTPException(404, str(err)) from err


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


@router.post("/bookmarks/bulk-action", response_model=BookmarkBulkActionResult)
async def bulk_action_bookmarks(
    body: BookmarkBulkActionIn,
    session: AsyncSession = Depends(get_session),
):
    if body.collection is not None:
        _check_collection(body.collection)
    if body.read_status is not None and body.read_status not in READ_STATUSES:
        raise HTTPException(422, f"read_status su olmali: {READ_STATUSES}")
    affected = await service.bulk_action(session, body)
    return BookmarkBulkActionResult(affected=affected, action=body.action)


@router.post("/bookmarks/{bookmark_id}/convert-to-task")
async def convert_bookmark_to_task(
    bookmark_id: uuid.UUID,
    body: ConvertToTaskIn,
    session: AsyncSession = Depends(get_session),
):
    try:
        todo_id = await service.convert_to_task(session, bookmark_id, body)
        return {"todo_id": todo_id}
    except ValueError as err:
        raise HTTPException(404, str(err)) from err


@router.post(
    "/bookmarks/{bookmark_id}/source-note", response_model=VaultItem, status_code=201
)
async def create_source_note(
    bookmark_id: uuid.UUID,
    body: CreateSourceNoteIn,
    session: AsyncSession = Depends(get_session),
):
    """Yer iminin kanonik Vault kaynak notunu çözer veya oluşturur.

    Yer imi ve vurguları forkOS'ta operasyonel kalır; burada yalnızca bir Vault
    dosyası üretilir. forkOS veritabanında not kaydı OLUŞMAZ.
    """
    try:
        return await service.ensure_source_note(session, bookmark_id, body)
    except ValueError as err:
        raise HTTPException(404, str(err)) from err
    except (
        obsidian_service.VaultConflictError,
        obsidian_service.VaultStaleWriteError,
        obsidian_service.VaultWriteError,
        PermissionError,
        RuntimeError,
    ) as err:
        raise vault_http_error(err) from err


@router.post("/bookmarks/{bookmark_id}/enrich", response_model=BookmarkOut)
async def enrich_bookmark(
    bookmark_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    bookmark = await service.enrich_bookmark(session, bookmark_id)
    if bookmark is None:
        raise HTTPException(404)
    return bookmark
