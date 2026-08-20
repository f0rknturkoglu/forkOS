from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PomodoroStart(BaseModel):
    planned_min: int = Field(default=25, ge=1, le=240)
    context_entity_id: uuid.UUID | None = None
    topic: str | None = None
    kind: str = "focus"


class PomodoroStop(BaseModel):
    interrupted: bool = False


class PomodoroOut(BaseModel):
    id: uuid.UUID
    started_at: datetime
    ended_at: datetime | None
    planned_min: int
    actual_min: int | None
    kind: str
    context_entity_id: uuid.UUID | None
    context_title: str | None = None
    topic: str | None
    interrupted: bool


class PomodoroStats(BaseModel):
    minutes: int
    sessions: int
    interrupted: int
