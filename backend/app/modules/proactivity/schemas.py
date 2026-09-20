"""H6 kontrol yuzeyi sozlesmeleri (REST + MCP ayni semayi kullanir)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProactivityConfigIn(BaseModel):
    """Yalnizca BILINEN alanlar; bilinmeyen anahtar SESSIZCE DUSMEZ (§106)."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    quiet_hours_start: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    quiet_hours_end: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    focus_deferral_enabled: bool | None = None
    digest_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")


class ProactivityRuleIn(BaseModel):
    """Kural ac/kapa ve esik ayari — kapali sema, serbest JSON degil."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    config: dict | None = None
    scope_entity_id: uuid.UUID | None = None


class ProactivityRuleOut(BaseModel):
    kind: str
    version: int
    logical_key: str
    enabled: bool
    config: dict
    snoozed_until: datetime | None = None


class ProactivityFailureOut(BaseModel):
    rule_kind: str | None
    failure_code: str | None
    at: str


class ProactivityStatusOut(BaseModel):
    enabled: bool
    quiet_hours_start: str
    quiet_hours_end: str
    focus_deferral_enabled: bool
    digest_time: str
    immediate_budget: int
    immediate_surfaces_today: int
    pending_deferred: int
    pending_digest: int
    worker_heartbeat: dict | None = None
    last_run_at: str | None = None
    rules: list[ProactivityRuleOut]
    recent_failures: list[ProactivityFailureOut]


class ProactivityRunOut(BaseModel):
    id: int
    rule_kind: str | None = None
    subject_type: str | None = None
    subject_id: str | None = None
    state: str
    reason_codes: list[str] = Field(default_factory=list)
    why_now: str | None = None
    triggered_at: str
    delivered_at: str | None = None
    delivery_count: int
    snoozed_until: str | None = None
    notification_id: int | None = None
    failure_code: str | None = None


class SnoozeIn(BaseModel):
    """Saat dilimli MUTLAK zaman; serbest metin cozumleme backend'de YOK (§108)."""

    until: datetime
