from uuid import UUID

from pydantic import BaseModel, Field


class CourseIn(BaseModel):
    title: str = Field(min_length=1)
    platform: str | None = None
    url: str | None = None
    status: str = "planned"
    progress_pct: int = Field(0, ge=0, le=100)
    notes: str | None = None


class CoursePatch(BaseModel):
    title: str | None = None
    status: str | None = None
    progress_pct: int | None = Field(None, ge=0, le=100)
    notes: str | None = None


class AreaIn(BaseModel):
    title: str = Field(min_length=1)
    color: str | None = None
    position: int = 0


class TopicIn(BaseModel):
    title: str = Field(min_length=1)
    area_id: UUID
    parent_id: UUID | None = None
    status: str = "not_started"
    confidence: int | None = Field(None, ge=1, le=5)
    target_min: int | None = Field(None, ge=1)
    position: int = 0


class TopicPatch(BaseModel):
    title: str | None = None
    parent_id: UUID | None = None
    status: str | None = None
    confidence: int | None = Field(None, ge=1, le=5)
    target_min: int | None = Field(None, ge=1)
    position: int | None = None
