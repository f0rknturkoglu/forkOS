"""Targeted regression tests for A2.2 correctness pass.

Contracts verified:
1. H2 revision v1 -> v2 stale detection and deletion
2. Provider-aware deadline freshness (Todo + Non-Todo)
3. Current project scope isolation (Scope A never leaks Scope B)
4. Semantic f0rknbrain selection (arbitrary 90 Agent notes never become preferences)
5. Safe vault path resolution and policy exclusion in freshness check
6. Path traversal rejection for vault source IDs
7. Truthful hard-ceiling truncation diagnostics
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import delete, select

from app.core.entity import create_entity
from app.db import SessionLocal
from app.modules.agent_continuity import service as continuity_svc
from app.modules.agent_continuity.models import AgentSessionContext, AgentSessionSource
from app.modules.agent_continuity.renderer import render_bootstrap_context
from app.modules.agent_continuity.schemas import (
    BootstrapDiagnostics,
    BootstrapIdentity,
    BootstrapPacketV1,
    OperationalState,
)
from app.modules.agent_lifecycle.models import AgentSession
from app.modules.agent_lifecycle.service import session_key
from app.modules.project.models import Project
from app.modules.todo.models import Todo


@pytest.fixture
async def a2_session():
    async with SessionLocal() as db:
        sk = session_key("hermes", "test_a2_2_session")
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

        await db.execute(delete(AgentSessionSource).where(AgentSessionSource.session_id == sess.id))
        await db.execute(delete(AgentSessionContext).where(AgentSessionContext.session_id == sess.id))
        await db.commit()
        return sess


async def test_h2_revision_v1_to_v2_stale_detection(a2_session: AgentSession):
    """H2 source version must carry real revision; changing revision must trigger SOURCE_STALE and delete old source."""
    async with SessionLocal() as db:
        mem_id = "mem-rev-test-1"

        # Mock initial H2 item with revision=1
        mock_item_v1 = MagicMock(
            memory_id=mem_id,
            title="User prefers dark theme",
            text="Dark mode preference",
            revision=1,
        )
        mock_ctx_v1 = MagicMock(
            profile=[mock_item_v1],
            constraints=[],
            goals=[],
            decisions=[],
            preferences=[],
        )

        with patch("app.integrations.agent.hot_memory.get_context", return_value=mock_ctx_v1):
            items, _ = await continuity_svc._collect_hot_memory(db)
            assert len(items) > 0
            assert items[0]["revision"] == 1

        # Seed source row with revision 1
        now = datetime.now(UTC)
        source_row = AgentSessionSource(
            session_id=a2_session.id,
            source_id=f"hot_memory:{mem_id}",
            source_type="hot_memory",
            source_version="1",
            delivered_at=now,
            expires_at=now + timedelta(minutes=60),
        )
        db.add(source_row)
        await db.commit()
        await db.refresh(source_row)

        # 1. Unchanged revision -> Fresh
        with patch("app.integrations.agent.hot_memory.get_context", return_value=mock_ctx_v1):
            is_fresh, title = await continuity_svc._check_source_freshness(db, source_row)
            assert is_fresh is True
            assert title == "User prefers dark theme"

        # 2. Revision bumped to 2 -> Stale
        mock_item_v2 = MagicMock(
            memory_id=mem_id,
            title="User prefers light theme",
            text="Light mode preference",
            revision=2,
        )
        mock_ctx_v2 = MagicMock(
            profile=[mock_item_v2],
            constraints=[],
            goals=[],
            decisions=[],
            preferences=[],
        )

        with patch("app.integrations.agent.hot_memory.get_context", return_value=mock_ctx_v2):
            is_fresh, title = await continuity_svc._check_source_freshness(db, source_row)
            assert is_fresh is False
            assert title == "User prefers light theme"

            # In later-turn context, it must delete stale source and report SOURCE_STALE
            packet, sources, rendered, degraded = await continuity_svc.compose_later_turn_context(
                db,
                session_row=a2_session,
                transient_prompt="bunu biraz aç",
            )
            assert "SOURCE_STALE" in degraded
            assert not any(s.source_id == f"hot_memory:{mem_id}" for s in sources)

            # Assert deleted from DB
            remaining = (await db.execute(
                select(AgentSessionSource).where(
                    AgentSessionSource.session_id == a2_session.id,
                    AgentSessionSource.source_id == f"hot_memory:{mem_id}",
                )
            )).scalar_one_or_none()
            assert remaining is None

        # 3. Memory retired / missing from active context -> Stale & unavailable
        mock_ctx_empty = MagicMock(
            profile=[],
            constraints=[],
            goals=[],
            decisions=[],
            preferences=[],
        )
        # Re-seed row
        source_row2 = AgentSessionSource(
            session_id=a2_session.id,
            source_id=f"hot_memory:{mem_id}",
            source_type="hot_memory",
            source_version="1",
            delivered_at=now,
            expires_at=now + timedelta(minutes=60),
        )
        db.add(source_row2)
        await db.commit()

        with patch("app.integrations.agent.hot_memory.get_context", return_value=mock_ctx_empty):
            is_fresh, title = await continuity_svc._check_source_freshness(db, source_row2)
            assert is_fresh is False
            assert title is None


async def test_deadline_freshness_todo_and_nontodo(a2_session: AgentSession):
    """Deadline source version must be provider-aware and match between first-turn and freshness check."""
    async with SessionLocal() as db:
        now = datetime.now(UTC)

        # 1. Todo deadline
        ent_todo = await create_entity(db, type="todo", title="Deploy migration 0065")
        due1 = now + timedelta(days=2)
        todo = Todo(id=ent_todo.id, status="open", due_at=due1)
        db.add(todo)
        await db.commit()

        v1 = continuity_svc.compute_deadline_source_version(
            title=ent_todo.title,
            due_at=due1,
            entity_type="todo",
            module="todo",
            priority=2,
        )

        source_todo = AgentSessionSource(
            session_id=a2_session.id,
            source_id=f"entity:{ent_todo.id}",
            source_type="deadline",
            source_version=v1,
            delivered_at=now,
            expires_at=now + timedelta(minutes=60),
        )
        db.add(source_todo)
        await db.commit()

        # Unchanged -> Fresh
        is_fresh, title = await continuity_svc._check_source_freshness(db, source_todo)
        assert is_fresh is True
        assert title == "Deploy migration 0065"

        # Changed due_at -> Stale
        todo.due_at = now + timedelta(days=5)
        await db.commit()

        is_fresh, title = await continuity_svc._check_source_freshness(db, source_todo)
        assert is_fresh is False
        assert title == "Deploy migration 0065"

        # 2. Non-Todo deadline (e.g. Media / Calendar / Opportunity provider)
        non_todo_id = str(uuid.uuid4())
        mock_deadlines = [
            {
                "entity_id": non_todo_id,
                "type": "media",
                "title": "Release Episode 42",
                "due_at": now + timedelta(days=3),
                "module": "media",
                "sub_kind": "podcast",
                "priority": 1,
                "condition_id": None,
            }
        ]

        v_media = continuity_svc.compute_deadline_source_version(
            title="Release Episode 42",
            due_at=now + timedelta(days=3),
            entity_type="media",
            module="media",
            priority=1,
        )

        source_media = AgentSessionSource(
            session_id=a2_session.id,
            source_id=f"entity:{non_todo_id}",
            source_type="deadline",
            source_version=v_media,
            delivered_at=now,
            expires_at=now + timedelta(minutes=60),
        )
        db.add(source_media)
        await db.commit()

        with patch("app.core.deadlines.collect_deadlines", return_value=mock_deadlines):
            # Unchanged non-todo deadline -> Fresh
            is_fresh, title = await continuity_svc._check_source_freshness(db, source_media)
            assert is_fresh is True
            assert title == "Release Episode 42"

            # Non-todo deadline changed date -> Stale
            changed_mock = [
                {
                    "entity_id": non_todo_id,
                    "type": "media",
                    "title": "Release Episode 42",
                    "due_at": now + timedelta(days=10),
                    "module": "media",
                    "sub_kind": "podcast",
                    "priority": 1,
                    "condition_id": None,
                }
            ]
            with patch("app.core.deadlines.collect_deadlines", return_value=changed_mock):
                is_fresh, title = await continuity_svc._check_source_freshness(db, source_media)
                assert is_fresh is False
                assert title == "Release Episode 42"

            # Non-todo deadline removed/completed -> Stale
            with patch("app.core.deadlines.collect_deadlines", return_value=[]):
                is_fresh, title = await continuity_svc._check_source_freshness(db, source_media)
                assert is_fresh is False
                assert title is None


async def test_current_scope_a_does_not_leak_project_b(a2_session: AgentSession):
    """When current scope is Project A, Project B sources stored in session must NEVER be reused or injected."""
    async with SessionLocal() as db:
        now = datetime.now(UTC)

        ent_a = await create_entity(db, type="project", title="Project Alpha")
        proj_a = Project(id=ent_a.id, status="active", next_action="Action A")
        db.add(proj_a)

        ent_b = await create_entity(db, type="project", title="Project Beta")
        proj_b = Project(id=ent_b.id, status="active", next_action="Action B")
        db.add(proj_b)
        await db.commit()

        # Seed initial session context with scope=Project Alpha
        ctx0 = AgentSessionContext(
            session_id=a2_session.id,
            turn_id=None,
            schema_version=1,
            is_first_turn=True,
            item_count=3,
            char_count=500,
            truncated=False,
            omitted_count=0,
            degraded_reasons=[],
            scope_project=str(ent_a.id),
            created_at=now,
        )
        db.add(ctx0)

        # Seed stored sources: Project A + Project B + General
        src_a = AgentSessionSource(
            session_id=a2_session.id,
            source_id=f"entity:{ent_a.id}",
            source_type="project",
            source_version=continuity_svc.compute_project_source_version("Project Alpha", "active", "Action A"),
            scope_project=str(ent_a.id),
            delivered_at=now,
            expires_at=now + timedelta(minutes=60),
        )
        src_b = AgentSessionSource(
            session_id=a2_session.id,
            source_id=f"entity:{ent_b.id}",
            source_type="project",
            source_version=continuity_svc.compute_project_source_version("Project Beta", "active", "Action B"),
            scope_project=str(ent_b.id),
            delivered_at=now,
            expires_at=now + timedelta(minutes=60),
        )
        src_gen = AgentSessionSource(
            session_id=a2_session.id,
            source_id="hot_memory:general-rule",
            source_type="hot_memory",
            source_version="1",
            scope_project=None,
            delivered_at=now,
            expires_at=now + timedelta(minutes=60),
        )
        db.add_all([src_a, src_b, src_gen])
        await db.commit()

        # Mock general rule freshness
        mock_item = MagicMock(memory_id="general-rule", title="General Rule", text="Rule text", revision=1)
        mock_ctx = MagicMock(profile=[mock_item], constraints=[], goals=[], decisions=[], preferences=[])

        with patch("app.integrations.agent.hot_memory.get_context", return_value=mock_ctx):
            packet, sources, rendered, degraded = await continuity_svc.compose_later_turn_context(
                db,
                session_row=a2_session,
                transient_prompt="bunu biraz aç",
                scope_project=str(ent_a.id),
            )

        assert rendered is not None
        assert "Project Alpha" in rendered
        # Project Beta must STRICTLY NOT be in rendered context!
        assert "Project Beta" not in rendered
        assert not any(s.scope_project == str(ent_b.id) for s in sources)


async def test_arbitrary_90_agent_note_not_treated_as_preference(tmp_path: Path):
    """An arbitrary note in 90 Agent must NOT be treated as durable_preferences."""
    agent_dir = tmp_path / "90 Agent"
    agent_dir.mkdir(parents=True)
    random_note = agent_dir / "random_notes.md"
    random_note.write_text("# Random Note\nSome completely arbitrary scratch content here.")

    with patch("app.config.settings.obsidian_vault_path", str(tmp_path)), \
         patch("app.integrations.agent.knowledge.is_vault_accessible", return_value=True):
        notes, degraded = await continuity_svc._collect_vault_notes(scope_project=None)
        # Must not return arbitrary notes as durable preferences
        for n in notes:
            assert n.get("kind") != "preference"
            assert "Some completely arbitrary" not in n.get("snippet", "")


async def test_excluded_and_policy_rejected_vault_note_never_injected(tmp_path: Path):
    """Vault notes in excluded directories or matching memory exclusion policy are rejected."""
    excluded_dir = tmp_path / ".git"
    excluded_dir.mkdir()
    secret_note = excluded_dir / "secret.md"
    secret_note.write_text("CONFIDENTIAL")

    async with SessionLocal() as db:
        now = datetime.now(UTC)
        source_row = AgentSessionSource(
            session_id=12345,
            source_id="vault:.git/secret.md",
            source_type="vault_note",
            source_version="xyz",
            delivered_at=now,
            expires_at=now + timedelta(minutes=60),
        )

        with patch("app.config.settings.obsidian_vault_path", str(tmp_path)):
            is_fresh, title = await continuity_svc._check_source_freshness(db, source_row)
            assert is_fresh is False
            assert title is None


async def test_vault_traversal_source_id_rejected(tmp_path: Path):
    """Path traversal in vault source ID (e.g. ../../etc/passwd) must be rejected safely."""
    async with SessionLocal() as db:
        now = datetime.now(UTC)
        source_row = AgentSessionSource(
            session_id=12345,
            source_id="vault:../../etc/passwd",
            source_type="vault_note",
            source_version="xyz",
            delivered_at=now,
            expires_at=now + timedelta(minutes=60),
        )

        with patch("app.config.settings.obsidian_vault_path", str(tmp_path)):
            is_fresh, title = await continuity_svc._check_source_freshness(db, source_row)
            assert is_fresh is False
            assert title is None


def test_final_hard_ceiling_sets_truncation_diagnostics():
    """If hard ceiling cuts text, diagnostics.truncated MUST be True and ending wrapper must be valid."""
    from app.modules.agent_continuity.schemas import BootstrapContinuity, BootstrapHotMemory
    conventions = ["A" * 900 for _ in range(3)]
    preferences = ["B" * 900 for _ in range(3)]
    packet = BootstrapPacketV1(
        session_key="test_sess",
        generated_at=datetime.now(UTC).isoformat(),
        identity=BootstrapIdentity(
            interaction_conventions=conventions,
            durable_preferences=preferences,
        ),
        operational_state=OperationalState(open_todos_count=0),
        continuity=BootstrapContinuity(),
        hot_memory=BootstrapHotMemory(items=[]),
        diagnostics=BootstrapDiagnostics(truncated=False, omitted_count=0),
    )

    rendered = render_bootstrap_context(packet, enforce_hard_ceiling=True)
    assert len(rendered) <= 4000
    assert rendered.endswith("</forkos-context>")
    assert packet.diagnostics.truncated is True

