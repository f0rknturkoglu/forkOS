"""Opt-in real poorjev NLI over synthetic claim and H3 evidence on test PostgreSQL."""

import json
import os

import pytest

from app.config import settings
from app.core.entity import create_entity
from app.db import SessionLocal
from app.integrations.judgment.answer import judge_answer
from app.integrations.judgment.poorjev_answer import MODEL_ID, MODEL_REVISION
from app.modules.project.models import Project

pytestmark = pytest.mark.a5_answer_live


async def test_answer_judge_shadow_live_on_local_model(monkeypatch, tmp_path):
    if os.getenv("A5_ANSWER_LIVE") != "1":
        pytest.skip("Set A5_ANSWER_LIVE=1 only with a local model and isolated test DB")

    model_path = os.getenv("A5_ANSWER_MODEL_PATH") or os.getenv("A5_MEMORY_MODEL_PATH")
    if not model_path:
        pytest.skip("A5_ANSWER_MODEL_PATH or A5_MEMORY_MODEL_PATH is required for live test")

    monkeypatch.setattr(settings, "a5_answer_model_path", model_path)

    async with SessionLocal() as session:
        entity = await create_entity(
            session, type="project", title="Atlas Project", search_text="Atlas Project Rust stack"
        )
        project_id = entity.id
        session.add(Project(id=project_id, status="active", next_action="Deploy Rust"))
        await session.commit()

    async with SessionLocal() as session:
        result = await judge_answer(
            session,
            claim="Atlas Project uses Rust.",
            entity_id=str(project_id),
            scope="operational",
            mode="shadow",
        )

    assert result.status == "success", result.degraded_reasons
    assert result.observed_support in {"supported", "insufficient", "uncertain", "contradicted"}
    assert result.effective_support == "uncertain"  # Zero downstream authority in shadow!
    assert result.provenance is not None
    assert result.provenance.provider_id == "poorjev-local-nli"
    assert result.provenance.provider_version == "0.1.0"
    assert result.provenance.model_id == MODEL_ID
    assert result.provenance.model_revision == MODEL_REVISION
    assert result.provenance.question_version == "a5-answer-questions-v1"
    assert result.provenance.question_hash is not None
    assert result.provenance.claim_digest is not None
    assert result.provenance.evidence_digest is not None
    print(
        json.dumps(
            {
                "status": result.status,
                "provider": result.provenance.provider_id,
                "model_id": result.provenance.model_id,
                "model_revision": result.provenance.model_revision,
                "latency_ms": result.provenance.latency_ms,
                "observed_support": result.observed_support,
                "effective_support": result.effective_support,
                "evidence_count": result.evidence_count,
                "context_complete": result.context_complete,
            },
            sort_keys=True,
        )
    )
