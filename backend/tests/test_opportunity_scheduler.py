from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from app.modules.opportunity.worker import _error_message, select_due_sources

pytestmark = pytest.mark.no_database


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


def test_error_message_never_discards_exception_type():
    assert _error_message(RuntimeError()) == "RuntimeError"
    assert _error_message(RuntimeError("upstream failed")) == "RuntimeError: upstream failed"
