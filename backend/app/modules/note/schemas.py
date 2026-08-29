from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class NoteIn(BaseModel):
    body: str = Field(min_length=1, max_length=200_000)
    pinned: bool = False
    #: Opsiyonel iliski intent'i (Faz 29): doluysa not oluşturulurken AYNI
    #: transaction icinde notes_about bagi kurulur. Iliski basarisizsa not
    #: da olusmaz (yarim kayit yok). Geriye uyumlu: bos birakilabilir.
    relate_to: uuid.UUID | None = None


class NoteUpdate(BaseModel):
    body: str | None = Field(default=None, min_length=1, max_length=200_000)
    pinned: bool | None = None


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    body: str
    pinned: bool
    project_id: uuid.UUID | None = None
    journal_day: date | None = None
    created_at: datetime
    updated_at: datetime
