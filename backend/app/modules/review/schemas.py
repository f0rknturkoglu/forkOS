from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class TodoReviewStats(BaseModel):
    completed: int
    created: int
    dropped: int
    overdue_now: int


class FocusReviewStats(BaseModel):
    minutes: int
    sessions: int
    interrupted: int
    active_days: int
    best_day: date | None
    best_day_minutes: int
    longest_session: int


class TopicReviewStats(BaseModel):
    topic: str
    minutes: int


class CaptureReviewStats(BaseModel):
    bookmarks: int
    rss_read: int
    notes: int


class ApplicationReviewStats(BaseModel):
    discovered: int
    updated: int


class StudyReviewStats(BaseModel):
    minutes_by_area: dict[str, int]


class GithubReviewStats(BaseModel):
    commits: int
    repos: dict[str, int]


class ReviewStats(BaseModel):
    todos: TodoReviewStats
    focus: FocusReviewStats
    topics: list[TopicReviewStats]
    habits: dict[str, int]
    capture: CaptureReviewStats
    applications: ApplicationReviewStats
    study: StudyReviewStats
    github: GithubReviewStats


class UnfinishedTodo(BaseModel):
    id: uuid.UUID
    title: str
    priority: int
    due_at: datetime | None


class CompletedTodo(BaseModel):
    id: uuid.UUID | None
    title: str
    completed_at: datetime


class ReviewPreview(BaseModel):
    kind: Literal["daily", "weekly"]
    period_start: date
    period_end: date
    stats: ReviewStats
    unfinished_todos: list[UnfinishedTodo]
    completed_todos: list[CompletedTodo]


class ReviewIn(BaseModel):
    kind: Literal["daily", "weekly"]
    period_start: date
    decisions: dict = {}
    note: str | None = None


class ReviewOut(BaseModel):
    id: uuid.UUID
    kind: Literal["daily", "weekly"]
    period_start: date
    period_end: date
    stats: dict
    decisions: dict
    note: str | None
