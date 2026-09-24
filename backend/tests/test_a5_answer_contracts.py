"""Contract, boundary, and baseline unit tests for A5.3 Answer Evidence Judge."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.integrations.judgment.models import (
    AnswerEvidenceItem,
    AnswerEvidenceRequest,
    SourceSnapshot,
    SupportVerdict,
)
from app.integrations.judgment.policy import (
    PurposeModes,
    answer_baseline,
    may_affect_selection,
    may_invoke,
)

pytestmark = pytest.mark.no_database


def snap(source_id: str = "item:1") -> SourceSnapshot:
    return SourceSnapshot(
        source_id=source_id,
        source_type="vault",
        source_revision="rev_1",
        captured_at=datetime.now(UTC),
    )


def item(evidence_id: str, excerpt: str = "Excerpt", context: str = "") -> AnswerEvidenceItem:
    return AnswerEvidenceItem(
        evidence_id=evidence_id,
        excerpt=excerpt,
        surrounding_context=context,
        snapshot=snap(evidence_id),
        remote_allowed=False,
    )


def test_answer_evidence_request_bounds():
    # Valid request
    req = AnswerEvidenceRequest(
        request_id="r1",
        claim="Atlas uses Rust.",
        evidence=(item("e1"),),
        context_complete=True,
    )
    assert req.claim == "Atlas uses Rust."

    # Duplicate evidence IDs forbidden
    with pytest.raises(ValidationError, match="duplicate evidence IDs"):
        AnswerEvidenceRequest(
            request_id="r2",
            claim="Atlas uses Rust.",
            evidence=(item("e1"), item("e1")),
            context_complete=True,
        )

    # Total excerpt budget exceeded (> 8000)
    with pytest.raises(ValidationError, match="budget exceeded"):
        AnswerEvidenceRequest(
            request_id="r3",
            claim="Atlas uses Rust.",
            evidence=tuple(item(f"e{i}", excerpt="a" * 1000) for i in range(9)),  # 9000 chars > 8000
            context_complete=True,
        )

    # Claim min_length = 2
    with pytest.raises(ValidationError):
        AnswerEvidenceRequest(
            request_id="r4",
            claim="",
            evidence=(item("e1"),),
            context_complete=True,
        )
    with pytest.raises(ValidationError):
        AnswerEvidenceRequest(
            request_id="r5",
            claim="x",
            evidence=(item("e1"),),
            context_complete=True,
        )
    # Claim max_length = 1000
    with pytest.raises(ValidationError):
        AnswerEvidenceRequest(
            request_id="r6",
            claim="a" * 1001,
            evidence=(item("e1"),),
            context_complete=True,
        )


def test_support_verdict_non_success_is_uncertain():
    # Success can have any support label
    v_succ = SupportVerdict(status="success", support="supported")
    assert v_succ.support == "supported"

    # Non-success must be uncertain
    with pytest.raises(ValidationError, match="non-success support verdict must be uncertain"):
        SupportVerdict(status="unavailable", support="supported")

    with pytest.raises(ValidationError, match="non-success support verdict must be uncertain"):
        SupportVerdict(status="abstained", support="contradicted")

    v_abst = SupportVerdict(status="abstained", support="uncertain")
    assert v_abst.support == "uncertain"


def test_answer_baseline_deterministic_policy():
    # Stale / invalid evidence
    b_stale = answer_baseline(evidence_current=False, locator_valid=True, context_complete=True)
    assert b_stale.status == "invalid"
    assert b_stale.support == "uncertain"
    assert "mechanical_policy_block" in b_stale.reason_codes

    # Invalid locator
    b_loc = answer_baseline(evidence_current=True, locator_valid=False, context_complete=True)
    assert b_loc.status == "invalid"
    assert b_loc.support == "uncertain"
    assert "mechanical_policy_block" in b_loc.reason_codes

    # Incomplete context
    b_inc = answer_baseline(evidence_current=True, locator_valid=True, context_complete=False)
    assert b_inc.status == "abstained"
    assert b_inc.support == "uncertain"
    assert "context_incomplete" in b_inc.reason_codes

    # Complete context
    b_comp = answer_baseline(evidence_current=True, locator_valid=True, context_complete=True)
    assert b_comp.status == "abstained"
    assert b_comp.support == "uncertain"
    assert "insufficient_evidence" in b_comp.reason_codes


def test_may_invoke_for_answer_evidence():
    # OFF mode
    d_off = may_invoke(
        purpose="answer_evidence",
        modes=PurposeModes(answer_evidence="off"),
        locality="local",
        capabilities=frozenset({"answer_support"}),
        remote_allowed=(False,),
        mechanically_eligible=True,
        provider_available=True,
    )
    assert not d_off.allowed
    assert d_off.status == "abstained"
    assert d_off.reason == "mechanical_policy_block"

    # Unsupported capability
    d_cap = may_invoke(
        purpose="answer_evidence",
        modes=PurposeModes(answer_evidence="on"),
        locality="local",
        capabilities=frozenset({"context_relevance"}),  # lacks answer_support
        remote_allowed=(False,),
        mechanically_eligible=True,
        provider_available=True,
    )
    assert not d_cap.allowed
    assert d_cap.status == "abstained"
    assert d_cap.reason == "unsupported_capability"

    # Remote locality without remote_allowed
    d_rem = may_invoke(
        purpose="answer_evidence",
        modes=PurposeModes(answer_evidence="on"),
        locality="remote",
        capabilities=frozenset({"answer_support"}),
        remote_allowed=(False,),
        mechanically_eligible=True,
        provider_available=True,
    )
    assert not d_rem.allowed
    assert d_rem.status == "invalid"

    # Valid local invocation
    d_ok = may_invoke(
        purpose="answer_evidence",
        modes=PurposeModes(answer_evidence="shadow"),
        locality="local",
        capabilities=frozenset({"answer_support"}),
        remote_allowed=(False,),
        mechanically_eligible=True,
        provider_available=True,
    )
    assert d_ok.allowed
    assert d_ok.status == "success"


def test_may_affect_selection_authority_boundary():
    # In shadow, never affects selection
    assert not may_affect_selection(mode="shadow", status="success", sources_current=True)
    # In off, never affects selection
    assert not may_affect_selection(mode="off", status="success", sources_current=True)
    # In assist/on with stale sources, never affects selection
    assert not may_affect_selection(mode="on", status="success", sources_current=False)
    # In assist/on with failed status, never affects selection
    assert not may_affect_selection(mode="on", status="stale", sources_current=True)
    # In on with success and current sources, allowed
    assert may_affect_selection(mode="on", status="success", sources_current=True)
    assert may_affect_selection(mode="assist", status="success", sources_current=True)
