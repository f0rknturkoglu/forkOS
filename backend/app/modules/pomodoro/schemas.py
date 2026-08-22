from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PomodoroStart(BaseModel):
    # Varsayilan blok 50 dk odak / 10 dk mola (bkz. system DEFAULTS).
    planned_min: int = Field(default=50, ge=1, le=240)
    context_entity_id: uuid.UUID | None = None
    topic: str | None = None
    kind: str = "focus"


class PomodoroStop(BaseModel):
    interrupted: bool = False


class PomodoroManual(BaseModel):
    """Gecmise elle islenen seans -- sayac calistirilmadan yapilan is."""

    started_at: datetime
    minutes: int = Field(ge=1, le=600)
    kind: str = "focus"
    topic: str | None = None
    context_entity_id: uuid.UUID | None = None


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
    #: Dolu ise seans duraklatilmis; kalan sure bu ana gore donuyor.
    paused_at: datetime | None = None
    #: Duraklamada gecen toplam saniye.
    paused_s: int = 0


class PomodoroStats(BaseModel):
    minutes: int
    sessions: int
    interrupted: int
