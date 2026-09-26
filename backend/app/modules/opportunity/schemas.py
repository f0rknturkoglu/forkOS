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


class ListingHealthOut(BaseModel):
    health_score: int = Field(ge=0, le=100)
    jd_completeness: Literal["complete", "concise", "stub"]
    salary_transparency: Literal["transparent", "unclear", "missing"]
    liveness_status: Literal["live", "unchecked", "at_risk", "expired"]
    repost_frequency: Literal["none", "moderate", "frequent"]


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
    listing_health: ListingHealthOut | None = None


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
    #: Kayitli parmak izleri: profil/ilan degisince degerlendirme BAYAT olur.
    listing_fingerprint: str = ""
    profile_fingerprint: str = ""
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
    #: Mevcut durumdan izinli kesif/duyuru gecisleri (backend state machine).
    allowed_transitions: list[str] = Field(default_factory=list)
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
    #: Kural tabanli genel uygunluk puani: -1..100.
    #: -1 = kill kelimesi yakalandi (elendi) · null = henuz hesaplanmadi.
    score: float | None = None
    #: Puanin kaynagi ve hesaplanma ani (aciklanabilirlik).
    score_source: str | None = None
    score_computed_at: datetime | None = None
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
    #: Profil/beceri ortusmesi (0..1). CV DOSYASI kullanmaz; gercek CV
    #: degerlendirmesi `evaluation` alanindadir. null = hesaplanmadi.
    profile_match_ratio: float | None = None
    #: Profil ve CV beceri uyumu (eşleşen ve eksik teknolojiler)
    skill_match: SkillMatchOut | None = None
    #: Basvuru hatti (yalnizca gercek basvuru kayitlarinda dolu).
    application_status: str | None = None
    application_status_changed_at: datetime | None = None
    allowed_application_transitions: list[str] = Field(default_factory=list)
    #: career-ops esinli, tamamen yerel hizli risk ve meşruiyet sinyalleri.
    intelligence: OpportunityIntelligenceOut | None = None
    #: Gercek CV belgesiyle yapilan iki asamali degerlendirme (belge + parmak izi).
    evaluation: OpportunityEvaluationOut | None = None
    #: Degerlendirme bayatsa nedeni, guncelse null (bkz. intelligence.
    #: EVALUATION_STALE_REASONS). Eski skor guncel gibi sunulmaz.
    evaluation_stale_reason: str | None = None
    # ── Kaynak gozlemi / kapanma ───────────────────────────────────────
    source_status: str = "active"
    last_seen_at: datetime | None = None
    closed_at: datetime | None = None
    # ── Duyuru alanlari (job kayitlarinda bos kalir) ───────────────────
    official: bool | None = None
    parent_id: UUID | None = None
    stage: str | None = None
    application_start_at: datetime | None = None
    application_end_at: datetime | None = None
    exam_at: datetime | None = None
    result_at: datetime | None = None
    guide_url: str | None = None
    apply_url: str | None = None
    quota_total: int | None = None
    fields: list[str] = Field(default_factory=list)


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


#: Gereksinim durumlari. Kaynak: ``lifecycle.REQUIREMENT_STATUSES``; ayni
#: kumede kaldiklarini ``test_application_crm`` dogrular.
RequirementStatus = Literal["missing", "ready", "submitted", "waived"]


class RequirementIn(BaseModel):
    name: str = Field(min_length=1)
    required: bool = True
    status: RequirementStatus = "missing"
    note: str | None = None


class RequirementOut(BaseModel):
    id: UUID
    opportunity_id: UUID
    name: str
    required: bool = True
    status: RequirementStatus = "missing"
    document_entity_id: UUID | None = None
    note: str | None = None
    position: int = 0


class PrunePreviewOut(BaseModel):
    """Silme onizlemesi. Kullaniciya ikinci onaydan once gosterilir."""

    candidates: int
    protected: int
    archived: int
    estimated_bytes: int
    days: int
    #: Silinecek tam kimlik kumesinin deterministik ozeti (denetim icin).
    candidate_digest: str = ""
    confirm_token: str


class PruneResultOut(BaseModel):
    pruned: int
    protected: int
    archived: int
    freed_bytes: int
    days: int
    event: str = "opportunity.pruned"


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
    #: Kaynak calisti ama kapsamin tamamini taramadi (bkz. source_run.partial).
    partial_sources: int = 0
    empty_sources: int
    error_sources: int
    items_found: int
    progress_pct: int
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class SourceSyncItemOut(BaseModel):
    source: str
    status: Literal["queued", "running", "ok", "partial", "empty", "error"]
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
    #: Basvuru hatti durumu (lifecycle.APPLICATION_FLOW).
    status: str = "applied"
    status_changed_at: datetime | None = None
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
    #: 'discovery' | 'application' -- kesif ve basvuru gecmisi ayrisir.
    scope: str = "application"


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


class CoverLetterOut(BaseModel):
    """Kaydedilmis on yazi. Panel bunlari TEK istekle alir."""

    opportunity_id: UUID
    title: str
    organization: str | None = None
    cover_letter: str


class InterviewPrepOut(BaseModel):
    """Mulakat hazirligi grubu: ilan + gorusmeler + maas tutarliligi."""

    opportunity: OpportunityOut
    interviews: list[InterviewOut]
    salary: SalaryConsistencyOut


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


class FunnelBreakdownRow(BaseModel):
    """Kirilim satiri. Payda ve paylar UI'da acikca yazilir."""

    key: str
    label: str
    total: int
    responded: int
    interviewed: int
    offers: int
    response_rate: float | None = None
    interview_rate: float | None = None


class FunnelVolumeRow(BaseModel):
    period: str
    applied: int


class FunnelOut(BaseModel):
    #: Payda: yalnizca gercek basvuru kayitlari. Kesfedilmis ilanlar sayilmaz.
    total: int
    #: Takip edilen (preparing + applied ve sonrasi) kayit sayisi.
    tracked: int
    by_status: list[FunnelRow]
    #: Kohort tabanli donusum oranlari (stok sayimi degil).
    conversions: dict[str, float | None]
    #: Hangi asamaya kac basvuru ULASTI (gecmis + guncel durum).
    cohort: dict[str, int] = Field(default_factory=dict)
    #: `applied` asamasina ulasan basvuru sayisi = donusum paydasi.
    cohort_size: int = 0
    #: Bu sayinin altinda yuzde yerine ham sayi gosterilir.
    min_cohort_size: int = 10
    #: Kohort esigin altinda mi? Yuzdeler yaniltici olabilir.
    sufficient: bool = False
    rejection_reasons: list[dict[str, Any]]
    avg_first_response_days: float | None = None
    avg_applied_to_interview_days: float | None = None
    by_source: list[FunnelBreakdownRow] = Field(default_factory=list)
    by_cv: list[FunnelBreakdownRow] = Field(default_factory=list)
    by_role: list[FunnelBreakdownRow] = Field(default_factory=list)
    by_country: list[FunnelBreakdownRow] = Field(default_factory=list)
    by_work_mode: list[FunnelBreakdownRow] = Field(default_factory=list)
    weekly_volume: list[FunnelVolumeRow] = Field(default_factory=list)
    monthly_volume: list[FunnelVolumeRow] = Field(default_factory=list)


class ApplicationListOut(BaseModel):
    """Basvuru listesi ZARFI. Limitli liste "toplam" gibi sunulmaz."""

    items: list[OpportunityOut]
    #: Filtreye uyan GERCEK toplam (limit'ten bagimsiz).
    total: int
    offset: int
    limit: int


class TimelineEntryOut(BaseModel):
    """Basvuru zaman cizelgesi -- event/history kayitlarindan deterministik uretilir."""

    kind: Literal[
        "discovered",
        "shortlisted",
        "status",
        "followup",
        "interview",
        "note",
        "document",
        "todo",
        "offer",
        "rejection",
    ]
    at: datetime
    title: str
    detail: str | None = None
    status: str | None = None


class ApplicationTimelineOut(BaseModel):
    opportunity_id: UUID
    entries: list[TimelineEntryOut]


class FollowupOut(BaseModel):
    id: UUID
    title: str
    status: str
    follow_up_at: datetime
    note: str | None = None
