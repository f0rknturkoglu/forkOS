from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def _now_utc() -> datetime:
    return datetime.now(UTC)


SENSITIVE_KEY_SUBSTRINGS = (
    "token",
    "secret",
    "password",
    "api_key",
    "apikey",
    "auth",
    "credential",
    "private_key",
)


def sanitize_payload(obj: Any) -> Any:
    """Recursively sanitize dictionary/list structures to prevent leaking credentials or secrets."""
    if isinstance(obj, dict):
        sanitized = {}
        for k, v in obj.items():
            k_lower = str(k).lower()
            if any(sub in k_lower for sub in SENSITIVE_KEY_SUBSTRINGS):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_payload(v)
        return sanitized
    elif isinstance(obj, list):
        return [sanitize_payload(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(sanitize_payload(item) for item in obj)
    return obj


class AgentEnvelope[T](BaseModel):
    """Standard read-only envelope returned by all H0 tools."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    as_of: datetime = Field(default_factory=_now_utc, description="Timestamp when the context was collected.")
    source: Literal["forkos", "f0rknbrain"] = Field(..., description="Origin domain of the returned data.")
    data: T = Field(..., description="Structured payload.")
    truncated: bool = Field(default=False, description="Whether the payload was capped due to budget/bounds.")


class BriefingData(BaseModel):
    """Operational briefing of current day execution state."""

    day: str = Field(..., description="Target date (YYYY-MM-DD).")
    agenda: list[dict[str, Any]] = Field(default_factory=list, description="Top scheduled/time-blocked events (max 30).")
    open_todos: list[dict[str, Any]] = Field(default_factory=list, description="High-priority and open todos (max 20).")
    deadlines: list[dict[str, Any]] = Field(default_factory=list, description="Upcoming deadlines within 7 days (max 15).")
    active_projects: list[dict[str, Any]] = Field(default_factory=list, description="Top active projects with next_action (max 10).")
    learning_due: list[dict[str, Any]] = Field(default_factory=list, description="SRS flashcards due and active topics (max 10).")
    opportunity_attention: list[dict[str, Any]] = Field(default_factory=list, description="Active career opportunities requiring action (max 10).")
    notifications: list[dict[str, Any]] = Field(default_factory=list, description="Recent unread notifications (max 10).")
    recent_activity_summary: list[dict[str, Any]] = Field(default_factory=list, description="Key recent activities (max 10).")
    vault_status: dict[str, Any] = Field(default_factory=dict, description="Summary of Obsidian Vault availability.")


class EntitySearchResult(BaseModel):
    """Compact operational entity search hit."""

    id: str = Field(..., description="Entity UUID.")
    type: str = Field(..., description="Entity type spec name (e.g. project, todo).")
    title: str = Field(..., description="Entity human-readable title.")
    route: str = Field(..., description="Web UI deep link route.")
    summary: str = Field(default="", description="Short excerpt or description.")


class EntityContextData(BaseModel):
    """Detailed operational context for a single entity."""

    id: str = Field(..., description="Entity UUID.")
    type: str = Field(..., description="Entity type.")
    title: str = Field(..., description="Entity title.")
    route: str = Field(..., description="Web UI deep link route.")
    details: dict[str, Any] = Field(default_factory=dict, description="Entity attributes.")
    related_entities: list[dict[str, Any]] = Field(default_factory=list, description="Linked operational entities.")
    recent_events: list[dict[str, Any]] = Field(default_factory=list, description="Last events touching this entity.")
    knowledge_ref: dict[str, Any] | None = Field(default=None, description="Vault note pointer if linked.")


class ProjectContextData(BaseModel):
    """Operational context packet for a project."""

    project: dict[str, Any] = Field(..., description="Project identity, status, next_action, stack, github_repo.")
    milestones: list[dict[str, Any]] = Field(default_factory=list, description="Project milestones.")
    todos: list[dict[str, Any]] = Field(default_factory=list, description="Open tasks under this project (max 20).")
    recent_activity: list[dict[str, Any]] = Field(default_factory=list, description="Recent project events (max 10).")
    deadlines: list[dict[str, Any]] = Field(default_factory=list, description="Upcoming deadlines.")
    knowledge: dict[str, Any] = Field(default_factory=dict, description="Vault knowledge pointer only (forkos_id, relative_path, title, available).")


class ActivityEventData(BaseModel):
    """Sanitized operational event record."""

    id: int = Field(..., description="Event sequence ID.")
    timestamp: str = Field(..., description="Event ISO timestamp.")
    verb: str = Field(..., description="Event action verb.")
    entity_id: str | None = Field(default=None, description="Affected entity UUID.")
    entity_type: str | None = Field(default=None, description="Affected entity type.")
    title: str = Field(default="", description="Affected entity title or event summary.")
    payload: dict[str, Any] = Field(default_factory=dict, description="Bounded sanitized event payload.")


class BrainStatusData(BaseModel):
    """Status and health of f0rknbrain Vault knowledge interface."""

    brain_interface_version: int = Field(default=1, description="Agent contract interface version.")
    configured: bool = Field(..., description="Whether OBSIDIAN_VAULT_PATH is set.")
    available: bool = Field(..., description="Whether the Vault directory exists and is accessible.")
    readable: bool = Field(..., description="Whether files can be read from the Vault.")
    writable: bool = Field(..., description="Informational only. H0 does not mutate the Vault.")
    vault_name: str = Field(default="", description="Display name of the Vault.")
    total_markdown_files: int = Field(default=0, description="Total safe Markdown files available.")
    managed_files_count: int = Field(default=0, description="Files with recognized forkos_id frontmatter.")
    conflicts_count: int = Field(default=0, description="Files with duplicate forkos_id conflicts.")
    invalid_metadata_count: int = Field(default=0, description="Files with malformed forkOS frontmatter.")


class BrainSearchResult(BaseModel):
    """Single lexical search match across Vault markdown files."""

    locator: str = Field(..., description="Stable locator: forkos_id if managed, otherwise relative_path.")
    title: str = Field(..., description="Note title derived from frontmatter, H1, or filename.")
    relative_path: str = Field(..., description="Vault-relative path to the note.")
    forkos_id: str | None = Field(default=None, description="forkos_id UUID if note is managed.")
    forkos_type: str | None = Field(default=None, description="forkOS entity type if note is managed.")
    matched_heading: str | None = Field(default=None, description="Section heading under which the match occurred.")
    snippet: str = Field(..., description="Bounded text excerpt (~300–700 chars) around match.")
    score: int = Field(default=0, description="Deterministic lexical rank score.")


class BrainReadData(BaseModel):
    """Bounded content read of a single Vault note."""

    title: str = Field(..., description="Derived note title.")
    relative_path: str = Field(..., description="Vault-relative path.")
    forkos_id: str | None = Field(default=None, description="forkos_id if managed.")
    forkos_type: str | None = Field(default=None, description="forkos_type if managed.")
    frontmatter: dict[str, Any] = Field(default_factory=dict, description="Whitelisted frontmatter attributes.")
    headings: list[str] = Field(default_factory=list, description="Top-level headings detected in document.")
    content: str = Field(..., description="Note markdown body (bounded to character limit).")
    truncated: bool = Field(default=False, description="True if content exceeded character budget.")
