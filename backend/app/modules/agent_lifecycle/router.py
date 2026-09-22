"""Hermes host plumbing; MCP araç yüzeyine eklenmez."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.agent_lifecycle import service
from app.modules.agent_lifecycle.schemas import (
    LifecycleEventIn,
    LifecycleEventOut,
    LifecycleStatusOut,
)

router = APIRouter(prefix="/agent/lifecycle", tags=["agent-lifecycle"])


@router.post("/event", response_model=LifecycleEventOut)
async def lifecycle_event(body: LifecycleEventIn, session: AsyncSession = Depends(get_session)):
    try:
        return await service.observe(session, body)
    except service.SessionAlreadyFinalized as exc:
        await session.rollback()
        raise HTTPException(409, detail={"code": "LIFECYCLE_ALREADY_FINALIZED"}) from exc
    except SQLAlchemyError as exc:
        await session.rollback()
        raise HTTPException(503, detail={"code": "LIFECYCLE_STORAGE_UNAVAILABLE"}) from exc


@router.get("/status", response_model=LifecycleStatusOut)
async def lifecycle_status(session: AsyncSession = Depends(get_session)):
    try:
        return await service.status(session)
    except SQLAlchemyError as exc:
        raise HTTPException(503, detail={"code": "LIFECYCLE_STORAGE_UNAVAILABLE"}) from exc
