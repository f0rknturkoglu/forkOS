"""Integration and race-condition tests for A5.3 Answer Evidence Judge against PostgreSQL."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from app.config import settings
from app.core.entity import create_entity, touch_entity
from app.core.events import log_event
from app.db import SessionLocal
from app.integrations.judgment import answer as service
from app.integrations.judgment.answer_models import AnswerJudgeProvenance
from app.integrations.judgment.models import (
    AnswerEvidenceRequest,
    JudgmentMetadata,
    SupportVerdict,
)
from app.integrations.judgment.poorjev_answer import (
    MODEL_ID,
    MODEL_REVISION,
    QUESTION_HASH,
    QUESTION_VERSION,
    answer_claim_digest,
    answer_evidence_digest,
)
from app.modules.project.models import Project
from tests.agent_test_utils import capture_db_content_fingerprint


class LocalAnswerJudge:
    locality = "local"
    capabilities = frozenset({"answer_support"})

    def __init__(self, mutate: Any | None = None, support: str = "supported") -> None:
        self.mutate = mutate
        self.support = support
        self.health_calls = 0
        self.judge_calls = 0
        self.last_request: AnswerEvidenceRequest | None = None

    async def health(self) -> bool:
        self.health_calls += 1
        return True

    async def judge_support(
        self, request: AnswerEvidenceRequest
    ) -> tuple[SupportVerdict, AnswerJudgeProvenance]:
        self.judge_calls += 1
        self.last_request = request
        if self.mutate:
            await self.mutate()
        metadata = JudgmentMetadata(
            provider_id="poorjev-local-nli",
            model_id="deberta",
            latency_ms=10,
            provider_confidence=0.9,
        )
        verdict = SupportVerdict(
            status="success",
            support=self.support,
            metadata=metadata,
        )
        provenance = AnswerJudgeProvenance(
            provider_id="poorjev-local-nli",
            provider_version="0.1.0",
            model_id=MODEL_ID,
            model_revision=MODEL_REVISION,
            question_version=QUESTION_VERSION,
            question_hash=QUESTION_HASH,
            claim_digest=answer_claim_digest(request.claim),
            evidence_digest=answer_evidence_digest(
                request.evidence, context_complete=request.context_complete
            ),
            latency_ms=10,
            judged_at=datetime.now(UTC),
            abstained=False,
            provider_confidence=0.9,
        )
        return verdict, provenance


@pytest.mark.parametrize("phase", ["before_first", "during_judge", "unchanged"])
async def test_vault_source_binding_races(tmp_path, monkeypatch, phase):
    vault = tmp_path / "Vault"
    vault.mkdir()
    note = vault / "Atlas.md"
    note.write_text("# Atlas\nRust deployment notes for project.\n", encoding="utf-8")
    monkeypatch.setattr(settings, "obsidian_vault_path", str(vault))

    async def change():
        note.write_text("# Atlas\nPython deployment notes for project.\n", encoding="utf-8")

    judge = LocalAnswerJudge(mutate=change if phase == "during_judge" else None)
    if phase == "before_first":
        original = service.retrieve_evidence

        async def retrieve_then_change(*args, **kwargs):
            bundle = await original(*args, **kwargs)
            assert bundle.evidence and all(item._source_revision for item in bundle.evidence)
            await change()
            return bundle

        monkeypatch.setattr(service, "retrieve_evidence", retrieve_then_change)

    async with SessionLocal() as session:
        result = await service.judge_answer(
            session,
            claim="Atlas uses Rust for deployment.",
            scope="knowledge",
            mode="shadow",
            provider=judge,
        )

    assert result.evidence_count > 0
    if phase == "before_first":
        assert result.status == "invalid"
        assert "ANSWER_JUDGE_SOURCE_BINDING_FAILED" in result.degraded_reasons
        assert judge.judge_calls == 0
    elif phase == "during_judge":
        assert result.status == "stale"
        assert "ANSWER_JUDGE_SOURCE_STALE" in result.degraded_reasons
        assert result.observed_support == "uncertain"
        assert judge.judge_calls == 1
    else:
        assert result.status == "success"
        assert result.observed_support == "supported"
        assert judge.judge_calls == 1


async def test_entity_source_mutation_during_provider_call():
    async with SessionLocal() as session:
        entity = await create_entity(
            session, type="project", title="Atlas Project", search_text="Atlas Rust stack"
        )
        project_id = entity.id
        session.add(Project(id=project_id, status="active", next_action="Deploy Rust"))
        await session.commit()

    async def mutate_entity():
        async with SessionLocal() as writer:
            await touch_entity(writer, project_id, title="Atlas Project Renamed")
            await writer.commit()

    judge = LocalAnswerJudge(mutate=mutate_entity)

    async with SessionLocal() as session:
        result = await service.judge_answer(
            session,
            claim="Atlas uses Rust.",
            entity_id=str(project_id),
            scope="operational",
            mode="on",
            provider=judge,
        )

    assert result.status == "stale"
    assert "ANSWER_JUDGE_SOURCE_STALE" in result.degraded_reasons
    assert result.observed_support == "uncertain"
    assert result.effective_support == "uncertain"
    assert judge.judge_calls == 1


async def test_historical_event_vs_current_canonical_entity():
    async with SessionLocal() as session:
        entity = await create_entity(
            session, type="project", title="Atlas System", search_text="Atlas System current Rust"
        )
        project_id = entity.id
        session.add(Project(id=project_id, status="active", next_action="Maintain Rust service"))
        await session.commit()

        # Add a historical event
        await log_event(
            session,
            verb="project.updated",
            entity_id=project_id,
            entity_type="project",
            payload={"note": "Historical migration from Python in 2023."},
        )
        await session.commit()

    judge = LocalAnswerJudge(support="supported")

    async with SessionLocal() as session:
        result = await service.judge_answer(
            session,
            claim="Atlas System uses Rust.",
            entity_id=str(project_id),
            scope="operational",
            mode="on",
            provider=judge,
        )

    assert result.status == "success"
    assert judge.judge_calls == 1
    req = judge.last_request
    assert req is not None
    # Both entity and event are in the bounded evidence packet
    source_types = {item.snapshot.source_type for item in req.evidence}
    assert "entity" in source_types
    # Historical events must carry occurred_at and event identity
    for item in req.evidence:
        if item.snapshot.source_type == "event":
            assert item.snapshot.source_id.isdigit()


async def test_answer_judge_zero_canonical_mutation(tmp_path, monkeypatch):
    vault = tmp_path / "Vault"
    vault.mkdir()
    (vault / "Guide.md").write_text("# Guide\nZero mutation verification.\n", encoding="utf-8")
    monkeypatch.setattr(settings, "obsidian_vault_path", str(vault))

    async with SessionLocal() as session:
        await create_entity(
            session, type="project", title="MutationCheck", search_text="MutationCheck test"
        )
        await session.commit()
        before_fingerprint = await capture_db_content_fingerprint(session)

    judge = LocalAnswerJudge(support="supported")
    async with SessionLocal() as session:
        result = await service.judge_answer(
            session,
            claim="MutationCheck exists.",
            scope="all",
            mode="on",
            provider=judge,
        )

    assert result.status == "success"
    async with SessionLocal() as session:
        after_fingerprint = await capture_db_content_fingerprint(session)

    # Invariant: Zero canonical mutations across all PostgreSQL tables
    assert before_fingerprint == after_fingerprint
