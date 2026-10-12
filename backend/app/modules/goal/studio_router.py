from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.local_ui import StudioRoute
from app.db import get_session
from app.integrations.contextual import build_summary
from app.integrations.contextual_schemas import AssistanceContext, AssistanceSummary
from app.modules.goal import studio, studio_policy, studio_transport
from app.modules.goal.studio_schemas import (
    StudioConsentIn,
    StudioConsentOut,
    StudioDecisionIn,
    StudioProposal,
    StudioSessionIn,
    StudioSessionOut,
    StudioStatus,
    StudioTurnIn,
)

router = APIRouter(prefix="/goals/studio", tags=["goals"], route_class=StudioRoute)


@router.post("/context", response_model=AssistanceSummary)
async def context(body: AssistanceContext, db: AsyncSession = Depends(get_session)):
    return await build_summary(db, body)


@router.get("/status", response_model=StudioStatus)
async def status(db: AsyncSession = Depends(get_session)):
    return await studio_transport.status(db)


@router.put("/consent", response_model=StudioConsentOut)
async def consent(body: StudioConsentIn, db: AsyncSession = Depends(get_session)):
    return await studio_policy.update_consent(db, body)


@router.post("/sessions", response_model=StudioSessionOut)
async def start(body: StudioSessionIn, db: AsyncSession = Depends(get_session)):
    return await studio.start(db, body)


@router.get("/sessions/{session_id}", response_model=StudioSessionOut)
async def read(session_id: UUID, db: AsyncSession = Depends(get_session)):
    return await studio.reconcile(db, await studio.get_session(db, session_id))


@router.post("/sessions/{session_id}/turns", response_model=StudioSessionOut)
async def turn(session_id: UUID, body: StudioTurnIn, db: AsyncSession = Depends(get_session)):
    return await studio.turn(db, await studio.get_session(db, session_id), body)


@router.post("/sessions/{session_id}/stop", response_model=StudioSessionOut)
async def stop(session_id: UUID, db: AsyncSession = Depends(get_session)):
    return await studio.stop(db, await studio.get_session(db, session_id))


@router.put("/sessions/{session_id}/proposal", response_model=StudioSessionOut)
async def revise(session_id: UUID, body: StudioProposal, db: AsyncSession = Depends(get_session)):
    try:
        return await studio.revise(db, await studio.get_session(db, session_id), body)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/sessions/{session_id}/decision", response_model=StudioSessionOut)
async def decide(session_id: UUID, body: StudioDecisionIn, db: AsyncSession = Depends(get_session)):
    return await studio.decide(db, await studio.get_session(db, session_id), body)


@router.get("/sessions/{session_id}/events")
async def events(session_id: UUID, db: AsyncSession = Depends(get_session)):
    row = await studio.get_session(db, session_id)
    run_id = row.data.get("run_id")
    await db.rollback()  # Never hold DB lock/connection for the stream lifetime.
    if not run_id:
        raise HTTPException(409, "Aktif Hermes koşusu yok")
    await studio_transport.require_ready()
    return StreamingResponse(
        studio_transport.public_events(run_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
