"""A5.1 modes, deterministic reranking and fail-open H3 preservation."""

from datetime import UTC, datetime

import pytest

from app.integrations.agent.evidence_models import EvidenceBundle, EvidenceItem
from app.integrations.judgment import context as service
from app.integrations.judgment.jevmlx import ContextProviderError
from app.integrations.judgment.models import ContextVerdict, SourceSnapshot

pytestmark = pytest.mark.no_database


def bundle(count: int = 3) -> EvidenceBundle:
    return EvidenceBundle(
        query="Which source helps?",
        evidence=[EvidenceItem(
            evidence_id=f"entity:{i}", source_type="entity", source_id=str(i),
            title=f"Source {i}", excerpt=f"Content {i}", retrieval_reason="synthetic",
        ) for i in range(count)],
    )


class FakeProvider:
    locality = "local"
    capabilities = frozenset({"context_relevance"})

    def __init__(self, *, ready=True, error=None, partial=False):
        self.ready = ready
        self.error = error
        self.partial = partial
        self.health_calls = 0
        self.judge_calls = 0

    async def health(self):
        self.health_calls += 1
        return self.ready

    async def judge_context(self, request):
        self.judge_calls += 1
        if self.error:
            raise ContextProviderError(self.error)
        verdicts = tuple(ContextVerdict(
            evidence_id=item.evidence_id,
            status="success", usefulness="essential" if i == 2 else "weak",
            redundancy="unique",
        ) for i, item in enumerate(request.candidates))
        return verdicts[:-1] if self.partial else verdicts


def setup(monkeypatch, evidence=None, revisions=None):
    packet = evidence if evidence is not None else bundle()
    state = {"calls": 0}

    async def retrieve(*args, **kwargs):
        return packet

    async def capture(*args, **kwargs):
        state["calls"] += 1
        revision = (revisions or ["r1", "r1"])[min(state["calls"] - 1, 1)]
        return tuple(SourceSnapshot(
            source_id=item.source_id, source_type=item.source_type,
            source_revision=revision, captured_at=datetime.now(UTC),
        ) for item in packet.evidence)

    monkeypatch.setattr(service, "retrieve_evidence", retrieve)
    monkeypatch.setattr(service, "capture_snapshots", capture)
    return packet, state


@pytest.mark.parametrize(("mode", "effective"), [
    ("shadow", ("entity:0", "entity:1", "entity:2")),
    ("assist", ("entity:2", "entity:0", "entity:1")),
    ("on", ("entity:2", "entity:0", "entity:1")),
])
async def test_mode_ordering_and_no_deletion(monkeypatch, mode, effective):
    packet, _ = setup(monkeypatch)
    provider = FakeProvider()
    result = await service.judge_context(None, query=packet.query, mode=mode, provider=provider)
    assert provider.judge_calls == 1 and result.status == "success"
    assert result.baseline_order == ("entity:0", "entity:1", "entity:2")
    assert result.advisory_order == ("entity:2", "entity:0", "entity:1")
    assert result.effective_order == effective
    assert set(result.effective_order) == set(result.baseline_order)
    assert result.bundle is packet


async def test_off_and_empty_never_call_provider(monkeypatch):
    packet, state = setup(monkeypatch)
    provider = FakeProvider()
    result = await service.judge_context(None, query=packet.query, mode="off", provider=provider)
    assert result.effective_order == result.baseline_order
    assert provider.health_calls == provider.judge_calls == state["calls"] == 0
    empty, _ = setup(monkeypatch, bundle(0))
    result = await service.judge_context(None, query=empty.query, mode="assist", provider=provider)
    assert result.status == "abstained" and result.effective_order == ()
    assert provider.health_calls == 0


@pytest.mark.parametrize(("ready", "error", "partial", "status"), [
    (False, None, False, "unavailable"),
    (True, "CONTEXT_JUDGE_TIMEOUT", False, "unavailable"),
    (True, "CONTEXT_JUDGE_BUSY", False, "unavailable"),
    (True, "CONTEXT_JUDGE_INVALID_RESPONSE", False, "invalid"),
    (True, "UNKNOWN_PROVIDER_ERROR", False, "unavailable"),
    (True, None, True, "invalid"),
])
async def test_provider_failure_keeps_h3(monkeypatch, ready, error, partial, status):
    packet, _ = setup(monkeypatch)
    result = await service.judge_context(None, query=packet.query, mode="assist", provider=FakeProvider(ready=ready, error=error, partial=partial))
    assert result.status == status
    assert result.effective_order == result.baseline_order
    assert result.bundle is packet
    assert all(v.usefulness == v.redundancy == "uncertain" for v in result.verdicts)


async def test_stale_revalidation_discards_ranking(monkeypatch):
    packet, _ = setup(monkeypatch, revisions=["r1", "r2"])
    result = await service.judge_context(None, query=packet.query, mode="assist", provider=FakeProvider())
    assert result.status == "stale"
    assert result.effective_order == result.baseline_order
    assert all(v.status == "stale" for v in result.verdicts)


async def test_snapshot_failure_never_calls_provider(monkeypatch):
    packet, _ = setup(monkeypatch)

    async def fail(*args, **kwargs):
        raise RuntimeError("private snapshot detail")

    monkeypatch.setattr(service, "capture_snapshots", fail)
    provider = FakeProvider()
    result = await service.judge_context(None, query=packet.query, mode="assist", provider=provider)
    assert result.status == "invalid" and result.effective_order == result.baseline_order
    assert provider.health_calls == provider.judge_calls == 0


async def test_unexpected_provider_error_keeps_h3(monkeypatch):
    packet, _ = setup(monkeypatch)
    provider = FakeProvider()

    async def crash():
        raise RuntimeError("private provider detail")

    provider.health = crash
    result = await service.judge_context(None, query=packet.query, mode="assist", provider=provider)
    assert result.status == "unavailable"
    assert result.degraded_reasons == ("CONTEXT_JUDGE_UNAVAILABLE",)
    assert result.effective_order == result.baseline_order
    assert result.bundle is packet


async def test_remote_provider_is_rejected_before_health_probe(monkeypatch):
    packet, _ = setup(monkeypatch)
    provider = FakeProvider()
    provider.locality = "remote"
    result = await service.judge_context(None, query=packet.query, mode="assist", provider=provider)
    assert result.effective_order == result.baseline_order
    assert provider.health_calls == provider.judge_calls == 0


def test_typed_ranking_tiers_and_h3_ties():
    packet = bundle(4)
    verdicts = (
        ContextVerdict(evidence_id="entity:0", status="success", usefulness="weak", redundancy="unique"),
        ContextVerdict(evidence_id="entity:1", status="success", usefulness="useful", redundancy="redundant"),
        ContextVerdict(evidence_id="entity:2", status="success", usefulness="useful", redundancy="unique"),
        ContextVerdict(evidence_id="entity:3", status="success", usefulness="useful", redundancy="unique"),
    )
    assert service.semantic_order(packet, verdicts) == ("entity:2", "entity:3", "entity:1", "entity:0")
