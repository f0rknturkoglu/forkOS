import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.agent_continuity.schemas import TurnContextIn, TurnContextOut
from app.modules.agent_lifecycle import service
from app.modules.agent_lifecycle.schemas import (
    LifecycleEventIn,
    LifecycleEventOut,
    LifecycleStatusOut,
)

LOGGER = logging.getLogger("forkos.agent_lifecycle")

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


@router.post("/turn", response_model=TurnContextOut)
async def lifecycle_turn(body: TurnContextIn, session: AsyncSession = Depends(get_session)):
    # 1. A1 Lifecycle gözlemi (kendi transaction'ında commit edilir)
    lifecycle_in = LifecycleEventIn(
        schema_version=1,
        event="session_start" if body.is_first_turn else "turn_seen",
        harness=body.harness,
        session_id=body.session_id,
        turn_id=body.turn_id,
        platform=body.platform,
    )
    try:
        lifecycle_out = await service.observe(session, lifecycle_in)
    except service.SessionAlreadyFinalized as exc:
        await session.rollback()
        raise HTTPException(409, detail={"code": "LIFECYCLE_ALREADY_FINALIZED"}) from exc
    except SQLAlchemyError as exc:
        await session.rollback()
        raise HTTPException(503, detail={"code": "LIFECYCLE_STORAGE_UNAVAILABLE"}) from exc

    # 2. Duplicate kontrolü: Eğer bu turn daha önce işlendiyse, güvenli no-op
    if lifecycle_out.duplicate:
        return TurnContextOut(
            lifecycle=lifecycle_out,
            packet=None,
            rendered_context=None,
            degraded_reasons=[],
        )

    # 3. A2 Bağlam Kompozisyonu (bağımsız hata alanı; A1 commit'i asla geri alınmaz)
    from app.modules.agent_continuity import service as continuity_svc
    from app.modules.agent_lifecycle.models import AgentSession, AgentSessionTurn
    from app.modules.agent_lifecycle.service import session_key, turn_key

    s_key = session_key(body.harness, body.session_id)
    session_row = (await session.execute(
        select(AgentSession).where(AgentSession.session_key == s_key)
    )).scalar_one_or_none()

    turn_db_id = None
    if body.turn_id and session_row:
        t_key = turn_key(s_key, body.turn_id)
        turn_row = (await session.execute(
            select(AgentSessionTurn).where(AgentSessionTurn.turn_key == t_key)
        )).scalar_one_or_none()
        if turn_row:
            turn_db_id = turn_row.id

    if not session_row:
        return TurnContextOut(
            lifecycle=lifecycle_out,
            packet=None,
            rendered_context=None,
            degraded_reasons=["SESSION_ROW_NOT_FOUND"],
        )

    try:
        if body.is_first_turn:
            packet, sources, rendered = await continuity_svc.compose_first_turn_bootstrap(
                session,
                session_row=session_row,
                turn_id=turn_db_id,
                scope_project=body.scope_project,
            )
            return TurnContextOut(
                lifecycle=lifecycle_out,
                packet=packet,
                rendered_context=rendered,
                degraded_reasons=packet.diagnostics.degraded_reasons,
            )
        else:
            packet, sources, rendered, degraded = await continuity_svc.compose_later_turn_context(
                session,
                session_row=session_row,
                transient_prompt=body.user_message or "",
                turn_id=turn_db_id,
                scope_project=body.scope_project,
            )
            return TurnContextOut(
                lifecycle=lifecycle_out,
                packet=packet,
                rendered_context=rendered,
                degraded_reasons=degraded,
            )
    except Exception as exc:
        await session.rollback()
        LOGGER.exception("A2 context composition failed in /turn endpoint: %s", type(exc).__name__)
        return TurnContextOut(
            lifecycle=lifecycle_out,
            packet=None,
            rendered_context=None,
            degraded_reasons=[f"CONTEXT_COMPOSITION_FAILED: {exc.__class__.__name__}"],
        )



@router.get("/status", response_model=LifecycleStatusOut)
async def lifecycle_status(session: AsyncSession = Depends(get_session)):
    try:
        return await service.status(session)
    except SQLAlchemyError as exc:
        raise HTTPException(503, detail={"code": "LIFECYCLE_STORAGE_UNAVAILABLE"}) from exc

