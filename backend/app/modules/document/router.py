from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

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
