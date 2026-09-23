"""Pure A5.0 gates and conservative deterministic controls; no provider calls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.modules.semantic_memory.policy import normalize_statement

from .models import (
    AbstentionReason,
    ContextJudgmentRequest,
    ContextVerdict,
    JudgeCapability,
    JudgmentMode,
    JudgmentPurpose,
    JudgmentStatus,
    ProviderLocality,
    SourceSnapshot,
    SupportVerdict,
)


class PurposeModes(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    context: JudgmentMode = "off"
    memory_relation: JudgmentMode = "off"
    memory_support: JudgmentMode = "off"
    answer_evidence: JudgmentMode = "off"

    def for_purpose(self, purpose: JudgmentPurpose) -> JudgmentMode:
        return getattr(self, purpose)


PURPOSE_CAPABILITY: dict[JudgmentPurpose, JudgeCapability] = {
    "context": "context_relevance",
    "memory_relation": "semantic_relation",
    "memory_support": "entailment",
    "answer_evidence": "answer_support",
}


@dataclass(frozen=True)
class InvocationDecision:
    allowed: bool
    status: JudgmentStatus
    reason: AbstentionReason | None = None


def may_invoke(
    *,
    purpose: JudgmentPurpose,
    modes: PurposeModes,
    locality: ProviderLocality,
    capabilities: frozenset[JudgeCapability],
    remote_allowed: tuple[bool, ...],
    mechanically_eligible: bool,
    provider_available: bool,
) -> InvocationDecision:
    """Mechanical eligibility happens before content reaches any provider.

    Callers must assemble packets only from already-filtered H3/A4 inputs; this
    gate is a second boundary and never attempts to restore excluded sources.
    """
    if modes.for_purpose(purpose) == "off":
        return InvocationDecision(False, "abstained", "mechanical_policy_block")
    if not mechanically_eligible:
        return InvocationDecision(False, "invalid", "mechanical_policy_block")
    if PURPOSE_CAPABILITY[purpose] not in capabilities:
        return InvocationDecision(False, "abstained", "unsupported_capability")
    if not provider_available:
        return InvocationDecision(False, "unavailable", "provider_unavailable")
    if locality == "remote" and not all(remote_allowed):
        return InvocationDecision(False, "invalid", "mechanical_policy_block")
    return InvocationDecision(True, "success")


def revalidate_snapshots(
    captured: tuple[SourceSnapshot, ...], current: tuple[SourceSnapshot, ...]
) -> JudgmentStatus:
    """Changed or missing source means stale; caller must discard verdict."""
    if len(captured) != len(current):
        return "stale"
    for before, after in zip(captured, current, strict=True):
        if (before.source_id, before.source_type) != (after.source_id, after.source_type):
            return "stale"
        if (before.source_version, before.source_revision) != (after.source_version, after.source_revision):
            return "stale"
    return "success"


def may_affect_selection(*, mode: JudgmentMode, status: JudgmentStatus, sources_current: bool) -> bool:
    """Only bounded selection may be influenced; never a canonical write."""
    return mode in {"assist", "on"} and status == "success" and sources_current


def grants_write_authority(*, mode: JudgmentMode, status: JudgmentStatus) -> Literal[False]:
    return False


def context_baseline(request: ContextJudgmentRequest) -> tuple[str, ...]:
    """Control condition: preserve H3 order and all mechanically eligible items."""
    return tuple(item.evidence_id for item in request.candidates)


def context_verdicts_valid(request: ContextJudgmentRequest, verdicts: tuple[ContextVerdict, ...]) -> bool:
    """Exactly one verdict per H3-filtered candidate; no omissions or inventions."""
    allowed = {item.evidence_id for item in request.candidates}
    seen = [verdict.evidence_id for verdict in verdicts]
    return (
        len(verdicts) == len(request.candidates)
        and len(seen) == len(set(seen))
        and set(seen) == allowed
    )


def memory_baseline(*, candidate: str, existing: str) -> str:
    """A4 normalized duplicate signal only; no semantic or fuzzy guess."""
    return "same_claim" if normalize_statement(candidate) == normalize_statement(existing) else "uncertain"


def answer_baseline(*, evidence_current: bool, locator_valid: bool, context_complete: bool) -> SupportVerdict:
    """Mechanical validation only; even a valid locator cannot prove entailment."""
    if not evidence_current or not locator_valid:
        return SupportVerdict(status="invalid", support="uncertain", reason_codes=("mechanical_policy_block",))
    reason = "context_incomplete" if not context_complete else "insufficient_evidence"
    return SupportVerdict(status="abstained", support="uncertain", reason_codes=(reason,))
