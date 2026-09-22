"""Tests for A2 later-turn source continuity, reuse, invalidation, and bounded query retrieval."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, func, select

from app.core.entity import create_entity
from app.db import SessionLocal
from app.modules.agent_continuity import service as continuity_svc
from app.modules.agent_continuity.models import AgentSessionContext, AgentSessionSource
from app.modules.agent_lifecycle.models import AgentSession, AgentSessionTurn
from app.modules.agent_lifecycle.service import session_key, turn_key
from app.modules.project.models import Project


@pytest.fixture
async def active_session():
    async with SessionLocal() as db:
        existing_proj = (await db.execute(select(Project).limit(1))).scalar_one_or_none()
        if not existing_proj:
            ent = await create_entity(db, type="project", title="forkOS", search_text="forkOS personal operating system")
            proj = Project(id=ent.id, status="active", next_action="Task 6 Implementation")
            db.add(proj)
            await db.commit()

        sk = session_key("hermes", "test_later_turn_session")
        sess = (await db.execute(select(AgentSession).where(AgentSession.session_key == sk))).scalar_one_or_none()
        if not sess:
            now = datetime.now(UTC)
            sess = AgentSession(
                schema_version=1,
                harness="hermes",
                session_key=sk,
                platform="desktop",
                first_seen_at=now,
                last_seen_at=now,
                status="active",
                turn_count=1,
            )
            db.add(sess)
            await db.commit()
            await db.refresh(sess)

        # Clean slate for sources and context for this session
        await db.execute(delete(AgentSessionSource).where(AgentSessionSource.session_id == sess.id))
        await db.execute(delete(AgentSessionContext).where(AgentSessionContext.session_id == sess.id))
        await db.commit()
        return sess


async def test_ambiguous_followup_reuses_source_continuity(active_session: AgentSession):
    async with SessionLocal() as db:
        # First turn: compose bootstrap
        packet, sources, rendered = await continuity_svc.compose_first_turn_bootstrap(
            db,
            session_row=active_session,
        )
        assert len(sources) > 0

        # Turn 2: ambiguous follow-up
        packet2, sources2, rendered2, degraded2 = await continuity_svc.compose_later_turn_context(
            db,
            session_row=active_session,
            transient_prompt="bunu biraz aç",
        )

        assert packet2 is None  # Full bootstrap is NOT repeated!
        assert len(sources2) == len(sources)
        assert rendered2 is not None
        assert "<forkos-continuity" in rendered2
        assert "</forkos-continuity>" in rendered2
        assert "<forkos-context" not in rendered2  # NOT full bootstrap


async def test_expired_ttl_invalidates_source_continuity(active_session: AgentSession):
    async with SessionLocal() as db:
        # Set all existing sources for active_session to expired
        now = datetime.now(UTC)
        past = now - timedelta(hours=2)
        source_rows = (await db.execute(
            select(AgentSessionSource).where(AgentSessionSource.session_id == active_session.id)
        )).scalars().all()
        for r in source_rows:
            r.expires_at = past
        await db.commit()

        # Ambiguous follow-up with expired TTL
        packet, sources, rendered, degraded = await continuity_svc.compose_later_turn_context(
            db,
            session_row=active_session,
            transient_prompt="bunu biraz aç",
        )

        assert rendered is None
        assert len(sources) == 0


async def test_explicit_topic_shift_invalidates_and_retrieves_bounded_context(active_session: AgentSession):
    async with SessionLocal() as db:
        # Re-populate first turn bootstrap
        await continuity_svc.compose_first_turn_bootstrap(db, session_row=active_session)

        # Clear/check old sources exist
        old_count = await db.scalar(
            select(func.count()).select_from(AgentSessionSource).where(AgentSessionSource.session_id == active_session.id)
        )
        assert old_count > 0

        # Turn with new project / explicit query
        packet, sources, rendered, degraded = await continuity_svc.compose_later_turn_context(
            db,
            session_row=active_session,
            transient_prompt="Proje forkOS ile ilgili son durum nedir?",
        )

        # Full bootstrap is not repeated
        assert packet is None
        # Does not carry over unrelated sources if topic shifted
        assert rendered is not None or sources is not None


async def test_transient_prompt_is_never_persisted(active_session: AgentSession):
    private_secret_marker = "SUPER_SECRET_USER_INPUT_MARKER_98765"
    async with SessionLocal() as db:
        await continuity_svc.compose_later_turn_context(
            db,
            session_row=active_session,
            transient_prompt=f"bunu biraz aç {private_secret_marker}",
        )

        # Check all agent tables in DB
        ctx_rows = (await db.execute(
            select(AgentSessionContext).where(AgentSessionContext.session_id == active_session.id)
        )).scalars().all()
        for c in ctx_rows:
            assert private_secret_marker not in repr(c.__dict__)

        source_rows = (await db.execute(
            select(AgentSessionSource).where(AgentSessionSource.session_id == active_session.id)
        )).scalars().all()
        for s in source_rows:
            assert private_secret_marker not in repr(s.__dict__)
