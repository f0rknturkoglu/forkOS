from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core import contributions
from app.core.time import streak_stats
from app.modules.statistics.schemas import (
    CounterBreakdown,
    MonthlyPoint,
    StatisticsSummary,
    StreakOut,
)

#: Sayac adi -> sayan event verb'u. Isimler API sozlesmesi.
#:
#: Kural: EMEK HARITASININ saydigi her fiilin burada bir sayaci olmali
#: (`tests/test_statistics.py` bunu kod taramasindan gecirir). Yoksa harita o
#: gun yanarken istatistik "0" gosterir; iki ekran ayni gunu farkli anlatir.
#: Asagidaki kategori yorumlari contributions.KINDS ile birebir aynidir.
VERB_COUNTERS: dict[str, str] = {
    # odak
    "pomodoros": "pomodoro.completed",
    # gorev
    "todos": "todo.completed",
    # rutin
    "routines": "habit.checked",
    # okuma
    "bookmarks": "bookmark.saved",
    "bookmark_reads": "bookmark.read",
    "rss_read": "rss.item_read",
    "rss_saved": "rss.item_saved",
    # calisma
    "reviews": "review.completed",
    "studies": "study.topic_completed",
    "books": "book.finished",
    "courses": "course.completed",
    # medya
    "media": "media.consumed",
    # haritada olmayan ek insan eylemleri
    "notes": "note.created",
    "flashcards": "flashcard.reviewed",
}

#: Sayacin ek SQL kosulu (verilmeyenler yalnizca verb eslesmesiyle sayilir).
#: Medya tuketimi haritayla ayni kurala uyar: yalnizca POZITIF miktar.
COUNTER_FILTERS: dict[str, str] = {"media": contributions.POSITIVE_MEDIA_SQL}

_MONTHS = 6


def _day_counts_sql(families: list[tuple[str, str]]) -> str:
    """Son 6 ayin gun gun sayaclarini tek sorguda toplar.

    `at time zone :tz` app gunune cevirir (plan: Europe/Istanbul). FILTER
    yan taraflari dogrudan dize birlestirilir -- sayac adlari ve ek kosullar
    kod sabitidir, kullanici girdisi degil. Event tablosu `e` alias'i ile
    kullanilir cunku ek kosullar (bkz. COUNTER_FILTERS) bu alias'a yazilmistir.
    """
    selects = "\n    ,".join(
        f"count(*) filter (where e.verb = '{verb}'"
        + (f" and ({COUNTER_FILTERS[name]})" if name in COUNTER_FILTERS else "")
        + f") as {name}"
        for name, verb in families
    )
    return f"""
        select
            (e.occurred_at at time zone :tz)::date as day
            ,{selects}
        from event e
        where e.occurred_at >= now() - interval '{_MONTHS} months'
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


async def summary(session: AsyncSession) -> StatisticsSummary:
    tz = ZoneInfo(settings.timezone)
    now = datetime.now(tz)
    today = now.date()
    week_start = now - timedelta(days=7)

    families = [(name, verb) for name, verb in VERB_COUNTERS.items() if name != "pomodoros"]
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
    focus_rows = [dict(row) for row in (await session.execute(text(
        "select (started_at at time zone :tz)::date as day, count(*) as pomodoros "
        "from pomodoro_session where kind = 'focus' and ended_at is not null "
        f"and started_at >= now() - interval '{_MONTHS} months' group by 1"
    ), {"tz": settings.timezone})).mappings()]
    counters.update(_buckets(focus_rows, today, week_start, ["pomodoros"]))

    # Seri YALNIZCA insan eliyle yapilan islerden sayilir: haritanin filtre
    # Filtresiyle ayni kume (contributions.COUNTED_VERBS). Tum event'leri
    # saymak, worker'in kostugu gunu "seri" gibi gosteriyordu.
    current, longest = streak_stats(await contributions.active_days(session), today=today)

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
        applications=CounterBreakdown(
            today=int(app_today), week=int(app_week), total=int(app_total)
        ),
        streak=StreakOut(current=current, longest=longest),
    )


async def monthly(session: AsyncSession, months: int) -> list[MonthlyPoint]:
    tz = ZoneInfo(settings.timezone)
    now = datetime.now(tz)

    rows = [
        dict(row)
        for row in (
            await session.execute(
                text(
                    "select to_char(e.occurred_at at time zone :tz, 'YYYY-MM') as month\n"
                    "    ,0 as pomodoros\n"
                    "    ,count(*) filter (where e.verb = 'todo.completed') as todos\n"
                    "    ,count(*) filter (where e.verb = 'bookmark.saved') as bookmarks\n"
                    "    ,count(*) filter (where e.verb = 'note.created') as notes\n"
                    "    ,count(*) filter (where e.verb = 'rss.item_read') as rss_read\n"
                    "    ,count(*) filter (where e.verb = 'review.completed') as reviews\n"
                    "from event e\n"
                    f"where e.occurred_at >= now() - interval '{months + 1} months'\n"
                    "group by month"
                ),
                {"tz": settings.timezone},
            )
        ).mappings()
    ]
    by_month = {row["month"]: row for row in rows}

    focus_rows = (await session.execute(text(
        "select to_char(started_at at time zone :tz, 'YYYY-MM') as month, count(*) as n "
        "from pomodoro_session where kind = 'focus' and ended_at is not null "
        f"and started_at >= now() - interval '{months + 1} months' group by 1"
    ), {"tz": settings.timezone})).all()
    for row in by_month.values():
        row["pomodoros"] = 0
    for month, count in focus_rows:
        row = by_month.setdefault(month, dict.fromkeys(
            ["pomodoros", "todos", "bookmarks", "notes", "rss_read", "reviews"], 0))
        row["pomodoros"] = count

    # Basvurular event'ten gelmez (kural 3 ek verisi: applied_at kolonu);
    # aylik kirilim o yuzden ayri sorgudan okunur.
    app_rows = [
        dict(row)
        for row in (
            await session.execute(
                text(
                    "select to_char(applied_at at time zone :tz, 'YYYY-MM') as month"
                    "    ,count(*) as applications from opportunity"
                    " where applied_at is not null and trashed_at is null"
                    f"   and applied_at >= now() - interval '{months + 1} months'"
                    " group by month"
                ),
                {"tz": settings.timezone},
            )
        ).mappings()
    ]
    apps_by_month = {row["month"]: int(row["applications"]) for row in app_rows}

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
                applications=apps_by_month.get(key, 0),
            )
        )
        cursor = (cursor - timedelta(days=1)).replace(day=1)
    points.reverse()
    return points
