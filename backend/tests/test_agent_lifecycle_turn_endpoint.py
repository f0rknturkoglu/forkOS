"""Integration tests for POST /api/agent/lifecycle/turn orchestration endpoint."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db import SessionLocal
from app.main import app
from app.modules.agent_lifecycle.models import AgentSession
from app.modules.agent_lifecycle.service import session_key


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_turn_endpoint_first_turn(client: AsyncClient):
    payload = {
        "schema_version": 1,
        "harness": "hermes",
        "session_id": "test_turn_endpoint_sess_1",
        "turn_id": "turn_001",
        "platform": "desktop",
        "is_first_turn": True,
        "user_message": "merhaba",
    }
    resp = await client.post("/api/agent/lifecycle/turn", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["lifecycle"]["accepted"] is True
    assert data["lifecycle"]["event"] == "session_start"
    assert data["lifecycle"]["duplicate"] is False
    assert data["rendered_context"] is not None
    assert "<forkos-context" in data["rendered_context"]
    assert data["packet"] is not None
    assert data["packet"]["is_first_turn"] is True

    # Verify A1 state is committed in database
    async with SessionLocal() as db:
        sk = session_key("hermes", "test_turn_endpoint_sess_1")
        row = (await db.execute(select(AgentSession).where(AgentSession.session_key == sk))).scalar_one_or_none()
        assert row is not None
        assert row.turn_count >= 1


async def test_turn_endpoint_duplicate_idempotent(client: AsyncClient):
    payload = {
        "schema_version": 1,
        "harness": "hermes",
        "session_id": "test_turn_endpoint_sess_dup",
        "turn_id": "turn_dup_001",
        "platform": "desktop",
        "is_first_turn": True,
        "user_message": "ilk mesaj",
    }
    # First call
    resp1 = await client.post("/api/agent/lifecycle/turn", json=payload)
    assert resp1.status_code == 200
    assert resp1.json()["lifecycle"]["duplicate"] is False

    # Duplicate call with same turn_id
    resp2 = await client.post("/api/agent/lifecycle/turn", json=payload)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["lifecycle"]["duplicate"] is True
    assert data2["rendered_context"] is None
    assert data2["packet"] is None


async def test_turn_endpoint_later_turn_ambiguous_continuation(client: AsyncClient):
    sess_id = "test_turn_endpoint_sess_cont"
    # First turn to establish sources
    p1 = {
        "schema_version": 1,
        "harness": "hermes",
        "session_id": sess_id,
        "turn_id": "turn_c_001",
        "platform": "desktop",
        "is_first_turn": True,
        "user_message": "ilk mesaj",
    }
    r1 = await client.post("/api/agent/lifecycle/turn", json=p1)
    assert r1.status_code == 200

    # Turn 2: ambiguous follow-up
    p2 = {
        "schema_version": 1,
        "harness": "hermes",
        "session_id": sess_id,
        "turn_id": "turn_c_002",
        "platform": "desktop",
        "is_first_turn": False,
        "user_message": "bunu biraz aç",
    }
    r2 = await client.post("/api/agent/lifecycle/turn", json=p2)
    assert r2.status_code == 200
    data2 = r2.json()

    assert data2["lifecycle"]["accepted"] is True
    assert data2["lifecycle"]["event"] == "turn_seen"
    assert data2["lifecycle"]["duplicate"] is False
    assert data2["packet"] is None  # Full bootstrap not repeated


async def test_turn_endpoint_fails_open_on_a2_internal_error(client: AsyncClient):
    sess_id = "test_turn_endpoint_sess_crash"
    payload = {
        "schema_version": 1,
        "harness": "hermes",
        "session_id": sess_id,
        "turn_id": "turn_crash_001",
        "platform": "desktop",
        "is_first_turn": True,
        "user_message": "merhaba",
    }

    with patch(
        "app.modules.agent_continuity.service.compose_first_turn_bootstrap",
        side_effect=RuntimeError("Simulated unexpected composition crash"),
    ):
        resp = await client.post("/api/agent/lifecycle/turn", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["lifecycle"]["accepted"] is True
        assert data["rendered_context"] is None
        assert any("CONTEXT_COMPOSITION_FAILED" in r for r in data["degraded_reasons"])

    # Invariant: A1 lifecycle observation MUST be committed in DB despite A2 crash
    async with SessionLocal() as db:
        sk = session_key("hermes", sess_id)
        row = (await db.execute(select(AgentSession).where(AgentSession.session_key == sk))).scalar_one_or_none()
        assert row is not None
        assert row.status == "active"


async def test_continuity_status_endpoint(client: AsyncClient):
    resp = await client.get("/api/agent/continuity/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "available" in data
    assert data["available"] is True
    assert "active_source_count" in data
