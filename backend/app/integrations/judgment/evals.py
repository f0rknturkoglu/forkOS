"""Immutable v1 fixture identity and deterministic control measurements."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .policy import answer_baseline, memory_baseline

FIXTURES = {
    "context": ("context-v1", "e6c7537e47e1ef0a1f65e6d262456508049a4a56b52fab70c35750c51eb216e4"),
    "memory": ("memory-v1", "c3eac5d7b65ec6b1f0319b7f4e9250f73f4fe49997a6c082a2e98907ae56b770"),
    "answer_evidence": ("answer-evidence-v1", "6de1b082e91c34d7f607999077caef2084d9dd514ac9093d056ca9825b718397"),
}


def load_fixture(name: str, root: Path) -> dict[str, Any]:
    version, digest = FIXTURES[name]
    path = root / f"{name}_eval_v1.json"
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError(f"frozen {name} v1 fixture changed; create a documented v2")
    data: dict[str, Any] = json.loads(raw)
    if data["schema_version"] != "1" or data["dataset_version"] != version:
        raise ValueError("fixture schema/dataset version mismatch")
    return data


def baseline_metrics(root: Path) -> dict[str, dict[str, int | float]]:
    """No semantic guess: conservative control metrics, not provider scores."""
    context = load_fixture("context", root)["cases"]
    memory = load_fixture("memory", root)["cases"]
    answer = load_fixture("answer_evidence", root)["cases"]
    eligible = [case for case in context if case["items"]]
    item_count = sum(len(case["items"]) for case in eligible)
    verdicts = [memory_baseline(candidate=case["candidate"], existing=case["existing"]) for case in memory]
    exact = sum(verdict == case["relation"] for verdict, case in zip(verdicts, memory, strict=True))
    answers = [
        answer_baseline(evidence_current=True, locator_valid=True, context_complete=case["context_complete"])
        for case in answer
    ]
    return {
        "context": {"eligible_cases": len(eligible), "retained_items": item_count, "false_exclusions": 0, "semantic_reorders": 0},
        "memory": {"cases": len(memory), "relation_matches": exact, "uncertain": verdicts.count("uncertain")},
        "answer_evidence": {"cases": len(answer), "uncertain": sum(verdict.support == "uncertain" for verdict in answers), "false_supported": sum(verdict.support == "supported" and case["support"] != "supported" for verdict, case in zip(answers, answer, strict=True))},
    }
