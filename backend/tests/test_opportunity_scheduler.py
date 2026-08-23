from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.modules.opportunity.worker import select_due_sources


@dataclass
class FakeSource:
    id: str
    interval_minutes: int


def test_due_sources_honor_each_adapter_interval_and_oldest_due_first():
    now = datetime(2026, 8, 23, 12, tzinfo=UTC)
    never = FakeSource("never", 360)
    overdue = FakeSource("overdue", 60)
    recent = FakeSource("recent", 30)
    latest = {
        "overdue": now - timedelta(minutes=90),
        "recent": now - timedelta(minutes=10),
    }

    assert select_due_sources([recent, overdue, never], latest, now=now) == [
        never,
        overdue,
    ]
