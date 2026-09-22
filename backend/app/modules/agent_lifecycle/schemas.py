"""A1: dar, sürümlü ve kişisel içerik kabul etmeyen REST sözleşmesi."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LifecycleEventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    event: Literal["session_start", "turn_seen", "session_finalize"]
    harness: Literal["hermes", "codex", "claude"]
    session_id: str = Field(min_length=1, max_length=256)
    turn_id: str | None = Field(default=None, min_length=1, max_length=256)
    platform: str = Field(default="unknown", max_length=64)

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
    def require_turn_for_turn_event(self) -> "LifecycleEventIn":
        if self.event == "turn_seen" and self.turn_id is None:
            raise ValueError("turn_seen requires turn_id")
        return self


class LifecycleEventOut(BaseModel):
    accepted: bool
    event: Literal["session_start", "turn_seen", "session_finalize"]
    duplicate: bool


class LifecycleStatusOut(BaseModel):
    available: bool
    last_event_at: datetime | None
    last_harness: str | None
    active_sessions: int
    last_finalized_at: datetime | None
    incomplete_session_count: int
