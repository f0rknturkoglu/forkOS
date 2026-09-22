"""A2: Sürümlü, typed bootstrap bağlamı ve turn orkestrasyon şemaları."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.agent_episode.schemas import SessionHandoffV1
from app.modules.agent_lifecycle.schemas import LifecycleEventOut

_ABSOLUTE_PATH_CHECK = re.compile(r"(?:^[A-Za-z]:[\\/]|^\/|\/Users\/|\/home\/|\\Users\\)")


class BootstrapSourceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1, max_length=128)
    source_type: str = Field(min_length=1, max_length=32)
    source_version: str | None = Field(default=None, max_length=64)
    scope_project: str | None = Field(default=None, max_length=64)
    title: str | None = Field(default=None, max_length=128)

    @field_validator("source_id")
    @classmethod
    def validate_source_id_relative(cls, value: str) -> str:
        # Prevent any absolute host paths from leaking into source identifiers
        val_clean = value.strip()
        if _ABSOLUTE_PATH_CHECK.search(val_clean):
            raise ValueError("source_id must not contain absolute filesystem paths")
        return val_clean


class BootstrapIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interaction_conventions: list[str] = Field(default_factory=list, max_length=3)
    durable_preferences: list[str] = Field(default_factory=list, max_length=4)
    explicit_corrections: list[str] = Field(default_factory=list, max_length=3)
    long_running_goals: list[str] = Field(default_factory=list, max_length=3)


class OperationalDeadline(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    due_at: str | None = None
    remaining_days: int | None = None
    entity_type: str = "todo"
    module: str | None = None
    priority: int | None = None


class OperationalProject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    status: str
    next_action: str | None = None
    last_activity_at: str | None = None



class OperationalState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_projects: list[OperationalProject] = Field(default_factory=list, max_length=5)
    upcoming_deadlines: list[OperationalDeadline] = Field(default_factory=list, max_length=5)
    open_todos_count: int = 0
    pending_decisions_count: int = 0
    pending_decisions_summary: list[str] = Field(default_factory=list, max_length=3)


class BootstrapContinuity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    anchor_timestamp: str | None = None
    anchor_kind: str | None = None
    activity_gap_hours: float | None = None
    last_meaningful_activity: str | None = None
    recent_completed: list[str] = Field(default_factory=list, max_length=3)
    active_threads: list[str] = Field(default_factory=list, max_length=3)
    stalled_projects: list[str] = Field(default_factory=list, max_length=2)


class BootstrapHotMemory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[dict[str, Any]] = Field(default_factory=list, max_length=6)


class BootstrapDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    available: bool = True
    truncated: bool = False
    omitted_count: int = 0
    degraded_reasons: list[str] = Field(default_factory=list)
    generation_ms: float = 0.0


class BootstrapPacketV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    session_key: str
    generated_at: str
    is_first_turn: bool = True
    identity: BootstrapIdentity
    operational_state: OperationalState
    continuity: BootstrapContinuity
    hot_memory: BootstrapHotMemory
    sources: list[BootstrapSourceRef] = Field(default_factory=list, max_length=5)
    diagnostics: BootstrapDiagnostics


class TurnContextIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    harness: Literal["hermes", "codex", "claude"]
    session_id: str = Field(min_length=1, max_length=256)
    turn_id: str | None = Field(default=None, min_length=1, max_length=256)
    platform: str = Field(default="unknown", max_length=64)
    is_first_turn: bool = False
    user_message: str | None = Field(default=None, max_length=2000)
    scope_project: str | None = Field(default=None, max_length=64)

    @field_validator("session_id", "turn_id")
    @classmethod
    def validate_identity(cls, value: str | None) -> str | None:
        if value is not None and (not value.strip() or any(ord(char) < 32 or ord(char) == 127 for char in value)):
            raise ValueError("invalid identity")
        return value

    @field_validator("platform")
    @classmethod
    def normalize_platform(cls, value: str) -> str:
        value = value.strip().lower()
        if not value or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for char in value):
            raise ValueError("invalid platform")
        return value

    @model_validator(mode="after")
    def require_turn_for_later_turns(self) -> "TurnContextIn":
        if not self.is_first_turn and self.turn_id is None:
            raise ValueError("later turns require turn_id")
        return self


class TurnContextOut(BaseModel):
    lifecycle: LifecycleEventOut
    packet: BootstrapPacketV1 | None = None
    rendered_context: str | None = None
    degraded_reasons: list[str] = Field(default_factory=list)
    #: A3 epizodik devri. Yalnız YENİ oturumun ilk turunda dolu olabilir ve
    #: yalnızca ilgili, mühürlenmiş, süresi geçmemiş bir devir seçilebilirse
    #: doldurulur. A2 servisi bu alanı BİLMEZ; orkestrasyon ucudur.
    handoff: SessionHandoffV1 | None = None


class ContinuityStatusOut(BaseModel):
    available: bool
    last_bootstrap_at: datetime | None
    last_context_at: datetime | None = None
    last_harness: str | None
    active_source_count: int
    is_truncated: bool
    degraded_reasons: list[str]
    has_active_continuity: bool
