"""A4: Semantic candidate Pydantic şemaları."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CandidateKind = Literal[
    "identity",
    "preference",
    "correction",
    "constraint",
    "goal",
    "decision",
    "lesson",
    "project_knowledge",
    "reference",
]
CandidateStatus = Literal["proposed", "needs_review", "ready", "promoted", "rejected", "stale"]
PrimaryEvidenceClass = Literal["explicit_user", "canonical_source", "episode_derived", "model_derived"]
SuggestedDestination = Literal["operational", "hot_memory", "durable_vault", "procedural_candidate", "discard"]


class SemanticCandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_key: str
    kind: CandidateKind
    statement: str
    scope: str
    scope_project: str | None = None
    subject_key: str | None = None
    domains: list[str] = Field(default_factory=list)
    suggested_destination: SuggestedDestination
    primary_evidence_class: PrimaryEvidenceClass
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    observed_at: datetime
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    rationale: str | None = None
    conditions: list[str] = Field(default_factory=list)
    exceptions: list[str] = Field(default_factory=list)
    sensitivity: str = "normal"
    remote_allowed: bool = False
    status: CandidateStatus
    reviewed_by: str | None = None
    possible_related_card_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recurrence_count: int = 1
    first_seen_at: datetime
    last_seen_at: datetime
    revision: str
    created_at: datetime
    updated_at: datetime


class SemanticCandidateListResponse(BaseModel):
    items: list[SemanticCandidateRead]
    total: int
    status_counts: dict[str, int] = Field(default_factory=dict)


class SemanticCandidateConfirmIn(BaseModel):
    expected_revision: str


class SemanticCandidateRejectIn(BaseModel):
    expected_revision: str
    reason: str | None = None


class SemanticCandidatePromoteIn(BaseModel):
    expected_revision: str
    target_destination: SuggestedDestination | None = None
    supersedes: list[str] | None = None


class SemanticCandidatePromoteOut(BaseModel):
    status: str
    card_id: str | None = None
    relative_path: str | None = None
    destination: str
    revision: str


class SemanticCandidateRefreshIn(BaseModel):
    include_episodes: bool = True
    include_events: bool = True
    limit: int = 50


class SemanticCandidateRefreshOut(BaseModel):
    created_count: int
    updated_count: int
    total_candidates: int


class SemanticStatusOut(BaseModel):
    total_candidates: int
    proposed_count: int
    needs_review_count: int
    ready_count: int
    promoted_count: int
    rejected_count: int
    durable_card_count: int
