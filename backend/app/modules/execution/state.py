"""H7 plan durum makinesi — geçişler açık ve zorunlu.

Durum yalnızca burada tanımlı geçişlerle değişir; `approved → executing`
haricinde hiçbir yol canonical yürütmeye çıkmaz. Terminal durumdan çıkış
YOKTUR (`completed → approved` imkânsız).
"""

from __future__ import annotations

from app.modules.execution.models import PLAN_STATES, TERMINAL_PLAN_STATES

#: İzinli geçişler. Anahtar: kaynak durum.
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"validating", "input_required", "cancelled", "expired"}),
    "validating": frozenset({"awaiting_approval", "input_required", "expired"}),
    "input_required": frozenset({"draft", "cancelled", "expired"}),
    "awaiting_approval": frozenset({"approved", "rejected", "cancelled", "expired"}),
    # Onaydan sonra plan revizyonu DEĞİŞEMEZ; yalnızca yürütme ya da iptal.
    "approved": frozenset({"executing", "cancelled", "expired"}),
    "executing": frozenset({"completed", "partial", "failed"}),
    "completed": frozenset(),
    "partial": frozenset(),
    "failed": frozenset(),
    "rejected": frozenset(),
    "cancelled": frozenset(),
    "expired": frozenset(),
}


class TransitionError(Exception):
    """Geçersiz durum geçişi — sınırlı, model-okunur."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def ensure_transition(current: str, target: str) -> None:
    """Geçişi doğrular; geçersizse fail-closed hata yükseltir."""
    if current not in PLAN_STATES or target not in PLAN_STATES:
        raise TransitionError("UNKNOWN_STATE", f"bilinmeyen durum: {current} → {target}")
    if current in TERMINAL_PLAN_STATES:
        raise TransitionError("PLAN_TERMINAL", f"plan terminal durumda: {current}")
    if target not in ALLOWED_TRANSITIONS[current]:
        raise TransitionError("INVALID_TRANSITION", f"{current} → {target} izinli değil")


def can_execute(state: str) -> bool:
    return state == "approved"
