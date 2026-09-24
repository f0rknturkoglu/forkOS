"""Opt-in real poorjev NLI over synthetic A4 candidate on test PostgreSQL."""

import json
import os

import pytest

from app.config import settings
from app.db import SessionLocal
from app.integrations.judgment.memory import judge_memory
from app.integrations.judgment.poorjev_memory import MODEL_ID, MODEL_REVISION
from app.integrations.obsidian import semantic_memory as sem_storage
from app.modules.semantic_memory.models import AgentSemanticCandidate
from tests.test_a5_memory_binding_db import _fixture_candidate

pytestmark = pytest.mark.a5_memory_live


async def test_a4_candidate_shadow_live_on_local_model(monkeypatch, tmp_path):
    if os.getenv("A5_MEMORY_LIVE") != "1":
        pytest.skip("Set A5_MEMORY_LIVE=1 only with a local model and isolated test DB")
    monkeypatch.setattr(sem_storage, "readable_root", lambda: tmp_path)
    monkeypatch.setattr(settings, "a5_memory_model_path", os.environ["A5_MEMORY_MODEL_PATH"])
    candidate_id, _ = await _fixture_candidate()
    async with SessionLocal() as session:
        result = await judge_memory(session, candidate_id, mode="shadow")
        candidate = await session.get(AgentSemanticCandidate, candidate_id, populate_existing=True)
    assert result.status == "success", result.reason
    assert result.provenance is not None
    assert result.provenance.provider_id == "poorjev-local-nli"
    assert result.provenance.model_id == MODEL_ID
    assert result.provenance.model_revision == MODEL_REVISION
    assert result.signals is not None
    assert result.review_flags == ()
    assert candidate is not None and candidate.status == "proposed"
    assert not list(tmp_path.rglob("*.md"))
    print(json.dumps({
        "status": result.status, "provider": result.provenance.provider_id,
        "model_id": result.provenance.model_id,
        "model_revision": result.provenance.model_revision,
        "latency_ms": result.provenance.latency_ms,
        "signals": result.signals.model_dump(),
        "baseline_status": result.baseline_status,
        "candidate_status_after": candidate.status,
    }, sort_keys=True))
