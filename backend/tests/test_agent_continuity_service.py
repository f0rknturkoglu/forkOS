"""Tests for A2 context composition service (first-turn bootstrap, hard budget, fail-open)."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.db import SessionLocal
from app.modules.agent_continuity import service as continuity_svc
from app.modules.agent_continuity.models import AgentSessionContext, AgentSessionSource
from app.modules.agent_lifecycle.models import AgentSession
from app.modules.agent_lifecycle.service import session_key


@pytest.fixture
async def test_session():
    async with SessionLocal() as db:
        sk = session_key("hermes", "test_compose_session_1")
        existing = (await db.execute(select(AgentSession).where(AgentSession.session_key == sk))).scalar_one_or_none()
        if not existing:
            from datetime import UTC, datetime
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
            return sess
        return existing


async def test_compose_first_turn_bootstrap_success(test_session: AgentSession):
    async with SessionLocal() as db:
        packet, sources, rendered = await continuity_svc.compose_first_turn_bootstrap(
            db,
            session_row=test_session,
            scope_project=None,
        )

        assert packet.schema_version == 1
        assert packet.session_key == test_session.session_key
        assert packet.is_first_turn is True
        assert len(rendered) <= 4000
        assert "<forkos-context" in rendered
        assert "</forkos-context>" in rendered
        assert packet.diagnostics.available is True

        # Verify support state was persisted
        ctx_row = (await db.execute(
            select(AgentSessionContext).where(AgentSessionContext.session_id == test_session.id)
        )).scalar_one_or_none()
        assert ctx_row is not None
        assert ctx_row.is_first_turn is True
        assert ctx_row.char_count == len(rendered)

        source_rows = (await db.execute(
            select(AgentSessionSource).where(AgentSessionSource.session_id == test_session.id)
        )).scalars().all()
        assert len(source_rows) <= 5
        for s in source_rows:
            assert not s.source_id.startswith("/")
            assert "/Users/" not in s.source_id


async def test_compose_bootstrap_budget_truncation(test_session: AgentSession, monkeypatch):
    # Mock very long active projects to force budget truncation
    from app.modules.agent_continuity.schemas import OperationalProject

    original_projects = continuity_svc._collect_operational_projects

    async def mock_long_projects(*args, **kwargs):
        return [
            OperationalProject(id=f"p-{i}", title=f"Very Long Project Name {i} " + "X" * 400, status="active", next_action="Step " + "Y" * 450)
            for i in range(5)
        ]

    monkeypatch.setattr(continuity_svc, "_collect_operational_projects", mock_long_projects)

    async with SessionLocal() as db:
        packet, sources, rendered = await continuity_svc.compose_first_turn_bootstrap(
            db,
            session_row=test_session,
            scope_project=None,
        )
        assert len(rendered) <= 4000
        assert packet.diagnostics.truncated is True
        assert packet.diagnostics.omitted_count > 0


async def test_compose_bootstrap_fails_open_on_vault_error(test_session: AgentSession, monkeypatch):
    # Simulate Vault unavailability
    def mock_vault_error(*args, **kwargs):
        raise RuntimeError("Vault disk unmounted")

    monkeypatch.setattr("app.integrations.agent.knowledge.is_vault_accessible", mock_vault_error)

    async with SessionLocal() as db:
        packet, sources, rendered = await continuity_svc.compose_first_turn_bootstrap(
            db,
            session_row=test_session,
            scope_project=None,
        )
        # Does not raise! Degrades gracefully
        assert "VAULT_UNAVAILABLE" in packet.diagnostics.degraded_reasons
        assert "<forkos-context" in rendered


async def test_compose_bootstrap_never_calls_os_walk(test_session: AgentSession, monkeypatch):
    """Regresyon testi: İlk tur bağlam üretiminin hot path'i asla os.walk çalıştırmamalıdır."""
    import os
    walk_called = False

    def forbidden_walk(*args, **kwargs):
        nonlocal walk_called
        walk_called = True
        raise AssertionError("Hot-path os.walk violation!")

    monkeypatch.setattr(os, "walk", forbidden_walk)

    async with SessionLocal() as db:
        packet, sources, rendered = await continuity_svc.compose_first_turn_bootstrap(
            db,
            session_row=test_session,
            scope_project=None,
        )
        assert not walk_called, "os.walk must never be called during first-turn bootstrap hot path!"
        assert "<forkos-context" in rendered
