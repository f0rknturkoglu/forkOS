"""H7 değerlendirme veri seti: yapı + sınıf kapsamı + servis karşılığı.

Vakalar servis/state-machine akışlarıdır (saf politika değil); bu yüzden
"fixture var" demek yeterli değildir: her davranış sınıfının gerçek bir test
karşılığı olmalıdır.
"""

from __future__ import annotations

import pathlib

import yaml

EVAL_PATH = pathlib.Path("../docs/hermes/evals/h7-execution.yaml")

REQUIRED_CLASSES = {
    "simple_approved_plan",
    "rejected_plan",
    "edited_revision",
    "input_required",
    "expired_approval",
    "stale_target",
    "partial_execution",
    "duplicate_execution",
    "concurrent_execution",
    "crash_resume",
    "fake_approval",
    "budget_exceeded",
    "unknown_action",
    "unsupported_destructive_action",
    "missing_evidence",
    "h1_validation_failure",
}


def _load() -> dict:
    return yaml.safe_load(EVAL_PATH.read_text(encoding="utf-8"))


def test_eval_dataset_shape() -> None:
    data = _load()
    cases = data["cases"]
    assert len(cases) >= 20
    assert len({case["id"] for case in cases}) == len(cases)
    for case in cases:
        assert case["scenario"]
        assert case["flow"]
        assert case["expected"]


#: Davranış sınıfı → vakalarda geçmesi gereken anahtar sözcükler.
CLASS_KEYWORDS: dict[str, tuple[str, ...]] = {
    "simple_approved_plan": ("simple",),
    "rejected_plan": ("reject",),
    "edited_revision": ("edit", "revision"),
    "input_required": ("input",),
    "expired_approval": ("expire",),
    "stale_target": ("stale",),
    "partial_execution": ("partial",),
    "duplicate_execution": ("duplicate",),
    "concurrent_execution": ("concurrent", "concurrency"),
    "crash_resume": ("crash", "resume", "restart"),
    "fake_approval": ("fake", "approval_required", "unapproved"),
    "budget_exceeded": ("budget", "step_limit", "too_many"),
    "unknown_action": ("unknown", "bilinmeyen eylem"),
    "unsupported_destructive_action": ("destructive", "delete", "shell"),
    "missing_evidence": ("evidence", "fabricated", "source_ref"),
    "h1_validation_failure": ("h1fail", "h1 şeması", "h1 semasi"),
}


def test_eval_covers_required_behaviour_classes() -> None:
    cases = _load()["cases"]
    # Kimlikler tire ayırıcı kullanır; sınıf adları alt çizgi: normalize et.
    haystack = " ".join(
        f"{case['id']} {case['scenario']}".lower().replace("-", "_") for case in cases
    )
    missing = [
        name
        for name, keywords in CLASS_KEYWORDS.items()
        if not any(keyword in haystack for keyword in keywords)
    ]
    assert not missing, sorted(missing)


def test_eval_references_real_operations_and_errors() -> None:
    """Vakalardaki işlem adları ve hata kodları kodda GERÇEKTEN var olmalı."""
    from app.modules.execution.models import PLAN_STATES

    cases = _load()["cases"]
    operations = {"prepare", "approve", "reject", "respond", "cancel", "execute", "get"}
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in pathlib.Path("app/modules/execution").glob("*.py")
    )
    for case in cases:
        for flow_step in case["flow"]:
            operation = flow_step.get("op")
            if operation is not None:
                assert operation in operations, f"{case['id']}: bilinmeyen işlem {operation}"
        expected = case["expected"]
        state = expected.get("state") if isinstance(expected, dict) else None
        if state is not None:
            assert state in PLAN_STATES, f"{case['id']}: bilinmeyen durum {state}"
        code = expected.get("error") if isinstance(expected, dict) else None
        if code is not None:
            assert f'"{code}"' in sources, f"{case['id']}: kodda olmayan hata {code}"


def test_eval_has_no_personal_data() -> None:
    text = EVAL_PATH.read_text(encoding="utf-8")
    for forbidden in ("furkanturkoglu", "@gmail", "github.com/f0rk", "forkos_pgdata"):
        assert forbidden not in text
