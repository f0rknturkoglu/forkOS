from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.note import service
from app.modules.note.schemas import NoteAttachmentOut, NoteIn, NoteOut, NoteUpdate

router = APIRouter(tags=["note"])


@router.get("/notes", response_model=list[NoteOut])
async def list_notes(include_archived: bool = Query(False),
                     about: uuid.UUID | None = Query(None),
                     session: AsyncSession = Depends(get_session)):
    return await service.list_notes(
        session, include_archived=include_archived, about=about
    )


@router.post("/notes", response_model=NoteOut, status_code=201)
async def create_note(body: NoteIn, session: AsyncSession = Depends(get_session)):
    try:
        return await service.create(session, body)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/notes/{note_id}", response_model=NoteOut)
async def get_note(note_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    result = await service.get(session, note_id)
    if result is None:
        raise HTTPException(404, "not bulunamadi")
    return result


@router.patch("/notes/{note_id}", response_model=NoteOut)
async def patch_note(note_id: uuid.UUID, body: NoteUpdate,
                     session: AsyncSession = Depends(get_session)):
    result = await service.update(session, note_id, body)
    if result is None:
        raise HTTPException(404, "not bulunamadi")
    return result


@router.post("/notes/{note_id}/archive", response_model=NoteOut | None)
async def archive_note(note_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    if not await service.archive(session, note_id):
        raise HTTPException(404, "not bulunamadi")
    return None


@router.delete("/notes/{note_id}", status_code=204)
async def delete_note(note_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    if not await service.delete(session, note_id):
        raise HTTPException(404, "not bulunamadi")


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
    content, mime, _name = result
    return Response(
        content=content,
        media_type=mime,
        headers={"Cache-Control": "private, max-age=86400"},
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
