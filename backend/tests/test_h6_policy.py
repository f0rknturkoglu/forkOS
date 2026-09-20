"""H6 dikkat politikası: saf, tablo tabanlı, veritabansız kararlar."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta

import pytest

from app.modules.proactivity import policy

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)
LOCAL = NOW.astimezone()  # politika yerel değeri DIŞARIDAN alır


def _state(**overrides: object) -> policy.PolicyInput:
    base = {
        "category": "deadline_soon",
        "now": NOW,
        "local_now": LOCAL,
        "master_enabled": True,
        "rule_enabled": True,
        "one_shot": True,
        "run_state": "candidate",
        "delivery_count": 0,
        "quiet_hours": None,
        "focus_active": False,
        "focus_deferral_enabled": True,
        "immediate_surfaces_today": 0,
        "immediate_budget": policy.MAX_IMMEDIATE_SURFACES_PER_DAY,
        "why_now": "YLSY için son tarih 3 gün içinde",
    }
    base.update(overrides)
    return policy.PolicyInput(**base)  # type: ignore[arg-type]


def test_silence_is_the_default_when_master_is_disabled() -> None:
    decision = policy.decide(_state(master_enabled=False, category="deadline_today"))
    assert decision.outcome == "silent"
    assert decision.reason_codes == ["PROACTIVITY_DISABLED"]


def test_disabled_rule_is_silent() -> None:
    decision = policy.decide(_state(rule_enabled=False))
    assert decision.outcome == "silent"
    assert decision.reason_codes == ["RULE_DISABLED"]


def test_user_snooze_beats_automation() -> None:
    decision = policy.decide(_state(snoozed_until=NOW + timedelta(hours=3)))
    assert decision.outcome == "silent"
    assert decision.reason_codes == ["USER_SNOOZED"]


def test_expired_snooze_does_not_suppress() -> None:
    decision = policy.decide(_state(snoozed_until=NOW - timedelta(hours=1)))
    assert decision.outcome == "surface"


def test_one_shot_condition_is_not_delivered_twice() -> None:
    decision = policy.decide(_state(delivery_count=1, run_state="delivered"))
    assert decision.outcome == "silent"
    assert decision.reason_codes == ["DUPLICATE_TRIGGER"]


def test_cooldown_suppresses_repeatable_condition() -> None:
    decision = policy.decide(
        _state(
            category="project_stalled",
            one_shot=False,
            delivery_count=1,
            last_delivered_at=NOW - timedelta(days=2),
            cooldown_hours=7 * 24,
        )
    )
    assert decision.outcome == "silent"
    assert decision.reason_codes == ["RECENTLY_SURFACED"]


def test_cooldown_expiry_allows_resurfacing() -> None:
    decision = policy.decide(
        _state(
            category="project_stalled",
            one_shot=False,
            delivery_count=1,
            last_delivered_at=NOW - timedelta(days=8),
            cooldown_hours=7 * 24,
        )
    )
    assert decision.outcome == "digest"


def test_quiet_hours_defer_even_critical_deadlines() -> None:
    """§32: H6 v1'de acil istisnasi YOK — T-1 bile 03:00'te durtmez."""
    night = datetime(2026, 9, 21, 2, 30, tzinfo=UTC)
    decision = policy.decide(
        _state(
            category="deadline_tomorrow",
            now=night,
            local_now=night,
            quiet_hours=(time(23, 30), time(8, 30)),
        )
    )
    assert decision.outcome == "defer"
    assert "QUIET_HOURS" in decision.reason_codes
    assert decision.earliest_delivery_at is not None
    assert decision.earliest_delivery_at.hour == 8


def test_quiet_hours_crossing_midnight_is_detected() -> None:
    assert policy.in_quiet_hours(time(23, 45), time(23, 30), time(8, 30)) is True
    assert policy.in_quiet_hours(time(3, 0), time(23, 30), time(8, 30)) is True
    assert policy.in_quiet_hours(time(9, 0), time(23, 30), time(8, 30)) is False
    # Gündüz penceresi de çalışır.
    assert policy.in_quiet_hours(time(13, 0), time(12, 0), time(14, 0)) is True
    assert policy.in_quiet_hours(time(11, 59), time(12, 0), time(14, 0)) is False


def test_focus_defers_non_critical_but_not_critical() -> None:
    deferred = policy.decide(_state(category="project_stalled", focus_active=True))
    assert deferred.outcome == "defer"
    assert deferred.reason_codes[0] == "FOCUS_ACTIVE"

    critical = policy.decide(_state(category="deadline_tomorrow", focus_active=True))
    assert critical.outcome == "surface"


def test_focus_deferral_can_be_disabled_by_user() -> None:
    decision = policy.decide(
        _state(category="project_stalled", focus_active=True, focus_deferral_enabled=False)
    )
    assert decision.outcome == "digest"


def test_daily_immediate_budget_pushes_extra_surfaces_to_digest() -> None:
    decision = policy.decide(_state(immediate_surfaces_today=3, immediate_budget=3))
    assert decision.outcome == "digest"
    assert "IMMEDIATE_BUDGET_EXHAUSTED" in decision.reason_codes


def test_budget_does_not_block_deferral_or_silence() -> None:
    quiet = policy.decide(
        _state(
            immediate_surfaces_today=3,
            immediate_budget=3,
            quiet_hours=(time(23, 30), time(8, 30)),
            local_now=datetime(2026, 9, 21, 2, 0),
            now=datetime(2026, 9, 21, 2, 0, tzinfo=UTC),
        )
    )
    assert quiet.outcome == "defer"


@pytest.mark.parametrize(
    ("category", "expected"),
    [
        ("deadline_today", "surface"),
        ("deadline_tomorrow", "surface"),
        ("deadline_soon", "surface"),
        ("deadline_near", "digest"),
        ("deadline_far", "digest"),
        ("continuity_comeback", "prepare"),
        ("ritual", "surface"),
        ("project_stalled", "digest"),
        ("accumulation", "digest"),
    ],
)
def test_category_delivery_policy_is_categorical(category: str, expected: str) -> None:
    """Ondalık skor YOK: kategori ya yüzeye çıkar ya sindirilir."""
    assert policy.decide(_state(category=category)).outcome == expected


def test_importance_is_bounded_and_ordered() -> None:
    assert policy.importance_for("deadline_today") == 3
    assert policy.importance_for("deadline_tomorrow") == 3
    assert policy.importance_for("deadline_soon") == 2
    assert policy.importance_for("project_stalled") == 1
    assert 1 <= policy.importance_for("unknown_category") <= 3


def test_decisions_are_deterministic() -> None:
    state = _state(category="continuity_comeback")
    first = policy.decide(state)
    second = policy.decide(state)
    assert first == second
    assert first.requires_revalidation is True


def test_every_reason_code_is_reachable() -> None:
    """Ölü sözleşme yok: tanımlı her gerekçe kodunun üretim yolu olmalı."""
    import pathlib

    # Yalnızca TANIM bloğu hariç tutulur: kod listesi kendini kanıtlamasın,
    # ama politikanın ürettiği kodlar da sayılsın.
    text = "\n".join(
        item.read_text(encoding="utf-8")
        for item in pathlib.Path("app/modules/proactivity").glob("*.py")
    )
    definition_start = text.index("REASON_CODES")
    definition_end = text.index(")", text.index("STALE_TRIGGER"))
    text = text[:definition_start] + text[definition_end:]
    emitted = {code for code in policy.REASON_CODES if f'"{code}"' in text}
    assert emitted == set(policy.REASON_CODES), sorted(set(policy.REASON_CODES) - emitted)


def test_no_opaque_scoring_fields_exist() -> None:
    """Güven/aciliyet olasılığı gibi opak alanlar YOKTUR."""
    fields = set(policy.InterventionDecision.__dataclass_fields__)
    assert fields == {"outcome", "reason_codes", "why_now", "earliest_delivery_at", "requires_revalidation"}
