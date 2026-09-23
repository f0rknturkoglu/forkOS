import re
from datetime import UTC, datetime
from pathlib import Path
from typing import get_args

import pytest

from app.integrations.judgment.evals import FIXTURES, baseline_metrics, load_fixture
from app.integrations.judgment.models import (
    ContextCandidate,
    ContextJudgmentRequest,
    ContextRedundancy,
    ContextUsefulness,
    EvidenceSupport,
    MemoryRelation,
    SourceSnapshot,
)
from app.integrations.judgment.policy import context_baseline

ROOT = Path(__file__).parent / "fixtures" / "a5"
pytestmark = pytest.mark.no_database


def test_v1_fixtures_frozen_and_complete():
    expected = {
        "context": {"directly_useful", "weak_lexical_overlap", "lexically_similar_irrelevant", "redundant_relevant", "historical_query", "current_state_query", "ambiguous_query", "complementary_sources", "out_of_scope", "privacy_blocked", "stale_source", "hot_memory_not_evidence", "unsafe_vault_path"},
        "memory": {"same_claim_paraphrase", "exact_duplicate", "narrows", "elaborates", "changed_decision", "direct_incompatibility", "same_entity_not_supersession", "same_subject_key_not_supersession", "same_project_not_contradiction", "historical_vs_current", "conditional_vs_unconditional", "insufficient_context", "ambiguous_relation", "newer_timestamp_not_replacement"},
        "answer_evidence": {"direct_support", "paraphrase_support", "contradiction", "surrounding_context_reverses", "related_insufficient", "partial_compound", "historical_as_current", "current_correct", "context_incomplete", "unsupported_added_detail", "joint_support", "ambiguous_evidence"},
    }
    for name in FIXTURES:
        data = load_fixture(name, ROOT)
        raw = (ROOT / f"{name}_eval_v1.json").read_text()
        assert not re.search(r"(?:/Users/|/home/|[A-Za-z]:\\|sk-[A-Za-z0-9]{12}|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,})", raw)
        cases = data["cases"]
        assert {case["category"] for case in cases} == expected[name]
        assert len({case["id"] for case in cases}) == len(cases)
        assert all(not case["id"].startswith("/") for case in cases)
        if name == "context":
            for case in cases:
                if "excluded" in case:
                    assert not case["items"]
                for item in case["items"]:
                    assert item["usefulness"] in get_args(ContextUsefulness)
                    assert item["redundancy"] in get_args(ContextRedundancy)
        elif name == "memory":
            assert all(case["relation"] in get_args(MemoryRelation) for case in cases)
        else:
            assert all(case["support"] in get_args(EvidenceSupport) for case in cases)


def test_baseline_measurements_are_conservative():
    for case in load_fixture("context", ROOT)["cases"]:
        if not case["items"]:
            continue
        candidates = tuple(
            ContextCandidate(
                evidence_id=item["id"],
                source_type=item["id"].split(":", 1)[0],
                title="Synthetic source",
                excerpt=item["text"],
                retrieval_position=position,
                snapshot=SourceSnapshot(source_id=item["id"], source_type=item["id"].split(":", 1)[0], source_revision="r1", captured_at=datetime.now(UTC)),
            )
            for position, item in enumerate(case["items"])
        )
        packet = ContextJudgmentRequest(request_id=case["id"], query=case["query"], candidates=candidates)
        assert context_baseline(packet) == tuple(item["id"] for item in case["items"])
    metrics = baseline_metrics(ROOT)
    assert metrics["context"] == {"eligible_cases": 8, "retained_items": 11, "false_exclusions": 0, "semantic_reorders": 0}
    assert metrics["memory"]["cases"] == 14
    assert metrics["memory"]["relation_matches"] == 4
    assert metrics["memory"]["uncertain"] == 13
    assert metrics["answer_evidence"] == {"cases": 12, "uncertain": 12, "false_supported": 0}
