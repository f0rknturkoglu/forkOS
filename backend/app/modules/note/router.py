from __future__ import annotations

import uuid
from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.note import service
from app.modules.note.schemas import (
    NoteAttachmentOut,
    NoteFolderIn,
    NoteFolderOut,
    NoteFolderUpdate,
    NoteIn,
    NoteOut,
    NoteUpdate,
)

router = APIRouter(tags=["note"])


@router.get("/note-folders", response_model=list[NoteFolderOut])
async def list_note_folders(session: AsyncSession = Depends(get_session)):
    return await service.list_folders(session)


@router.post("/note-folders", response_model=NoteFolderOut, status_code=201)
async def create_note_folder(
    body: NoteFolderIn, session: AsyncSession = Depends(get_session)
):
    try:
        return await service.create_folder(session, body)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.patch("/note-folders/{folder_id}", response_model=NoteFolderOut)
async def patch_note_folder(
    folder_id: uuid.UUID,
    body: NoteFolderUpdate,
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await service.update_folder(session, folder_id, body)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if result is None:
        raise HTTPException(404, "not klasörü bulunamadı")
    return result


@router.delete("/note-folders/{folder_id}", status_code=204)
async def delete_note_folder(
    folder_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    if not await service.delete_folder(session, folder_id):
        raise HTTPException(404, "not klasörü bulunamadı")
    return Response(status_code=204)


@router.get("/notes", response_model=list[NoteOut])
async def list_notes(include_archived: bool = Query(False),
                     about: uuid.UUID | None = Query(None),
                     scope: str = Query("active", pattern="^(active|archive|trash)$"),
                     session: AsyncSession = Depends(get_session)):
    return await service.list_notes(
        session, include_archived=include_archived, about=about, scope=scope
    )


@router.post("/notes", response_model=NoteOut, status_code=201)
async def create_note(body: NoteIn, session: AsyncSession = Depends(get_session)):
    try:
        return await service.create(session, body)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/notes/daily/{journal_day}", response_model=NoteOut)
async def ensure_daily_note(
    journal_day: date, session: AsyncSession = Depends(get_session)
):
    return await service.ensure_daily_note(session, journal_day)


@router.get("/notes/{note_id}", response_model=NoteOut)
async def get_note(note_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    result = await service.get(session, note_id)
    if result is None:
        raise HTTPException(404, "not bulunamadi")
    return result


@router.patch("/notes/{note_id}", response_model=NoteOut)
async def patch_note(note_id: uuid.UUID, body: NoteUpdate,
                     session: AsyncSession = Depends(get_session)):
    try:
        result = await service.update(session, note_id, body)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if result is None:
        raise HTTPException(404, "not bulunamadi")
    return result


@router.post("/notes/{note_id}/archive", response_model=NoteOut | None)
async def archive_note(note_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    if not await service.archive(session, note_id):
        raise HTTPException(404, "not bulunamadi")
    return None


@router.post("/notes/{note_id}/restore", status_code=204)
async def restore_note(note_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    if not await service.restore_from_trash(session, note_id):
        raise HTTPException(404, "cop kutusunda not bulunamadi")
    return Response(status_code=204)


@router.post("/notes/{note_id}/unarchive", status_code=204)
async def unarchive_note(note_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    if not await service.restore_archive(session, note_id):
        raise HTTPException(404, "arsivde not bulunamadi")
    return Response(status_code=204)


@router.delete("/notes/{note_id}", status_code=204)
async def delete_note(note_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    if not await service.delete(session, note_id):
        raise HTTPException(404, "not bulunamadi")


@router.delete("/notes/{note_id}/permanent", status_code=204)
async def permanently_delete_note(note_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    if not await service.permanently_delete(session, note_id):
        raise HTTPException(404, "cop kutusunda not bulunamadi")
    return Response(status_code=204)


@router.post(
    "/notes/{note_id}/attachments",
    response_model=NoteAttachmentOut,
    status_code=201,
)
async def upload_attachment(
    note_id: uuid.UUID,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    # UploadFile disk spool kullanir; byte siniri serviste tek yerde dogrulanir.
    content = await file.read(service.MAX_ATTACHMENT_BYTES + 1)
    try:
        result = await service.add_attachment(
            session,
            note_id,
            filename=file.filename,
            mime=file.content_type,
            content=content,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if result is None:
        raise HTTPException(404, "not bulunamadi")
    return result


@router.get("/notes/{note_id}/attachments/{attachment_id}")
async def get_attachment(
    note_id: uuid.UUID,
    attachment_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await service.attachment_content(session, note_id, attachment_id)
    if result is None:
        raise HTTPException(404, "ek bulunamadi")
    content, mime, name = result
    inline = mime.startswith(("image/", "audio/", "video/", "text/")) or mime == "application/pdf"
    return Response(
        content=content,
        media_type=mime,
        headers={
            "Cache-Control": "private, max-age=86400",
            "Content-Disposition": f"{'inline' if inline else 'attachment'}; filename*=UTF-8''{quote(name)}",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/notes/{note_id}/attachments/{attachment_id}", status_code=204)
async def remove_attachment(
    note_id: uuid.UUID,
    attachment_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    if not await service.delete_attachment(session, note_id, attachment_id):
        raise HTTPException(404, "ek bulunamadi")
    return Response(status_code=204)
