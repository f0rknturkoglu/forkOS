from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, Field

from app.core.time import local_today


class HabitIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    cadence: str = "daily"
    target_per_week: int = Field(default=7, ge=1, le=7)
    color: str | None = None
    position: int = 0


class HabitUpdate(BaseModel):
    title: str | None = None
    cadence: str | None = None
    target_per_week: int | None = Field(default=None, ge=1, le=7)
    color: str | None = None
    active: bool | None = None
    position: int | None = None


class HabitCheck(BaseModel):
    day: date = Field(default_factory=local_today)
    done: bool = True
    note: str | None = None


class HabitOut(BaseModel):
    id: uuid.UUID
    title: str
    cadence: str
    target_per_week: int
    color: str | None
    active: bool
    position: int
    done_today: bool = False
    streak: int = 0
    #: Bu hafta (pazartesiden bugune) kac gun isaretlendi.
    week_done: int = 0
    #: En uzun kesintisiz seri -- "rekorun neydi" sorusu.
    best_streak: int = 0


class HabitGridEntry(BaseModel):
    habit_id: uuid.UUID
    title: str
    day: date
    done: bool
    note: str | None = None
