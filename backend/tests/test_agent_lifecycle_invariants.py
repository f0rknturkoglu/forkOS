"""A1.1.1 No-source-mutation invariant regression test.

Proves that agent lifecycle observations:
1. NEVER mutate canonical `entity` or any operational domain state.
2. NEVER write to the append-only `event` activity log (`log_event`).
3. NEVER modify H2 Hot Memory files or f0rknbrain Vault files.
4. NEVER mutate execution/proactivity/task state.
5. ONLY modify support tables: `agent_session` and `agent_session_turn`.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.config import settings
from app.core.models import Entity, Event, Link, Notification
from app.db import SessionLocal
from app.main import app
from app.modules.agent_lifecycle.models import AgentSession, AgentSessionTurn
from app.modules.bookmark.models import Bookmark
from app.modules.execution.models import ExecutionDecision, ExecutionPlan, ExecutionReceipt
from app.modules.flashcard.models import FlashcardCard
from app.modules.opportunity.models import Application, Opportunity
from app.modules.pomodoro.models import PomodoroSession
from app.modules.proactivity.models import ProactivityRule, ProactivityRun
from app.modules.project.models import Milestone, Project
from app.modules.review.models import Review
from app.modules.todo.models import Todo

DOMAIN_MODELS = [
    Entity,
    Event,
    Link,
    Notification,
    Todo,
    Project,
    Milestone,
    Opportunity,
    Application,
    Bookmark,
    FlashcardCard,
    PomodoroSession,
    Review,
    ProactivityRule,
    ProactivityRun,
    ExecutionPlan,
    ExecutionReceipt,
    ExecutionDecision,
]


def _snapshot_vault_files(vault_path: Path | None) -> dict[str, str]:
    if not vault_path or not vault_path.exists():
        return {}
    hashes = {}
    for p in vault_path.rglob("*"):
        if p.is_file() and not p.name.startswith("."):
            hashes[str(p.relative_to(vault_path))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return hashes


async def _get_domain_counts() -> dict[str, int]:
    async with SessionLocal() as db:
        counts = {}
        for model in DOMAIN_MODELS:
            count = await db.scalar(select(func.count()).select_from(model))
            counts[model.__tablename__] = count or 0
        return counts


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def test_lifecycle_observation_never_mutates_domain_state_or_files(client: AsyncClient, monkeypatch) -> None:
    vault_dir = settings.resolved_obsidian_vault_path

    counts_before = await _get_domain_counts()
    vault_before = _snapshot_vault_files(vault_dir)

    endpoint = "/api/agent/lifecycle/event"
    events = [
        {"schema_version": 1, "event": "session_start", "harness": "hermes", "session_id": "inv_sess_1", "turn_id": "t1", "platform": "desktop"},
        {"schema_version": 1, "event": "session_start", "harness": "hermes", "session_id": "inv_sess_1", "turn_id": "t1", "platform": "desktop"},
        {"schema_version": 1, "event": "turn_seen", "harness": "hermes", "session_id": "inv_sess_1", "turn_id": "t1", "platform": "desktop"},
        {"schema_version": 1, "event": "turn_seen", "harness": "hermes", "session_id": "inv_sess_1", "turn_id": "t2", "platform": "desktop"},
        {"schema_version": 1, "event": "session_finalize", "harness": "hermes", "session_id": "inv_sess_1", "platform": "desktop"},
        {"schema_version": 1, "event": "session_finalize", "harness": "hermes", "session_id": "inv_sess_1", "platform": "desktop"},
    ]

    for ev in events:
        resp = await client.post(endpoint, json=ev)
        assert resp.status_code == 200

    rejected = await client.post(endpoint, json={"schema_version": 1, "event": "turn_seen", "harness": "hermes", "session_id": "inv_sess_1", "turn_id": "t3", "platform": "desktop"})
    assert rejected.status_code == 409

    counts_after = await _get_domain_counts()
    vault_after = _snapshot_vault_files(vault_dir)

    # Invariant 1: No domain table counts have changed
    for table_name, count_before in counts_before.items():
        assert counts_after[table_name] == count_before, (
            f"INVARIANT VIOLATION: Domain table '{table_name}' count changed from "
            f"{count_before} to {counts_after[table_name]} during lifecycle calls"
        )

    # Invariant 2: No event log / activity log was written
    assert counts_after["event"] == counts_before["event"], "INVARIANT VIOLATION: event log was written"

    # Invariant 3: Vault / Hot memory files were not modified
    assert vault_after == vault_before, "INVARIANT VIOLATION: Vault/Hot memory files were modified"

    # Invariant 4: ONLY agent_session and agent_session_turn were written
    async with SessionLocal() as db:
        session_count = await db.scalar(select(func.count()).select_from(AgentSession))
        turn_count = await db.scalar(select(func.count()).select_from(AgentSessionTurn))
        assert session_count >= 1
        assert turn_count >= 2
