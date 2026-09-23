"""Frozen A5 v1 vocabularies and bounded provider-neutral packets.

These packets are advice, not truth, authorization, or canonical state.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.integrations.agent.evidence_models import EvidenceSourceType

JudgmentPurpose = Literal["context", "memory_relation", "memory_support", "answer_evidence"]
JudgmentMode = Literal["off", "shadow", "assist", "on"]
JudgmentStatus = Literal["success", "abstained", "unavailable", "stale", "invalid"]
ProviderLocality = Literal["local", "remote"]
JudgeCapability = Literal[
    "context_relevance", "semantic_relation", "entailment", "contradiction", "answer_support"
]
ContextUsefulness = Literal["essential", "useful", "weak", "irrelevant", "uncertain"]
ContextRedundancy = Literal["unique", "redundant", "uncertain"]
MemoryRelation = Literal[
    "same_claim", "narrows", "elaborates", "changed_decision", "incompatible", "unrelated", "uncertain"
]
EvidenceSupport = Literal["supported", "contradicted", "insufficient", "uncertain"]
AbstentionReason = Literal[
    "insufficient_evidence", "ambiguous_relation", "context_incomplete", "low_provider_margin",
    "unsupported_capability", "provider_unavailable", "source_stale", "mechanical_policy_block",
]

MAX_CANDIDATES = 15  # H3 maximum
MAX_EXCERPT = 1200  # H3 per-item maximum
MAX_TOTAL_EXCERPT = 8000  # H3 bundle maximum
MAX_CLAIM = 1000


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceSnapshot(ContractModel):
    source_id: str = Field(min_length=1, max_length=200)
    source_type: str = Field(min_length=1, max_length=40)
    source_version: str | None = Field(default=None, max_length=128)
    source_revision: str | None = Field(default=None, max_length=128)
    captured_at: datetime

    @model_validator(mode="after")
    def has_revision(self) -> SourceSnapshot:
        if not (self.source_version or self.source_revision):
            raise ValueError("source snapshot needs version or revision")
        if self.captured_at.tzinfo is None or self.captured_at.utcoffset() is None:
            raise ValueError("captured_at must be timezone-aware")
        if self.source_id.startswith("/") or self.source_id.startswith("file:"):
            raise ValueError("absolute source paths are forbidden")
        return self


class ContextCandidate(ContractModel):
    evidence_id: str = Field(min_length=1, max_length=240)
    source_type: EvidenceSourceType
    title: str = Field(max_length=240)
    excerpt: str = Field(min_length=1, max_length=MAX_EXCERPT)
    retrieval_position: int = Field(ge=0, lt=MAX_CANDIDATES)
    snapshot: SourceSnapshot
    remote_allowed: bool = False


class ContextJudgmentRequest(ContractModel):
    schema_version: Literal["1"] = "1"
    purpose: Literal["context"] = "context"
    request_id: str = Field(min_length=1, max_length=128)
    query: str = Field(min_length=2, max_length=200)
    candidates: tuple[ContextCandidate, ...] = Field(min_length=1, max_length=MAX_CANDIDATES)
    truncated: bool = False
    omitted_total: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def bounded_packet(self) -> ContextJudgmentRequest:
        if sum(len(item.excerpt) for item in self.candidates) > MAX_TOTAL_EXCERPT:
            raise ValueError("H3 total excerpt budget exceeded")
        if len({item.evidence_id for item in self.candidates}) != len(self.candidates):
            raise ValueError("duplicate evidence IDs")
        if [item.retrieval_position for item in self.candidates] != list(range(len(self.candidates))):
            raise ValueError("H3 order must be contiguous and preserved")
        return self


class JudgmentMetadata(ContractModel):
    provider_id: str | None = Field(default=None, max_length=100)
    model_id: str | None = Field(default=None, max_length=100)
    latency_ms: int | None = Field(default=None, ge=0)
    # Provider-reported uncertainty signal, NOT probability of objective truth.
    provider_confidence: float | None = Field(default=None, ge=0, le=1)
    probability_margin: float | None = Field(default=None, ge=0, le=1)
    calibrated: bool | None = None


class VerdictBase(ContractModel):
    status: JudgmentStatus
    reason_codes: tuple[AbstentionReason, ...] = Field(default_factory=tuple, max_length=8)
    metadata: JudgmentMetadata | None = None


class ContextVerdict(VerdictBase):
    evidence_id: str = Field(min_length=1, max_length=240)
    usefulness: ContextUsefulness
    redundancy: ContextRedundancy


class MemorySnapshot(ContractModel):
    item_id: str = Field(min_length=1, max_length=128)
    statement: str = Field(min_length=1, max_length=1000)
    scope: str = Field(min_length=1, max_length=64)
    scope_project: str | None = Field(default=None, max_length=128)
    subject_key: str | None = Field(default=None, max_length=64)
    snapshot: SourceSnapshot
    remote_allowed: bool = False


class MemoryRelationRequest(ContractModel):
    schema_version: Literal["1"] = "1"
    purpose: Literal["memory_relation"] = "memory_relation"
    request_id: str = Field(min_length=1, max_length=128)
    candidate: MemorySnapshot
    existing_card: MemorySnapshot


class MemoryRelationVerdict(VerdictBase):
    relation: MemoryRelation


class MemorySupportRequest(ContractModel):
    """Pairwise support uses the same bounded candidate/card snapshots."""

    schema_version: Literal["1"] = "1"
    purpose: Literal["memory_support"] = "memory_support"
    request_id: str = Field(min_length=1, max_length=128)
    candidate: MemorySnapshot
    existing_card: MemorySnapshot


class SupportVerdict(VerdictBase):
    support: EvidenceSupport


class AnswerEvidenceItem(ContractModel):
    evidence_id: str = Field(min_length=1, max_length=240)
    excerpt: str = Field(min_length=1, max_length=MAX_EXCERPT)
    surrounding_context: str = Field(default="", max_length=MAX_EXCERPT)
    snapshot: SourceSnapshot
    remote_allowed: bool = False


class AnswerEvidenceRequest(ContractModel):
    schema_version: Literal["1"] = "1"
    purpose: Literal["answer_evidence"] = "answer_evidence"
    request_id: str = Field(min_length=1, max_length=128)
    claim: str = Field(min_length=1, max_length=MAX_CLAIM)
    evidence: tuple[AnswerEvidenceItem, ...] = Field(min_length=1, max_length=MAX_CANDIDATES)
    context_complete: bool

    @model_validator(mode="after")
    def bounded_packet(self) -> AnswerEvidenceRequest:
        if sum(len(item.excerpt) + len(item.surrounding_context) for item in self.evidence) > MAX_TOTAL_EXCERPT:
            raise ValueError("answer evidence packet budget exceeded")
        if len({item.evidence_id for item in self.evidence}) != len(self.evidence):
            raise ValueError("duplicate evidence IDs")
        return self
