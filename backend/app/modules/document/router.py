from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity
from app.db import get_session
from app.modules.document import service
from app.modules.document.models import Document

router = APIRouter(tags=["documents"])

@router.get("/documents")
async def documents(category: str | None = None, session: AsyncSession = Depends(get_session)):
    return await service.list_documents(session, category)


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
