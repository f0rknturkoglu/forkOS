"""A2: Ephemeral agent devamlılık ve tanı durum uçları."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.agent_continuity import service
from app.modules.agent_continuity.schemas import ContinuityStatusOut

router = APIRouter(prefix="/agent/continuity", tags=["agent-continuity"])


@router.get("/status", response_model=ContinuityStatusOut)
async def continuity_status(session: AsyncSession = Depends(get_session)):
    try:
        return await service.status(session)
    except SQLAlchemyError as exc:
        raise HTTPException(503, detail={"code": "CONTINUITY_STORAGE_UNAVAILABLE"}) from exc
