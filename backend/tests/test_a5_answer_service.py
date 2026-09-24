"""Unit tests for A5.3 Answer Evidence Judge service."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.integrations.agent.evidence_models import (
    EvidenceBundle,
    EvidenceItem,
    EvidenceLocator,
)
from app.integrations.judgment import answer as service
from app.integrations.judgment.answer_models import AnswerJudgeProvenance
from app.integrations.judgment.models import (
    AnswerEvidenceRequest,
    JudgmentMetadata,
    SourceSnapshot,
    SupportVerdict,
)

pytestmark = pytest.mark.no_database


class FakeProvider:
    provider_id = "poorjev-local-nli"
    locality = "local"
    capabilities = frozenset({"answer_support"})

    def __init__(
        self,
        verdict: SupportVerdict | None = None,
        exc: Exception | None = None,
        on_call: Any | None = None,
    ) -> None:
        self.verdict = verdict or SupportVerdict(
            status="success",
            support="supported",
            metadata=JudgmentMetadata(
                provider_id="poorjev-local-nli",
                model_id="deberta",
                latency_ms=10,
                provider_confidence=0.95,
            ),
        )
        self.exc = exc
        self.on_call = on_call
        self.calls = 0
        self.last_request: AnswerEvidenceRequest | None = None

    async def health(self) -> bool:
        return True

    async def judge_support(
        self, request: AnswerEvidenceRequest
    ) -> tuple[SupportVerdict, AnswerJudgeProvenance]:
        self.calls += 1
        self.last_request = request
        if self.on_call:
            await self.on_call()
        if self.exc:
            raise self.exc
        provenance = AnswerJudgeProvenance(
            provider_id="poorjev-local-nli",
            provider_version="0.1.0",
            model_id="deberta",
            model_revision="rev1",
            question_version="a5-answer-questions-v1",
            question_hash="h" * 64,
            claim_digest="c" * 64,
            evidence_digest="e" * 64,
            latency_ms=10,
            judged_at=datetime.now(UTC),
            abstained=False,
            provider_confidence=0.95,
        )
        return self.verdict, provenance


def make_evidence_item(evidence_id: str = "entity:123", excerpt: str = "Atlas uses Rust.") -> EvidenceItem:
    item = EvidenceItem(
        evidence_id=evidence_id,
        source_type="entity",
        source_id="123",
        title="Atlas Project",
        locator=EvidenceLocator(entity_id="123"),
        excerpt=excerpt,
        retrieval_reason="matched query",
    )
    item._source_revision = "rev_1"
    return item


def test_derive_h3_query_bounds():
    # Short claim
    assert service.derive_h3_query("Atlas uses Rust.") == "Atlas uses Rust."

    # Explicit query
    assert service.derive_h3_query("Long claim", explicit_query="Rust stack") == "Rust stack"

    # Explicit query bounds
    with pytest.raises(ValueError, match="between 2 and 200"):
        service.derive_h3_query("Claim", explicit_query="a")
    with pytest.raises(ValueError, match="between 2 and 200"):
        service.derive_h3_query("Claim", explicit_query="x" * 201)

    # Long claim truncated at word boundary <= 200
    long_claim = "word " * 50  # 250 chars
    derived = service.derive_h3_query(long_claim)
    assert len(derived) <= 200
    assert not derived.endswith(" ")


async def test_empty_evidence_bundle_returns_abstained(monkeypatch):
    empty_bundle = EvidenceBundle(query="Atlas", evidence=[])
    monkeypatch.setattr(service, "retrieve_evidence", AsyncMock(return_value=empty_bundle))

    session = AsyncMock()
    provider = FakeProvider()
    response = await service.judge_answer(session, claim="Atlas uses Rust.", provider=provider)

    assert response.status == "abstained"
    assert response.baseline_support == "uncertain"
    assert response.observed_support == "uncertain"
    assert response.effective_support == "uncertain"
    assert "ANSWER_JUDGE_EMPTY" in response.degraded_reasons
    assert provider.calls == 0


async def test_invalid_claim_returns_invalid_baseline():
    session = AsyncMock()
    provider = FakeProvider()

    # Empty claim
    res1 = await service.judge_answer(session, claim="", provider=provider)
    assert res1.status == "invalid"
    assert res1.observed_support == "uncertain"
    assert "ANSWER_JUDGE_INVALID_RESPONSE" in res1.degraded_reasons

    # Too long claim (> 1000)
    res2 = await service.judge_answer(session, claim="x" * 1001, provider=provider)
    assert res2.status == "invalid"
    assert provider.calls == 0


async def test_mode_off_does_not_invoke_provider(monkeypatch):
    item = make_evidence_item()
    bundle = EvidenceBundle(query="Atlas", evidence=[item])
    monkeypatch.setattr(service, "retrieve_evidence", AsyncMock(return_value=bundle))

    session = AsyncMock()
    provider = FakeProvider()
    response = await service.judge_answer(
        session, claim="Atlas uses Rust.", mode="off", provider=provider
    )

    assert response.mode == "off"
    assert response.status == "abstained"
    assert response.baseline_support == "uncertain"
    assert response.observed_support == "uncertain"
    assert response.effective_support == "uncertain"
    assert "ANSWER_JUDGE_DISABLED" in response.degraded_reasons
    assert provider.calls == 0


async def test_mode_shadow_runs_provider_without_downstream_authority(monkeypatch):
    item = make_evidence_item()
    bundle = EvidenceBundle(query="Atlas", evidence=[item])
    monkeypatch.setattr(service, "retrieve_evidence", AsyncMock(return_value=bundle))

    snap = SourceSnapshot(
        source_id="123", source_type="entity", source_revision="rev_1",
        captured_at=datetime.now(UTC),
    )
    monkeypatch.setattr(service, "capture_snapshots", AsyncMock(return_value=(snap,)))

    session = AsyncMock()
    provider = FakeProvider()
    response = await service.judge_answer(
        session, claim="Atlas uses Rust.", mode="shadow", provider=provider
    )

    assert response.mode == "shadow"
    assert response.status == "success"
    assert response.observed_support == "supported"
    # In SHADOW, effective_support has ZERO authority, remains baseline "uncertain"
    assert response.effective_support == "uncertain"
    assert response.baseline_support == "uncertain"
    assert provider.calls == 1


async def test_mode_on_allows_effective_support(monkeypatch):
    item = make_evidence_item()
    bundle = EvidenceBundle(query="Atlas", evidence=[item])
    monkeypatch.setattr(service, "retrieve_evidence", AsyncMock(return_value=bundle))

    snap = SourceSnapshot(
        source_id="123", source_type="entity", source_revision="rev_1",
        captured_at=datetime.now(UTC),
    )
    monkeypatch.setattr(service, "capture_snapshots", AsyncMock(return_value=(snap,)))

    session = AsyncMock()
    provider = FakeProvider()
    response = await service.judge_answer(
        session, claim="Atlas uses Rust.", mode="on", provider=provider
    )

    assert response.mode == "on"
    assert response.status == "success"
    assert response.observed_support == "supported"
    assert response.effective_support == "supported"
    assert provider.calls == 1


async def test_snapshot_unavailable_fails_closed(monkeypatch):
    item = make_evidence_item()
    bundle = EvidenceBundle(query="Atlas", evidence=[item])
    monkeypatch.setattr(service, "retrieve_evidence", AsyncMock(return_value=bundle))
    monkeypatch.setattr(
        service, "capture_snapshots", AsyncMock(side_effect=RuntimeError("Cannot read source"))
    )

    session = AsyncMock()
    provider = FakeProvider()
    response = await service.judge_answer(
        session, claim="Atlas uses Rust.", mode="on", provider=provider
    )

    assert response.status == "invalid"
    assert response.effective_support == "uncertain"
    assert "ANSWER_JUDGE_SNAPSHOT_UNAVAILABLE" in response.degraded_reasons
    assert provider.calls == 0


async def test_snapshot_mismatch_fails_closed(monkeypatch):
    item = make_evidence_item()
    bundle = EvidenceBundle(query="Atlas", evidence=[item])
    monkeypatch.setattr(service, "retrieve_evidence", AsyncMock(return_value=bundle))

    # Mismatched revision
    snap = SourceSnapshot(
        source_id="123", source_type="entity", source_revision="wrong_rev",
        captured_at=datetime.now(UTC),
    )
    monkeypatch.setattr(service, "capture_snapshots", AsyncMock(return_value=(snap,)))

    session = AsyncMock()
    provider = FakeProvider()
    response = await service.judge_answer(
        session, claim="Atlas uses Rust.", mode="on", provider=provider
    )

    assert response.status == "invalid"
    assert response.effective_support == "uncertain"
    assert "ANSWER_JUDGE_SOURCE_BINDING_FAILED" in response.degraded_reasons
    assert provider.calls == 0


async def test_source_mutation_during_provider_call_becomes_stale(monkeypatch):
    item = make_evidence_item()
    bundle = EvidenceBundle(query="Atlas", evidence=[item])
    monkeypatch.setattr(service, "retrieve_evidence", AsyncMock(return_value=bundle))

    snap1 = SourceSnapshot(
        source_id="123", source_type="entity", source_revision="rev_1",
        captured_at=datetime.now(UTC),
    )
    snap2 = SourceSnapshot(
        source_id="123", source_type="entity", source_revision="mutated_during_inference",
        captured_at=datetime.now(UTC),
    )
    # First call returns snap1; second call after inference returns snap2
    snapshots = [ (snap1,), (snap2,) ]
    monkeypatch.setattr(service, "capture_snapshots", AsyncMock(side_effect=lambda *_: snapshots.pop(0)))

    session = AsyncMock()
    provider = FakeProvider()
    response = await service.judge_answer(
        session, claim="Atlas uses Rust.", mode="on", provider=provider
    )

    assert response.status == "stale"
    assert response.observed_support == "uncertain"
    assert response.effective_support == "uncertain"
    assert "ANSWER_JUDGE_SOURCE_STALE" in response.degraded_reasons
    assert provider.calls == 1


async def test_provider_timeout_returns_unavailable(monkeypatch):
    item = make_evidence_item()
    bundle = EvidenceBundle(query="Atlas", evidence=[item])
    monkeypatch.setattr(service, "retrieve_evidence", AsyncMock(return_value=bundle))

    snap = SourceSnapshot(
        source_id="123", source_type="entity", source_revision="rev_1",
        captured_at=datetime.now(UTC),
    )
    monkeypatch.setattr(service, "capture_snapshots", AsyncMock(return_value=(snap,)))

    from app.integrations.judgment.poorjev_answer import AnswerProviderError

    session = AsyncMock()
    provider = FakeProvider(exc=AnswerProviderError("ANSWER_PROVIDER_TIMEOUT"))
    response = await service.judge_answer(
        session, claim="Atlas uses Rust.", mode="on", provider=provider
    )

    assert response.status == "unavailable"
    assert response.observed_support == "uncertain"
    assert response.effective_support == "uncertain"
    assert "ANSWER_JUDGE_TIMEOUT" in response.degraded_reasons


async def test_truncated_bundle_reflected_in_context_complete(monkeypatch):
    item = make_evidence_item()
    bundle = EvidenceBundle(query="Atlas", evidence=[item], truncated=True, omitted_total=2)
    monkeypatch.setattr(service, "retrieve_evidence", AsyncMock(return_value=bundle))

    snap = SourceSnapshot(
        source_id="123", source_type="entity", source_revision="rev_1",
        captured_at=datetime.now(UTC),
    )
    monkeypatch.setattr(service, "capture_snapshots", AsyncMock(return_value=(snap,)))

    session = AsyncMock()
    provider = FakeProvider()
    response = await service.judge_answer(
        session, claim="Atlas uses Rust.", mode="on", provider=provider
    )

    assert response.truncated is True
    assert response.omitted_total == 2
    assert response.context_complete is False
    assert provider.last_request.context_complete is False
