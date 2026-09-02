from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.modules.statistics.schemas import CounterBreakdown, MonthlyPoint, StatisticsSummary, StreakOut

#: Sayac adi -> sayan event verb'u. Bu liste bittikce buyur; isimler API sozlesmesi.
VERB_COUNTERS: dict[str, str] = {
    "pomodoros": "pomodoro.completed",
    "todos": "todo.completed",
    "bookmarks": "bookmark.saved",
    "notes": "note.created",
    "rss_read": "rss.item_read",
    "reviews": "review.completed",
    "courses": "course.completed",
}

_MONTHS = 6


def _day_counts_sql(families: list[str]) -> str:
    """Son 6 ayin gun gun sayaclarini tek sorguda toplar.

    `at time zone :tz` app gunune cevirir (plan: Europe/Istanbul). FILTER
    yan taraflari dogrudan dize birlestirilir -- sayac adlari kod sabitidir,
    kullanici girdisi degil.
    """
    selects = "\n    ,".join(
        f"count(*) filter (where verb = '{verb}') as {name}" for name, verb in families
    )
    return f"""
        select
            (occurred_at at time zone :tz)::date as day
            ,{selects}
        from event
        where occurred_at >= now() - interval '{_MONTHS} months'
        group by day
    """


def _buckets(rows: list[dict], today: date, week_start: datetime, names: list[str]) -> dict[str, CounterBreakdown]:
    """Gun satirlarini today/week/total dilimlerine dagitir."""
    out: dict[str, CounterBreakdown] = {}
    for name in names:
        today_total = sum(int(row[name]) for row in rows if row["day"] == today)
        week_total = sum(int(row[name]) for row in rows if row["day"] >= week_start.date())
        total = sum(int(row[name]) for row in rows)
        out[name] = CounterBreakdown(today=today_total, week=week_total, total=total)
    return out


def _streak(days: list[date], today: date) -> StreakOut:
    """Kesintisiz gun serisi. Bugun hareket yoksa seri dunyadan sayilir."""
    unique = set(days)
    current = 0
    probe = today if today in unique else today - timedelta(days=1)
    while probe in unique:
        current += 1
        probe -= timedelta(days=1)
    longest = 0
    run = 0
    prev: date | None = None
    for day in sorted(unique):
        run = run + 1 if prev is not None and (day - prev).days == 1 else 1
        longest = max(longest, run)
        prev = day
    return StreakOut(current=current, longest=longest)


async def summary(session: AsyncSession) -> StatisticsSummary:
    tz = ZoneInfo(settings.timezone)
    now = datetime.now(tz)
    today = now.date()
    week_start = now - timedelta(days=7)

    families = list(VERB_COUNTERS.items())
    names = [name for name, _ in families]
    rows = [
        dict(row)
        for row in (
            await session.execute(
                text(_day_counts_sql(families)),
                {"tz": settings.timezone},
            )
        ).mappings()
    ]
    counters = _buckets(rows, today, week_start, names)

    day_rows = (
        await session.execute(
            text("select distinct (occurred_at at time zone :tz)::date as day from event"),
            {"tz": settings.timezone},
        )
    ).scalars().all()

    # Basvuru sayaci event'ten degil opportunity.applied_at'ten gelir (kural 3'e
    # ek veri: basvuru bir durum gecisi, her gecis ayni kaydi event'e yazmaz).
    app_total = (
        await session.execute(
            text("select count(*) from opportunity where applied_at is not null and trashed_at is null")
        )
    ).scalar_one()
    app_week = (
        await session.execute(
            text(
                "select count(*) from opportunity "
                "where applied_at is not null and applied_at >= now() - interval '7 days' "
                "and trashed_at is null"
            )
        )
    ).scalar_one()
    app_today = (
        await session.execute(
            text(
                "select count(*) from opportunity "
                "where applied_at is not null "
                "and (applied_at at time zone :tz)::date = :today "
                "and trashed_at is null"
            ),
            {"tz": settings.timezone, "today": today},
        )
    ).scalar_one()

    return StatisticsSummary(
        counters=counters,
        applications=CounterBreakdown(today=int(app_today), week=int(app_week), total=int(app_total)),
        streak=_streak(list(day_rows), today),
    )


async def monthly(session: AsyncSession, months: int) -> list[MonthlyPoint]:
    tz = ZoneInfo(settings.timezone)
    now = datetime.now(tz)

    rows = [
        dict(row)
        for row in (
            await session.execute(
                text(
                    "select to_char(occurred_at at time zone :tz, 'YYYY-MM') as month\n"
                    "    ,count(*) filter (where verb = 'pomodoro.completed') as pomodoros\n"
                    "    ,count(*) filter (where verb = 'todo.completed') as todos\n"
                    "    ,count(*) filter (where verb = 'bookmark.saved') as bookmarks\n"
                    "    ,count(*) filter (where verb = 'note.created') as notes\n"
                    "    ,count(*) filter (where verb = 'rss.item_read') as rss_read\n"
                    "    ,count(*) filter (where verb = 'review.completed') as reviews\n"
                    "from event\n"
                    f"where occurred_at >= now() - interval '{months + 1} months'\n"
                    "group by month"
                ),
                {"tz": settings.timezone},
            )
        ).mappings()
    ]
    by_month = {row["month"]: row for row in rows}

    points: list[MonthlyPoint] = []
    cursor = date(now.year, now.month, 1)
    for _ in range(months):
        key = cursor.strftime("%Y-%m")
        row = by_month.get(key)
        points.append(
            MonthlyPoint(
                month=key,
                pomodoros=int(row["pomodoros"]) if row else 0,
                todos=int(row["todos"]) if row else 0,
                bookmarks=int(row["bookmarks"]) if row else 0,
                notes=int(row["notes"]) if row else 0,
                rss_read=int(row["rss_read"]) if row else 0,
                reviews=int(row["reviews"]) if row else 0,
            )
        )
        cursor = (cursor - timedelta(days=1)).replace(day=1)
    points.reverse()
    return points
