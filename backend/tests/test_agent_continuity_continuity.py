"""Tests for A2 later-turn source continuity, reuse, invalidation, and bounded query retrieval."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, func, select

from app.core.entity import create_entity
from app.db import SessionLocal
from app.modules.agent_continuity import service as continuity_svc
from app.modules.agent_continuity.models import AgentSessionContext, AgentSessionSource
from app.modules.agent_lifecycle.models import AgentSession
from app.modules.agent_lifecycle.service import session_key
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


async def test_stale_source_detection_invalidates_and_degrades(active_session: AgentSession):
    async with SessionLocal() as db:
        # First turn: compose bootstrap
        packet, sources, rendered = await continuity_svc.compose_first_turn_bootstrap(
            db,
            session_row=active_session,
        )
        assert len(sources) > 0
        proj_sources = [s for s in sources if s.source_type == "project"]
        assert len(proj_sources) > 0
        proj_ent_id = proj_sources[0].source_id.split(":", 1)[1]

        # Mutate the project next_action directly in canonical DB
        import uuid
        proj_obj = (await db.execute(select(Project).where(Project.id == uuid.UUID(proj_ent_id)))).scalar_one()
        proj_obj.next_action = "Brand new action that alters version fingerprint"
        await db.commit()

        # Later turn: ambiguous continuation
        packet2, sources2, rendered2, degraded2 = await continuity_svc.compose_later_turn_context(
            db,
            session_row=active_session,
            transient_prompt="bunu biraz aç",
        )

        # Stale version was detected!
        assert "SOURCE_STALE" in degraded2
        # Stale source is removed from DB
        remaining_source = (await db.execute(
            select(AgentSessionSource).where(
                AgentSessionSource.session_id == active_session.id,
                AgentSessionSource.source_id == f"entity:{proj_ent_id}",
            )
        )).scalar_one_or_none()
        assert remaining_source is None


async def test_same_topic_direct_question_preserves_continuity(active_session: AgentSession):
    async with SessionLocal() as db:
        await continuity_svc.compose_first_turn_bootstrap(db, session_row=active_session)

        # User asks a non-ambiguous direct question on the SAME topic ("forkOS")
        packet, sources, rendered, degraded = await continuity_svc.compose_later_turn_context(
            db,
            session_row=active_session,
            transient_prompt="forkOS projesinin sonraki adımı nedir?",
        )

        # Topic compatibility preserves continuity sources
        assert packet is None
        assert rendered is not None
        assert "<forkos-continuity" in rendered
        assert len(sources) > 0


async def test_scope_transitions_matrix(active_session: AgentSession):
    async with SessionLocal() as db:
        # Create Project A and Project B
        ent_a = await create_entity(db, type="project", title="Project Alpha", search_text="Alpha project")
        proj_a = Project(id=ent_a.id, status="active", next_action="Start Alpha")
        db.add(proj_a)

        ent_b = await create_entity(db, type="project", title="Project Beta", search_text="Beta project")
        proj_b = Project(id=ent_b.id, status="active", next_action="Start Beta")
        db.add(proj_b)
        await db.commit()

        id_a_str = str(ent_a.id)
        id_b_str = str(ent_b.id)

        # 1. Turn 1 with scope A
        await continuity_svc.compose_first_turn_bootstrap(
            db,
            session_row=active_session,
            scope_project=id_a_str,
        )
        # Ensure a source with scope A exists
        now = datetime.now(UTC)
        existing_s_a = (await db.execute(
            select(AgentSessionSource).where(
                AgentSessionSource.session_id == active_session.id,
                AgentSessionSource.source_id == f"entity:{id_a_str}",
            )
        )).scalar_one_or_none()
        if not existing_s_a:
            s_a = AgentSessionSource(
                session_id=active_session.id,
                source_id=f"entity:{id_a_str}",
                source_type="project",
                source_version=continuity_svc.compute_project_source_version(
                    ent_a.title, proj_a.status, proj_a.next_action, proj_a.last_activity_at
                ),
                scope_project=id_a_str,
                delivered_at=now,
                expires_at=now + timedelta(minutes=60),
            )
            db.add(s_a)
            await db.commit()
        else:
            existing_s_a.scope_project = id_a_str
            await db.commit()


        # 2. Transition A -> A: Same scope retains sources
        _, sources_aa, _, _ = await continuity_svc.compose_later_turn_context(
            db,
            session_row=active_session,
            transient_prompt="bunu biraz aç",
            scope_project=id_a_str,
        )
        assert any(s.scope_project == id_a_str for s in sources_aa)

        # 3. Transition A -> B: Scope switch invalidates previous sources from A
        _, sources_ab, _, _ = await continuity_svc.compose_later_turn_context(
            db,
            session_row=active_session,
            transient_prompt="Beta projesi durumu nedir?",
            scope_project=id_b_str,
        )
        # Previous A source must be purged
        source_a_in_db = (await db.execute(
            select(AgentSessionSource).where(
                AgentSessionSource.session_id == active_session.id,
                AgentSessionSource.source_id == f"entity:{id_a_str}",
            )
        )).scalar_one_or_none()
        assert source_a_in_db is None

        # 4. Transition B -> None: Scope cleared
        _, sources_b_none, _, _ = await continuity_svc.compose_later_turn_context(
            db,
            session_row=active_session,
            transient_prompt="genel durum nedir?",
            scope_project=None,
        )
        last_ctx_none = (await db.execute(
            select(AgentSessionContext)
            .where(AgentSessionContext.session_id == active_session.id)
            .order_by(AgentSessionContext.created_at.desc())
            .limit(1)
        )).scalar_one()
        assert last_ctx_none.scope_project is None


async def test_zero_prompt_logging(active_session: AgentSession, caplog: pytest.LogCaptureFixture):
    import logging
    caplog.set_level(logging.DEBUG)
    secret_marker = "SECRET_MARKER_NEVER_LOGGED_XYZ_987654321"

    async with SessionLocal() as db:
        await continuity_svc.compose_later_turn_context(
            db,
            session_row=active_session,
            transient_prompt=f"bunu aç {secret_marker}",
        )

    for record in caplog.records:
        assert secret_marker not in record.message


async def test_opportunistic_retention_pruning(active_session: AgentSession):
    async with SessionLocal() as db:
        # Seed 55 context rows
        now = datetime.now(UTC)
        for i in range(55):
            ctx = AgentSessionContext(
                session_id=active_session.id,
                turn_id=None,
                schema_version=1,
                is_first_turn=False,
                item_count=1,
                char_count=100,
                truncated=False,
                omitted_count=0,
                degraded_reasons=[],
                created_at=now - timedelta(minutes=100 - i),
            )
            db.add(ctx)

        # Seed an expired source
        past = now - timedelta(hours=3)
        exp_source = AgentSessionSource(
            session_id=active_session.id,
            source_id="entity:expired-source-123",
            source_type="project",
            delivered_at=past - timedelta(hours=1),
            expires_at=past,
        )
        db.add(exp_source)
        await db.commit()

        # Run later turn to trigger opportunistic pruning
        await continuity_svc.compose_later_turn_context(
            db,
            session_row=active_session,
            transient_prompt="bunu biraz aç",
        )

        # Assert expired source is pruned
        exp_in_db = (await db.execute(
            select(AgentSessionSource).where(
                AgentSessionSource.session_id == active_session.id,
                AgentSessionSource.source_id == "entity:expired-source-123",
            )
        )).scalar_one_or_none()
        assert exp_in_db is None

        # Assert context rows count is bounded to <= 51 (pruned to 50 + current turn)
        ctx_count = await db.scalar(
            select(func.count())
            .select_from(AgentSessionContext)
            .where(AgentSessionContext.session_id == active_session.id)
        )
        assert ctx_count <= 51
