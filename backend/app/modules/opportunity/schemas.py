from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


class SkillMatchOut(BaseModel):
    match_ratio: float
    matched: list[str]
    missing: list[str]


class RiskSignalOut(BaseModel):
    code: str
    label: str
    detail: str
    severity: Literal["neutral", "warn", "danger"] = "neutral"


class OpportunityIntelligenceOut(BaseModel):
    repost_count: int = 0
    is_repost: bool = False
    pay_min: int | None = None
    pay_max: int | None = None
    pay_currency: str | None = None
    pay_range_ratio: float | None = None
    pay_transparency_risk: bool = False
    geo_mismatch: bool = False
    sponsorship_status: Literal["sponsors", "not_needed", "unstated", "no_sponsorship"] = "unstated"
    connection_count: int = 0
    signals: list[RiskSignalOut] = Field(default_factory=list)


RequirementImportance = Literal["critical", "high", "meaningful", "preferred", "low_signal"]
RequirementEvidence = Literal["stated", "structural", "inferred"]
CandidateMatch = Literal["strong", "partial", "missing"]
OpportunityArchetype = Literal["fde", "sa", "pm", "llmops", "agentic", "transformation"]


class EvaluationRequirementOut(BaseModel):
    id: str
    name: str = Field(min_length=1, max_length=240)
    importance: RequirementImportance
    evidence: RequirementEvidence
    excerpt: str | None = Field(None, max_length=500)
    terms: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def inferred_is_never_critical_or_high(self):
        if self.evidence == "inferred" and self.importance in {"critical", "high"}:
            raise ValueError("Tahmini gereksinim critical veya high olamaz")
        return self


class EvaluationMatchOut(BaseModel):
    requirement_id: str
    requirement: str
    match: CandidateMatch
    evidence: str
    gap_mitigation: str | None = None
    story_ids: list[UUID] = Field(default_factory=list)


class EvaluationGateOut(BaseModel):
    job_country: str | None = None
    authorized_to_work: bool | None = None
    sponsorship_status: Literal["sponsors", "not_needed", "unstated", "no_sponsorship"] = "unstated"
    geo_mismatch: bool = False
    hard_blocker: bool = False
    reasons: list[str] = Field(default_factory=list)


class OpportunityEvaluationOut(BaseModel):
    version: str
    evaluated_at: datetime
    source_fingerprint: str
    engine: Literal["local_rules"] = "local_rules"
    candidate_source: Literal["document", "profile"] = "profile"
    candidate_document_id: UUID | None = None
    candidate_document_title: str | None = None
    archetype: OpportunityArchetype | None = None
    archetype_scores: dict[str, int] = Field(default_factory=dict)
    score: int = Field(ge=0, le=100)
    recommendation: Literal["pursue", "consider", "skip"]
    requirements: list[EvaluationRequirementOut] = Field(default_factory=list)
    matches: list[EvaluationMatchOut] = Field(default_factory=list)
    gate: EvaluationGateOut
    notes: str | None = None

    @model_validator(mode="after")
    def matches_reference_known_requirements(self):
        requirement_ids = [item.id for item in self.requirements]
        if len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError("Gereksinim kimlikleri benzersiz olmalı")
        match_ids = [item.requirement_id for item in self.matches]
        if len(match_ids) != len(set(match_ids)):
            raise ValueError("Her gereksinimin tek bir eşleşmesi olabilir")
        unknown = set(match_ids) - set(requirement_ids)
        if unknown:
            raise ValueError("Eşleşme bilinmeyen bir gereksinime bağlı")
        return self


class OpportunityEvaluationPatch(BaseModel):
    archetype: OpportunityArchetype | None = None
    requirements: list[EvaluationRequirementOut] | None = None
    matches: list[EvaluationMatchOut] | None = None
    notes: str | None = Field(None, max_length=10_000)


class OpportunityIn(BaseModel):
    title: str = Field(min_length=1)
    kind: str = "job"
    organization: str | None = None
    url: HttpUrl | None = None
    status: str = "discovered"
    priority: int = Field(2, ge=1, le=3)
    deadline_at: datetime | None = None
    location: str | None = None
    remote: str | None = None
    compensation: str | None = None
    notes: str | None = None


class OpportunityPatch(BaseModel):
    title: str | None = None
    status: str | None = None
    priority: int | None = Field(None, ge=1, le=3)
    deadline_at: datetime | None = None
    notes: str | None = None
    follow_up_at: datetime | None = None
    rejection_reason: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value == "trashed":
            raise ValueError("Çöp durumu için trash endpoint'ini kullanın")
        return value


class OpportunityOut(BaseModel):
    id: UUID
    title: str
    kind: str
    category: str | None
    organization: str | None
    url: str | None
    status: str
    priority: int
    found_at: datetime
    published_at: datetime | None
    deadline_at: datetime | None
    applied_at: datetime | None
    location: str | None
    remote: str | None
    compensation: str | None
    source: str
    external_id: str | None
    raw: dict[str, Any]
    #: forkjob uyum puani (0-100). -1 = kill kelimesi yakalandi, eleme.
    score: float | None = None
    #: Puanin bilesenleri. Yalnizca detay ucunda dolu -- liste hafif kalsin.
    score_reasons: dict[str, Any] | None = None
    notes: str | None
    trashed_at: datetime | None = None
    country: str | None = None
    region: str | None = None
    follow_up_at: datetime | None = None
    rejection_reason: str | None = None
    trashed_from_status: str | None = None
    #: Belge ters-bağı (DocumentsPage "bu belge hangi başvurularda kullanılıyor"):
    #: başvuru kaydındaki CV belgesi. Liste ucunda dolu gelir.
    cv_document_id: UUID | None = None
    #: Belge ters-bağı (DocumentsPage): gereksinime bağlanan ilk belge.
    requirement_document_id: UUID | None = None
    #: Profil ve CV beceri uyumu (eşleşen ve eksik teknolojiler)
    skill_match: SkillMatchOut | None = None
    #: career-ops esinli, tamamen yerel hizli risk ve meşruiyet sinyalleri.
    intelligence: OpportunityIntelligenceOut | None = None
    #: career-ops iki asamali gereksinim ve aday eslestirmesi.
    evaluation: OpportunityEvaluationOut | None = None


class ReplyAnalysisIn(BaseModel):
    text: str = Field(min_length=8, max_length=50_000)


class ReplyAnalysisOut(BaseModel):
    kind: Literal[
        "interview_invite",
        "rejection",
        "take_home_assessment",
        "auto_acknowledgement",
        "unknown",
    ]
    label: str
    confidence: float = Field(ge=0, le=1)
    evidence: list[str]
    suggested_status: Literal["applied", "interview", "rejected"] | None = None
    suggested_todo_title: str | None = None
    summary: str


class SilentApplicationOut(BaseModel):
    id: UUID
    title: str
    organization: str | None = None
    status: str
    last_interview_at: datetime
    days_silent: int


class OpportunityBrowseOut(BaseModel):
    items: list[OpportunityOut]
    total: int
    offset: int
    limit: int
    section_counts: dict[str, int]
    facets: dict[str, dict[str, int]]


class RequirementIn(BaseModel):
    name: str = Field(min_length=1)
    required: bool = True
    status: Literal["missing", "ready", "submitted", "waived"] = "missing"
    note: str | None = None


class DeadlineOut(BaseModel):
    entity_id: UUID
    type: str
    title: str
    due_at: datetime
    module: str
    sub_kind: str | None
    priority: int


class SourceSyncBatchOut(BaseModel):
    id: UUID
    scope: Literal["opportunity", "media"] = "opportunity"
    status: Literal["queued", "running", "completed", "completed_with_errors"]
    source_ids: list[str]
    total_sources: int
    completed_sources: int
    ok_sources: int
    empty_sources: int
    error_sources: int
    items_found: int
    progress_pct: int
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class SourceSyncItemOut(BaseModel):
    source: str
    status: Literal["queued", "running", "ok", "empty", "error"]
    started_at: datetime | None
    finished_at: datetime | None
    items_found: int
    error: str | None


class SourceSyncStatusOut(BaseModel):
    active: SourceSyncBatchOut | None
    last_completed: SourceSyncBatchOut | None
    sources: list[SourceSyncItemOut]
    running: list[SourceSyncItemOut]


class SourceRefreshOut(BaseModel):
    batch_id: UUID | None
    queued: int
    total_sources: int


class ApplicationOut(BaseModel):
    opportunity_id: UUID
    cv_document_id: UUID | None = None
    cv_title: str | None = None
    cv_modified_at: datetime | None = None
    cover_letter: str | None = None
    company_research: str | None = None
    salary_expectation: str | None = None
    posting_snapshot: dict[str, Any] = {}
    note: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ApplicationIn(BaseModel):
    cv_document_id: UUID | None = None
    cover_letter: str | None = None
    company_research: str | None = None
    salary_expectation: str | None = None
    note: str | None = None


class ApplyIn(ApplicationIn):
    """Ilk basvuru: durum 'applied' yapar, snapshot'i birlikte alir."""


class TransitionIn(BaseModel):
    to: str
    note: str | None = None
    rejection_reason: str | None = None


class HistoryOut(BaseModel):
    id: UUID
    from_status: str | None = None
    to_status: str
    at: datetime
    note: str | None = None


class InterviewOut(BaseModel):
    id: UUID
    opportunity_id: UUID
    stage: str
    mode: str | None = None
    scheduled_at: datetime | None = None
    duration_min: int | None = None
    notes: str | None = None
    outcome: str | None = None
    salary_stated: str | None = None
    position: int = 0


class InterviewIn(BaseModel):
    stage: str = "genel"
    mode: str | None = None
    scheduled_at: datetime | None = None
    duration_min: int | None = None
    notes: str | None = None
    outcome: str | None = None
    salary_stated: str | None = Field(None, max_length=500)


CareerStoryProvenance = Literal[
    "existing",
    "supported",
    "derived-unverified",
    "user-cannot-confirm",
]


class CareerStoryIn(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    situation: str | None = Field(None, max_length=10_000)
    task: str | None = Field(None, max_length=10_000)
    action: str | None = Field(None, max_length=10_000)
    result: str | None = Field(None, max_length=10_000)
    reflection: str | None = Field(None, max_length=10_000)
    provenance: CareerStoryProvenance = "existing"
    tags: list[str] = Field(default_factory=list, max_length=20)


class CareerStoryPatch(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=240)
    situation: str | None = Field(None, max_length=10_000)
    task: str | None = Field(None, max_length=10_000)
    action: str | None = Field(None, max_length=10_000)
    result: str | None = Field(None, max_length=10_000)
    reflection: str | None = Field(None, max_length=10_000)
    provenance: CareerStoryProvenance | None = None
    tags: list[str] | None = Field(None, max_length=20)


class CareerStoryOut(BaseModel):
    id: UUID
    title: str
    situation: str | None = None
    task: str | None = None
    action: str | None = None
    result: str | None = None
    reflection: str | None = None
    provenance: CareerStoryProvenance
    tags: list[str] = Field(default_factory=list)
    updated_at: datetime


class SalaryClaimOut(BaseModel):
    interview_id: UUID
    stage: str
    statement: str
    pay_min: int | None = None
    pay_max: int | None = None
    currency: str | None = None


class SalaryConsistencyOut(BaseModel):
    inconsistent: bool = False
    claims: list[SalaryClaimOut] = Field(default_factory=list)
    warning: str | None = None


class CoverLetterReviewIn(BaseModel):
    text: str = Field(min_length=20, max_length=50_000)


class CoverLetterReviewOut(BaseModel):
    score: int = Field(ge=0, le=100)
    generic_phrases: list[str] = Field(default_factory=list)
    matched_story_ids: list[UUID] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class CareerConnectionOut(BaseModel):
    id: UUID
    name: str
    first_name: str | None = None
    last_name: str | None = None
    profile_url: str | None = None
    email: str | None = None
    company: str | None = None
    position: str | None = None
    connected_on: date | None = None


class CareerConnectionsImportOut(BaseModel):
    total_rows: int
    created: int
    updated: int
    skipped: int


class OpportunityConnectionsOut(BaseModel):
    organization: str | None = None
    normalized_organization: str | None = None
    connections: list[CareerConnectionOut] = Field(default_factory=list)


class FunnelRow(BaseModel):
    status: str
    count: int


class FunnelOut(BaseModel):
    total: int
    by_status: list[FunnelRow]
    conversions: dict[str, float | None]
    rejection_reasons: list[dict[str, Any]]


class FollowupOut(BaseModel):
    id: UUID
    title: str
    status: str
    follow_up_at: datetime
    note: str | None = None
