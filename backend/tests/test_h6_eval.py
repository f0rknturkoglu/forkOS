"""H6 değerlendirme veri seti: `docs/hermes/evals/h6-proactivity.yaml` ÇALIŞTIRILIR.

Veri seti dokümantasyon değil, SÖZLEŞMEDİR: her saf politika vakası gerçek
`policy.decide()` ile tekrar oynatılır. Bir politika değişikliği veri setini
kırarsa bu test kırılır — sessizlik davranışı böylece kilitlenir.

Servis yaşam döngüsü vakaları (`lifecycle != null`) burada oynatılmaz;
onların davranışı `test_h6_service.py` içinde gerçek tur üzerinden doğrulanır.
"""

from __future__ import annotations

import pathlib
from datetime import UTC, datetime, time, timedelta
from typing import Any

import pytest
import yaml

from app.core.time import local_zone
from app.modules.proactivity import policy

#: Veri setinin çapası: yerel 2026-09-21T14:00+03:00 → UTC 11:00Z.
ANCHOR_UTC = datetime(2026, 9, 21, 11, 0, tzinfo=UTC)
EVAL_PATH = pathlib.Path("../docs/hermes/evals/h6-proactivity.yaml")


def _load_cases() -> list[dict[str, Any]]:
    data = yaml.safe_load(EVAL_PATH.read_text(encoding="utf-8"))
    return list(data["cases"])


def _state_for(case: dict[str, Any]) -> policy.PolicyInput:
    raw = case["state"]
    local_time = raw.get("local_time")
    if local_time:
        hour, minute = (int(part) for part in str(local_time).split(":"))
        # DUVAR SAATI yerel dilimde kurulur: ofset eklemek ani kaydırır, saati değil.
        local_now = datetime(2026, 9, 21, hour, minute, tzinfo=local_zone())
        now = local_now.astimezone(UTC)
    else:
        local_now = ANCHOR_UTC.astimezone(local_zone())
        now = ANCHOR_UTC

    quiet = raw.get("quiet_hours")
    quiet_hours = None
    if quiet:
        quiet_hours = (time.fromisoformat(quiet[0]), time.fromisoformat(quiet[1]))

    last_delivered = raw.get("last_delivered_at")
    delivered_at = None
    if last_delivered:
        delivered_at = now + timedelta(hours=int(str(last_delivered).replace("h", "")))

    return policy.PolicyInput(
        category=raw["category"],
        now=now,
        local_now=local_now,
        master_enabled=bool(raw["master_enabled"]),
        rule_enabled=bool(raw["rule_enabled"]),
        one_shot=bool(raw.get("one_shot", True)),
        run_state="candidate",
        delivery_count=int(raw.get("delivery_count", 0)),
        last_delivered_at=delivered_at,
        snoozed_until=now + timedelta(hours=3) if raw.get("snoozed") else None,
        cooldown_hours=raw.get("cooldown_hours"),
        quiet_hours=quiet_hours,
        focus_active=bool(raw.get("focus_active", False)),
        focus_deferral_enabled=bool(raw.get("focus_deferral_enabled", True)),
        immediate_surfaces_today=int(raw.get("immediate_surfaces_today", 0)),
        immediate_budget=int(raw.get("immediate_budget", policy.MAX_IMMEDIATE_SURFACES_PER_DAY)),
    )


CASES = _load_cases()
PURE_CASES = [case for case in CASES if not case.get("lifecycle")]
LIFECYCLE_CASES = [case for case in CASES if case.get("lifecycle")]


def test_eval_dataset_shape() -> None:
    assert len(CASES) >= 30
    assert len({case["id"] for case in CASES}) == len(CASES)
    # Sessizlik çoğunluğu: yalnız pozitif vakalarla değerlendirme YAPILMAZ.
    negative = [case for case in CASES if case["expected_outcome"] in {"silent", "defer"}]
    assert len(negative) >= 12
    for case in CASES:
        assert case["expected_outcome"] in {*policy.OUTCOMES, "cancel"}
        for code in case["expected_reason_codes"]:
            assert code in policy.REASON_CODES


@pytest.mark.parametrize("case", PURE_CASES, ids=[case["id"] for case in PURE_CASES])
def test_policy_replays_every_case(case: dict[str, Any]) -> None:
    decision = policy.decide(_state_for(case))
    assert decision.outcome == case["expected_outcome"], case["scenario"]
    assert decision.reason_codes == list(case["expected_reason_codes"]), case["scenario"]


def test_lifecycle_cases_are_covered_elsewhere() -> None:
    """Yaşam döngüsü vakaları servis testlerinde karşılık bulmalı."""
    lifecycle_kinds = {case["lifecycle"] for case in LIFECYCLE_CASES}
    assert lifecycle_kinds <= {
        "revalidate_failed",
        "stale_trigger",
        "rule_disabled",
        "no_meaningful_content",
        "duplicate_delivery",
        "snooze_expired",
    }
    service_source = pathlib.Path("tests/test_h6_service.py").read_text(encoding="utf-8")
    for marker in ("CONDITION_RESOLVED", "STALE_TRIGGER", "RULE_DISABLED", "snoozed"):
        assert marker in service_source


def test_eval_dataset_contains_no_personal_data() -> None:
    """Veri seti sentetiktir: kişisel kimlik taşımaz."""
    text = EVAL_PATH.read_text(encoding="utf-8")
    for forbidden in ("furkanturkoglu", "@gmail", "github.com/f0rk", "forkos_pgdata"):
        assert forbidden not in text
