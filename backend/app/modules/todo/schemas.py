from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

#: Rutin araliklari. None = tek seferlik.
RECUR = Literal["daily", "weekdays", "weekly", "monthly"]


class TodoIn(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    priority: int = Field(default=2, ge=0, le=3)
    status: str = "open"
    due_at: datetime | None = None
    reminder_at: datetime | None = None
    parent_id: uuid.UUID | None = None
    position: int = 0
    tags: list[str] = []
    recur: RECUR | None = None
    project_id: uuid.UUID | None = None
    milestone_id: uuid.UUID | None = None
    #: "Bugune al" akisi: doluysa create() ayni transaction icinde bu gun icin
    #: plan slotu da yazar (plan = "bu gun yapmayi planliyorum", due_at ayri bir
    #: kavramdir -- teslim). Gecmis gun kisitlanmaz: schedule() ile ayni
    #: semantik (planner gecmise de yazabilir); "bugun"u komposerlar Istanbul
    #: gunune gore uretir, API bu alani genel plan gunu olarak gorur.
    plan_day: date | None = None


class TodoUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: int | None = Field(default=None, ge=0, le=3)
    status: str | None = None
    due_at: datetime | None = None
    reminder_at: datetime | None = None
    parent_id: uuid.UUID | None = None
    position: int | None = None
    tags: list[str] | None = None
    #: "" (bos metin) rutini KALDIRIR; None alani hic degistirmez.
    recur: RECUR | Literal[""] | None = None
    milestone_id: uuid.UUID | None = None


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
    tags: list[str] = []
    recur: str | None = None
    #: Gorev bir projeye bagliysa dolu -- arayuzde rozet olarak gosterilir.
    project_id: uuid.UUID | None = None
    project_title: str | None = None
    milestone_id: uuid.UUID | None = None
    #: Plan bilgisi (plan_slot'tan). Plan ile due_at FARKLI kavramlardir:
    #: plan = "bugun yapmayi planliyorum", due_at = "bugun teslim".
    #: En yakin gelecek slot dondurulur; gecmis slotlar listelenmez.
    planned_day: date | None = None
    planned_start_min: int | None = None
    milestone_title: str | None = None
    #: Alt gorev sayilari (parent_id ile baglananlar).
    subtask_total: int = 0
    subtask_done: int = 0


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
