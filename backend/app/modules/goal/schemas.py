from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

GoalStatus = Literal["active", "paused", "completed", "retired"]
GoalHorizon = Literal["short_term", "quarter", "year", "long_term"]


def _title(value: str) -> str:
    clean = " ".join(value.split())
    if not clean:
        raise ValueError("Başlık boş olamaz")
    return clean


class GoalIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    horizon: GoalHorizon = "quarter"
    target_at: datetime | None = None
    position: int = 0
    source_memory_id: str | None = Field(default=None, max_length=64)

    _clean_title = field_validator("title")(_title)


class GoalPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    status: GoalStatus | None = None
    horizon: GoalHorizon | None = None
    target_at: datetime | None = None
    position: int | None = None

    @field_validator("title")
    @classmethod
    def _clean_title(cls, value: str | None) -> str | None:
        return _title(value) if value is not None else None


class GoalMilestoneIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    due_at: datetime | None = None
    position: int = 0

    _clean_title = field_validator("title")(_title)


class GoalMilestonePatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    due_at: datetime | None = None
    completed: bool | None = None
    position: int | None = None

    @field_validator("title")
    @classmethod
    def _clean_title(cls, value: str | None) -> str | None:
        return _title(value) if value is not None else None


class GoalMilestoneOut(BaseModel):
    id: UUID
    goal_id: UUID
    title: str
    due_at: datetime | None
    completed_at: datetime | None
    position: int


class GoalOut(BaseModel):
    id: UUID
    title: str
    description: str | None
    status: GoalStatus
    horizon: GoalHorizon
    target_at: datetime | None
    position: int
    source_memory_id: str | None
    created_at: datetime
    updated_at: datetime
    milestones: list[GoalMilestoneOut]
    milestone_count: int
    completed_milestones: int
    progress_percent: int | None
