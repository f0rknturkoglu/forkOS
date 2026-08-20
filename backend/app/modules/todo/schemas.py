from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class TodoIn(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    priority: int = Field(default=2, ge=0, le=3)
    status: str = "open"
    due_at: datetime | None = None
    reminder_at: datetime | None = None
    parent_id: uuid.UUID | None = None
    position: int = 0


class TodoUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: int | None = Field(default=None, ge=0, le=3)
    status: str | None = None
    due_at: datetime | None = None
    reminder_at: datetime | None = None
    parent_id: uuid.UUID | None = None
    position: int | None = None


class TodoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    description: str | None
    priority: int
    status: str
    due_at: datetime | None
    reminder_at: datetime | None
    completed_at: datetime | None
    parent_id: uuid.UUID | None
    position: int


class PlanSlotIn(BaseModel):
    entity_id: uuid.UUID
    day: date
    start_min: int | None = Field(default=None, ge=0, le=1439)
    duration_min: int | None = Field(default=None, ge=1, le=1440)
    note: str | None = None
    position: int = 0


class PlanSlotUpdate(BaseModel):
    day: date | None = None
    start_min: int | None = Field(default=None, ge=0, le=1439)
    duration_min: int | None = Field(default=None, ge=1, le=1440)
    note: str | None = None
    position: int | None = None


class PlanSlotOut(BaseModel):
    id: uuid.UUID
    entity_id: uuid.UUID
    entity_type: str
    title: str
    day: date
    start_min: int | None
    duration_min: int | None
    note: str | None
    position: int
