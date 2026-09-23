from datetime import UTC, datetime
from typing import get_args

import pytest
from pydantic import ValidationError

from app.integrations.judgment import models as m

pytestmark = pytest.mark.no_database


def snapshot():
    return m.SourceSnapshot(source_id="entity:1", source_type="entity", source_revision="r1", captured_at=datetime.now(UTC))


def test_frozen_vocabularies():
    assert get_args(m.JudgmentPurpose) == ("context", "memory_relation", "memory_support", "answer_evidence")
    assert get_args(m.JudgmentMode) == ("off", "shadow", "assist", "on")
    assert get_args(m.JudgmentStatus) == ("success", "abstained", "unavailable", "stale", "invalid")
    assert get_args(m.ContextUsefulness) == ("essential", "useful", "weak", "irrelevant", "uncertain")
    assert get_args(m.ContextRedundancy) == ("unique", "redundant", "uncertain")
    assert get_args(m.MemoryRelation) == ("same_claim", "narrows", "elaborates", "changed_decision", "incompatible", "unrelated", "uncertain")
    assert get_args(m.EvidenceSupport) == ("supported", "contradicted", "insufficient", "uncertain")
    assert len(get_args(m.AbstentionReason)) == 8
    assert len(get_args(m.JudgeCapability)) == 5
    assert get_args(m.ProviderLocality) == ("local", "remote")


def test_context_bounds_and_h3_order():
    item = m.ContextCandidate(evidence_id="entity:1", source_type="entity", title="Atlas", excerpt="Current state", retrieval_position=0, snapshot=snapshot())
    packet = m.ContextJudgmentRequest(request_id="r1", query="Atlas?", candidates=(item,))
    assert packet.candidates[0].evidence_id == "entity:1"
    with pytest.raises(ValidationError):
        m.ContextJudgmentRequest(request_id="r1", query="Atlas?", candidates=(item, item))
    with pytest.raises(ValidationError):
        m.ContextCandidate.model_validate({**item.model_dump(), "source_type": "hot_memory"})
    with pytest.raises(ValidationError):
        m.ContextCandidate.model_validate({**item.model_dump(), "excerpt": "x" * 1201})
    with pytest.raises(ValidationError):
        m.ContextJudgmentRequest(request_id="r1", query="Atlas?", candidates=(item,), schema_version="2")
    with pytest.raises(ValidationError):
        m.ContextJudgmentRequest(request_id="r1", query="Atlas?", candidates=(item,), purpose="judge")


def test_memory_and_answer_bounds_no_actions():
    memory = m.MemorySnapshot(item_id="1", statement="Prefer short answers", scope="global", snapshot=snapshot())
    assert m.MemoryRelationRequest(request_id="r1", candidate=memory, existing_card=memory)
    assert m.MemorySupportRequest(request_id="r1", candidate=memory, existing_card=memory)
    with pytest.raises(ValidationError):
        m.MemorySupportRequest(request_id="r1", candidate=memory, existing_card=memory, purpose="memory_relation")
    with pytest.raises(ValidationError):
        m.MemoryRelationVerdict(status="success", relation="same_claim", supersede=True)
    with pytest.raises(ValidationError):
        m.SupportVerdict(status="success", support="supported", write=True)
    evidence = m.AnswerEvidenceItem(evidence_id="entity:1", excerpt="Atlas uses Rust.", snapshot=snapshot())
    assert m.AnswerEvidenceRequest(request_id="r1", claim="Atlas uses Rust.", evidence=(evidence,), context_complete=True)
    with pytest.raises(ValidationError):
        m.AnswerEvidenceRequest(request_id="r1", claim="x" * 1001, evidence=(evidence,), context_complete=True)
    with pytest.raises(ValidationError):
        m.SourceSnapshot(source_id="1", source_type="entity", captured_at=datetime.now(UTC))
    with pytest.raises(ValidationError):
        m.SourceSnapshot(source_id="/private/note", source_type="vault", source_revision="r1", captured_at=datetime.now(UTC))


def test_result_validation():
    with pytest.raises(ValidationError):
        m.JudgmentMetadata(provider_confidence=1.1)
    with pytest.raises(ValidationError):
        m.ContextVerdict(evidence_id="e1", usefulness="true", redundancy="unique", status="success")
    with pytest.raises(ValidationError):
        m.MemoryRelationVerdict(status="abstained", relation="uncertain", reason_codes=("arbitrary",))
