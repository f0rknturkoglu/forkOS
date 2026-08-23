from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.config import settings


def local_zone() -> ZoneInfo:
    return ZoneInfo(settings.timezone)


def local_now() -> datetime:
    return datetime.now(local_zone())


def local_today(at: datetime | None = None) -> date:
    value = at or local_now()
    if value.tzinfo is None:
        raise ValueError("at timezone-aware olmalı")
    return value.astimezone(local_zone()).date()


def local_day_bounds(day: date) -> tuple[datetime, datetime]:
    start = local_datetime(day).astimezone(UTC)
    end = local_datetime(day + timedelta(days=1)).astimezone(UTC)
    return start, end


def local_datetime(day: date, minute: int = 0) -> datetime:
    if minute < 0 or minute >= 24 * 60:
        raise ValueError("minute 0 ile 1439 arasında olmalı")
    wall_time = time(hour=minute // 60, minute=minute % 60)
    return datetime.combine(day, wall_time, tzinfo=local_zone())
