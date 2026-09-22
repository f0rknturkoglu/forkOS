"""Atomik, idempotent A1 oturum gözlemleri; hiçbir domain/Vault yazımı yok."""

import hashlib
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agent_lifecycle.models import AgentSession, AgentSessionTurn
from app.modules.agent_lifecycle.schemas import (
    LifecycleEventIn,
    LifecycleEventOut,
    LifecycleStatusOut,
)


class SessionAlreadyFinalized(Exception):
    pass


def session_key(harness: str, raw_session_id: str) -> str:
    return hashlib.sha256(
        b"forkos-agent-session-v1\0" + harness.encode() + b"\0" + raw_session_id.encode()
    ).hexdigest()


def turn_key(derived_session_key: str, raw_turn_id: str) -> str:
    return hashlib.sha256(
        b"forkos-agent-turn-v1\0" + derived_session_key.encode() + b"\0" + raw_turn_id.encode()
    ).hexdigest()


async def observe(session: AsyncSession, event: LifecycleEventIn) -> LifecycleEventOut:
    """Session upsert, row lock, unique turn insert ve sayaç aynı transaction'da."""
    now = datetime.now(UTC)
    key = session_key(event.harness, event.session_id)
    await session.execute(
        insert(AgentSession).values(
            schema_version=event.schema_version,
            harness=event.harness,
            session_key=key,
            platform=event.platform,
            first_seen_at=now,
            last_seen_at=now,
            status="active",
            turn_count=0,
        ).on_conflict_do_nothing(index_elements=["session_key"])
    )
    row = (await session.execute(
        select(AgentSession).where(AgentSession.session_key == key).with_for_update()
    )).scalar_one()

    if row.status == "finalized" and event.event != "session_finalize":
        raise SessionAlreadyFinalized

    duplicate = False
    if event.event == "session_start":
        duplicate = row.start_seen_at is not None
        if not duplicate:
            row.start_seen_at = now
    elif event.event == "session_finalize":
        duplicate = row.finalized_at is not None
        if not duplicate:
            row.finalized_at = now
            row.status = "finalized"

    if event.event != "session_finalize" and event.turn_id is not None:
        inserted = (await session.execute(
            insert(AgentSessionTurn).values(
                session_id=row.id,
                turn_key=turn_key(key, event.turn_id),
                first_seen_at=now,
            ).on_conflict_do_nothing(constraint="uq_agent_session_turn_identity")
            .returning(AgentSessionTurn.id)
        )).scalar_one_or_none()
        if inserted is not None:
            row.turn_count += 1
        elif event.event == "turn_seen":
            duplicate = True

    row.last_seen_at = now
    row.platform = event.platform
    await session.commit()
    return LifecycleEventOut(accepted=True, event=event.event, duplicate=duplicate)


async def status(session: AsyncSession) -> LifecycleStatusOut:
    latest = (await session.execute(
        select(AgentSession.harness, AgentSession.last_seen_at)
        .order_by(AgentSession.last_seen_at.desc()).limit(1)
    )).first()
    active = await session.scalar(select(func.count()).select_from(AgentSession).where(AgentSession.status == "active"))
    incomplete = await session.scalar(select(func.count()).select_from(AgentSession).where(AgentSession.start_seen_at.is_(None)))
    finalized = await session.scalar(select(func.max(AgentSession.finalized_at)))
    return LifecycleStatusOut(
        available=True,
        last_event_at=latest.last_seen_at if latest else None,
        last_harness=latest.harness if latest else None,
        active_sessions=active or 0,
        last_finalized_at=finalized,
        incomplete_session_count=incomplete or 0,
    )
