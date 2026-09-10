"""Istatistik modulu testleri: event toplamlari + seri hesabi.

HTTP ucu uzerinden dogrulanir; veri kurulumu DB helper'lariyla (log_event /
create_entity) yapilir. DB testleri truncate edilen temiz semada calisir.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core import contributions
from app.core.entity import create_entity
from app.core.events import log_event
from app.db import SessionLocal
from app.main import app
from app.modules.statistics import service

pytestmark = pytest.mark.asyncio


async def _database_ready() -> bool:
    try:
        async with SessionLocal() as session:
            await session.execute(text("select 1"))
        return True
    except Exception:
        return False


@pytest.fixture
async def client():
    if not await _database_ready():
        pytest.skip("Postgres yok veya migration calismamis")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


async def _seed(verbs: list[str], *, payload: dict | None = None) -> uuid.UUID:
    """Tek entity + verilen verb'lerde event; entity id'sini dondurur."""
    async with SessionLocal() as session:
        entity = await create_entity(session, type="todo", title="örnek")
        for verb in verbs:
            await log_event(
                session, verb=verb, entity_type="todo", entity_id=entity.id, payload=payload
            )
        await session.commit()
        return entity.id


async def test_summary_buckets_and_verb_families(client: AsyncClient) -> None:
    await _seed(["pomodoro.completed"] * 2 + ["todo.completed"] * 3 + ["bookmark.saved"])

    response = await client.get("/api/statistics/summary")
    assert response.status_code == 200
    body = response.json()
    counters = body["counters"]
    assert counters["pomodoros"]["total"] == 2
    assert counters["todos"]["total"] == 3
    assert counters["bookmarks"]["total"] == 1
    assert counters["notes"]["total"] == 0
    # Bugun eklenen her event bugun dilimine girer.
    assert counters["pomodoros"]["today"] == 2
    assert counters["pomodoros"]["week"] == 2
    # Streak: tek gun -> en az 1.
    assert body["streak"]["current"] >= 1
    assert body["streak"]["longest"] >= 1
    # Basvuru sayaci: opportunity satiri yok -> sifir.
    assert body["applications"]["total"] == 0


async def test_application_counter_reads_opportunity_table(client: AsyncClient) -> None:
    async with SessionLocal() as session:
        entity = await create_entity(session, type="opportunity", title="fırsat")
        await session.execute(
            text(
                "insert into opportunity (id, kind, status, applied_at) "
                "values (:id, 'job', 'applied', now())"
            ),
            {"id": entity.id},
        )
        await session.commit()

    response = await client.get("/api/statistics/summary")
    body = response.json()
    assert body["applications"]["total"] == 1
    assert body["applications"]["week"] == 1
    assert body["applications"]["today"] == 1


async def test_monthly_fills_gaps_with_zeroes(client: AsyncClient) -> None:
    await _seed(["pomodoro.completed"])

    response = await client.get("/api/statistics/monthly", params={"months": 6})
    assert response.status_code == 200
    points = response.json()
    assert len(points) == 6
    assert points[-1]["pomodoros"] == 1  # bu ay
    assert all(p["pomodoros"] == 0 for p in points[:-1])  # gecmis aylar sifirli
    keys = [p["month"] for p in points]
    assert keys == sorted(keys)
    assert len(set(keys)) == 6


async def test_streak_current_and_longest(client: AsyncClient) -> None:
    # Bugun + dun + onceki gun event at (3 gunluk seri); 5 gun once ayri parca.
    async with SessionLocal() as session:
        entity = await create_entity(session, type="todo", title="örnek")
        today = datetime.now(UTC).date()
        for offset in (0, 1, 2, 5):
            day = today - timedelta(days=offset)
            await session.execute(
                text(
                    "insert into event (entity_id, entity_type, verb, occurred_at) "
                    "values (:e, 'todo', 'todo.completed', :at)"
                ),
                {"e": entity.id, "at": datetime(day.year, day.month, day.day, 12, 0, tzinfo=UTC)},
            )
        await session.commit()

    response = await client.get("/api/statistics/summary")
    body = response.json()
    assert body["streak"]["current"] == 3
    assert body["streak"]["longest"] == 3


@pytest.mark.no_database
async def test_every_heatmap_verb_has_a_counter() -> None:
    """Emek haritasinin saydigi HER fiilin istatistikte bir sayaci olmali.

    Yoksa harita o gun yanarken istatistik "0" gosterir; iki ekran ayni gunu
    farkli anlatir (bu test o ayrisimi yakalar).
    """
    heatmap_verbs = set(contributions.VERB_KIND)
    counter_verbs = set(service.VERB_COUNTERS.values())

    assert heatmap_verbs - counter_verbs == set()


async def test_new_human_actions_feed_their_counters(client: AsyncClient) -> None:
    """Haritaya yeni giren insan eylemleri sayaclara da yansimali.

    Medya POZITIF miktarla verilir: harita da yalnizca pozitif tuketimi sayar
    (eslesme ayri testte dogrulanir).
    """
    await _seed(
        ["habit.checked", "study.topic_completed", "flashcard.reviewed"]
    )
    await _seed(["media.consumed"], payload={"amount": 2})

    counters = (await client.get("/api/statistics/summary")).json()["counters"]

    assert counters["media"]["today"] == 1
    assert counters["routines"]["today"] == 1
    assert counters["studies"]["today"] == 1
    assert counters["flashcards"]["today"] == 1


async def test_media_counter_matches_heatmap_positive_amount_rule(client: AsyncClient) -> None:
    """Negatif/miktarsiz tuketim haritada sayilmaz; sayacta da sayilmamali."""
    async with SessionLocal() as session:
        entity = await create_entity(session, type="media", title="dizi")
        await log_event(session, verb="media.consumed", entity_id=entity.id,
                        entity_type="media", payload={"amount": -3})
        await log_event(session, verb="media.consumed", entity_id=entity.id,
                        entity_type="media", payload={})
        await log_event(session, verb="media.consumed", entity_id=entity.id,
                        entity_type="media", payload={"amount": 2})
        await session.commit()

        heatmap = await contributions.heatmap(session, days=7)

    counters = (await client.get("/api/statistics/summary")).json()["counters"]
    assert counters["media"]["today"] == 1
    assert heatmap["days"][-1]["kinds"].get("media", 0) == 1


async def test_streak_counts_only_human_work(client: AsyncClient) -> None:
    """Yalnizca worker kaydi olan gunler seri SAYILMAZ -- harita ile ayni kume."""
    async with SessionLocal() as session:
        entity = await create_entity(session, type="feed", title="besleme")
        today = datetime.now(UTC).date()
        for offset in (0, 1, 2):
            day = today - timedelta(days=offset)
            await session.execute(
                text(
                    "insert into event (entity_id, entity_type, verb, occurred_at) "
                    "values (:e, 'feed', 'source_sync.completed', :at)"
                ),
                {"e": entity.id, "at": datetime(day.year, day.month, day.day, 12, 0, tzinfo=UTC)},
            )
        await session.commit()

    body = (await client.get("/api/statistics/summary")).json()
    assert body["streak"]["current"] == 0
    assert body["streak"]["longest"] == 0


async def test_monthly_reports_applications(client: AsyncClient) -> None:
    async with SessionLocal() as session:
        entity = await create_entity(session, type="opportunity", title="fırsat")
        await session.execute(
            text(
                "insert into opportunity (id, kind, status, applied_at) "
                "values (:id, 'job', 'applied', now())"
            ),
            {"id": entity.id},
        )
        await session.commit()

    points = (await client.get("/api/statistics/monthly", params={"months": 6})).json()

    assert points[-1]["applications"] == 1
    assert all(point["applications"] == 0 for point in points[:-1])
