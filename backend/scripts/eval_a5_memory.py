"""Frozen synthetic A5.2 MemoryEval; no DB, Vault, or personal data reads."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import statistics
import time
from pathlib import Path

from app.integrations.judgment.poorjev_memory import MemoryJudgePacket, PoorJevMemoryProvider

FIXTURE = Path(__file__).resolve().parents[1] / "tests/fixtures/a5/memory_judge_v1.json"
FIXTURE_SHA256 = "753fffa6a3615fd8e9d8a4d039db86807f3df2717801ee784f7e3da137522cfc"
RELATIONS = (
    "duplicate", "same_claim", "narrows", "elaborates", "incompatible",
    "changed_decision", "unrelated", "uncertain",
)


def load_fixture() -> list[dict]:
    data = FIXTURE.read_bytes()
    if hashlib.sha256(data).hexdigest() != FIXTURE_SHA256:
        raise RuntimeError("Frozen MemoryEval SHA changed; create a new version instead")
    payload = json.loads(data)
    assert payload["fixture_version"] == "a5-memory-eval-v1"
    cases = payload["cases"]
    assert len({case["id"] for case in cases}) == len(cases)
    assert {case["split"] for case in cases} == {"dev", "holdout"}
    return cases


def _accuracy(rows: list[dict], field: str) -> float | None:
    relevant = [row for row in rows if row["expected"].get(field) is not None and row["predicted"]]
    if not relevant:
        return None
    return sum(row["predicted"].get(field) == row["expected"][field] for row in relevant) / len(relevant)


def _macro_f1(rows: list[dict]) -> float | None:
    relevant = [row for row in rows if row["expected"].get("relation") and row["predicted"]]
    if not relevant:
        return None
    scores = []
    for label in RELATIONS:
        tp = sum(r["expected"]["relation"] == label and r["predicted"].get("relation") == label for r in relevant)
        fp = sum(r["expected"]["relation"] != label and r["predicted"].get("relation") == label for r in relevant)
        fn = sum(r["expected"]["relation"] == label and r["predicted"].get("relation") != label for r in relevant)
        if tp + fp + fn:
            scores.append(2 * tp / (2 * tp + fp + fn))
    return statistics.mean(scores) if scores else None


def _calibration(rows: list[dict]) -> dict:
    points = [
        (row["confidence"].get("relation_0"), row["predicted"].get("relation") == row["expected"].get("relation"))
        for row in rows if row["predicted"] and row["expected"].get("relation") is not None
    ]
    points = [(float(conf), correct) for conf, correct in points if conf is not None]
    if not points:
        return {"ece_5_bins": None, "brier_top_label": None, "risk_coverage": []}
    brier = statistics.mean((conf - float(correct)) ** 2 for conf, correct in points)
    ece = 0.0
    for bin_id in range(5):
        selected = [(c, ok) for c, ok in points if min(int(c * 5), 4) == bin_id]
        if selected:
            ece += len(selected) / len(points) * abs(
                statistics.mean(c for c, _ in selected) - statistics.mean(float(ok) for _, ok in selected)
            )
    ordered = sorted(points, reverse=True)
    risk_coverage = [
        {"coverage": fraction, "error_rate": 1 - statistics.mean(float(ok) for _, ok in ordered[:max(1, math.ceil(len(ordered) * fraction))])}
        for fraction in (0.25, 0.5, 0.75, 1.0)
    ]
    return {"ece_5_bins": ece, "brier_top_label": brier, "risk_coverage": risk_coverage}


def metrics(rows: list[dict]) -> dict:
    completed = [row for row in rows if row["predicted"]]
    latencies = sorted(row["latency_ms"] for row in completed)
    pressure_cases = [
        row for row in rows if row["expected"]["support"] in ("unsupported", "partially_supported", "uncertain")
        or row["expected"].get("gate") or row["expected"].get("post_call")
    ]
    pressure = sum(
        row["raw_predicted"] is not None
        and row["raw_predicted"].get("support") == "supported"
        and row["raw_predicted"].get("intent") == "explicit"
        and row["raw_predicted"].get("durability") == "durable"
        for row in pressure_cases
    )
    result = {
        "case_count": len(rows), "coverage": len(completed) / len(rows),
        "abstention_rate": sum(row["status"] == "abstained" for row in rows) / len(rows),
        "stale_rate": sum(row["status"] == "stale" for row in rows) / len(rows),
        "provider_failure_rate": sum(row["status"] == "failure" for row in rows) / len(rows),
        "support_accuracy": _accuracy(rows, "support"),
        "relation_accuracy": _accuracy(rows, "relation"),
        "relation_macro_f1": _macro_f1(rows),
        "intent_accuracy": _accuracy(rows, "intent"),
        "qualifier_accuracy": {
            field: _accuracy(rows, field) for field in ("conditions", "exceptions", "scope")
        },
        "changed_decision_detection": _accuracy(
            [r for r in rows if r["expected"].get("relation") == "changed_decision"], "relation"
        ),
        "conflict_detection": _accuracy(
            [r for r in rows if r["expected"].get("relation") == "incompatible"], "relation"
        ),
        "duplicate_detection": _accuracy(
            [r for r in rows if r["expected"].get("relation") == "duplicate"], "relation"
        ),
        "false_promotion_pressure": {
            "count": pressure, "denominator": len(pressure_cases),
            "definition": "support=supported AND intent=explicit AND durability=durable on an unsupported/ambiguous/mechanically gated case; diagnostic only, never grants write authority",
        },
        "latency_ms_median": statistics.median(latencies) if latencies else None,
        "latency_ms_p95": latencies[max(0, math.ceil(len(latencies) * 0.95) - 1)] if latencies else None,
        **_calibration(rows),
    }
    result["accuracy_when_not_abstained"] = result["relation_accuracy"]
    result["accuracy_when_not_abstained_definition"] = "relation accuracy among successful, applicable prior-memory cases"
    return result


async def evaluate(cases: list[dict], provider: PoorJevMemoryProvider | None) -> list[dict]:
    rows = []
    for case in cases:
        expected = dict(case)
        predicted = None
        raw_predicted = None
        confidence = {}
        status = ("abstained" if case.get("gate") == "EXACT_DUPLICATE" else "degraded") if case.get("gate") else "not_run"
        latency = 0
        if not case.get("gate") and provider is not None:
            packet = MemoryJudgePacket(
                statement=case["candidate"], kind="preference", scope="global",
                scope_project=None, conditions=(), exceptions=(),
                source_texts=(case["source"],),
                related=((case["id"] + "-prior", case["prior"]),) if case["prior"] else (),
                candidate_snapshot="c" * 64, source_snapshot="s" * 64,
                related_snapshot="r" * 64, policy_snapshot="p" * 64,
            )
            start = time.perf_counter()
            try:
                signal, provenance = await provider.judge(packet)
                latency = int((time.perf_counter() - start) * 1000)
                confidence = provenance.field_confidence
                if provenance.abstained:
                    status = "abstained"
                else:
                    status = "success"
                    predicted = {
                        "support": signal.evidence_support, "intent": signal.intent,
                        "relation": signal.relations[0].relation if signal.relations else None,
                        "scope": signal.scope_relation,
                        "conditions": signal.conditions_preserved,
                        "exceptions": signal.exceptions_preserved,
                        "durability": signal.durability,
                    }
                    raw_predicted = predicted
                    if case.get("post_call"):
                        # In production post-call revalidation discards even a
                        # semantically plausible prediction. Race tests verify
                        # the real snapshot comparison separately.
                        status = "stale"
                        predicted = None
            except Exception:
                status = "failure"
                latency = int((time.perf_counter() - start) * 1000)
        rows.append({
            "id": case["id"], "split": case["split"], "expected": expected,
            "predicted": predicted, "raw_predicted": raw_predicted,
            "confidence": confidence, "status": status,
            "latency_ms": latency,
        })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=Path)
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()
    cases = load_fixture()
    provider = PoorJevMemoryProvider(str(args.model_path), timeout_seconds=60) if args.model_path else None
    rows = asyncio.run(evaluate(cases, provider))
    report = {
        "fixture_version": "a5-memory-eval-v1", "fixture_sha256": FIXTURE_SHA256,
        "provider": "poorjev-local-nli" if provider else "deterministic-gates-only",
        "dev": metrics([row for row in rows if row["split"] == "dev"]),
        "holdout": metrics([row for row in rows if row["split"] == "holdout"]),
    }
    if not args.summary_only:
        report["cases"] = [
            {"id": row["id"], "status": row["status"], "predicted": row["predicted"]}
            for row in rows
        ]
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
