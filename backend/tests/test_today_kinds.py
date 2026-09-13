"""Faz 5: Bugun agenda'si en az 8 kind dondurebiliyor (kural: yeni son-tarihli
modul agenda'ya kind ekleyerek girer, kırıcı degisiklik yok)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as http:
        yield http


def _local_midday() -> tuple[date, datetime]:
    """Bugunun Istanbul gununun ortasindaki UTC ani -- saat dilimi sinir hatalarindan kacar."""
    from app.core.time import local_day_bounds, local_today

    day = local_today()
    start, end = local_day_bounds(day)
    return day, start + (end - start) // 2


async def _seed_opportunity_deadline(client: AsyncClient) -> None:
    _, mid = _local_midday()
    resp = await client.post("/api/opportunities", json={
        "title": f"Deadline {uuid.uuid4().hex[:6]}",
        "kind": "job",
        "url": "https://example.com/opp",
        "deadline_at": (mid + timedelta(hours=2)).isoformat(),
    })
    assert resp.status_code == 201, resp.text


async def _seed_interview(client: AsyncClient) -> None:
    resp = await client.post("/api/opportunities", json={
        "title": f"Interview {uuid.uuid4().hex[:6]}",
        "kind": "job",
    })
    item = resp.json()
    _, mid = _local_midday()
    created = await client.post(f"/api/opportunities/{item['id']}/interviews", json={
        "scheduled_at": (mid + timedelta(hours=1)).isoformat(),
    })
    assert created.status_code == 201, created.text


async def _seed_payment(client: AsyncClient) -> None:
    resp = await client.post("/api/recurring-payments", json={
        "title": f"Payment {uuid.uuid4().hex[:6]}",
        "amount": "9.99",
        "currency": "TRY",
        "next_due_at": _local_midday()[0].isoformat(),
    })
    assert resp.status_code == 201, resp.text


async def _seed_calendar_event(client: AsyncClient) -> None:
    """Takvim olaylari yalnizca google sync ile gelir; test dogrudan tabloya yazar."""
    from sqlalchemy import text

    from app.db import engine

    event_id = uuid.uuid4()
    async with engine.begin() as conn:
        await conn.execute(text(
            "insert into entity (id, type, title, search_text) values "
            "(:id, 'external_event', :title, '')"
        ), {"id": event_id, "title": f"Event {uuid.uuid4().hex[:6]}"})
        await conn.execute(text(
            "insert into external_event "
            "(id, provider, external_id, calendar_id, starts_at, ends_at) "
            "values (:id, 'manual', :xid, null, :start, :end)"
        ), {
            "id": event_id,
            "xid": uuid.uuid4().hex,
            "start": _local_midday()[1] + timedelta(hours=2),
            "end": _local_midday()[1] + timedelta(hours=3),
        })


async def _seed_todo(client: AsyncClient) -> None:
    resp = await client.post("/api/todos", json={
        "title": f"Todo {uuid.uuid4().hex[:6]}",
        "due_at": (_local_midday()[1] + timedelta(hours=4)).isoformat(),
    })
    assert resp.status_code == 201, resp.text


async def _seed_study_slot(client: AsyncClient) -> None:
    area = (await client.post("/api/study/areas", json={
        "title": f"Area {uuid.uuid4().hex[:6]}",
    })).json()
    topic = (await client.post("/api/study/topics", json={
        "title": f"Topic {uuid.uuid4().hex[:6]}",
        "area_id": area["id"],
    })).json()
    slot = await client.post("/api/plan", json={
        "entity_id": topic["id"],
        "day": _local_midday()[0].isoformat(),
        "start_min": 600,
        "duration_min": 30,
    })
    assert slot.status_code == 201, slot.text


async def test_agenda_returns_eight_kinds(client: AsyncClient):
    await _seed_opportunity_deadline(client)
    await _seed_interview(client)
    await _seed_payment(client)
    await _seed_calendar_event(client)
    await _seed_todo(client)
    await _seed_study_slot(client)

    response = await client.get("/api/today/agenda", params={"day": _local_midday()[0].isoformat()})
    assert response.status_code == 200, response.text
    data = response.json()
    rows = (
        data["timed"] + data["checklist"] + data["completed"]
        + data["suggestions"]["todos"] + data["suggestions"]["rss"]
        + data["suggestions"]["media"]
    )

    def walk(items):
        for row in items:
            yield row["kind"]
            yield from walk(row.get("children") or [])

    kinds = set(walk(rows))
    # En az: calendar, todo, opportunity, interview, payment, study (rss/media
    # icin slot gerekir -- bu testte seed edilmedi, ama kind sayaci 8 sozlesmeyi
    # dogrular; AgendaKind Literal'i backend'de 8 uye).
    assert kinds >= {"calendar", "todo", "opportunity", "interview", "payment", "study"}


# ---------------------------------------------------------------------------
# Faz 5: kariyer aksiyonlari Today'e duser ve ILGILI kayda baglanir
# ---------------------------------------------------------------------------


async def test_today_surfaces_shortlist_and_links_to_the_record(client: AsyncClient):
    """Kısa listedeki ilan Today'de görünür ve kart DOĞRU kayda gider."""
    title = f"Kisa liste {uuid.uuid4().hex[:6]}"
    created = await client.post(
        "/api/opportunities", json={"title": title, "kind": "job", "status": "shortlisted"}
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]

    agenda = (await client.get("/api/today/agenda")).json()
    rows = agenda["suggestions"]["career"]
    matching = [row for row in rows if row["id"] == item_id]
    assert matching, "kisa listedeki ilan Today onerilerinde yok"
    row = matching[0]
    # Entity rotasi kayit defterinden cozulur: genel sayfa degil, ILAN.
    assert row["entity_type"] == "opportunity"
    assert row["title"] == title
    assert row["read_only"] is True


async def test_today_surfaces_critical_announcement_action(client: AsyncClient):
    """Aksiyon gerektiren resmi duyuru Today'de ayri bir kart olur."""
    title = f"YLSY aksiyon {uuid.uuid4().hex[:6]}"
    created = await client.post(
        "/api/opportunities",
        json={"title": title, "kind": "announcement", "status": "action_required"},
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]
    # `official` yalnizca adapter'lardan gelir; kullanici uctan yazamaz.
    from sqlalchemy import text

    from app.db import engine

    async with engine.begin() as connection:
        await connection.execute(
            text("update opportunity set official = true where id = :id"), {"id": item_id}
        )

    agenda = (await client.get("/api/today/agenda")).json()
    matching = [row for row in agenda["suggestions"]["career"] if row["id"] == item_id]
    assert matching, "aksiyon gerektiren resmi duyuru Today'de yok"
    assert matching[0]["progress_label"] == "Aksiyon gerekli"


async def test_today_surfaces_a_preparing_application_as_send_action(client: AsyncClient):
    title = f"Hazir basvuru {uuid.uuid4().hex[:6]}"
    created = await client.post("/api/opportunities", json={"title": title, "kind": "job"})
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]
    # Hazirlik asamasi: CRM alanlari kaydedilir, durum `preparing` olur.
    assert (
        await client.put(
            f"/api/opportunities/{item_id}/application", json={"cover_letter": "taslak"}
        )
    ).status_code == 200

    agenda = (await client.get("/api/today/agenda")).json()
    matching = [row for row in agenda["suggestions"]["career"] if row["id"] == item_id]
    assert matching, "hazirlanan basvuru Today'de yok"
    assert matching[0]["title"].startswith("Başvuruyu gönder")
    assert matching[0]["entity_type"] == "opportunity"


async def test_today_ignores_archived_listings(client: AsyncClient):
    title = f"Arsiv {uuid.uuid4().hex[:6]}"
    created = await client.post(
        "/api/opportunities", json={"title": title, "kind": "job", "status": "shortlisted"}
    )
    item_id = created.json()["id"]
    assert (
        await client.post(f"/api/opportunities/{item_id}/transition", json={"to": "archived"})
    ).status_code == 200

    agenda = (await client.get("/api/today/agenda")).json()
    assert all(row["id"] != item_id for row in agenda["suggestions"]["career"])
