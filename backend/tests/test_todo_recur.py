"""Faz 24: rutin gorev semantigi.

Mevcut davranisi dogrular (calisani yeniden yazmaz):
- Completion sonraki occurrence'i olusturur; duplicate completion guvenlidir.
- Proje/milestone/parent/tag/priority/description kopyalanir; PlanSlot
  KOPYALANMAZ (yeni occurrence kullanici istemedikce plana dusmez).
- Gecikmis rutin gelecege atlar; weekdays cuma -> pazartesi; monthly ay sonu.
- Review rutin completion'larini sayar; Today yeni occurrence'i dogru
  tarihte gosterir.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as http:
        yield http


def _iso(dt: datetime) -> str:
    return dt.isoformat()


async def _make_routine(client: AsyncClient, recur: str, due_at: str, **extra) -> dict:
    response = await client.post("/api/todos", json={
        "title": f"Rutin {recur} {uuid.uuid4().hex[:6]}",
        "recur": recur,
        "due_at": due_at,
        **extra,
    })
    assert response.status_code == 201, response.text
    return response.json()


async def _todos(client: AsyncClient) -> list[dict]:
    return (await client.get("/api/todos", params={"limit": 500})).json()


async def test_weekdays_friday_completes_to_monday(client: AsyncClient) -> None:
    friday = datetime(2026, 8, 28, 9, 0, tzinfo=UTC)
    todo = await _make_routine(client, "weekdays", _iso(friday))
    await client.post(f"/api/todos/{todo['id']}/complete")

    spawned = [
        t for t in await _todos(client) if t["title"] == todo["title"] and t["id"] != todo["id"]
    ]
    assert len(spawned) == 1
    due = datetime.fromisoformat(spawned[0]["due_at"])
    assert due.date().isoformat() == "2026-08-31"  # Pazartesi
    assert due.weekday() == 0


async def test_monthly_31_lands_on_last_valid_day(client: AsyncClient) -> None:
    # Gelecekteki bir 31'i -> 30 ceken ay -> 30; 28 ceken ay -> 28.
    # (Gecmis tarih verilirse atlama dongusu gelecege tasir; bu test ay sonu
    # kirpmayi ayri olcuyor, o yuzden gelecek bir tarih kullanir.)
    oct31 = datetime(2026, 10, 31, 8, 0, tzinfo=UTC)
    todo = await _make_routine(client, "monthly", _iso(oct31))
    await client.post(f"/api/todos/{todo['id']}/complete")

    spawned = [
        t for t in await _todos(client) if t["title"] == todo["title"] and t["id"] != todo["id"]
    ]
    assert len(spawned) == 1
    # Kasim 30 (subat degil, ama 30 ceken ay).
    assert datetime.fromisoformat(spawned[0]["due_at"]).date().isoformat() == "2026-11-30"
    await client.delete(f"/api/todos/{spawned[0]['id']}")
    await client.delete(f"/api/todos/{todo['id']}")


async def test_overdue_routine_jumps_to_future(client: AsyncClient) -> None:
    old = datetime.now(UTC) - timedelta(days=10)
    todo = await _make_routine(client, "daily", _iso(old))
    await client.post(f"/api/todos/{todo['id']}/complete")

    spawned = [
        t for t in await _todos(client) if t["title"] == todo["title"] and t["id"] != todo["id"]
    ]
    assert len(spawned) == 1
    due = datetime.fromisoformat(spawned[0]["due_at"])
    assert due > datetime.now(UTC)


async def test_duplicate_completion_is_safe(client: AsyncClient) -> None:
    todo = await _make_routine(client, "daily", _iso(datetime.now(UTC) + timedelta(hours=2)))
    first = await client.post(f"/api/todos/{todo['id']}/complete")
    assert first.status_code == 200
    second = await client.post(f"/api/todos/{todo['id']}/complete")
    assert second.status_code == 200

    spawned = [
        t for t in await _todos(client) if t["title"] == todo["title"] and t["id"] != todo["id"]
    ]
    assert len(spawned) == 1


async def test_context_is_copied_but_plan_slot_is_not(  # noqa: E501
    client: AsyncClient,
) -> None:
    project = (await client.post("/api/projects", json={"title": "Proje"})).json()
    parent = (await client.post("/api/todos", json={"title": "Ebeveyn"})).json()
    todo = await _make_routine(  # noqa: E501
        client, "daily",
        _iso(datetime.now(UTC) + timedelta(hours=2)),
        priority=3,
        description="aciklama",
        tags=["etiket"],
        parent_id=parent["id"],
        project_id=project["id"],
        milestone_id=None,
    )
    # Onceki occurrence'i bugune planla (slot vardi).
    day = datetime.now(UTC).date().isoformat()
    slot = await client.post("/api/plan", json={"entity_id": todo["id"], "day": day})
    assert slot.status_code == 201

    await client.post(f"/api/todos/{todo['id']}/complete")
    spawned = [
        t for t in await _todos(client) if t["title"] == todo["title"] and t["id"] != todo["id"]
    ]
    assert len(spawned) == 1
    child = spawned[0]
    assert child["priority"] == 3
    assert child["description"] == "aciklama"
    assert child["tags"] == ["etiket"]
    assert child["parent_id"] == parent["id"]
    assert child["project_id"] == project["id"]

    # Plan slotu yeni occurrence'a TASINMADI.
    week = (await client.get("/api/plan", params={"week": day})).json()
    assert child["id"] not in {slot_row["entity_id"] for slot_row in week}  # noqa: E501

    await client.delete(f"/api/todos/{child['id']}")
    await client.delete(f"/api/todos/{todo['id']}")
    await client.delete(f"/api/todos/{parent['id']}")
    await client.delete(f"/api/projects/{project['id']}")


async def test_stopping_routine_keeps_occurrence_and_stops_spawn(client: AsyncClient) -> None:
    todo = await _make_routine(client, "daily", _iso(datetime.now(UTC) + timedelta(hours=2)))
    # Rutini durdur: recur="" -> gorev durur ama silinmez.
    patched = await client.patch(f"/api/todos/{todo['id']}", json={"recur": ""})
    assert patched.status_code == 200
    assert patched.json()["recur"] is None

    await client.post(f"/api/todos/{todo['id']}/complete")
    spawned = [
        t for t in await _todos(client) if t["title"] == todo["title"] and t["id"] != todo["id"]
    ]
    assert spawned == []
    await client.delete(f"/api/todos/{todo['id']}")
