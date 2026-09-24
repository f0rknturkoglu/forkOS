"""A5.2 advisory authority, mode and snapshot race contract (synthetic only)."""

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.integrations.judgment import memory as service
from app.integrations.judgment.memory_models import MemoryJudgeProvenance, MemorySignals
from app.integrations.judgment.poorjev_memory import MemoryProviderError

pytestmark = pytest.mark.no_database

ID = uuid.UUID("55555555-5555-4555-8555-555555555555")


class FakeSession:
    async def get(self, model, key, **kwargs):
        return SimpleNamespace(
            id=ID, status="proposed", suggested_destination="durable_vault"
        )


class FakeProvider:
    def __init__(self, error=None, abstained=False):
        self.calls = 0
        self.error = error
        self.abstained = abstained

    async def judge(self, packet):
        self.calls += 1
        if self.error:
            raise self.error
        return MemorySignals(
            evidence_support="supported", intent="explicit", durability="durable",
            scope_relation="same_scope", conditions_preserved="yes",
            exceptions_preserved="not_applicable", relations=(),
        ), MemoryJudgeProvenance(
            provider_id="fake-local", provider_version="test", model_id="synthetic",
            question_version="test-v1", candidate_snapshot=packet.candidate_snapshot,
            source_snapshot=packet.source_snapshot, related_snapshot=packet.related_snapshot,
            policy_snapshot=packet.policy_snapshot, latency_ms=1,
            judged_at=datetime.now(UTC), abstained=self.abstained,
        )


def bound(revision="a", duplicate=False):
    state = service.BoundState(
        candidate_digest=revision * 64, source_digest="s" * 64,
        related_digest="r" * 64, policy_digest="p" * 64,
        sources=(SimpleNamespace(text="I choose Python for this project."),),
        related=(), exact_duplicate=duplicate,
    )
    candidate = SimpleNamespace(
        statement="I choose Python for this project.", kind="decision",
        scope="project", scope_project="demo", conditions=[], exceptions=[],
    )
    return candidate, state, None


@pytest.mark.parametrize("mode", ["off", "shadow", "assist", "on"])
async def test_modes_never_write_or_promote(monkeypatch, mode):
    provider = FakeProvider()

    async def get_state(*args):
        return bound()

    monkeypatch.setattr(service, "_bound_state", get_state)
    result = await service.judge_memory(FakeSession(), ID, provider=provider, mode=mode)
    assert result.baseline_status == "proposed"
    assert result.baseline_destination == "durable_vault"
    assert provider.calls == (0 if mode == "off" else 1)
    assert result.status == ("disabled" if mode == "off" else "success")
    assert result.review_flags == ()


@pytest.mark.parametrize("reason", [
    "CANDIDATE_INELIGIBLE", "SENSITIVITY_BLOCKED", "SOURCE_UNBOUND",
    "SOURCE_STALE", "RELATED_SENSITIVITY_BLOCKED",
])
async def test_mechanical_block_never_invokes_provider(monkeypatch, reason):
    async def blocked(*args):
        return SimpleNamespace(), None, reason

    monkeypatch.setattr(service, "_bound_state", blocked)
    provider = FakeProvider()
    result = await service.judge_memory(FakeSession(), ID, provider=provider, mode="shadow")
    assert result.status == "degraded"
    assert result.reason == reason
    assert provider.calls == 0


async def test_exact_duplicate_is_mechanical(monkeypatch):
    async def get_state(*args):
        return bound(duplicate=True)

    monkeypatch.setattr(service, "_bound_state", get_state)
    provider = FakeProvider()
    result = await service.judge_memory(FakeSession(), ID, provider=provider, mode="shadow")
    assert result.status == "abstained"
    assert result.reason == "EXACT_DUPLICATE"
    assert provider.calls == 0


@pytest.mark.parametrize("mutated", ["candidate", "source", "related", "policy", "revoked"])
async def test_post_call_mutation_discards_semantics(monkeypatch, mutated):
    states = [bound(), bound(), bound()]
    if mutated == "candidate":
        states[2] = bound("b")
    elif mutated == "source":
        states[2] = (states[2][0], service.BoundState(
            **{**states[2][1].__dict__, "source_digest": "x" * 64}
        ), None)
    elif mutated == "related" or mutated == "revoked":
        states[2] = (states[2][0], service.BoundState(
            **{**states[2][1].__dict__, "related_digest": "x" * 64}
        ), None)
    else:
        states[2] = (states[2][0], service.BoundState(
            **{**states[2][1].__dict__, "policy_digest": "x" * 64}
        ), None)

    async def get_state(*args):
        return states.pop(0)

    monkeypatch.setattr(service, "_bound_state", get_state)
    result = await service.judge_memory(FakeSession(), ID, provider=FakeProvider(), mode="on")
    assert result.status == "stale"
    assert result.signals is None and result.review_flags == ()
    assert result.baseline_status == "proposed"


@pytest.mark.parametrize("error,status", [
    (MemoryProviderError("MEMORY_PROVIDER_TIMEOUT"), "unavailable"),
    (RuntimeError("bad model"), "invalid"),
])
async def test_provider_failure_is_baseline(monkeypatch, error, status):
    async def get_state(*args):
        return bound()

    monkeypatch.setattr(service, "_bound_state", get_state)
    result = await service.judge_memory(
        FakeSession(), ID, provider=FakeProvider(error=error), mode="on"
    )
    assert result.status == status
    assert result.signals is None and result.review_flags == ()


async def test_provider_abstention_is_not_success(monkeypatch):
    async def get_state(*args):
        return bound()

    monkeypatch.setattr(service, "_bound_state", get_state)
    result = await service.judge_memory(
        FakeSession(), ID, provider=FakeProvider(abstained=True), mode="assist"
    )
    assert result.status == "abstained"
    assert result.signals is None


async def test_provider_snapshot_mismatch_is_invalid(monkeypatch):
    async def get_state(*args):
        return bound()

    class WrongSnapshot(FakeProvider):
        async def judge(self, packet):
            signals, provenance = await super().judge(packet)
            return signals, provenance.model_copy(update={"source_snapshot": "x" * 64})

    monkeypatch.setattr(service, "_bound_state", get_state)
    result = await service.judge_memory(
        FakeSession(), ID, provider=WrongSnapshot(), mode="on"
    )
    assert result.status == "invalid"
    assert result.reason == "MEMORY_PROVIDER_RESPONSE_MISMATCH"
    assert result.signals is None and result.review_flags == ()


def test_select_memory_sources_role_priority_and_recency():
    s_user_old = service.MemorySource("episode_item:1", "text", "r1", "user", None)
    s_user_new = service.MemorySource("episode_item:5", "text", "r2", "user", None)
    s_canonical = service.MemorySource("event:10", "text", "r3", "canonical", None)
    s_assistant = service.MemorySource("episode_item:20", "text", "r4", "assistant", None)
    s_unknown = service.MemorySource("event:2", "text", "r5", None, None)

    # 5 sources provided; selection must pick top 3:
    # 1: user_new (user, id=5)
    # 2: user_old (user, id=1)
    # 3: canonical (canonical, id=10)
    # Excluded: assistant (rank 1), unknown (rank 0)
    selected = service.select_memory_sources([s_assistant, s_unknown, s_user_old, s_canonical, s_user_new])
    assert len(selected) == 3
    assert [s.ref for s in selected] == ["episode_item:5", "episode_item:1", "event:10"]


def test_select_memory_sources_stability():
    s1 = service.MemorySource("episode_item:1", "text1", "r1", "user", None)
    s2 = service.MemorySource("episode_item:2", "text2", "r2", "user", None)
    s3 = service.MemorySource("event:3", "text3", "r3", "canonical", None)
    s4 = service.MemorySource("episode_item:4", "text4", "r4", "assistant", None)

    order1 = service.select_memory_sources([s1, s2, s3, s4])
    order2 = service.select_memory_sources([s4, s3, s2, s1])
    order3 = service.select_memory_sources([s2, s4, s1, s3])
    assert order1 == order2 == order3
    assert [s.ref for s in order1] == ["episode_item:2", "episode_item:1", "event:3"]


@pytest.mark.parametrize("mutated", ["full_source", "source", "candidate"])
async def test_unselected_and_full_source_mutation_discards_semantics(monkeypatch, mutated):
    states = [bound(), bound(), bound()]
    if mutated == "full_source":
        # Simulates an unselected source mutating its revision
        states[2] = (
            states[2][0],
            service.BoundState(
                **{**states[2][1].__dict__, "full_source_digest": "f" * 64}
            ),
            None,
        )
    elif mutated == "source":
        states[2] = (
            states[2][0],
            service.BoundState(
                **{**states[2][1].__dict__, "source_digest": "s2" * 32}
            ),
            None,
        )
    else:
        states[2] = bound("mutated_candidate")

    async def get_state(*args):
        return states.pop(0)

    monkeypatch.setattr(service, "_bound_state", get_state)
    result = await service.judge_memory(FakeSession(), ID, provider=FakeProvider(), mode="on")
    assert result.status == "stale"
    assert result.signals is None and result.review_flags == ()
    assert result.baseline_status == "proposed"
