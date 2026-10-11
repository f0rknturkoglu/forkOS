from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, Field


class PomodoroStart(BaseModel):
    # Varsayilan blok 50 dk odak / 10 dk mola (bkz. system DEFAULTS).
    planned_min: int = Field(default=50, ge=1, le=240)
    context_entity_id: uuid.UUID | None = None
    topic: str | None = None
    kind: Literal["focus", "short_break", "long_break"] = "focus"


class PomodoroStop(BaseModel):
    interrupted: bool = False


class PomodoroManual(BaseModel):
    """Gecmise elle islenen seans -- sayac calistirilmadan yapilan is."""

    started_at: AwareDatetime
    minutes: int = Field(ge=1, le=600)
    kind: Literal["focus", "short_break", "long_break"] = "focus"
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
    #: Baglamin entity tipi -- arayuz "nereden geldi" rozetini bundan cizer.
    context_type: str | None = None
    topic: str | None
    interrupted: bool
    source: Literal["timer", "manual"] = "timer"
    #: Dolu ise seans duraklatilmis; kalan sure bu ana gore donuyor.
    paused_at: datetime | None = None
    #: Duraklamada gecen toplam saniye.
    paused_s: int = 0


class PomodoroStats(BaseModel):
    minutes: int
    sessions: int
    interrupted: int


class PomodoroDailyPoint(BaseModel):
    date: date
    minutes: int
    sessions: int
    interrupted: int


class PomodoroContextStat(BaseModel):
    context_entity_id: uuid.UUID | None
    title: str
    context_type: str | None
    minutes: int
    sessions: int
    share: float


class PomodoroAnalytics(BaseModel):
    range: Literal["week", "month", "all"]
    start_date: date
    end_date: date
    minutes: int
    sessions: int
    completed: int
    interrupted: int
    daily: list[PomodoroDailyPoint]
    contexts: list[PomodoroContextStat]


class ContextOut(BaseModel):
    """Odaklanilabilecek bir kayit: gorev, calisma konusu, kaynak, proje, medya..."""

    id: uuid.UUID
    type: str
    title: str
    #: Medya kayitlari icin: tur ve kapak (secicide dogru rozet/gorsel cizilir).
    kind: str | None = None
    cover_url: str | None = None
