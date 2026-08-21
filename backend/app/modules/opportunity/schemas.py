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
    organization: str | None
    url: str | None
    status: str
    priority: int
    found_at: datetime
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
    trashed_from_status: str | None = None


class RequirementIn(BaseModel):
    name: str = Field(min_length=1)
    required: bool = True
    status: Literal["missing", "ready", "submitted", "waived"] = "missing"
    note: str | None = None


class NotificationOut(BaseModel):
    id: int
    kind: str
    title: str
    body: str | None
    entity_id: UUID | None
    #: Bildirime tiklayinca nereye gidilecegini arayuz bundan cozer.
    entity_type: str | None = None
    importance: int
    created_at: datetime
    read_at: datetime | None


class DeadlineOut(BaseModel):
    entity_id: UUID
    type: str
    title: str
    due_at: datetime
    module: str
    sub_kind: str | None
    priority: int
