"""Hareket akisi filtreleri: her alan SUNUCUDA suzulur.

Emek haritasinin kategorileri ("bugun insan eliyle is yapildi mi?") ile akis
filtreleri ("bu kayit hangi alandan?") AYRI sorulardir; bu dosya ikincisinin
sozlesmesini kilitler. Uyarilar da buradadir: eskiden istemci yalnizca cekilen
sayfayi suzuyordu, sayfa disindaki uyari hic gorunmuyordu.

DB yoksa dosya atlanir; compose icinde `make test` ile kosar.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import get_args

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core import events as event_svc
from app.core.registry import all_event_verbs
from app.core.time import local_today
from app.db import SessionLocal, engine
from app.main import app

#: Her alandan TEMSILI bir fiil: filtre kendi alanini getirmeli, baskasini
#: getirmemeli. Id'ler kullanicinin gordugu ciplerle birebir ayni.
REPRESENTATIVE: dict[str, str] = {
    "tasks": "todo.completed",
    "focus": "pomodoro.completed",
    "learning": "study.topic_completed",
    "reading": "bookmark.saved",
    "career": "opportunity.status_changed",
    "system": "link.created",
}


async def _database_ready() -> bool:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("select 1 from event limit 1"))
        return True
    except Exception:
        return False


@pytest.fixture
async def client():
    if not await _database_ready():
        pytest.skip("Postgres yok veya migration calismamis (make up && make migrate)")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


async def _log(verb: str, payload: dict | None = None, *, at: datetime | None = None) -> None:
    """Temsili olay yaz. Uretim yolu log_event'tir; olay saati gerekirse geriye alinir."""
    async with SessionLocal() as session:
        event = await event_svc.log_event(session, verb=verb, payload=payload or {})
        if at is not None:
            event.occurred_at = at
        await session.commit()


async def _feed_verbs(client: AsyncClient, **params: object) -> set[str]:
    response = await client.get("/api/activity", params={"limit": 500, **params})
    assert response.status_code == 200, response.text
    return {row["verb"] for row in response.json()}


# --- model sozlesmesi (DB'siz) -------------------------------------------------


@pytest.mark.no_database
def test_filters_partition_the_verb_ledger() -> None:
    """Her kayitli fiil TAM BIR alana ait olmali.

    Yeni bir fiil ekleyen modul onu burada bir alana baglar; aksi halde kayit
    akista hicbir cipin altinda gorunmez (yalnizca "Tumu"nde kalir).
    """
    ledger = set(all_event_verbs())
    claimed = [verb for verbs in event_svc.ACTIVITY_FILTERS.values() for verb in verbs]
    assert len(claimed) == len(set(claimed)), "alan filtreleri ayrik olmali"
    assert set(claimed) == ledger


@pytest.mark.no_database
def test_filter_ids_are_closed() -> None:
    """Ucun kabul ettigi kimlikler modelle ayni: sessiz yok sayilan deger olmaz."""
    assert set(get_args(event_svc.ActivityFilterId)) == {
        "all",
        "alerts",
        *event_svc.ACTIVITY_FILTERS,
    }


@pytest.mark.no_database
def test_alert_rule_reads_payload_errors() -> None:
    """`source_sync.completed` hata tasiyorsa uyaridir; sifir hata uyari degil."""
    assert event_svc.is_alert("source_sync.completed", {"errors": 2}) is True
    assert event_svc.is_alert("source_sync.completed", {"errors": 0}) is False
    assert event_svc.is_alert("source_sync.completed", {}) is False
    assert event_svc.is_alert("rss.feed_failed", {}) is True
    assert event_svc.is_alert("todo.completed", {}) is False


# --- alan semantigi (DB) -------------------------------------------------------


@pytest.mark.parametrize("name", sorted(REPRESENTATIVE))
async def test_each_filter_returns_only_its_own_domain(client: AsyncClient, name: str) -> None:
    """Temsili kayitlar: filtre kendi alanini getirir, baska alanin kaydi sizmaz."""
    for verb in sorted({*REPRESENTATIVE.values(), "rss.feed_failed", "backup.created"}):
        await _log(verb, {"title": f"{verb} kaydi"})

    verbs = await _feed_verbs(client, filter=name)

    assert REPRESENTATIVE[name] in verbs
    assert verbs <= set(event_svc.ACTIVITY_FILTERS[name])


async def test_all_filter_is_the_unfiltered_feed(client: AsyncClient) -> None:
    await _log("todo.completed", {"title": "Gorev"})
    await _log("link.created", {"title": "Bag"})

    assert await _feed_verbs(client, filter="all") == {"todo.completed", "link.created"}
    assert await _feed_verbs(client) == {"todo.completed", "link.created"}


async def test_unknown_filter_is_rejected(client: AsyncClient) -> None:
    """Eski harita kategorisi kimligi sessizce yok sayilmaz."""
    response = await client.get("/api/activity", params={"filter": "task"})
    assert response.status_code == 422


# --- uyarilar ------------------------------------------------------------------


async def test_alerts_filter_finds_alerts_beyond_the_first_page(client: AsyncClient) -> None:
    """Asil hata buydu: uyari ilk sayfanin disinda kalirsa gorunmuyordu."""
    await _log("rss.feed_failed", {"message": "zaman asimi"}, at=datetime.now(UTC) - timedelta(days=2))
    for index in range(60):
        await _log("todo.completed", {"title": f"Gorev {index}"})

    assert "rss.feed_failed" not in await _feed_verbs(client, limit=50)
    assert await _feed_verbs(client, filter="alerts") == {"rss.feed_failed"}


async def test_alerts_filter_includes_error_carrying_sync(client: AsyncClient) -> None:
    await _log("source_sync.completed", {"errors": 3, "count": 12})
    await _log("source_sync.completed", {"errors": 0, "count": 5})

    assert await _feed_verbs(client, filter="alerts") == {"source_sync.completed"}

    unfiltered = (await client.get("/api/activity", params={"limit": 500})).json()
    assert len(unfiltered) == 2, "suzme yalnizca uyari sorusunda uygulanir"


async def test_feed_marks_alert_rows_on_the_server(client: AsyncClient) -> None:
    """Satir bayragi sunucudan gelir: istemci "hangi fiil uyaridir" listesi tutmaz."""
    await _log("media.sync_failed", {"source": "media:x"})
    await _log("todo.completed", {"title": "Normal"})

    response = await client.get("/api/activity", params={"limit": 50})
    flags = {row["verb"]: row["is_alert"] for row in response.json()}

    assert flags["media.sync_failed"] is True
    assert flags["todo.completed"] is False


async def test_day_detail_marks_alerts(client: AsyncClient) -> None:
    await _log("source.stalled", {"message": "sessizlesti"})

    body = (await client.get("/api/activity/day", params={"day": local_today().isoformat()})).json()
    stalled = next(row for row in body["events"] if row["verb"] == "source.stalled")

    assert stalled["is_alert"] is True
