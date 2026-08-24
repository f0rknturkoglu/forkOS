from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.modules.media.models import (
    CONSUMPTION_ACTIONS,
    KINDS,
    MEASURES,
    STATUSES,
    UNIT_TYPES,
)


def _known(value: str | None, values: list[str], label: str) -> str | None:
    if value is not None and value not in values:
        raise ValueError(f"{label} su olmali: {values}")
    return value


class MediaItemIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: Literal["manual", "provider"] = "manual"
    title: str = Field(min_length=1)
    kind: str
    status: str = "planned"
    progress: float | None = None
    total: float | None = None
    score: int | None = None
    notes: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    meta: dict[str, Any] = Field(
        default_factory=dict, validation_alias=AliasChoices("meta", "metadata")
    )
    summary: str | None = None
    release_date: date | None = None
    progress_measure: str | None = None
    review: str | None = None
    favorite: bool = False
    owned: bool = False
    ownership: dict[str, Any] = Field(default_factory=dict)
    monitored: bool = False
    provider: str | None = None
    provider_id: str | None = None
    provider_ids: dict[str, Any] = Field(default_factory=dict)
    cover_url: str | None = None
    cover_path: str | None = None
    backdrop_url: str | None = None
    backdrop_path: str | None = None
    last_synced_at: datetime | None = None

    @field_validator("kind")
    @classmethod
    def kind_known(cls, value: str) -> str:
        return _known(value, KINDS, "kind") or value

    @field_validator("status")
    @classmethod
    def status_known(cls, value: str) -> str:
        return _known(value, STATUSES, "status") or value

    @field_validator("progress_measure")
    @classmethod
    def measure_known(cls, value: str | None) -> str | None:
        return _known(value, MEASURES, "progress_measure")

    @field_validator("progress", "total")
    @classmethod
    def nonnegative(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("progress/total negatif olamaz")
        return value

    @field_validator("score")
    @classmethod
    def score_range(cls, value: int | None) -> int | None:
        if value is not None and not 0 <= value <= 10:
            raise ValueError("score 0-10 olmali")
        return value

    @model_validator(mode="after")
    def provider_source_has_identity(self):
        if self.source == "provider" and (not self.provider or not self.provider_id):
            raise ValueError("Provider kaynak icin provider ve provider_id gerekli")
        return self


class MediaItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = None
    kind: str | None = None
    status: str | None = None
    progress: float | None = None
    total: float | None = None
    score: int | None = None
    notes: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    meta: dict[str, Any] | None = Field(
        default=None, validation_alias=AliasChoices("meta", "metadata")
    )
    summary: str | None = None
    release_date: date | None = None
    progress_measure: str | None = None
    review: str | None = None
    favorite: bool | None = None
    owned: bool | None = None
    ownership: dict[str, Any] | None = None
    monitored: bool | None = None
    provider: str | None = None
    provider_id: str | None = None
    provider_ids: dict[str, Any] | None = None
    cover_url: str | None = None
    cover_path: str | None = None
    backdrop_url: str | None = None
    backdrop_path: str | None = None
    last_synced_at: datetime | None = None

    @field_validator("kind")
    @classmethod
    def kind_known(cls, value: str | None) -> str | None:
        return _known(value, KINDS, "kind")

    @field_validator("status")
    @classmethod
    def status_known(cls, value: str | None) -> str | None:
        return _known(value, STATUSES, "status")

    @field_validator("progress_measure")
    @classmethod
    def measure_known(cls, value: str | None) -> str | None:
        return _known(value, MEASURES, "progress_measure")

    @field_validator("progress", "total")
    @classmethod
    def nonnegative(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("progress/total negatif olamaz")
        return value

    @field_validator("score")
    @classmethod
    def score_range(cls, value: int | None) -> int | None:
        if value is not None and not 0 <= value <= 10:
            raise ValueError("score 0-10 olmali")
        return value

    @model_validator(mode="after")
    def mutation_invariants(self):
        forbidden_nulls = {
            "title",
            "kind",
            "status",
            "meta",
            "favorite",
            "owned",
            "ownership",
            "monitored",
            "provider_ids",
        }
        for field in forbidden_nulls & self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} null olamaz")
        if "progress" in self.model_fields_set:
            raise ValueError("Ilerleme PATCH ile degistirilemez; consumption set kullanin")
        if self.status == "completed":
            raise ValueError("Tamamlama icin consumption finish kullanin")
        return self


class MediaItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    kind: str
    status: str
    progress: float | None = None
    total: float | None = None
    score: int | None = None
    notes: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
    summary: str | None = None
    release_date: date | None = None
    progress_measure: str | None = None
    review: str | None = None
    favorite: bool = False
    owned: bool = False
    ownership: dict[str, Any] = Field(default_factory=dict)
    monitored: bool = False
    provider: str | None = None
    provider_id: str | None = None
    provider_ids: dict[str, Any] = Field(default_factory=dict)
    cover_url: str | None = None
    cover_path: str | None = None
    backdrop_url: str | None = None
    backdrop_path: str | None = None
    last_synced_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    archived_at: datetime | None = None


class MediaPageOut(BaseModel):
    items: list[MediaItemOut]
    total: int
    next_cursor: str | None = None


class MediaUnitUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1)
    unit_type: str
    parent_id: uuid.UUID | None = None
    number: float | None = None
    duration_min: int | None = None
    release_at: datetime | None = None
    progress_total: float | None = None
    progress_measure: str | None = None
    provider: str | None = None
    provider_id: str | None = None
    provider_ids: dict[str, Any] = Field(default_factory=dict)
    cover_url: str | None = None
    cover_path: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)

    @field_validator("unit_type")
    @classmethod
    def type_known(cls, value: str) -> str:
        return _known(value, UNIT_TYPES, "unit_type") or value

    @field_validator("progress_measure")
    @classmethod
    def measure_known(cls, value: str | None) -> str | None:
        return _known(value, MEASURES, "progress_measure")


class MediaUnitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    media_id: uuid.UUID
    parent_id: uuid.UUID | None = None
    title: str
    unit_type: str
    number: float | None = None
    duration_min: int | None = None
    release_at: datetime | None = None
    progress_total: float | None = None
    progress_measure: str | None = None
    provider: str | None = None
    provider_id: str | None = None
    provider_ids: dict[str, Any] = Field(default_factory=dict)
    cover_url: str | None = None
    cover_path: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    children: list[MediaUnitOut] = Field(default_factory=list)


class UnitUpsertResult(BaseModel):
    id: uuid.UUID
    created: bool
    changed: bool = False
    cycle_reopened: bool = False


class MediaCycleStart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    started_at: datetime | None = None
    notes: str | None = None


class MediaCycleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    media_id: uuid.UUID
    ordinal: int
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    last_caught_up_at: datetime | None = None
    score: int | None = None
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MediaConsumptionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client_uuid: uuid.UUID
    action: str
    unit_id: uuid.UUID | None = None
    measure: str | None = None
    amount: float | None = None
    progress_after: float | None = None
    occurred_at: datetime | None = None
    duration_min: int | None = None
    note: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)

    @field_validator("action")
    @classmethod
    def action_known(cls, value: str) -> str:
        return _known(value, CONSUMPTION_ACTIONS, "action") or value

    @field_validator("measure")
    @classmethod
    def measure_known(cls, value: str | None) -> str | None:
        return _known(value, MEASURES, "measure")


class MediaConsumptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    media_id: uuid.UUID
    cycle_id: uuid.UUID
    unit_id: uuid.UUID | None = None
    client_uuid: uuid.UUID
    action: str
    measure: str | None = None
    amount: float | None = None
    progress_after: float | None = None
    occurred_at: datetime
    duration_min: int | None = None
    note: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class MediaCollectionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1)
    description: str | None = None
    color: str | None = Field(default=None, max_length=16)
    position: int = 0


class MediaCollectionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = None
    description: str | None = None
    color: str | None = Field(default=None, max_length=16)
    position: int | None = None

    @model_validator(mode="after")
    def non_null_required_fields(self):
        for field in {"title", "position"} & self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} null olamaz")
        return self


class MediaCollectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    description: str | None = None
    color: str | None = None
    position: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MediaDetailOut(BaseModel):
    item: MediaItemOut
    units: list[MediaUnitOut]
    cycles: list[MediaCycleOut]
    consumptions: list[MediaConsumptionOut]
    collections: list[MediaCollectionOut]


class MediaStats(BaseModel):
    total: int
    in_progress: int
    completed: int
    planned: int
    by_kind: dict[str, int]
    total_duration_min: int = 0
    scored_count: int = 0
    average_score: float | None = None


class MediaDashboardOut(BaseModel):
    continue_items: list[MediaItemOut]
    upcoming: list[MediaUnitOut]
    recent_consumptions: list[MediaConsumptionOut]
    stats: MediaStats


class ProgressValidationOut(BaseModel):
    valid: bool
    actual: float
    expected: float


class MetadataResult(BaseModel):
    """Provider arama sonucunun ortak, kayda dönüştürülebilir biçimi."""

    provider: str
    provider_id: str
    title: str
    subtitle: str | None = None
    summary: str | None = None
    total: float | None = None
    progress_measure: str | None = None
    cover: str | None = None
    backdrop: str | None = None
    cover_url: str | None = None
    backdrop_url: str | None = None
    year: int | None = None
    provider_ids: dict[str, Any] = Field(default_factory=dict)
    meta: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MediaProviderCapabilitiesOut(BaseModel):
    search: bool
    details: bool
    units: bool
    upcoming: bool
    cache_artwork: bool
    requires_settings: list[str]


class MediaProviderStatusOut(BaseModel):
    id: str
    kinds: list[str]
    capabilities: MediaProviderCapabilitiesOut
    ready: bool
    missing_settings: list[str]
    last_run_at: datetime | None = None
    last_status: str | None = None
    last_error: str | None = None


class MediaSyncBatchOut(BaseModel):
    id: uuid.UUID
    scope: Literal["media"]
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
    started_at: datetime | None = None
    finished_at: datetime | None = None


class MediaSyncIdleOut(BaseModel):
    scope: Literal["media"]
    status: Literal["idle"]
    source_ids: list[str]
    total_sources: Literal[0]
