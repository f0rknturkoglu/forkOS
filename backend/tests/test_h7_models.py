"""H7 plan modeli: revizyon determinizmi, durum makinesi, adım sözleşmesi."""

from __future__ import annotations

import pytest

from app.modules.execution import revision as revision_mod
from app.modules.execution import state as state_mod
from app.modules.execution.models import MAX_PLAN_STEPS, PLAN_STATES, TERMINAL_PLAN_STATES
from app.modules.execution.steps import StepError, validate_steps


def _steps(count: int = 1) -> list[dict]:
    return [
        {
            "step_id": f"s{index + 1}",
            "action": "todo_create",
            "arguments": {"title": f"Görev {index + 1}"},
        }
        for index in range(count)
    ]


def test_revision_is_deterministic_and_content_addressed() -> None:
    plan = revision_mod.normalized_plan(
        title="ALES", summary="özet", reason="gerekçe", steps=_steps(2)
    )
    first = revision_mod.revision_of(plan)
    second = revision_mod.revision_of(
        revision_mod.normalized_plan(
            title="ALES", summary="özet", reason="gerekçe", steps=_steps(2)
        )
    )
    assert first == second
    assert first.startswith(f"{revision_mod.REVISION_VERSION}:")
    assert len(first) == len(revision_mod.REVISION_VERSION) + 1 + 64


def test_revision_ignores_key_order_and_evidence_order() -> None:
    a = revision_mod.normalized_plan(
        title="t",
        summary=None,
        reason=None,
        steps=[{"step_id": "s1", "action": "todo_create", "arguments": {"title": "x", "priority": 2}}],
        source_refs=["entity:2", "entity:1"],
    )
    b = revision_mod.normalized_plan(
        title="t",
        summary=None,
        reason=None,
        steps=[{"step_id": "s1", "action": "todo_create", "arguments": {"priority": 2, "title": "x"}}],
        source_refs=["entity:1", "entity:2"],
    )
    assert revision_mod.revision_of(a) == revision_mod.revision_of(b)


def test_revision_changes_when_content_changes() -> None:
    base = revision_mod.normalized_plan(title="t", summary=None, reason=None, steps=_steps(1))
    changed = revision_mod.normalized_plan(
        title="t",
        summary=None,
        reason=None,
        steps=[
            {"step_id": "s1", "action": "todo_create", "arguments": {"title": "BAŞKA"}},
        ],
    )
    assert revision_mod.revision_of(base) != revision_mod.revision_of(changed)


def test_revision_excludes_nonsemantic_fields() -> None:
    """`state`, onay, zaman ve DB kimliği revizyona GİRMEZ."""
    plan = revision_mod.normalized_plan(title="t", summary=None, reason=None, steps=_steps(1))
    assert "created_at" not in plan
    assert "state" not in plan
    assert "approved_at" not in plan
    assert "plan_id" not in plan
    assert plan["version"] == revision_mod.REVISION_VERSION


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("completed", "approved"),
        ("rejected", "executing"),
        ("expired", "approved"),
        ("cancelled", "awaiting_approval"),
        ("executing", "approved"),
        ("draft", "executing"),
    ],
)
def test_invalid_transitions_are_rejected(current: str, target: str) -> None:
    with pytest.raises(state_mod.TransitionError):
        state_mod.ensure_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("input_required", "draft"),
        ("awaiting_approval", "approved"),
        ("awaiting_approval", "rejected"),
        ("approved", "executing"),
        ("executing", "completed"),
        ("executing", "partial"),
        ("executing", "failed"),
    ],
)
def test_valid_transitions_are_allowed(current: str, target: str) -> None:
    state_mod.ensure_transition(current, target)


def test_terminal_states_have_no_exit() -> None:
    for state in TERMINAL_PLAN_STATES:
        assert state_mod.ALLOWED_TRANSITIONS[state] == frozenset()
    assert set(state_mod.ALLOWED_TRANSITIONS) == set(PLAN_STATES)


def test_budget_constants_are_bounded() -> None:
    assert 1 <= MAX_PLAN_STEPS <= 20


def test_unknown_action_is_rejected() -> None:
    for action in ("shell", "sql", "delete_everything", "arbitrary_http", ""):
        with pytest.raises(StepError, match="UNKNOWN_ACTION"):
            validate_steps([{"action": action, "arguments": {}}])


def test_arguments_are_validated_by_h1_schema() -> None:
    """Argüman şeması H1'in kendi modelidir: ikinci bir doğrulama yazılmaz."""
    with pytest.raises(StepError, match="INVALID_STEP_ARGUMENT"):
        validate_steps([{"action": "todo_create", "arguments": {"title": ""}}])
    with pytest.raises(StepError, match="INVALID_STEP_ARGUMENT"):
        validate_steps([{"action": "todo_update", "arguments": {"todo_id": "yok"}}])


def test_step_budget_is_enforced() -> None:
    with pytest.raises(StepError, match="PLAN_BUDGET_EXCEEDED"):
        validate_steps(_steps(MAX_PLAN_STEPS + 1))


def test_empty_and_duplicate_steps_are_rejected() -> None:
    with pytest.raises(StepError, match="PLAN_HAS_NO_STEPS"):
        validate_steps([])
    with pytest.raises(StepError, match="DUPLICATE_STEP_ID"):
        validate_steps(
            [
                {"step_id": "s1", "action": "todo_create", "arguments": {"title": "a"}},
                {"step_id": "s1", "action": "todo_create", "arguments": {"title": "b"}},
            ]
        )


def test_valid_steps_normalize_through_h1_model() -> None:
    validated = validate_steps(
        [
            {
                "step_id": "s1",
                "action": "todo_create",
                "arguments": {"title": "ALES başvurusunu tamamla", "priority": 3},
                "description": "Takip görevi",
            }
        ]
    )
    assert len(validated) == 1
    step = validated[0]
    assert step.action == "todo_create"
    assert step.arguments["title"] == "ALES başvurusunu tamamla"
    assert step.arguments["priority"] == 3
    # H1 modelinin doldurduğu varsayılanlar da saklanır: plan H1'in gördüğüdür.
    assert "tags" in step.arguments


def test_every_declared_state_and_code_has_a_production_path() -> None:
    """Ölü sözleşme yok: tanımlı her değer kodda ÜRETİLİYOR olmalı."""
    import pathlib
    import re

    from app.modules.execution.models import DECISION_KINDS, PLAN_STATES, STEP_STATUSES

    source = "\n".join(
        item.read_text(encoding="utf-8")
        for item in pathlib.Path("app/modules/execution").glob("*.py")
        if item.name not in {"models.py", "state.py"}
    )
    # Durumlar: state ataması ya da geçiş hedefi olarak geçmeli.
    dynamic = {"input_required", "cancelled", "expired", "completed", "partial", "failed", "rejected", "draft"}
    for state in PLAN_STATES:
        if state in dynamic:
            continue
        assert re.search(rf'"{state}"', source), f"üretilmeyen durum: {state}"
    for kind in DECISION_KINDS:
        assert re.search(rf'"{kind}"', source), f"üretilmeyen karar türü: {kind}"
    for status in STEP_STATUSES:
        assert re.search(rf'"{status}"', source), f"üretilmeyen adım durumu: {status}"


def test_no_dead_helpers_remain() -> None:
    """Kullanılmayan yardımcı/ölü değer bırakılmaz."""
    from app.modules.execution import state as state_mod

    assert not hasattr(state_mod, "can_execute")
    assert "validating" not in state_mod.ALLOWED_TRANSITIONS
    from app.modules.execution.models import STEP_STATUSES

    assert "skipped" not in STEP_STATUSES


def test_decision_context_is_part_of_the_revision() -> None:
    """H7.1/B: kullanıcı cevabı yeni revizyon üretir; cevapsız hâli idempotent kalır."""
    base = revision_mod.normalized_plan(title="t", summary=None, reason=None, steps=_steps(1))
    answered = revision_mod.normalized_plan(
        title="t",
        summary=None,
        reason=None,
        steps=_steps(1),
        decision_context={"cv": "Backend CV"},
    )
    assert revision_mod.revision_of(base) != revision_mod.revision_of(answered)
    # Aynı cevap her zaman AYNI revizyonu üretir (deterministik).
    repeat = revision_mod.normalized_plan(
        title="t", summary=None, reason=None, steps=_steps(1), decision_context={"cv": "Backend CV"}
    )
    assert revision_mod.revision_of(answered) == revision_mod.revision_of(repeat)
    # Boş/whitespace cevap revizyona GİRMEZ.
    empty = revision_mod.normalized_plan(
        title="t", summary=None, reason=None, steps=_steps(1), decision_context={"cv": "   "}
    )
    assert revision_mod.revision_of(empty) == revision_mod.revision_of(base)


def test_decision_context_values_are_bounded() -> None:
    plan = revision_mod.normalized_plan(
        title="t", summary=None, reason=None, steps=_steps(1), decision_context={"cv": "x" * 999}
    )
    assert len(plan["decision_context"]["cv"]) <= revision_mod.MAX_DECISION_VALUE
