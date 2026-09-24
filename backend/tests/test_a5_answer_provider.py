"""Tests for A5.3 PoorJevAnswerProvider."""

import builtins
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.integrations.judgment.models import (
    AnswerEvidenceItem,
    AnswerEvidenceRequest,
    SourceSnapshot,
    SupportVerdict,
)
from app.integrations.judgment.poorjev_answer import (
    HYPOTHESES,
    LABELS,
    QUESTION_HASH,
    QUESTION_VERSION,
    AnswerProviderError,
    PoorJevAnswerProvider,
    _premise,
)

pytestmark = pytest.mark.no_database


def make_request(claim: str = "Atlas uses Rust.", context_complete: bool = True) -> AnswerEvidenceRequest:
    snap = SourceSnapshot(
        source_id="item:1",
        source_type="entity",
        source_revision="rev_1",
        captured_at=datetime.now(UTC),
    )
    item = AnswerEvidenceItem(
        evidence_id="entity:1",
        excerpt="The Atlas codebase is written in Rust.",
        surrounding_context="Project: Atlas | Status: Active",
        snapshot=snap,
        remote_allowed=False,
    )
    return AnswerEvidenceRequest(
        request_id="req-1",
        claim=claim,
        evidence=(item,),
        context_complete=context_complete,
    )


def test_frozen_hypotheses_and_question_hash():
    assert QUESTION_VERSION == "a5-answer-questions-v1"
    assert QUESTION_HASH == "fe04928f17c91038629a8186ecc2fb7753838b3b442da3141b91f3148ccda2cf"
    assert set(HYPOTHESES) == set(LABELS) == {"supported", "contradicted", "insufficient", "uncertain"}


def test_premise_construction():
    req = make_request("Atlas uses Rust.", context_complete=True)
    premise = _premise(req)
    assert "The Atlas codebase is written in Rust." in premise
    assert "Project: Atlas | Status: Active" in premise
    assert "[Notice: The retrieved evidence is truncated" not in premise

    req_incomplete = make_request("Atlas uses Rust.", context_complete=False)
    premise_incomplete = _premise(req_incomplete)
    assert "[Notice: The retrieved evidence is truncated" in premise_incomplete


@pytest.mark.parametrize("expected_label", ["supported", "contradicted", "insufficient", "uncertain"])
async def test_provider_returns_typed_verdict(monkeypatch, tmp_path, expected_label):
    provider = PoorJevAnswerProvider(str(tmp_path))
    monkeypatch.setattr(provider, "_read_manifest", lambda: {"model_id": "test_model", "revision": "rev"})

    req = make_request("Atlas uses Rust.")

    def fake_ask(request):
        winning_text = HYPOTHESES[expected_label].format(claim=request.claim)
        probabilities = [0.1, 0.1, 0.1, 0.1]
        decision = SimpleNamespace(value=winning_text, confidence=0.85, abstained=False)
        return decision, probabilities

    monkeypatch.setattr(provider, "_ask", fake_ask)

    verdict, provenance = await provider.judge_support(req)
    assert isinstance(verdict, SupportVerdict)
    assert verdict.status == "success"
    assert verdict.support == expected_label
    assert verdict.metadata.provider_confidence == 0.85
    assert provenance.model_id == "test_model"
    assert provenance.question_version == QUESTION_VERSION


async def test_incomplete_context_overrides_certain_support(monkeypatch, tmp_path):
    provider = PoorJevAnswerProvider(str(tmp_path))
    monkeypatch.setattr(provider, "_read_manifest", lambda: {"model_id": "test_model", "revision": "rev"})

    # Even if model says "supported", context_complete=False must force "uncertain"
    req = make_request("Atlas uses Rust.", context_complete=False)

    def fake_ask(request):
        winning_text = HYPOTHESES["supported"].format(claim=request.claim)
        probabilities = [0.9, 0.05, 0.03, 0.02]
        decision = SimpleNamespace(value=winning_text, confidence=0.9, abstained=False)
        return decision, probabilities

    monkeypatch.setattr(provider, "_ask", fake_ask)

    verdict, _ = await provider.judge_support(req)
    assert verdict.support == "uncertain"
    assert "context_incomplete" in verdict.reason_codes


async def test_missing_model_fails_before_import(tmp_path):
    provider = PoorJevAnswerProvider(str(tmp_path / "nonexistent"))
    with pytest.raises(AnswerProviderError, match="ANSWER_MODEL_UNAVAILABLE"):
        await provider.judge_support(make_request())


def test_missing_poorjev_dependency_is_explicit(monkeypatch, tmp_path):
    def without_poorjev(name, *args, **kwargs):
        if name == "poorjev" or name.startswith("poorjev."):
            raise ImportError("no poorjev")
        return real_import(name, *args, **kwargs)

    real_import = builtins.__import__
    monkeypatch.setattr(builtins, "__import__", without_poorjev)

    provider = PoorJevAnswerProvider(str(tmp_path))
    with pytest.raises(AnswerProviderError, match="ANSWER_DEPENDENCY_ABSENT"):
        provider._ask(make_request())


async def test_nan_confidence_raises_invalid_response(monkeypatch, tmp_path):
    provider = PoorJevAnswerProvider(str(tmp_path))
    monkeypatch.setattr(provider, "_read_manifest", lambda: {"model_id": "test_model", "revision": "rev"})

    req = make_request()

    def fake_ask(request):
        winning_text = HYPOTHESES["supported"].format(claim=request.claim)
        decision = SimpleNamespace(value=winning_text, confidence=float("nan"), abstained=False)
        return decision, [0.25, 0.25, 0.25, 0.25]

    monkeypatch.setattr(provider, "_ask", fake_ask)

    with pytest.raises(AnswerProviderError, match="ANSWER_INVALID_RESPONSE"):
        await provider.judge_support(req)
