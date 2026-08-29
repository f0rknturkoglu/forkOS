"""Faz 13: "bugune al" -- POST /todos plan_day ile ayni transaction'da plan slotu yazar.

due_at'e DOKUNMAZ: plan = "bugun yapmayi planliyorum", due_at = "teslim".
Agenda'daki kanit: plan_day ile olusan gorev checklist'e duser, suggestions'a
degil (bkz. today/service.py::agenda `relevant` filtresi).
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.time import local_today
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as http:
        yield http


async def test_plan_day_creates_todo_and_slot_in_one_request(client: AsyncClient) -> None:
    day = local_today()
    response = await client.post("/api/todos", json={
        "title": f"Bugune al {uuid.uuid4().hex[:6]}",
        "plan_day": day.isoformat(),
    })
    assert response.status_code == 201, response.text
    todo = response.json()

    # Ayni istek hem gorevi hem slotu yazdi; donus ciktisi da plani tasiyor.
    assert todo["planned_day"] == day.isoformat()
    week = (await client.get("/api/plan", params={"week": day.isoformat()})).json()
    assert todo["id"] in {slot["entity_id"] for slot in week}
    await client.delete(f"/api/todos/{todo['id']}")


async def test_plan_day_keeps_due_at_null(client: AsyncClient) -> None:
    """Faz 13'un ozu: plan yazmak son tarih VERMEZ (regresyon korumasi)."""
    day = local_today()
    todo = (await client.post("/api/todos", json={
        "title": f"Due kalmamali {uuid.uuid4().hex[:6]}",
        "plan_day": day.isoformat(),
    })).json()
    assert todo["due_at"] is None
    await client.delete(f"/api/todos/{todo['id']}")


async def test_without_plan_day_no_slot_is_written(client: AsyncClient) -> None:
    """plan_day bos -> mevcut davranis: yalnizca gorev, plan yok."""
    day = local_today()
    todo = (await client.post("/api/todos", json={
        "title": f"Plansiz {uuid.uuid4().hex[:6]}",
    })).json()
    assert todo["planned_day"] is None
    week = (await client.get("/api/plan", params={"week": day.isoformat()})).json()
    assert todo["id"] not in {slot["entity_id"] for slot in week}
    await client.delete(f"/api/todos/{todo['id']}")


async def test_planned_todo_lands_in_checklist_not_suggestions(client: AsyncClient) -> None:
    """Asil kabul kriteri: bugune alinan gorev Bugun panelinde "Yapilacaklar"da."""
    day = local_today()
    todo = (await client.post("/api/todos", json={
        "title": f"Agenda kaniti {uuid.uuid4().hex[:6]}",
        "plan_day": day.isoformat(),
    })).json()

    agenda = (await client.get("/api/today/agenda", params={"day": day.isoformat()})).json()
    checklist_ids = {row["id"] for row in agenda["checklist"]}
    suggestion_ids = {row["id"] for row in agenda["suggestions"]["todos"]}
    assert todo["id"] in checklist_ids
    assert todo["id"] not in suggestion_ids
    await client.delete(f"/api/todos/{todo['id']}")
