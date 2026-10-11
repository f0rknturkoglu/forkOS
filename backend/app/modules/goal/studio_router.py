from __future__ import annotations

from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.routing import APIRoute
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.goal import studio, studio_transport
from app.modules.goal.studio_schemas import (
    StudioDecisionIn,
    StudioProposal,
    StudioSessionIn,
    StudioSessionOut,
    StudioStatus,
    StudioTurnIn,
)


class StudioRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def bounded(request: Request):
            # No forwarded Host trust or extension/MCP approval path. Browser same-origin mutations only.
            host = urlsplit("http://" + request.headers.get("host", "")).hostname
            if host not in {"127.0.0.1", "localhost", "::1"}:
                raise HTTPException(403, "Goal Studio yalnız yerel host üzerinde kullanılabilir")
            if request.method != "GET":
                origin = request.headers.get("origin")
                if origin not in {"http://127.0.0.1:5173", "http://localhost:5173"}:
                    raise HTTPException(403, "Goal Studio yazması forkOS arayüzünden gelmeli")
                if request.headers.get("x-forkos-goal-studio") != "1":
                    raise HTTPException(403, "Goal Studio CSRF koruması eksik")
                if request.headers.get("content-type", "").split(";")[0] != "application/json":
                    raise HTTPException(415, "JSON gerekli")
                body = bytearray()
                async for chunk in request.stream():
                    body.extend(chunk)
                    if len(body) > 64_000:
                        raise HTTPException(413, "Goal Studio istek sınırı aşıldı")
                request._body = bytes(body)
            return await handler(request)

        return bounded


router = APIRouter(prefix="/goals/studio", tags=["goals"], route_class=StudioRoute)


@router.get("/status", response_model=StudioStatus)
async def status():
    return await studio_transport.status()


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
