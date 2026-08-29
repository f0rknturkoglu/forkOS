from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator


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
    position: int = 0


class InterviewIn(BaseModel):
    stage: str = "genel"
    mode: str | None = None
    scheduled_at: datetime | None = None
    duration_min: int | None = None
    notes: str | None = None
    outcome: str | None = None


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
