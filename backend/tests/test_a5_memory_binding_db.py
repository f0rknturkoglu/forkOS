"""Real PostgreSQL source binding, A4 baseline and TOCTOU checks."""

import uuid
from datetime import UTC, datetime

import pytest

from app.core.entity import create_entity, touch_entity
from app.core.events import log_event
from app.db import SessionLocal
from app.integrations.judgment.memory import judge_memory
from app.integrations.judgment.memory_models import MemoryJudgeProvenance, MemorySignals
from app.integrations.judgment.memory_sources import read_memory_source
from app.integrations.obsidian import semantic_memory as sem_storage
from app.modules.semantic_memory.models import AgentSemanticCandidate
from app.modules.semantic_memory.policy import compute_candidate_revision


class Provider:
    def __init__(self, mutate=None):
        self.calls = 0
        self.mutate = mutate

    async def judge(self, packet):
        self.calls += 1
        if self.mutate is not None:
            await self.mutate()
        return MemorySignals(
            evidence_support="supported", intent="explicit", durability="durable",
            scope_relation="same_scope", conditions_preserved="not_applicable",
            exceptions_preserved="not_applicable", relations=(),
        ), MemoryJudgeProvenance(
            provider_id="synthetic", provider_version="test", model_id="test",
            question_version="test", candidate_snapshot=packet.candidate_snapshot,
            source_snapshot=packet.source_snapshot, related_snapshot=packet.related_snapshot,
            policy_snapshot=packet.policy_snapshot, latency_ms=0,
            judged_at=datetime.now(UTC), abstained=False,
        )


async def _fixture_candidate():
    async with SessionLocal() as session:
        entity = await create_entity(session, type="project", title="Use Python for Atlas")
        event = await log_event(
            session, verb="project.updated", entity_id=entity.id, entity_type="project",
            payload={"title": "Use Python for Atlas"},
        )
        await session.flush()
        ref = f"event:{event.id}"
        source = await read_memory_source(session, ref)
        assert source is not None
        moment = datetime.now(UTC)
        candidate_id = uuid.uuid4()
        key = uuid.uuid4().hex
        session.add(AgentSemanticCandidate(
            id=candidate_id, candidate_key=key, kind="decision",
            statement="Use Python for Atlas", scope="project",
            scope_project=str(entity.id), suggested_destination="durable_vault",
            primary_evidence_class="canonical_source",
            evidence_refs=[{
                "ref": ref, "role": "canonical", "digest": None,
                "source_revision": source.revision,
            }], observed_at=moment, status="proposed", recurrence_count=1,
            first_seen_at=moment, last_seen_at=moment,
            revision=compute_candidate_revision(candidate_id, key, "proposed", 1, moment),
        ))
        await session.commit()
        return candidate_id, entity.id


async def test_stable_bound_source_returns_advice(monkeypatch, tmp_path):
    monkeypatch.setattr(sem_storage, "readable_root", lambda: tmp_path)
    candidate_id, _ = await _fixture_candidate()
    provider = Provider()
    async with SessionLocal() as session:
        result = await judge_memory(session, candidate_id, provider=provider, mode="shadow")
    assert result.status == "success"
    assert result.signals is not None
    assert result.baseline_status == "proposed"
    assert result.review_flags == ()
    assert provider.calls == 1


async def test_missing_related_memory_root_fails_closed(monkeypatch):
    monkeypatch.setattr(sem_storage, "readable_root", lambda: None)
    candidate_id, _ = await _fixture_candidate()
    provider = Provider()
    async with SessionLocal() as session:
        result = await judge_memory(session, candidate_id, provider=provider, mode="shadow")
    assert result.status == "degraded"
    assert result.reason == "RELATED_UNAVAILABLE"
    assert provider.calls == 0


async def test_sensitive_candidate_never_reaches_provider(monkeypatch, tmp_path):
    monkeypatch.setattr(sem_storage, "readable_root", lambda: tmp_path)
    candidate_id, _ = await _fixture_candidate()
    async with SessionLocal() as session:
        candidate = await session.get(AgentSemanticCandidate, candidate_id)
        assert candidate is not None
        candidate.sensitivity = "sensitive"
        await session.commit()
    provider = Provider()
    async with SessionLocal() as session:
        result = await judge_memory(session, candidate_id, provider=provider, mode="on")
    assert result.status == "degraded"
    assert result.reason == "SENSITIVITY_BLOCKED"
    assert provider.calls == 0


async def test_source_mutated_before_first_snapshot_never_calls_provider(monkeypatch, tmp_path):
    monkeypatch.setattr(sem_storage, "readable_root", lambda: tmp_path)
    candidate_id, entity_id = await _fixture_candidate()
    async with SessionLocal() as session:
        await touch_entity(session, entity_id, title="Use Rust for Atlas")
        await log_event(session, verb="project.updated", entity_id=entity_id, entity_type="project")
        await session.commit()
    provider = Provider()
    async with SessionLocal() as session:
        result = await judge_memory(session, candidate_id, provider=provider, mode="shadow")
    assert result.status == "degraded"
    assert result.reason == "SOURCE_STALE"
    assert provider.calls == 0


async def test_source_mutated_during_call_discards_advice(monkeypatch, tmp_path):
    monkeypatch.setattr(sem_storage, "readable_root", lambda: tmp_path)
    candidate_id, entity_id = await _fixture_candidate()

    async def mutate():
        async with SessionLocal() as session:
            await touch_entity(session, entity_id, title="Use Rust for Atlas")
            await log_event(session, verb="project.updated", entity_id=entity_id, entity_type="project")
            await session.commit()

    provider = Provider(mutate)
    async with SessionLocal() as session:
        result = await judge_memory(session, candidate_id, provider=provider, mode="on")
    assert result.status == "stale"
    assert result.signals is None and result.review_flags == ()
    assert provider.calls == 1


@pytest.mark.parametrize("supersede", [False, True])
async def test_related_memory_changed_during_call_is_stale(monkeypatch, tmp_path, supersede):
    monkeypatch.setattr(sem_storage, "readable_root", lambda: tmp_path)
    candidate_id, entity_id = await _fixture_candidate()
    old = sem_storage.create_semantic_card(
        tmp_path, kind="decision", title="Atlas prior",
        statement="Use Python for Atlas in 2025", scope="project",
        scope_project=str(entity_id),
    )

    async def mutate():
        sem_storage.create_semantic_card(
            tmp_path, kind="decision", title="Atlas revision",
            statement="Use Rust for Atlas", scope="project",
            scope_project=str(entity_id),
            supersedes=[old.card_id] if supersede else [],
        )

    provider = Provider(mutate)
    async with SessionLocal() as session:
        result = await judge_memory(session, candidate_id, provider=provider, mode="on")
    assert result.status == "stale"
    assert result.signals is None and result.review_flags == ()
    assert provider.calls == 1
