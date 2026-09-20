#!/usr/bin/env python
"""H4 eval / benchmark koşucusu.

İki mod:

```bash
# Yonlendirme + dogrulama: ag YOK, model YOK (betikli saglayici)
backend/.venv/bin/python backend/scripts/h4_eval.py --routing

# Canli yerel model (yalnizca H4_LIVE=1 ve yapilandirilmis model varsa)
H4_LIVE=1 backend/.venv/bin/python backend/scripts/h4_eval.py --live
```

Vaka seti `docs/hermes/evals/h4-routing.yaml` içindedir (sentetik veri; gerçek
kişisel içerik yoktur). Çıktı yalnızca SAYI ve KOD içerir: kaynak metin, prompt
veya model yanıtı YAZDIRILMAZ (§93).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import settings  # noqa: E402
from app.integrations.local_cognition import models as lc_models  # noqa: E402
from app.integrations.local_cognition import service as lc_svc  # noqa: E402
from app.integrations.local_cognition.ollama import OllamaProvider  # noqa: E402
from app.integrations.local_cognition.policy import ModelHealth, ModelProfile  # noqa: E402
from tests.h4_test_provider import (  # noqa: E402
    HEALTHY,
    MODEL_MISSING,
    ScriptedProvider,
)

DEFAULT_DATASET = REPO_ROOT / "docs" / "hermes" / "evals" / "h4-routing.yaml"

#: Varsayılan (baseline) yapılandırma: vaka aksini yazmadıkça geçerlidir.
BASELINE_CONFIG: dict[str, Any] = {
    "enabled": True,
    "small_model": "local-small-model",
    "medium_model": "local-medium-model",
    "small_input_chars": 12000,
    "medium_input_chars": 24000,
    "small_healthy": True,
    "medium_healthy": True,
    "endpoint": "http://127.0.0.1:11434",
}


@dataclass
class CaseOutcome:
    """Tek bir vakanın SONUCU (içerik taşımaz)."""

    case_id: str
    category: str
    lane: str
    status: str
    failure_code: str | None
    selected_slot: str | None
    attempts: int
    latency_ms: float
    reason_codes: tuple[str, ...]
    attempt_failure_codes: tuple[str, ...]
    mismatches: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.mismatches


def _load_dataset(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict) or not isinstance(payload.get("cases"), list):
        raise SystemExit(f"invalid dataset: {path}")
    return list(payload["cases"])


def _profiles_from_config(config: dict[str, Any]) -> dict[str, ModelProfile]:
    capabilities = frozenset(
        {"classify", "structured_extract", "query_rewrite", "structured_output"}
    )
    return {
        "local-small": ModelProfile(
            slot="local-small",
            provider="ollama",
            model_id=str(config["small_model"]),
            execution_boundary="local_loopback",
            max_input_chars=int(config["small_input_chars"]),
            capabilities=capabilities,
        ),
        "local-medium": ModelProfile(
            slot="local-medium",
            provider="ollama",
            model_id=str(config["medium_model"]),
            execution_boundary="local_loopback",
            max_input_chars=int(config["medium_input_chars"]),
            capabilities=capabilities,
        ),
    }


def _health_from_config(config: dict[str, Any]) -> dict[str, ModelHealth]:
    def snapshot(slot: str, key: str) -> ModelHealth:
        model_id = str(config[f"{slot}_model"])
        if not model_id:
            return ModelHealth(
                configured=False, provider_reachable=False, model_available=False, healthy=False
            )
        return HEALTHY if config[key] else MODEL_MISSING

    return {
        "local-small": snapshot("small", "small_healthy"),
        "local-medium": snapshot("medium", "medium_healthy"),
    }


def _build_request(case: dict[str, Any]) -> lc_models.LaneRequest:
    return lc_models.build_lane_request(
        lane=case["lane"],
        text=case["text"],
        contract=case.get("contract"),
        labels=case.get("labels"),
        classification_goal=case.get("classification_goal"),
        protected_terms=case.get("protected_terms"),
    )


def _compare(case: dict[str, Any], outcome: CaseOutcome) -> tuple[str, ...]:
    expect = case.get("expect") or {}
    mismatches: list[str] = []

    if "status" in expect and expect["status"] != outcome.status:
        mismatches.append(f"status: {outcome.status} != {expect['status']}")
    if "failure_code" in expect and expect["failure_code"] != outcome.failure_code:
        mismatches.append(f"failure_code: {outcome.failure_code} != {expect['failure_code']}")
    if "selected_slot" in expect and expect["selected_slot"] != outcome.selected_slot:
        mismatches.append(f"selected_slot: {outcome.selected_slot} != {expect['selected_slot']}")
    if "attempts" in expect and expect["attempts"] != outcome.attempts:
        mismatches.append(f"attempts: {outcome.attempts} != {expect['attempts']}")
    if "reason_codes" in expect:
        missing = set(expect["reason_codes"]) - set(outcome.reason_codes)
        if missing:
            mismatches.append(f"missing reason_codes: {sorted(missing)}")
    if "attempt_failure_codes" in expect:
        expected_codes = list(expect["attempt_failure_codes"])
        if expected_codes != list(outcome.attempt_failure_codes):
            mismatches.append(
                f"attempt_failure_codes: {list(outcome.attempt_failure_codes)} != {expected_codes}"
            )
    return tuple(mismatches)


async def _run_case_routing(case: dict[str, Any]) -> CaseOutcome:
    """Betikli sağlayıcıyla tek vakayı koşar. Ağ ve model GEREKMEZ."""
    config = {**BASELINE_CONFIG, **(case.get("config") or {})}
    provider_block = case.get("provider") or {}
    provider = ScriptedProvider(
        responses=[str(item) for item in (provider_block.get("responses") or [])],
        script=str(provider_block.get("script") or "ok"),
    )

    original_enabled = settings.h4_enabled
    original_endpoint = settings.h4_ollama_base_url
    settings.h4_enabled = bool(config["enabled"])
    settings.h4_ollama_base_url = str(config["endpoint"])
    try:
        request = _build_request(case)
        response = await lc_svc.run_local_cognition(
            request,
            provider_factory=lambda: provider,
            profiles=_profiles_from_config(config),
            health_snapshot=_health_from_config(config),
        )
        decision = response.route_decision
        outcome = CaseOutcome(
            case_id=str(case["id"]),
            category=str(case.get("category", "")),
            lane=str(case["lane"]),
            status=response.status,
            failure_code=response.failure_code,
            selected_slot=decision.selected_slot,
            attempts=len(decision.attempts),
            latency_ms=decision.latency_ms,
            reason_codes=tuple(decision.reason_codes),
            attempt_failure_codes=tuple(
                attempt.failure_code or "valid" for attempt in decision.attempts
            ),
            mismatches=(),
        )
    except lc_models.H4Error as exc:
        outcome = CaseOutcome(
            case_id=str(case["id"]),
            category=str(case.get("category", "")),
            lane=str(case["lane"]),
            status="error",
            failure_code=exc.code,
            selected_slot=None,
            attempts=0,
            latency_ms=0.0,
            reason_codes=(),
            attempt_failure_codes=(),
            mismatches=(),
        )
    finally:
        settings.h4_enabled = original_enabled
        settings.h4_ollama_base_url = original_endpoint

    return CaseOutcome(
        **{**outcome.__dict__, "mismatches": _compare(case, outcome)}
    )


async def _run_case_live(case: dict[str, Any], provider: OllamaProvider) -> CaseOutcome:
    """Gerçek yerel modelle tek vakayı koşar."""
    request = _build_request(case)
    try:
        response = await lc_svc.run_local_cognition(request, provider_factory=lambda: provider)
    except lc_models.H4Error as exc:
        return CaseOutcome(
            case_id=str(case["id"]),
            category=str(case.get("category", "")),
            lane=str(case["lane"]),
            status="error",
            failure_code=exc.code,
            selected_slot=None,
            attempts=0,
            latency_ms=0.0,
            reason_codes=(),
            attempt_failure_codes=(),
            mismatches=(),
        )
    decision = response.route_decision
    return CaseOutcome(
        case_id=str(case["id"]),
        category=str(case.get("category", "")),
        lane=str(case["lane"]),
        status=response.status,
        failure_code=response.failure_code,
        selected_slot=decision.selected_slot,
        attempts=len(decision.attempts),
        latency_ms=decision.latency_ms,
        reason_codes=tuple(decision.reason_codes),
        attempt_failure_codes=tuple(
            attempt.failure_code or "valid" for attempt in decision.attempts
        ),
        mismatches=(),
    )


def _report(outcomes: list[CaseOutcome], *, live: bool) -> int:
    total = len(outcomes)
    successes = [item for item in outcomes if item.status == "success"]
    escalations = [item for item in outcomes if item.status == "needs_escalation"]
    errors = [item for item in outcomes if item.status == "error"]
    retried = [item for item in outcomes if item.attempts > 1]
    escalated = [item for item in outcomes if item.selected_slot == "local-medium"]
    latencies = sorted(item.latency_ms for item in successes)
    failures = [item for item in outcomes if not item.ok]

    def percentile(values: list[float], fraction: float) -> float:
        if not values:
            return 0.0
        index = min(len(values) - 1, int(round(fraction * (len(values) - 1))))
        return values[index]

    print("=== H4 eval " + ("(live provider)" if live else "(routing, scripted provider)") + " ===")
    print(f"cases                : {total}")
    print(f"validated success    : {len(successes)}")
    print(f"needs_escalation     : {len(escalations)}")
    print(f"error                : {len(errors)}")
    print(f"retried (>1 attempt) : {len(retried)}")
    print(f"escalated to medium  : {len(escalated)}")
    print(f"p50 latency (ms)     : {statistics.median(latencies) if latencies else 0.0:.2f}")
    print(f"p95 latency (ms)     : {percentile(latencies, 0.95):.2f}")
    print(f"expectation failures : {len(failures)}")

    codes: dict[str, int] = {}
    for item in outcomes:
        if item.failure_code:
            codes[item.failure_code] = codes.get(item.failure_code, 0) + 1
    if codes:
        print("failure codes        : " + ", ".join(f"{code}={count}" for code, count in sorted(codes.items())))

    for item in failures:
        print(f"  FAIL {item.case_id}: " + "; ".join(item.mismatches))
    for item in outcomes:
        if not item.ok or item.status != "success":
            detail = "; ".join(item.mismatches) if item.mismatches else "-"
            print(f"  {item.status:16} {item.case_id:24} {item.failure_code or '':28} {detail}")

    return 1 if failures else 0


async def _main_async(args: argparse.Namespace) -> int:
    dataset_path = Path(args.dataset) if args.dataset else DEFAULT_DATASET
    cases = _load_dataset(dataset_path)

    if args.routing:
        outcomes = [await _run_case_routing(case) for case in cases]
        return _report(outcomes, live=False)

    if not args.live:
        print("choose --routing or --live")
        return 2

    import os

    if os.environ.get("H4_LIVE") != "1":
        print("LIVE OLLAMA NOT AVAILABLE: set H4_LIVE=1 to run live evaluation")
        return 3
    if not settings.h4_small_model and not settings.h4_medium_model:
        print("LIVE OLLAMA NOT AVAILABLE: configure H4_SMALL_MODEL or H4_MEDIUM_MODEL")
        return 3

    provider = OllamaProvider(
        settings.h4_ollama_base_url, timeout_seconds=settings.h4_timeout_seconds
    )
    live_cases = [
        case for case in cases if (case.get("provider") or {}).get("script", "ok") == "ok"
    ]
    if args.lane:
        live_cases = [case for case in live_cases if case.get("lane") == args.lane]
    if args.contract:
        live_cases = [case for case in live_cases if case.get("contract") == args.contract]
    if args.limit:
        live_cases = live_cases[: args.limit]
    outcomes = [await _run_case_live(case, provider) for case in live_cases]
    print(f"model small  : {settings.h4_small_model or '(unset)'}")
    print(f"model medium : {settings.h4_medium_model or '(unset)'}")
    return _report(outcomes, live=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="H4 eval / benchmark")
    parser.add_argument("--routing", action="store_true", help="routing+validation replay (no network)")
    parser.add_argument("--live", action="store_true", help="live local model evaluation")
    parser.add_argument("--dataset", default=None, help="path to h4-routing.yaml")
    parser.add_argument("--lane", default=None, help="only cases for this lane")
    parser.add_argument("--contract", default=None, help="only cases for this extraction contract")
    parser.add_argument("--limit", type=int, default=None, help="max cases to run (live mode)")
    parser.add_argument("--json", action="store_true", help="emit machine-readable summary")
    args = parser.parse_args()
    code = asyncio.run(_main_async(args))
    if args.json:
        print(json.dumps({"exit_code": code}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
