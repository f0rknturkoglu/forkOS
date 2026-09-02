from __future__ import annotations

from pydantic import BaseModel


class CounterBreakdown(BaseModel):
    """Bir sayacin uc zaman dilimi: bugun (app gunu), son 7 gun, tum zamanlar."""

    today: int
    week: int
    total: int


class StreakOut(BaseModel):
    current: int
    longest: int


class StatisticsSummary(BaseModel):
    """Keyfi verb ailesine gore sayaclar: family adi -> dilimler."""

    counters: dict[str, CounterBreakdown]
    applications: CounterBreakdown
    streak: StreakOut


class MonthlyPoint(BaseModel):
    month: str  # "YYYY-MM"
    pomodoros: int
    todos: int
    bookmarks: int
    notes: int
    rss_read: int
    reviews: int
