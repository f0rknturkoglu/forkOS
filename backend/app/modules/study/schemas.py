from uuid import UUID

from pydantic import BaseModel, Field


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
