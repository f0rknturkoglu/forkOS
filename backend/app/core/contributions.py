"""Gunluk emek haritasi (heatmap).

`event` tablosu HER SEYI yaziyor: worker'in cektigi feed'ler, sessizlesen
kaynaklar, hata kayitlari... Harita bunlarin hepsini sayarsa makinenin
calisma takvimini gosterir, KULLANICININ takvimini degil. Bu yuzden
asagida acikca sayilan fiiller var: hepsi bir insanin yaptigi bir is.

Yeni bir modul "bu da sayilsin" diyorsa fiilini buraya ekler.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

# Kategori -> o kategoriyi olusturan event fiilleri.
KINDS: dict[str, list[str]] = {
    "read":  ["rss.item_read", "rss.item_saved", "bookmark.saved", "bookmark.read"],
    "task":  ["todo.completed"],
    "focus": ["pomodoro.completed"],
    "routine": ["habit.checked"],
    "study": ["study.topic_completed", "review.completed",
              "book.finished", "course.completed"],
}

KIND_LABELS: dict[str, str] = {
    "read":  "okuma",
    "task":  "görev",
    "focus": "odak",
    "routine": "rutin",
    "study": "çalışma",
}

VERB_KIND: dict[str, str] = {
    verb: kind for kind, verbs in KINDS.items() for verb in verbs
}


def _kind_for(verb: str, routine: bool = False) -> str | None:
    if verb == "todo.completed" and routine:
        return "routine"
    return VERB_KIND.get(verb)


def _today() -> date:
    """Ayarlanan bolgedeki bugun."""
    return datetime.now(ZoneInfo(settings.timezone)).date()


async def heatmap(session: AsyncSession, *, days: int = 365) -> dict:
    """Son `days` gunun gunluk sayilari.

    Gun siniri `settings.timezone`'a gore; container UTC kostugu icin
    UTC'ye gore gruplarsak gece yarisindan sonraki is bir onceki gune duser.
    """
    start = _today() - timedelta(days=days - 1)
    rows = (
        (
            await session.execute(
                text(
                    "select (e.occurred_at at time zone :tz)::date as day,"
                    "       e.verb,"
                    "       (e.verb = 'habit.checked' or (e.verb = 'todo.completed' and ("
                    "         nullif(e.payload->>'recur', '') is not null or t.recur is not null"
                    "       ))) as routine, count(*) as n "
                    "from event e left join todo t on t.id = e.entity_id "
                    "where e.verb = any(:verbs) "
                    "  and (e.occurred_at at time zone :tz)::date >= :start "
                    "group by 1, 2, 3"
                ),
                {"verbs": list(VERB_KIND), "start": start, "tz": settings.timezone},
            )
        )
        .mappings()
        .all()
    )

    by_day: dict[str, dict] = {}
    for row in rows:
        day = row["day"].isoformat()
        entry = by_day.setdefault(day, {"day": day, "total": 0, "kinds": {}})
        kind = _kind_for(row["verb"], bool(row["routine"]))
        if kind is None:
            continue
        entry["total"] += row["n"]
        entry["kinds"][kind] = entry["kinds"].get(kind, 0) + row["n"]

    # Bos gunler de donsun: arayuz 365 kutuyu kendi uretmek zorunda kalmasin.
    series = []
    for offset in range(days):
        day = (start + timedelta(days=offset)).isoformat()
        series.append(by_day.get(day, {"day": day, "total": 0, "kinds": {}}))

    totals: dict[str, int] = {}
    for entry in by_day.values():
        for kind, count in entry["kinds"].items():
            totals[kind] = totals.get(kind, 0) + count

    active = [entry for entry in series if entry["total"] > 0]
    return {
        "days": series,
        "labels": KIND_LABELS,
        "totals": totals,
        "total": sum(totals.values()),
        "active_days": len(active),
        "best_day": max(series, key=lambda e: e["total"]) if active else None,
        "streak": _streak(series),
    }


def _streak(series: list[dict]) -> int:
    """Bugunden (ya da dunden) geriye kesintisiz aktif gun sayisi.

    Bugun henuz bos olabilir -- gun bitmedi; o yuzden seri dunden sayilir ve
    bugun doluysa bir eklenir. Yoksa her sabah "seri bozuldu" gorunurdu.
    """
    if not series:
        return 0
    today_active = series[-1]["total"] > 0
    count = 1 if today_active else 0
    for entry in reversed(series[:-1]):
        if entry["total"] == 0:
            break
        count += 1
    return count


async def day_detail(session: AsyncSession, day: date) -> dict:
    """Tek gunun dokumu: sayilan isler + o gunun tum hareketleri.

    Harita karesinden buraya geliniyor; "o kare neydi" sorusunun cevabi.
    Gun siniri yine `settings.timezone`.
    """
    rows = (
        (
            await session.execute(
                text(
                    "select e.id, e.entity_id, e.entity_type, e.verb, e.payload, e.occurred_at,"
                    "       (e.verb = 'habit.checked' or (e.verb = 'todo.completed' and ("
                    "         nullif(e.payload->>'recur', '') is not null or t.recur is not null"
                    "       ))) as routine "
                    "from event e left join todo t on t.id = e.entity_id "
                    "where (e.occurred_at at time zone :tz)::date = :day "
                    "order by e.occurred_at desc "
                    "limit 500"
                ),
                {"day": day, "tz": settings.timezone},
            )
        )
        .mappings()
        .all()
    )

    events = []
    kinds: dict[str, int] = {}
    for row in rows:
        event = dict(row)
        kind = _kind_for(event["verb"], bool(event.pop("routine")))
        event["kind"] = kind
        events.append(event)
        if kind:
            kinds[kind] = kinds.get(kind, 0) + 1

    return {
        "day": day.isoformat(),
        "events": events,
        "kinds": kinds,
        "labels": KIND_LABELS,
        "total": sum(kinds.values()),
        # Sayilmayanlar da gorunur ama ayri: worker gurultusu ile emek karismasin.
        "other": len(events) - sum(kinds.values()),
    }
