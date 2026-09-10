from collections.abc import Collection
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


def streak_stats(days: Collection[date], *, today: date) -> tuple[int, int]:
    """Kesintisiz gun serisi: (guncel, en uzun).

    Guncel seri BUGUNDEN ya da DUNDEN geriye sayilir: bugun henuz bos
    olabilir (gun bitmedi), o yuzden bugun bosSA seri dunden baslar --
    yoksa her sabah "seri bozuldu" gorunurdu.

    Emek haritasi (app/core/contributions.py) ve istatistik ozeti
    (app/modules/statistics) ayni kurali kullanir; iki kopya zamanla
    ayrisiyordu (biri tum event'leri, digeri yalnizca insan islerini
    sayiyordu), bu yuzden tek yerde.
    """
    unique = set(days)
    current = 0
    probe = today if today in unique else today - timedelta(days=1)
    while probe in unique:
        current += 1
        probe -= timedelta(days=1)

    longest = 0
    run = 0
    previous: date | None = None
    for day in sorted(unique):
        run = run + 1 if previous is not None and (day - previous).days == 1 else 1
        longest = max(longest, run)
        previous = day
    return current, longest
