"""Gunluk emek haritasi (heatmap).

`event` tablosu HER SEYI yaziyor: worker'in cektigi feed'ler, sessizlesen
kaynaklar, hata kayitlari... Harita bunlarin hepsini sayarsa makinenin
calisma takvimini gosterir, KULLANICININ takvimini degil. Bu yuzden
asagida acikca sayilan fiiller var: hepsi bir insanin yaptigi bir is.

Yeni bir modul "bu da sayilsin" diyorsa fiilini buraya ekler.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.events import is_alert
from app.core.time import local_today, streak_stats

# Kategori -> o kategoriyi olusturan event fiilleri.
KINDS: dict[str, list[str]] = {
    "read":  ["rss.item_read", "rss.item_saved", "bookmark.saved", "bookmark.read"],
    "task":  ["todo.completed"],
    "focus": ["pomodoro.completed"],
    "routine": ["habit.checked"],
    "study": ["study.topic_completed", "review.completed",
              "book.finished", "course.completed",
              # Kart tekrari da calismadir: Anki oturumu gunu yesillendirir.
              "flashcard.reviewed"],
    "media": ["media.consumed"],
}

KIND_LABELS: dict[str, str] = {
    "read":  "okuma",
    "task":  "görev",
    "focus": "odak",
    "routine": "rutin",
    "study": "çalışma",
    "media": "medya",
}

VERB_KIND: dict[str, str] = {
    verb: kind for kind, verbs in KINDS.items() for verb in verbs
}

#: Sayilan fiillerin kumesi -- tek sorgu sozlesmesi (heatmap, sayaclar, gun dokumu).
COUNTED_VERBS: list[str] = list(VERB_KIND)

#: Medya ILERLEMESI negatif de olabilir (geri alma); yalnizca pozitif tuketim
#: "bugun su kadar izledim" demektir. Fragment `e` alias'li event tablosu bekler.
POSITIVE_MEDIA_SQL = """
jsonb_typeof(e.payload) = 'object'
and jsonb_typeof(e.payload->'amount') = 'number'
and (e.payload->>'amount')::numeric > 0
""".strip()

#: Sayilan islerin ORTAK where parcasi. `:verbs` parametresi ve `e` alias'i sart.
COUNTED_WHERE = (
    "e.verb = any(:verbs) and (e.verb <> 'media.consumed' or (" + POSITIVE_MEDIA_SQL + "))"
)


def _kind_for(
    verb: str,
    routine: bool = False,
    *,
    positive_media_consumption: bool = False,
) -> str | None:
    if verb == "todo.completed" and routine:
        return "routine"
    if verb == "media.consumed":
        return "media" if positive_media_consumption else None
    return VERB_KIND.get(verb)


def _today() -> date:
    """Ayarlanan bolgedeki bugun -- tek kaynak app.core.time (Faz 14)."""
    return local_today()


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
                    f"where {COUNTED_WHERE} "
                    "  and (e.occurred_at at time zone :tz)::date >= :start "
                    "group by 1, 2, 3"
                ),
                {"verbs": COUNTED_VERBS, "start": start, "tz": settings.timezone},
            )
        )
        .mappings()
        .all()
    )

    by_day: dict[str, dict] = {}
    for row in rows:
        day = row["day"].isoformat()
        entry = by_day.setdefault(day, {"day": day, "total": 0, "kinds": {}})
        kind = _kind_for(
            row["verb"],
            bool(row["routine"]),
            positive_media_consumption=row["verb"] == "media.consumed",
        )
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
    current, _longest = streak_stats(
        [date.fromisoformat(entry["day"]) for entry in active], today=_today()
    )
    return {
        "days": series,
        "labels": KIND_LABELS,
        "totals": totals,
        "total": sum(totals.values()),
        "active_days": len(active),
        "best_day": max(series, key=lambda e: e["total"]) if active else None,
        "streak": current,
    }


async def active_days(session: AsyncSession, *, since: date | None = None) -> set[date]:
    """Insan eliyle is yapilmis gunler -- heatmap ile AYNI filtre.

    Istatistik ozeti seriyi buradan hesaplar; daha once tum event'leri
    sayiyordu, bu yuzden yalnizca worker'in kostugu bir gun istatistikte
    "seri var" derken harita bos gorunuyordu.
    """
    params: dict[str, object] = {"verbs": COUNTED_VERBS, "tz": settings.timezone}
    where = COUNTED_WHERE
    if since is not None:
        where += " and (e.occurred_at at time zone :tz)::date >= :since"
        params["since"] = since
    rows = (
        await session.execute(
            text(f"select distinct (e.occurred_at at time zone :tz)::date as day from event e where {where}"),
            params,
        )
    ).scalars().all()
    return set(rows)


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
                    "       ))) as routine, "
                    f"       (e.verb = 'media.consumed' and ({POSITIVE_MEDIA_SQL})) as positive_media_consumption "
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
        kind = _kind_for(
            event["verb"],
            bool(event.pop("routine")),
            positive_media_consumption=bool(
                event.pop("positive_media_consumption")
            ),
        )
        event["kind"] = kind
        # Uyari kurali tek kaynaktan (core/events.is_alert) gelir: gun sayfasi
        # da istemcide "hangi fiil uyaridir" listesi TUTMAZ.
        event["is_alert"] = is_alert(event["verb"], event["payload"])
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
