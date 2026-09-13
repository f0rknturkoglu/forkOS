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
    """Kariyer metrikleri. ORAN YOK: kucuk orneklemde yuzde yanilticidir."""

    #: Donemde kesfedilen ve kaynakta hala gorunen guncel ilan.
    discovered: int
    #: Donemde kisa listeye alinan ilanlar.
    shortlisted: int = 0
    #: Hazirliga alinan basvurular.
    prepared: int = 0
    #: Gonderilen basvurular.
    applied: int = 0
    #: Ulasilan gorusmeler.
    interview: int = 0
    #: Teklif (kabul dahil).
    offer: int = 0
    rejected: int = 0
    #: Onumuzdeki 7 gun icindeki son tarihler.
    upcoming_deadlines: int = 0
    #: Tamamlanan kariyer hazirligi (hikaye olusturma/guncelleme).
    career_prep: int = 0


class StudyReviewStats(BaseModel):
    minutes_by_area: dict[str, int]


class GithubReviewStats(BaseModel):
    commits: int
    repos: dict[str, int]


class FlashcardReviewStats(BaseModel):
    """Donemde tekrar edilen kart sayisi + deste kirilimi."""
    reviewed: int
    decks: dict[str, int]


class ReviewStats(BaseModel):
    todos: TodoReviewStats
    focus: FocusReviewStats
    topics: list[TopicReviewStats]
    habits: dict[str, int]
    capture: CaptureReviewStats
    applications: ApplicationReviewStats
    study: StudyReviewStats
    flashcards: FlashcardReviewStats
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
