"""H4 yönlendirme politikası — SAF, deterministik ve metinden bağımsız."""

from __future__ import annotations

from dataclasses import dataclass

from app.integrations.local_cognition import policy as policy_svc
from app.integrations.local_cognition.policy import ModelHealth, ModelProfile

CAPABILITIES = frozenset({"classify", "structured_extract", "query_rewrite", "structured_output"})
HEALTHY = ModelHealth(configured=True, provider_reachable=True, model_available=True, healthy=True)
UNHEALTHY = ModelHealth(configured=True, provider_reachable=True, model_available=False, healthy=False)
UNCONFIGURED = ModelHealth(
    configured=False, provider_reachable=False, model_available=False, healthy=False
)


@dataclass
class FakeSettings:
    h4_small_model: str = "small-x"
    h4_medium_model: str = "medium-y"
    h4_small_input_chars: int = 12000
    h4_medium_input_chars: int = 24000


def _profiles(small: str = "small-x", medium: str = "medium-y", *, small_budget: int = 12000,
              medium_budget: int = 24000, capabilities: frozenset[str] = CAPABILITIES) -> dict[str, ModelProfile]:
    return {
        "local-small": ModelProfile(
            slot="local-small", provider="ollama", model_id=small,
            execution_boundary="local_loopback", max_input_chars=small_budget,
            capabilities=capabilities,
        ),
        "local-medium": ModelProfile(
            slot="local-medium", provider="ollama", model_id=medium,
            execution_boundary="local_loopback", max_input_chars=medium_budget,
            capabilities=capabilities,
        ),
    }


def _health(small: ModelHealth = HEALTHY, medium: ModelHealth = HEALTHY) -> dict[str, ModelHealth]:
    return {"local-small": small, "local-medium": medium}


def test_small_is_selected_when_healthy_and_eligible() -> None:
    plan = policy_svc.route_task(
        lane="classify", input_chars=100, profiles=_profiles(), health=_health()
    )
    assert plan.selected_slot == "local-small"
    assert plan.eligible_slots == ("local-small", "local-medium")
    assert "LOCAL_SMALL_SELECTED" in plan.reason_codes
    assert "LANE_CLASSIFY" in plan.reason_codes


def test_medium_is_selected_when_small_is_unavailable() -> None:
    plan = policy_svc.route_task(
        lane="classify", input_chars=100, profiles=_profiles(small=""), health=_health(UNCONFIGURED)
    )
    assert plan.selected_slot == "local-medium"
    assert "LOCAL_SMALL_UNAVAILABLE" in plan.reason_codes
    assert "ESCALATED_TO_LOCAL_MEDIUM" in plan.reason_codes


def test_medium_is_selected_when_small_is_unhealthy() -> None:
    plan = policy_svc.route_task(
        lane="classify", input_chars=100, profiles=_profiles(), health=_health(UNHEALTHY)
    )
    assert plan.selected_slot == "local-medium"
    assert "LOCAL_SMALL_UNAVAILABLE" in plan.reason_codes


def test_medium_is_selected_when_input_exceeds_small_budget() -> None:
    plan = policy_svc.route_task(
        lane="structured_extract",
        input_chars=15000,
        profiles=_profiles(small_budget=12000, medium_budget=24000),
        health=_health(),
    )
    assert plan.selected_slot == "local-medium"
    assert "LOCAL_SMALL_CONTEXT_EXCEEDED" in plan.reason_codes
    assert "STRUCTURED_OUTPUT_REQUIRED" in plan.reason_codes


def test_no_eligible_model_when_input_exceeds_every_budget() -> None:
    plan = policy_svc.route_task(
        lane="structured_extract",
        input_chars=30000,
        profiles=_profiles(small_budget=12000, medium_budget=24000),
        health=_health(),
    )
    assert plan.selected_slot is None
    assert plan.eligible_slots == ()
    assert "NO_ELIGIBLE_MODEL" in plan.reason_codes


def test_no_eligible_model_when_nothing_is_configured() -> None:
    plan = policy_svc.route_task(
        lane="classify", input_chars=100, profiles=_profiles(small="", medium=""),
        health=_health(UNCONFIGURED, UNCONFIGURED),
    )
    assert plan.selected_slot is None
    assert "LOCAL_SMALL_UNAVAILABLE" in plan.reason_codes
    assert "LOCAL_MEDIUM_UNAVAILABLE" in plan.reason_codes
    assert "NO_ELIGIBLE_MODEL" in plan.reason_codes


def test_missing_capability_makes_a_slot_ineligible() -> None:
    plan = policy_svc.route_task(
        lane="query_rewrite",
        input_chars=100,
        profiles=_profiles(capabilities=frozenset({"classify", "structured_output"})),
        health=_health(),
    )
    assert plan.selected_slot is None
    assert "LOCAL_CAPABILITY_UNAVAILABLE" in plan.reason_codes


def test_required_capabilities_follow_the_lane() -> None:
    assert policy_svc.required_capabilities("classify") == ("classify", "structured_output")
    assert policy_svc.required_capabilities("structured_extract") == (
        "structured_extract",
        "structured_output",
    )
    assert policy_svc.required_capabilities("query_rewrite") == (
        "query_rewrite",
        "structured_output",
    )


def test_same_signals_produce_the_same_route() -> None:
    """Determinizm (§89): aynı girdi → aynı karar."""
    arguments = dict(
        lane="classify", input_chars=777, profiles=_profiles(), health=_health(UNHEALTHY)
    )
    assert policy_svc.route_task(**arguments) == policy_svc.route_task(**arguments)


def test_profiles_come_from_configuration_without_hard_coded_models() -> None:
    """Kodda sabit model adı YOKTUR (§54)."""
    profiles = policy_svc.build_profiles(FakeSettings())
    assert profiles["local-small"].model_id == "small-x"
    assert profiles["local-medium"].model_id == "medium-y"
    assert profiles["local-small"].max_input_chars == 12000
    assert profiles["local-medium"].max_input_chars == 24000

    empty = policy_svc.build_profiles(FakeSettings(h4_small_model="", h4_medium_model=""))
    assert empty["local-small"].configured is False
    assert empty["local-medium"].configured is False


def test_health_is_separate_from_eligibility() -> None:
    """Sağlıklı ama uygun olmayan model mümkündür (§57)."""
    plan = policy_svc.route_task(
        lane="structured_extract",
        input_chars=20000,
        profiles=_profiles(small_budget=12000),
        health=_health(HEALTHY, HEALTHY),
    )
    assert plan.selected_slot == "local-medium"
    assert "local-small" not in plan.eligible_slots
