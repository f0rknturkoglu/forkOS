from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.note import service
from app.modules.note.schemas import NoteIn, NoteOut, NoteUpdate

router = APIRouter(tags=["note"])


@router.get("/notes", response_model=list[NoteOut])
async def list_notes(include_archived: bool = Query(False),
                     session: AsyncSession = Depends(get_session)):
    return await service.list_notes(session, include_archived=include_archived)


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
