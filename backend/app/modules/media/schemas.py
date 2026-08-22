from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from app.modules.media.models import KINDS, STATUSES


class MediaItemIn(BaseModel):
    title: str
    kind: str
    status: str = "planned"
    progress: int | None = None
    total: int | None = None
    score: int | None = None
    notes: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    meta: dict[str, Any] = {}

    @field_validator("kind")
    @classmethod
    def kind_known(cls, v: str) -> str:
        if v not in KINDS:
            raise ValueError(f"kind su olmali: {KINDS}")
        return v

    @field_validator("status")
    @classmethod
    def status_known(cls, v: str) -> str:
        if v not in STATUSES:
            raise ValueError(f"status su olmali: {STATUSES}")
        return v

    @field_validator("score")
    @classmethod
    def score_range(cls, v: int | None) -> int | None:
        if v is not None and not 0 <= v <= 10:
            raise ValueError("score 0-10 olmali")
        return v


class MediaItemUpdate(BaseModel):
    """Kismi guncelleme. Verilmeyen alana dokunulmaz."""

    title: str | None = None
    status: str | None = None
    progress: int | None = None
    total: int | None = None
    score: int | None = None
    notes: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    meta: dict[str, Any] | None = None

    @field_validator("status")
    @classmethod
    def status_known(cls, v: str | None) -> str | None:
        if v is not None and v not in STATUSES:
            raise ValueError(f"status su olmali: {STATUSES}")
        return v

    @field_validator("score")
    @classmethod
    def score_range(cls, v: int | None) -> int | None:
        if v is not None and not 0 <= v <= 10:
            raise ValueError("score 0-10 olmali")
        return v


class MediaItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    kind: str
    status: str
    progress: int | None = None
    total: int | None = None
    score: int | None = None
    notes: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    meta: dict[str, Any] = {}
    created_at: datetime | None = None


class MetadataResult(BaseModel):
    """OpenLibrary/AniList/TMDB -> normalize sonuc."""

    title: str
    subtitle: str | None = None
    cover_url: str | None = None
    year: int | None = None
    metadata: dict[str, Any] = {}


class MediaStats(BaseModel):
    total: int
    in_progress: int
    completed: int
    planned: int
    by_kind: dict[str, int]