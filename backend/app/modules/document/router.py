from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity
from app.db import get_session
from app.integrations.google_auth import authorization_url, exchange
from app.integrations.models import OAuthToken
from app.modules.document import service
from app.modules.document.models import Document

router = APIRouter(tags=["documents"])


class SyncIn(BaseModel):
    folder_id: str
    category: str = "other"


@router.get("/auth/google/start")
async def auth_start():
    try:
        return RedirectResponse(authorization_url())
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/auth/google/callback")
async def callback(code: str, session: AsyncSession = Depends(get_session)):
    await exchange(session, code)
    return RedirectResponse("http://127.0.0.1:5173/#/documents")


@router.get("/auth/google/status")
async def status(session: AsyncSession = Depends(get_session)):
    token = await session.get(OAuthToken, "google")
    return {
        "connected": token is not None,
        "expires_at": token.expires_at if token else None,
        "scopes": token.scopes if token else None,
    }


@router.get("/documents")
async def documents(category: str | None = None, session: AsyncSession = Depends(get_session)):
    return await service.list_documents(session, category)


@router.post("/documents/sync")
async def sync(body: SyncIn, session: AsyncSession = Depends(get_session)):
    try:
        count = await service.sync_folder(session, body.folder_id, body.category)
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)) from exc
    return {"synced": count}


@router.get("/documents/{id}/open")
async def open_doc(id: UUID, session: AsyncSession = Depends(get_session)):
    doc = await session.get(Document, id)
    if not doc:
        raise HTTPException(404)
    return {"url": doc.web_view_link}


@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form("cv"),
    session: AsyncSession = Depends(get_session),
):
    content = await file.read()
    if not content:
        raise HTTPException(400, "Dosya boş olamaz")
    filename = file.filename or "belge"
    return await service.create_local_document(
        session,
        title=filename,
        category=category,
        mime=file.content_type,
        content=content,
    )


@router.get("/documents/{id}/file")
async def get_document_file(id: UUID, session: AsyncSession = Depends(get_session)):
    doc = await session.get(Document, id)
    if not doc:
        raise HTTPException(404, "Belge bulunamadı")
    entity = await session.get(Entity, id)
    title = entity.title if entity else "belge"
    file_path = service.get_local_file_path(id, title)
    if not file_path or not file_path.exists():
        raise HTTPException(404, "Dosya bulunamadı")
    return FileResponse(file_path, media_type=doc.mime, filename=title)


@router.delete("/documents/{id}")
async def delete_document(id: UUID, session: AsyncSession = Depends(get_session)):
    success = await service.delete_document(session, id)
    if not success:
        raise HTTPException(404, "Belge bulunamadı")
    return {"status": "ok"}
