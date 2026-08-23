from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

AgendaKind = Literal["calendar", "todo", "rss", "media"]
AgendaSource = Literal["calendar", "planned", "due", "routine", "suggestion"]
AgendaAction = Literal["complete_todo", "mark_rss_read", "log_media"]


class AgendaRow(BaseModel):
    kind: AgendaKind
    source: AgendaSource
    id: uuid.UUID
    slot_id: uuid.UUID | None = None
    title: str
    completed: bool = False
    action: AgendaAction | None = None
    read_only: bool = False
    context_only: bool = False
    starts_at: datetime | None = None
    duration_min: int | None = None
    parent_id: uuid.UUID | None = None
    project_title: str | None = None
    feed_title: str | None = None
    url: str | None = None
    media_kind: str | None = None
    media_status: str | None = None
    progress_label: str | None = None
    cover_url: str | None = None
    recur: Literal["daily", "weekdays", "weekly", "monthly"] | None = None
    children: list[AgendaRow] = Field(default_factory=list)


class AgendaSuggestions(BaseModel):
    todos: list[AgendaRow] = Field(default_factory=list)
    rss: list[AgendaRow] = Field(default_factory=list)
    media: list[AgendaRow] = Field(default_factory=list)


class TodayAgendaOut(BaseModel):
    day: date
    auto_suggestions: bool = True
    timed: list[AgendaRow] = Field(default_factory=list)
    checklist: list[AgendaRow] = Field(default_factory=list)
    completed: list[AgendaRow] = Field(default_factory=list)
    suggestions: AgendaSuggestions = Field(default_factory=AgendaSuggestions)
