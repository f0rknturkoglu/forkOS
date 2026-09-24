"""Opt-in synthetic H3 -> A5.1 -> jevmlx end-to-end validation."""

import os
import time
import uuid
from datetime import UTC, datetime

import pytest

from app.core.models import Entity, Event
from app.db import SessionLocal
from app.integrations.agent.evidence import retrieve_evidence
from app.integrations.judgment.context import judge_context
from app.integrations.judgment.jevmlx import JevMlxProvider

pytestmark = [
    pytest.mark.a5_context_live,
    pytest.mark.skipif(os.environ.get("A5_CONTEXT_LIVE") != "1", reason="set A5_CONTEXT_LIVE=1 for real local jevmlx"),
]


async def test_synthetic_h3_to_local_context_judge():
    entity_id = uuid.uuid4()
    async with SessionLocal() as session:
        session.add(Entity(id=entity_id, type="todo", title="Synthetic Atlas Rust task", search_text="Atlas Rust"))
        await session.flush()
        session.add(Event(
            entity_id=entity_id, entity_type="todo", verb="todo.created",
            payload={"synthetic": "Atlas task created"}, occurred_at=datetime.now(UTC),
        ))
        await session.commit()

    async with SessionLocal() as session:
        provider = JevMlxProvider("http://127.0.0.1:8000", timeout_seconds=5)
        assert await provider.health()
        baseline = await retrieve_evidence(
            session, query="What is the current Synthetic Atlas Rust task?",
            entity_id=str(entity_id), scope="operational",
        )
        started = time.perf_counter()
        result = await judge_context(
            session, query="What is the current Synthetic Atlas Rust task?",
            entity_id=str(entity_id), scope="operational", mode="shadow", provider=provider,
        )
        elapsed = round((time.perf_counter() - started) * 1000, 2)
        assert result.status == "success"
        assert result.bundle == baseline
        assert result.effective_order == result.baseline_order
        assert set(result.advisory_order) == set(result.baseline_order)
        assert len(result.verdicts) == len(baseline.evidence) >= 1
        print(f"A5 synthetic H3->judge end-to-end latency_ms={elapsed} evidence={len(baseline.evidence)}")
