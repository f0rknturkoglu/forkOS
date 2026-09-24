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
        self.last_packet = packet
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


async def _fixture_candidate_with_n_sources(n: int = 4):
    async with SessionLocal() as session:
        entity = await create_entity(session, type="project", title="Multi-source project")
        refs_data = []
        event_ids = []
        item_entities = []
        for i in range(n):
            item_entity = await create_entity(session, type="project", title=f"Update note {i + 1}")
            event = await log_event(
                session,
                verb="project.updated",
                entity_id=item_entity.id,
                entity_type="project",
                payload={"title": f"Update note {i + 1}"},
            )
            await session.flush()
            ref = f"event:{event.id}"
            source = await read_memory_source(session, ref)
            assert source is not None
            event_ids.append(event.id)
            item_entities.append(item_entity)
            refs_data.append({
                "ref": ref,
                "role": "canonical",
                "digest": None,
                "source_revision": source.revision,
            })
        moment = datetime.now(UTC)
        candidate_id = uuid.uuid4()
        key = uuid.uuid4().hex
        candidate = AgentSemanticCandidate(
            id=candidate_id,
            candidate_key=key,
            kind="decision",
            statement="Multi-source project decision",
            scope="project",
            scope_project=str(entity.id),
            suggested_destination="durable_vault",
            primary_evidence_class="canonical_source",
            evidence_refs=refs_data,
            observed_at=moment,
            status="proposed",
            recurrence_count=1,
            first_seen_at=moment,
            last_seen_at=moment,
            revision=compute_candidate_revision(candidate_id, key, "proposed", 1, moment),
        )
        session.add(candidate)
        await session.commit()
        return candidate_id, entity.id, event_ids, [e.id for e in item_entities]


async def test_candidate_with_four_evidence_refs_selects_max_sources_deterministically(monkeypatch, tmp_path):
    monkeypatch.setattr(sem_storage, "readable_root", lambda: tmp_path)
    candidate_id, _, event_ids, _ = await _fixture_candidate_with_n_sources(4)
    provider = Provider()

    async with SessionLocal() as session:
        result = await judge_memory(session, candidate_id, provider=provider, mode="shadow")

    assert result.status == "success"
    assert result.signals is not None
    assert provider.calls == 1
    assert len(provider.last_packet.source_texts) == 3
    # Top 3 selected events must be the newest canonical events (last 3 of 4)
    assert provider.last_packet.source_texts == tuple(
        f"project.updated: Update note {i}" for i in (4, 3, 2)
    )

    # Invariant: A4 full candidate provenance must be completely preserved in DB
    async with SessionLocal() as session:
        stored = await session.get(AgentSemanticCandidate, candidate_id)
        assert stored is not None
        assert len(stored.evidence_refs) == 4
        assert stored.status == "proposed"
        assert stored.recurrence_count == 1


async def test_candidate_with_five_evidence_refs_stable_selection(monkeypatch, tmp_path):
    monkeypatch.setattr(sem_storage, "readable_root", lambda: tmp_path)
    candidate_id, _, _, _ = await _fixture_candidate_with_n_sources(5)
    provider1 = Provider()
    provider2 = Provider()

    async with SessionLocal() as session:
        result1 = await judge_memory(session, candidate_id, provider=provider1, mode="shadow")
        result2 = await judge_memory(session, candidate_id, provider=provider2, mode="shadow")

    assert result1.status == "success" and result2.status == "success"
    assert provider1.last_packet.source_snapshot == provider2.last_packet.source_snapshot
    assert provider1.last_packet.source_texts == provider2.last_packet.source_texts
    assert len(provider1.last_packet.source_texts) == 3

    # Invariant: Full 5 evidence refs unchanged
    async with SessionLocal() as session:
        stored = await session.get(AgentSemanticCandidate, candidate_id)
        assert stored is not None
        assert len(stored.evidence_refs) == 5


async def test_unselected_source_mutation_during_call_is_stale(monkeypatch, tmp_path):
    monkeypatch.setattr(sem_storage, "readable_root", lambda: tmp_path)
    candidate_id, _, event_ids, item_entity_ids = await _fixture_candidate_with_n_sources(4)
    # The oldest event (event_ids[0]) is unselected (packet takes events 3, 2, 1)
    unselected_entity_id = item_entity_ids[0]

    async def mutate():
        async with SessionLocal() as session:
            await touch_entity(session, unselected_entity_id, title="Mutated title affecting unselected event")
            await session.commit()

    provider = Provider(mutate)
    async with SessionLocal() as session:
        result = await judge_memory(session, candidate_id, provider=provider, mode="on")

    assert result.status == "stale"
    assert result.signals is None and result.review_flags == ()
    assert provider.calls == 1


async def test_new_evidence_appended_during_call_is_stale(monkeypatch, tmp_path):
    monkeypatch.setattr(sem_storage, "readable_root", lambda: tmp_path)
    candidate_id, entity_id, _, _ = await _fixture_candidate_with_n_sources(4)

    async def mutate():
        async with SessionLocal() as session:
            new_event = await log_event(
                session, verb="project.updated", entity_id=entity_id, entity_type="project",
                payload={"title": "5th event appended during inference"},
            )
            await session.flush()
            ref = f"event:{new_event.id}"
            source = await read_memory_source(session, ref)
            assert source is not None
            candidate = await session.get(AgentSemanticCandidate, candidate_id)
            assert candidate is not None
            candidate.evidence_refs = [
                *candidate.evidence_refs,
                {"ref": ref, "role": "canonical", "digest": None, "source_revision": source.revision},
            ]
            await session.commit()

    provider = Provider(mutate)
    async with SessionLocal() as session:
        result = await judge_memory(session, candidate_id, provider=provider, mode="on")

    assert result.status == "stale"
    assert result.signals is None and result.review_flags == ()
    assert provider.calls == 1


async def test_invalid_evidence_in_accumulated_provenance_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setattr(sem_storage, "readable_root", lambda: tmp_path)
    candidate_id, _, _, _ = await _fixture_candidate_with_n_sources(4)

    # Corrupt the 4th evidence ref (which would be unselected)
    async with SessionLocal() as session:
        candidate = await session.get(AgentSemanticCandidate, candidate_id)
        assert candidate is not None
        corrupted_refs = list(candidate.evidence_refs)
        corrupted_refs[0] = {**corrupted_refs[0], "source_revision": "deadbeef" * 8}
        candidate.evidence_refs = corrupted_refs
        await session.commit()

    provider = Provider()
    async with SessionLocal() as session:
        result = await judge_memory(session, candidate_id, provider=provider, mode="shadow")

    assert result.status == "degraded"
    assert result.reason == "SOURCE_STALE"
    assert provider.calls == 0


async def test_zero_evidence_refs_returns_source_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(sem_storage, "readable_root", lambda: tmp_path)
    candidate_id, _, _, _ = await _fixture_candidate_with_n_sources(1)

    async with SessionLocal() as session:
        candidate = await session.get(AgentSemanticCandidate, candidate_id)
        assert candidate is not None
        candidate.evidence_refs = []
        await session.commit()

    provider = Provider()
    async with SessionLocal() as session:
        result = await judge_memory(session, candidate_id, provider=provider, mode="shadow")

    assert result.status == "degraded"
    assert result.reason == "SOURCE_MISSING"
    assert provider.calls == 0
