from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NoteIn(BaseModel):
    body: str = Field(min_length=1, max_length=200_000)
    pinned: bool = False


class NoteUpdate(BaseModel):
    body: str | None = Field(default=None, min_length=1, max_length=200_000)
    pinned: bool | None = None


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    body: str
    pinned: bool
    created_at: datetime
    updated_at: datetime
