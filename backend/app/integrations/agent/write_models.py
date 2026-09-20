from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _validate_uuid_str(v: Any) -> str:
    if isinstance(v, uuid.UUID):
        return str(v)
    if isinstance(v, str):
        v_stripped = v.strip()
        try:
            return str(uuid.UUID(v_stripped))
        except (ValueError, AttributeError, TypeError) as exc:
            raise ValueError(f"Invalid UUID: {v}") from exc
    raise ValueError(f"Invalid UUID type: {type(v)}")


def _validate_optional_uuid_str(v: Any) -> str | None:
    if v is None:
        return None
    return _validate_uuid_str(v)


def _validate_iso_datetime(v: str | None) -> str | None:
    if v is None:
        return None
    if not isinstance(v, str):
        raise ValueError("Datetime must be an ISO string")
    v_stripped = v.strip()
    try:
        normalized = v_stripped.replace("Z", "+00:00") if v_stripped.endswith("Z") else v_stripped
        datetime.fromisoformat(normalized)
    except Exception as exc:
        raise ValueError(f"Invalid ISO datetime: {v}") from exc
    return v_stripped


def _validate_date_str(v: str | None) -> str | None:
    if v is None:
        return None
    if not isinstance(v, str):
        raise ValueError("Date must be a string")
    v_stripped = v.strip()
    if len(v_stripped) != 10:
        raise ValueError("Date must be in YYYY-MM-DD format")
    try:
        parsed = datetime.strptime(v_stripped, "%Y-%m-%d")
        if parsed.strftime("%Y-%m-%d") != v_stripped:
            raise ValueError("Invalid calendar date")
    except Exception as exc:
        raise ValueError(f"Invalid date format, expected YYYY-MM-DD: {v}") from exc
    return v_stripped


def _validate_url_str(v: str) -> str:
    if not isinstance(v, str):
        raise ValueError("URL must be a string")
    v_stripped = v.strip()
    if not (v_stripped.startswith("http://") or v_stripped.startswith("https://")):
        raise ValueError("URL must start with http:// or https://")
    if len(v_stripped) > 2048:
        raise ValueError("URL cannot exceed 2048 characters")
    parsed = urlsplit(v_stripped)
    if not parsed.netloc:
        raise ValueError("URL must contain a valid domain / host")
    return v_stripped


def _validate_tags_list(v: list[str] | None) -> list[str] | None:
    if v is None:
        return None
    cleaned = [t.strip() for t in v if t and t.strip()]
    if len(cleaned) > 20:
        raise ValueError("Cannot have more than 20 tags")
    for tag in cleaned:
        if len(tag) > 50:
            raise ValueError("Each tag cannot exceed 50 characters")
    return cleaned


class ActionReceipt(BaseModel):
    request_id: str | None = None
    tool: str
    status: Literal["executed", "noop"]
    target_type: str
    target_id: str
    summary: str
    changed_fields: list[str] = Field(default_factory=list)
    before: dict[str, Any] = Field(default_factory=dict)
    after: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class TodoCreateIn(BaseModel):
    title: str
    description: str | None = Field(default=None, max_length=5000)
    priority: int = Field(default=2, ge=0, le=3)
    due_at: str | None = None
    reminder_at: str | None = None
    plan_day: str | None = None
    project_id: str | None = None
    milestone_id: str | None = None
    parent_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    recur: Literal["daily", "weekdays", "weekly", "monthly"] | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Title must be a string")
        stripped = v.strip()
        if not stripped:
            raise ValueError("Title cannot be empty")
        if len(stripped) > 300:
            raise ValueError("Title cannot exceed 300 characters")
        return stripped

    @field_validator("due_at", "reminder_at")
    @classmethod
    def validate_iso_dates(cls, v: str | None) -> str | None:
        return _validate_iso_datetime(v)

    @field_validator("plan_day")
    @classmethod
    def validate_plan_day(cls, v: str | None) -> str | None:
        return _validate_date_str(v)

    @field_validator("project_id", "milestone_id", "parent_id")
    @classmethod
    def validate_uuids(cls, v: Any) -> str | None:
        return _validate_optional_uuid_str(v)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        res = _validate_tags_list(v)
        return res if res is not None else []


class TodoUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    todo_id: str
    title: str | None = None
    description: str | None = Field(default=None, max_length=5000)
    priority: int | None = Field(default=None, ge=0, le=3)
    due_at: str | None = None
    reminder_at: str | None = None
    tags: list[str] | None = None
    recur: Literal["daily", "weekdays", "weekly", "monthly", ""] | None = None
    expected_updated_at: str | None = None

    @field_validator("todo_id")
    @classmethod
    def validate_todo_id(cls, v: Any) -> str:
        return _validate_uuid_str(v)

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip()
        if not stripped:
            raise ValueError("Title cannot be empty")
        if len(stripped) > 300:
            raise ValueError("Title cannot exceed 300 characters")
        return stripped

    @field_validator("due_at", "reminder_at", "expected_updated_at")
    @classmethod
    def validate_iso_dates(cls, v: str | None) -> str | None:
        return _validate_iso_datetime(v)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str] | None) -> list[str] | None:
        return _validate_tags_list(v)


class TodoPlanIn(BaseModel):
    todo_id: str
    day: str
    start_min: int | None = Field(default=None, ge=0, le=1439)
    duration_min: int | None = Field(default=None, ge=5, le=1440)

    @field_validator("todo_id")
    @classmethod
    def validate_todo_id(cls, v: Any) -> str:
        return _validate_uuid_str(v)

    @field_validator("day")
    @classmethod
    def validate_day(cls, v: str) -> str:
        res = _validate_date_str(v)
        if res is None:
            raise ValueError("Day is required")
        return res


class ProjectUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    next_action: str | None = Field(default=None, max_length=500)
    expected_updated_at: str | None = None

    @field_validator("project_id")
    @classmethod
    def validate_project_id(cls, v: Any) -> str:
        return _validate_uuid_str(v)

    @field_validator("next_action")
    @classmethod
    def validate_next_action(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip()
        if len(stripped) > 500:
            raise ValueError("next_action cannot exceed 500 characters")
        return stripped

    @field_validator("expected_updated_at")
    @classmethod
    def validate_expected_updated_at(cls, v: str | None) -> str | None:
        return _validate_iso_datetime(v)


class OpportunityTransitionIn(BaseModel):
    opportunity_id: str
    expected_status: str
    to_status: str
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("opportunity_id")
    @classmethod
    def validate_opp_id(cls, v: Any) -> str:
        return _validate_uuid_str(v)

    @field_validator("expected_status", "to_status")
    @classmethod
    def validate_status_str(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Status must be a string")
        stripped = v.strip()
        if not stripped:
            raise ValueError("Status cannot be empty")
        return stripped


class ApplicationTransitionIn(BaseModel):
    opportunity_id: str
    expected_status: str | None = None
    to_status: str
    note: str | None = Field(default=None, max_length=1000)
    rejection_reason: str | None = Field(default=None, max_length=200)

    @field_validator("opportunity_id")
    @classmethod
    def validate_opp_id(cls, v: Any) -> str:
        return _validate_uuid_str(v)

    @field_validator("to_status")
    @classmethod
    def validate_to_status(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Status must be a string")
        stripped = v.strip()
        if not stripped:
            raise ValueError("Status cannot be empty")
        return stripped

    @field_validator("expected_status")
    @classmethod
    def validate_expected_status(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip()
        if not stripped:
            raise ValueError("Expected status cannot be empty if provided")
        return stripped


class BookmarkCaptureIn(BaseModel):
    url: str
    title: str | None = Field(default=None, max_length=300)
    collection: Literal["inbox", "bookmarks", "archive"] = "inbox"
    tags: list[str] = Field(default_factory=list)
    note: str | None = Field(default=None, max_length=5000)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return _validate_url_str(v)

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip()
        if len(stripped) > 300:
            raise ValueError("Title cannot exceed 300 characters")
        return stripped

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        res = _validate_tags_list(v)
        return res if res is not None else []


class BookmarkUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bookmark_id: str
    collection: Literal["inbox", "bookmarks", "archive"] | None = None
    favorite: bool | None = None
    read_status: Literal["unread", "reading", "read"] | None = None
    tags: list[str] | None = None
    expected_updated_at: str | None = None

    @field_validator("bookmark_id")
    @classmethod
    def validate_bm_id(cls, v: Any) -> str:
        return _validate_uuid_str(v)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str] | None) -> list[str] | None:
        return _validate_tags_list(v)

    @field_validator("expected_updated_at")
    @classmethod
    def validate_expected_updated_at(cls, v: str | None) -> str | None:
        return _validate_iso_datetime(v)


class BrainCaptureIn(BaseModel):
    body: str
    title: str | None = Field(default=None, max_length=300)
    relate_to: str | None = None
    tags: list[str] | None = None

    @field_validator("body")
    @classmethod
    def validate_body(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Body must be a string")
        stripped = v.strip()
        if not stripped:
            raise ValueError("Body cannot be empty")
        if len(stripped) > 40000:
            raise ValueError("Body cannot exceed 40000 characters")
        return stripped

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip()
        if len(stripped) > 300:
            raise ValueError("Title cannot exceed 300 characters")
        return stripped

    @field_validator("relate_to")
    @classmethod
    def validate_relate_to(cls, v: Any) -> str | None:
        return _validate_optional_uuid_str(v)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str] | None) -> list[str] | None:
        return _validate_tags_list(v)


class BrainSaveToEntityIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    forkos_id: str
    text: str
    heading: str | None = Field(default=None, max_length=200)

    @field_validator("forkos_id")
    @classmethod
    def validate_forkos_id(cls, v: Any) -> str:
        return _validate_uuid_str(v)

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Text must be a string")
        stripped = v.strip()
        if not stripped:
            raise ValueError("Text cannot be empty")
        if len(stripped) > 20000:
            raise ValueError("Text cannot exceed 20000 characters")
        return stripped

    @field_validator("heading")
    @classmethod
    def validate_heading(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip()
        if len(stripped) > 200:
            raise ValueError("Heading cannot exceed 200 characters")
        return stripped


__all__ = [
    "ActionReceipt",
    "ApplicationTransitionIn",
    "BookmarkCaptureIn",
    "BookmarkUpdateIn",
    "BrainCaptureIn",
    "BrainSaveToEntityIn",
    "OpportunityTransitionIn",
    "ProjectUpdateIn",
    "TodoCreateIn",
    "TodoPlanIn",
    "TodoUpdateIn",
]
