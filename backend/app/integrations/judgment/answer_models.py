"""A5.3 Answer Evidence Judge: bounded contract, response and provenance models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from .models import (
    ContractModel,
    EvidenceSupport,
    JudgmentMode,
    JudgmentStatus,
    SupportVerdict,
)

AnswerDegradedReason = Literal[
    "ANSWER_JUDGE_DISABLED",
    "ANSWER_JUDGE_EMPTY",
    "ANSWER_JUDGE_UNAVAILABLE",
    "ANSWER_JUDGE_TIMEOUT",
    "ANSWER_JUDGE_BUSY",
    "ANSWER_JUDGE_INVALID_RESPONSE",
    "ANSWER_JUDGE_SOURCE_STALE",
    "ANSWER_JUDGE_SNAPSHOT_UNAVAILABLE",
    "ANSWER_JUDGE_SOURCE_BINDING_FAILED",
    "ANSWER_JUDGE_UNSUPPORTED_CAPABILITY",
    "ANSWER_JUDGE_SENSITIVITY_BLOCKED",
    "ANSWER_JUDGE_CONTEXT_INCOMPLETE",
]


class AnswerJudgeProvenance(ContractModel):
    provider_id: str = Field(max_length=100)
    provider_version: str | None = Field(default=None, max_length=100)
    model_id: str | None = Field(default=None, max_length=150)
    model_revision: str | None = Field(default=None, max_length=100)
    question_version: str = Field(max_length=64)
    question_hash: str | None = Field(default=None, min_length=64, max_length=64)
    claim_digest: str = Field(min_length=64, max_length=64)
    evidence_digest: str = Field(min_length=64, max_length=64)
    latency_ms: int = Field(ge=0)
    judged_at: datetime
    abstained: bool = False
    provider_confidence: float | None = Field(default=None, ge=0, le=1)
    field_confidence: dict[str, float] = Field(default_factory=dict)


class AnswerJudgeResponse(ContractModel):
    claim: str = Field(default="", max_length=1000)
    mode: JudgmentMode
    status: JudgmentStatus
    baseline_support: EvidenceSupport
    observed_support: EvidenceSupport
    effective_support: EvidenceSupport
    context_complete: bool
    evidence_count: int = Field(ge=0, le=15)
    truncated: bool = False
    omitted_total: int = Field(default=0, ge=0)
    verdict: SupportVerdict
    degraded_reasons: tuple[AnswerDegradedReason, ...] = Field(
        default_factory=tuple, max_length=5
    )
    provenance: AnswerJudgeProvenance | None = None
