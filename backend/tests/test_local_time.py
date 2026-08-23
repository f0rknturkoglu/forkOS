from datetime import UTC, date, datetime

import pytest

from app.core.time import local_datetime, local_day_bounds, local_today

pytestmark = pytest.mark.no_database


def test_local_day_bounds_are_istanbul_midnights_in_utc() -> None:
    start, end = local_day_bounds(date(2026, 1, 15))

    assert start == datetime(2026, 1, 14, 21, tzinfo=UTC)
    assert end == datetime(2026, 1, 15, 21, tzinfo=UTC)


def test_utc_instant_after_istanbul_midnight_belongs_to_next_day() -> None:
    instant = datetime(2026, 1, 14, 21, 30, tzinfo=UTC)

    assert local_today(instant) == date(2026, 1, 15)


def test_local_datetime_preserves_wall_clock_time_and_offset() -> None:
    value = local_datetime(date(2026, 1, 15), 9 * 60 + 5)

    assert value.isoformat() == "2026-01-15T09:05:00+03:00"


@pytest.mark.parametrize("minute", [-1, 1440])
def test_local_datetime_rejects_minutes_outside_a_day(minute: int) -> None:
    with pytest.raises(ValueError, match="minute"):
        local_datetime(date(2026, 1, 15), minute)
