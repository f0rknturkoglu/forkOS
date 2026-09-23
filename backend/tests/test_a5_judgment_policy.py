from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.integrations.judgment.models import (
    ContextCandidate,
    ContextJudgmentRequest,
    ContextVerdict,
    SourceSnapshot,
)
from app.integrations.judgment.policy import (
    PurposeModes,
    answer_baseline,
    context_verdicts_valid,
    grants_write_authority,
    may_affect_selection,
    may_invoke,
    memory_baseline,
    revalidate_snapshots,
)

pytestmark = pytest.mark.no_database


def decision(**overrides):
    args = dict(purpose="context", modes=PurposeModes(context="on"), locality="local", capabilities=frozenset({"context_relevance"}), remote_allowed=(True,), mechanically_eligible=True, provider_available=True)
    return may_invoke(**(args | overrides))


def test_off_shadow_remote_and_unavailable():
    assert set(PurposeModes().model_dump().values()) == {"off"}
    with pytest.raises(ValidationError):
        PurposeModes(context="unknown")
    assert not decision(modes=PurposeModes()).allowed
    assert decision(locality="local", remote_allowed=(False,)).allowed
    assert decision(locality="local", remote_allowed=(True,)).allowed
    assert decision(locality="local", remote_allowed=()).allowed
    assert decision(locality="remote", remote_allowed=(True,)).allowed
    assert not decision(locality="remote", remote_allowed=(False,)).allowed
    assert not decision(locality="remote", remote_allowed=(True, False)).allowed
    assert decision(locality="remote", remote_allowed=(True, True)).allowed
    assert not decision(mechanically_eligible=False).allowed
    assert not decision(locality="remote", mechanically_eligible=False).allowed
    assert decision(capabilities=frozenset()).reason == "unsupported_capability"
    assert decision(provider_available=False).status == "unavailable"
    assert decision().allowed
    assert not may_affect_selection(mode="shadow", status="success", sources_current=True)
    assert may_affect_selection(mode="assist", status="success", sources_current=True)
    assert not may_affect_selection(mode="on", status="stale", sources_current=False)


def test_source_changed_is_stale_and_never_authorizes():
    one = SourceSnapshot(source_id="c1", source_type="card", source_revision="a", captured_at=datetime.now(UTC))
    two = one.model_copy(update={"source_revision": "b"})
    assert revalidate_snapshots((one,), (two,)) == "stale"
    assert revalidate_snapshots((one,), (one,)) == "success"
    assert revalidate_snapshots((one,), ()) == "stale"
    for mode in ("off", "shadow", "assist", "on"):
        assert grants_write_authority(mode=mode, status="success") is False


def test_conservative_baselines():
    assert memory_baseline(candidate="same", existing="same") == "same_claim"
    assert memory_baseline(candidate="Prefer concise replies.", existing="Prefer concise replies.") == "same_claim"
    assert memory_baseline(candidate="Prefer concise replies.", existing="  PREFER   CONCISE REPLIES. ") == "same_claim"
    assert memory_baseline(candidate="Ａｔｌａｓ", existing="Atlas") == "same_claim"
    assert memory_baseline(candidate="Prefer concise replies.", existing="Keep answers brief.") == "uncertain"
    assert memory_baseline(candidate="Rust", existing="Python") == "uncertain"
    valid = answer_baseline(evidence_current=True, locator_valid=True, context_complete=True)
    assert valid.support == "uncertain" and valid.status == "abstained"
    assert answer_baseline(evidence_current=False, locator_valid=True, context_complete=True).status == "invalid"
    assert answer_baseline(evidence_current=True, locator_valid=False, context_complete=True).status == "invalid"
    assert answer_baseline(evidence_current=True, locator_valid=True, context_complete=False).reason_codes == ("context_incomplete",)


def test_context_cannot_invent_evidence():
    snap = SourceSnapshot(source_id="entity:1", source_type="entity", source_revision="r1", captured_at=datetime.now(UTC))
    item = ContextCandidate(evidence_id="entity:1", source_type="entity", title="Atlas", excerpt="Status", retrieval_position=0, snapshot=snap)
    request = ContextJudgmentRequest(request_id="r1", query="Atlas?", candidates=(item,))
    real = ContextVerdict(evidence_id="entity:1", usefulness="useful", redundancy="unique", status="success")
    invented = real.model_copy(update={"evidence_id": "entity:other"})
    assert context_verdicts_valid(request, (real,))
    assert not context_verdicts_valid(request, (invented,))
    assert not context_verdicts_valid(request, (real, real))
    assert not context_verdicts_valid(request, ())

    items = tuple(
        ContextCandidate(
            evidence_id=f"entity:{index}", source_type="entity", title="Atlas", excerpt="Status",
            retrieval_position=index, snapshot=snap,
        )
        for index in range(15)
    )
    full = ContextJudgmentRequest(request_id="r15", query="Atlas?", candidates=items)
    verdicts = tuple(real.model_copy(update={"evidence_id": item.evidence_id}) for item in items)
    assert context_verdicts_valid(full, verdicts)
    assert not context_verdicts_valid(full, verdicts[:-1])
    assert not context_verdicts_valid(full, verdicts[:-1] + (invented,))
    assert not context_verdicts_valid(full, verdicts[:-1] + (verdicts[0],))
