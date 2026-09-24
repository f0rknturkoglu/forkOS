"""Evaluation script for A5.3 Answer Evidence Judge against frozen benchmarks."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.integrations.judgment.models import (
    AnswerEvidenceItem,
    AnswerEvidenceRequest,
    SourceSnapshot,
)
from app.integrations.judgment.policy import answer_baseline
from app.integrations.judgment.poorjev_answer import PoorJevAnswerProvider

FROZEN_FIXTURE = Path(__file__).resolve().parents[1] / "tests/fixtures/a5/answer_evidence_eval_v1.json"
FROZEN_SHA256 = "6de1b082e91c34d7f607999077caef2084d9dd514ac9093d056ca9825b718397"

RUNTIME_FIXTURE = Path(__file__).resolve().parents[1] / "tests/fixtures/a5/answer_runtime_v1.json"
RUNTIME_SHA256 = "2394d8519e4cea8ae0af35463d834baa94108d9fac34fa26826b8a9539dc9190"

LABELS = ("supported", "contradicted", "insufficient", "uncertain")


def load_frozen_fixture() -> list[dict[str, Any]]:
    data = FROZEN_FIXTURE.read_bytes()
    if hashlib.sha256(data).hexdigest() != FROZEN_SHA256:
        raise RuntimeError("Frozen AnswerEvidenceEval SHA changed; create a documented v2 instead")
    payload = json.loads(data)
    assert payload["dataset_version"] == "answer-evidence-v1"
    cases = payload["cases"]
    assert len({case["id"] for case in cases}) == len(cases)
    return cases


def load_runtime_fixture() -> list[dict[str, Any]]:
    data = RUNTIME_FIXTURE.read_bytes()
    if hashlib.sha256(data).hexdigest() != RUNTIME_SHA256:
        raise RuntimeError("Supplemental answer_runtime_v1 SHA changed; create a documented v2 instead")
    payload = json.loads(data)
    assert payload["dataset_version"] == "a5-answer-runtime-v1"
    cases = payload["cases"]
    assert len({case["id"] for case in cases}) == len(cases)
    return cases


def make_request_from_case(case: dict[str, Any]) -> AnswerEvidenceRequest:
    evidence_items = []
    captured_at = datetime.now(UTC)
    for i, text in enumerate(case["evidence"]):
        snap = SourceSnapshot(
            source_id=f"item:{i}",
            source_type="vault",
            source_revision=f"r_{i}",
            captured_at=captured_at,
        )
        evidence_items.append(
            AnswerEvidenceItem(
                evidence_id=f"item:{i}",
                excerpt=text,
                surrounding_context=case.get("surrounding_context", "") or "",
                snapshot=snap,
                remote_allowed=False,
            )
        )
    return AnswerEvidenceRequest(
        request_id=f"eval-{case['id']}",
        claim=case["claim"],
        evidence=tuple(evidence_items),
        context_complete=bool(case.get("context_complete", True)),
    )


def compute_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(results)
    if n == 0:
        return {}

    correct = sum(r["predicted"] == r["expected"] for r in results)
    accuracy = correct / n

    # Macro-F1
    f1_scores = []
    for label in LABELS:
        tp = sum(r["expected"] == label and r["predicted"] == label for r in results)
        fp = sum(r["expected"] != label and r["predicted"] == label for r in results)
        fn = sum(r["expected"] == label and r["predicted"] != label for r in results)
        if tp + fp + fn > 0:
            f1_scores.append(2 * tp / (2 * tp + fp + fn))
        else:
            f1_scores.append(1.0 if tp == 0 and fp == 0 and fn == 0 else 0.0)
    macro_f1 = statistics.mean(f1_scores) if f1_scores else 0.0

    # Supported Precision & Recall
    sup_tp = sum(r["expected"] == "supported" and r["predicted"] == "supported" for r in results)
    sup_fp = sum(r["expected"] != "supported" and r["predicted"] == "supported" for r in results)
    sup_fn = sum(r["expected"] == "supported" and r["predicted"] != "supported" for r in results)
    supported_precision = sup_tp / (sup_tp + sup_fp) if (sup_tp + sup_fp) > 0 else 1.0
    supported_recall = sup_tp / (sup_tp + sup_fn) if (sup_tp + sup_fn) > 0 else 0.0

    # False-supported count and rate (MOST CRITICAL METRIC)
    # Number of times model predicted "supported" when expected was NOT supported
    false_supported_count = sup_fp
    non_supported_total = sum(r["expected"] != "supported" for r in results)
    false_supported_rate = false_supported_count / non_supported_total if non_supported_total > 0 else 0.0

    # Contradiction recall
    contra_tp = sum(r["expected"] == "contradicted" and r["predicted"] == "contradicted" for r in results)
    contra_expected = sum(r["expected"] == "contradicted" for r in results)
    contradiction_recall = contra_tp / contra_expected if contra_expected > 0 else 1.0

    # Insufficient recall
    insuff_tp = sum(r["expected"] == "insufficient" and r["predicted"] == "insufficient" for r in results)
    insuff_expected = sum(r["expected"] == "insufficient" for r in results)
    insufficient_recall = insuff_tp / insuff_expected if insuff_expected > 0 else 1.0

    # Uncertain rate
    uncertain_count = sum(r["predicted"] == "uncertain" for r in results)
    uncertain_rate = uncertain_count / n

    # Latencies
    latencies = [r["latency_ms"] for r in results if r.get("latency_ms") is not None]
    median_latency = statistics.median(latencies) if latencies else 0.0
    p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else (max(latencies) if latencies else 0.0)

    # Provider failures
    failures = sum(bool(r.get("error")) for r in results)

    # Calibration / Brier
    conf_points = [
        (float(r["confidence"]), r["predicted"] == r["expected"])
        for r in results
        if r.get("confidence") is not None and math.isfinite(float(r["confidence"]))
    ]
    brier = (
        statistics.mean((c - float(ok)) ** 2 for c, ok in conf_points)
        if conf_points
        else None
    )

    return {
        "cases": n,
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "supported_precision": round(supported_precision, 4),
        "supported_recall": round(supported_recall, 4),
        "false_supported_count": false_supported_count,
        "false_supported_rate": round(false_supported_rate, 4),
        "contradiction_recall": round(contradiction_recall, 4),
        "insufficient_recall": round(insufficient_recall, 4),
        "uncertain_rate": round(uncertain_rate, 4),
        "median_latency_ms": round(median_latency, 1),
        "p95_latency_ms": round(p95_latency, 1),
        "provider_failures": failures,
        "brier_score": round(brier, 4) if brier is not None else None,
    }


async def run_eval(model_path: str | None = None) -> dict[str, Any]:
    provider = PoorJevAnswerProvider(model_path) if model_path else None
    frozen_cases = load_frozen_fixture()
    runtime_cases = load_runtime_fixture()

    async def evaluate_suite(cases: list[dict[str, Any]], expected_key: str = "support") -> list[dict[str, Any]]:
        results = []
        for case in cases:
            req = make_request_from_case(case)
            expected = case.get(expected_key) or case.get("expected_support")
            if provider is not None:
                t0 = time.perf_counter()
                try:
                    verdict, prov = await provider.judge_support(req)
                    latency = prov.latency_ms
                    predicted = verdict.support
                    conf = verdict.metadata.provider_confidence if verdict.metadata else None
                    err = None
                except Exception as exc:
                    latency = int((time.perf_counter() - t0) * 1000)
                    predicted = "uncertain"
                    conf = None
                    err = str(exc)
            else:
                verdict = answer_baseline(
                    evidence_current=True, locator_valid=True, context_complete=req.context_complete
                )
                predicted = verdict.support
                latency = 0
                conf = None
                err = None

            results.append({
                "id": case["id"],
                "category": case.get("category", ""),
                "expected": expected,
                "predicted": predicted,
                "confidence": conf,
                "latency_ms": latency,
                "error": err,
                "split": case.get("split", "frozen"),
            })
        return results

    frozen_results = await evaluate_suite(frozen_cases, expected_key="support")
    runtime_results = await evaluate_suite(runtime_cases, expected_key="expected_support")

    runtime_dev = [r for r in runtime_results if r["split"] == "dev"]
    runtime_holdout = [r for r in runtime_results if r["split"] == "holdout"]

    return {
        "provider": "poorjev-local-nli" if provider else "deterministic-baseline-only",
        "frozen_v1": compute_metrics(frozen_results),
        "runtime_dev": compute_metrics(runtime_dev),
        "runtime_holdout": compute_metrics(runtime_holdout),
        "runtime_combined": compute_metrics(runtime_results),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate A5.3 Answer Evidence Judge")
    parser.add_argument("--model-path", help="Path to local poorjev model directory")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    results = asyncio.run(run_eval(args.model_path))
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"=== A5.3 Answer Evidence Evaluation (Provider: {results['provider']}) ===")
        print(f"Frozen v1 (12 cases): {results['frozen_v1']}")
        print(f"Runtime Dev (12 cases): {results['runtime_dev']}")
        print(f"Runtime Holdout (12 cases): {results['runtime_holdout']}")
        print(f"Runtime Combined (24 cases): {results['runtime_combined']}")


if __name__ == "__main__":
    main()
