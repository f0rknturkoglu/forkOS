"""Run the frozen synthetic ContextEval v1 against configured local jevmlx.

Explicit local command only; never called by forkOS startup or normal pytest.
"""

from __future__ import annotations

import asyncio
import json
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path

from app.config import settings
from app.integrations.judgment.evals import load_fixture
from app.integrations.judgment.jevmlx import ContextProviderError, JevMlxProvider
from app.integrations.judgment.models import (
    ContextCandidate,
    ContextJudgmentRequest,
    SourceSnapshot,
)

ROOT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "a5"


def build_request(case: dict) -> ContextJudgmentRequest:
    candidates = tuple(
        ContextCandidate(
            evidence_id=item["id"], source_type=item["id"].split(":", 1)[0],
            title="Synthetic source", excerpt=item["text"], retrieval_position=position,
            snapshot=SourceSnapshot(
                source_id=item["id"], source_type=item["id"].split(":", 1)[0],
                source_revision="context-v1", captured_at=datetime.now(UTC),
            ),
        )
        for position, item in enumerate(case["items"])
    )
    return ContextJudgmentRequest(request_id=case["id"], query=case["query"], candidates=candidates)


async def main() -> None:
    fixture = load_fixture("context", ROOT)
    provider = JevMlxProvider(settings.a5_jevmlx_base_url, timeout_seconds=settings.a5_context_timeout_seconds)
    if not await provider.health():
        raise RuntimeError("jevmlx /ready is not ready")
    cases = [case for case in fixture["cases"] if case["items"]]
    results = []
    durations = []
    models: set[str] = set()
    usefulness_matches = redundancy_matches = invalid = 0
    for case in cases:
        started = time.perf_counter()
        try:
            verdicts = await provider.judge_context(build_request(case))
        except ContextProviderError as exc:
            invalid += 1
            results.append({"case_id": case["id"], "error": exc.code})
            continue
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        durations.append(elapsed_ms)
        models.update(verdict.metadata.model_id for verdict in verdicts if verdict.metadata and verdict.metadata.model_id)
        pairs = []
        for expected, verdict in zip(case["items"], verdicts, strict=True):
            usefulness_matches += verdict.usefulness == expected["usefulness"]
            redundancy_matches += verdict.redundancy == expected["redundancy"]
            pairs.append({
                "evidence_id": verdict.evidence_id,
                "expected_usefulness": expected["usefulness"], "actual_usefulness": verdict.usefulness,
                "expected_redundancy": expected["redundancy"], "actual_redundancy": verdict.redundancy,
            })
        results.append({"case_id": case["id"], "latency_ms": elapsed_ms, "items": pairs})
    summary = {
        "dataset_version": fixture["dataset_version"],
        "provider": provider.provider_id,
        "models_reported": sorted(models),
        "eligible_cases": len(cases),
        "item_judgments": sum(len(case["items"]) for case in cases),
        "usefulness_matches": usefulness_matches,
        "redundancy_matches": redundancy_matches,
        "invalid_outputs": invalid,
        "provider_latency_median_ms": statistics.median(durations) if durations else None,
        "provider_latency_max_ms": max(durations) if durations else None,
        "results": results,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
