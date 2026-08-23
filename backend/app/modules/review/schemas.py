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


class TopicReviewStats(BaseModel):
    topic: str
    minutes: int


class CaptureReviewStats(BaseModel):
    bookmarks: int
    rss_read: int


class ReviewStats(BaseModel):
    todos: TodoReviewStats
    focus: FocusReviewStats
    topics: list[TopicReviewStats]
    habits: dict[str, int]
    capture: CaptureReviewStats


class UnfinishedTodo(BaseModel):
    id: uuid.UUID
    title: str
    priority: int
    due_at: datetime | None


class ReviewPreview(BaseModel):
    kind: Literal["daily", "weekly"]
    period_start: date
    period_end: date
    stats: ReviewStats
    unfinished_todos: list[UnfinishedTodo]


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
