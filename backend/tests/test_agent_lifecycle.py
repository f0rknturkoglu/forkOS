"""A1 REST sözleşmesi, gizlilik, sıra ve PostgreSQL eşzamanlılığı."""

from __future__ import annotations

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.db import SessionLocal
from app.main import app
from app.modules.agent_lifecycle.models import AgentSession, AgentSessionTurn


def payload(event: str, *, turn_id: str | None = None, session_id: str = "RAW_PRIVATE_SESSION") -> dict:
    value = {"schema_version": 1, "event": event, "harness": "hermes", "session_id": session_id, "platform": "desktop"}
    if turn_id is not None:
        value["turn_id"] = turn_id
    return value


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def test_validation_and_privacy(client: AsyncClient) -> None:
    invalid = [
        {**payload("unknown"), "event": "unknown"},
        payload("session_start", session_id=""),
        payload("session_start", session_id="x" * 257),
        payload("session_start", session_id="bad\x7fid"),
        {**payload("session_start"), "platform": "x" * 65},
        payload("turn_seen"),
        {**payload("session_start"), "schema_version": 2},
        {**payload("session_start"), "user_message": "VERY_PRIVATE_MESSAGE"},
        {**payload("session_start"), "conversation_history": ["VERY_PRIVATE_MESSAGE"]},
    ]
    for body in invalid:
        assert (await client.post("/api/agent/lifecycle/event", json=body)).status_code == 422

    assert (await client.post("/api/agent/lifecycle/event", json=payload("session_start", turn_id="RAW_PRIVATE_TURN"))).status_code == 200
    async with SessionLocal() as db:
        row = (await db.execute(select(AgentSession))).scalar_one()
        turn = (await db.execute(select(AgentSessionTurn))).scalar_one()
    assert row.session_key != "RAW_PRIVATE_SESSION" and len(row.session_key) == 64
    assert turn.turn_key != "RAW_PRIVATE_TURN" and len(turn.turn_key) == 64
    assert "RAW_PRIVATE" not in repr(row.__dict__) + repr(turn.__dict__)
    assert row.turn_count == 1


async def test_idempotency_finalize_and_post_finalized_policy(client: AsyncClient) -> None:
    endpoint = "/api/agent/lifecycle/event"
    first = payload("session_start", turn_id="t1")
    assert (await client.post(endpoint, json=first)).json()["duplicate"] is False
    assert (await client.post(endpoint, json=first)).json()["duplicate"] is True
    assert (await client.post(endpoint, json=payload("turn_seen", turn_id="t1"))).json()["duplicate"] is True
    assert (await client.post(endpoint, json=payload("turn_seen", turn_id="t2"))).json()["duplicate"] is False
    assert (await client.post(endpoint, json=payload("session_finalize"))).json()["duplicate"] is False
    assert (await client.post(endpoint, json=payload("session_finalize"))).json()["duplicate"] is True
    rejected = await client.post(endpoint, json=payload("turn_seen", turn_id="t3"))
    assert rejected.status_code == 409
    assert rejected.json()["detail"]["code"] == "LIFECYCLE_ALREADY_FINALIZED"
    async with SessionLocal() as db:
        row = (await db.execute(select(AgentSession))).scalar_one()
        assert row.turn_count == 2 and row.status == "finalized" and row.finalized_at
        assert await db.scalar(select(func.count()).select_from(AgentSessionTurn)) == 2


async def test_out_of_order_is_visible(client: AsyncClient) -> None:
    endpoint = "/api/agent/lifecycle/event"
    assert (await client.post(endpoint, json=payload("turn_seen", turn_id="late", session_id="s1"))).status_code == 200
    assert (await client.post(endpoint, json=payload("session_finalize", session_id="s2"))).status_code == 200
    async with SessionLocal() as db:
        rows = (await db.execute(select(AgentSession))).scalars().all()
        assert len(rows) == 2
        assert all(row.start_seen_at is None for row in rows)
        assert sorted(row.turn_count for row in rows) == [0, 1]
    status = (await client.get("/api/agent/lifecycle/status")).json()
    assert status["incomplete_session_count"] == 2
    assert status["active_sessions"] == 1
    assert status["last_finalized_at"] is not None


async def test_concurrent_duplicate_turn_has_one_row_and_count(client: AsyncClient) -> None:
    endpoint = "/api/agent/lifecycle/event"
    await client.post(endpoint, json=payload("session_start", turn_id="first"))
    body = payload("turn_seen", turn_id="same")
    replies = await asyncio.gather(*(client.post(endpoint, json=body) for _ in range(2)))
    assert [r.status_code for r in replies] == [200, 200]
    assert sorted(r.json()["duplicate"] for r in replies) == [False, True]
    async with SessionLocal() as db:
        row = (await db.execute(select(AgentSession))).scalar_one()
        assert row.turn_count == 2
        assert await db.scalar(select(func.count()).select_from(AgentSessionTurn)) == 2
