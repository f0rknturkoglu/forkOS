"""A5.2 advisory-only, bounded Memory Judge contract."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .models import JudgmentMode

MemoryRelation = Literal[
    "duplicate",
    "same_claim",
    "narrows",
    "elaborates",
    "incompatible",
    "changed_decision",
    "unrelated",
    "uncertain",
]
EvidenceSupport = Literal["supported", "partially_supported", "unsupported", "uncertain"]
IntentSignal = Literal["explicit", "implicit", "tentative", "uncertain"]
DurabilitySignal = Literal["durable", "temporary", "uncertain"]
ScopeRelation = Literal[
    "same_scope", "narrower_scope", "broader_scope", "different_scope", "uncertain"
]
Preservation = Literal["yes", "no", "not_applicable", "uncertain"]
MemoryJudgeStatus = Literal[
    "disabled", "success", "abstained", "unavailable", "invalid", "stale", "degraded"
]


class AdvisoryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RelatedMemoryRelation(AdvisoryModel):
    card_id: str = Field(min_length=1, max_length=128)
    relation: MemoryRelation


class MemorySignals(AdvisoryModel):
    evidence_support: EvidenceSupport
    intent: IntentSignal
    durability: DurabilitySignal
    scope_relation: ScopeRelation
    conditions_preserved: Preservation
    exceptions_preserved: Preservation
    relations: tuple[RelatedMemoryRelation, ...] = Field(max_length=3)


class MemoryJudgeProvenance(AdvisoryModel):
    provider_id: str = Field(max_length=100)
    provider_version: str | None = Field(default=None, max_length=100)
    model_id: str | None = Field(default=None, max_length=150)
    model_revision: str | None = Field(default=None, max_length=100)
    calibration_id: str | None = Field(default=None, max_length=128)
    question_version: str = Field(max_length=64)
    question_hash: str | None = Field(default=None, min_length=64, max_length=64)
    candidate_snapshot: str = Field(min_length=64, max_length=64)
    source_snapshot: str = Field(min_length=64, max_length=64)
    related_snapshot: str = Field(min_length=64, max_length=64)
    policy_snapshot: str = Field(min_length=64, max_length=64)
    latency_ms: int = Field(ge=0)
    judged_at: datetime
    abstained: bool
    # Uncalibrated provider confidence is telemetry only, not truth or policy.
    field_confidence: dict[str, float] = Field(default_factory=dict)


class MemoryJudgeResponse(AdvisoryModel):
    candidate_id: uuid.UUID
    mode: JudgmentMode
    status: MemoryJudgeStatus
    baseline_status: str = Field(max_length=24)
    baseline_destination: str = Field(max_length=32)
    signals: MemorySignals | None = None
    review_flags: tuple[str, ...] = Field(default_factory=tuple, max_length=8)
    reason: str | None = Field(default=None, max_length=80)
    provenance: MemoryJudgeProvenance | None = None
