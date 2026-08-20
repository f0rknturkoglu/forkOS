"""Uctan uca capture testi -- Postgres gerektirir.

DB yoksa TUM dosya atlanir, boylece `pytest` DB'siz makinede de yesil kalir.
Compose icinde calistir:  make test
"""
from __future__ import annotations

import uuid
from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db import engine
from app.main import app


async def _database_ready() -> bool:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("select 1 from bookmark limit 1"))
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


async def test_capture_is_idempotent(client: AsyncClient):
    client_uuid = str(uuid.uuid4())
    url = f"https://example.com/forkos-test/{uuid.uuid4()}"
    payload = {"url": url, "title": "Test yazisi", "client_uuid": client_uuid,
               "collection": "inbox", "source": "manual"}

    first = await client.post("/api/capture", json=payload)
    assert first.status_code == 201
    created = first.json()
    assert created["duplicate"] is False

    # Extension retry'si: ayni client_uuid ikinci kez -> YENI KAYIT ACILMAZ
    second = await client.post("/api/capture", json=payload)
    assert second.status_code == 201
    assert second.json()["id"] == created["id"]
    assert second.json()["duplicate"] is True

    # Ayni URL, farkli client_uuid -> yeni kayit ama duplicate uyarisi
    third = await client.post("/api/capture", json={**payload, "client_uuid": str(uuid.uuid4())})
    assert third.json()["id"] != created["id"]
    assert third.json()["duplicate"] is True
    assert third.json()["existing_id"] == created["id"]

    await client.delete(f"/api/bookmarks/{third.json()['id']}")
    await client.delete(f"/api/bookmarks/{created['id']}")


async def test_move_between_collections_logs_event(client: AsyncClient):
    url = f"https://example.com/forkos-move/{uuid.uuid4()}"
    created = (await client.post("/api/capture", json={
        "url": url, "title": "Tasinacak", "client_uuid": str(uuid.uuid4()),
    })).json()

    moved = await client.patch(
        f"/api/bookmarks/{created['id']}/collection", params={"collection": "learning"})
    assert moved.status_code == 200
    assert moved.json()["collection"] == "learning"

    events = (await client.get("/api/activity", params={"limit": 50})).json()
    moves = [e for e in events if e["verb"] == "bookmark.moved" and e["entity_id"] == created["id"]]
    assert moves and moves[0]["payload"]["to"] == "learning"

    await client.delete(f"/api/bookmarks/{created['id']}")


async def test_tags_and_search(client: AsyncClient):
    title = f"Turkce arama testi {uuid.uuid4().hex[:8]}"
    created = (await client.post("/api/capture", json={
        "url": f"https://example.com/forkos-search/{uuid.uuid4()}",
        "title": title, "tags": ["ai", "okunacak"], "client_uuid": str(uuid.uuid4()),
    })).json()

    listed = (await client.get("/api/bookmarks", params={"tag": "ai"})).json()
    assert any(b["id"] == created["id"] for b in listed)
    assert set((await client.get(f"/api/bookmarks/{created['id']}")).json()["tags"]) == \
        {"ai", "okunacak"}

    hits = (await client.get("/api/search", params={"q": title.split()[0]})).json()
    assert any(h["id"] == created["id"] for h in hits)

    await client.delete(f"/api/bookmarks/{created['id']}")


async def test_health_lists_modules():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        body = (await http.get("/health")).json()
    assert body["status"] == "ok"
    assert {"bookmark", "rss"} <= set(body["modules"])


async def test_phase2_productivity_flow(client: AsyncClient):
    """Todo -> plan -> pomodoro -> habit -> review dikey dilimi."""
    suffix = uuid.uuid4().hex[:8]
    created_ids: list[str] = []

    todo_response = await client.post("/api/todos", json={
        "title": f"Faz 2 test {suffix}", "priority": 3,
    })
    assert todo_response.status_code == 201
    todo = todo_response.json()
    created_ids.append(todo["id"])

    plan = await client.post("/api/plan", json={
        "entity_id": todo["id"], "day": date.today().isoformat(),
        "duration_min": 25,
    })
    assert plan.status_code == 201
    assert plan.json()["entity_type"] == "todo"

    pomo_response = await client.post("/api/pomodoro/start", json={
        "planned_min": 1, "context_entity_id": todo["id"], "topic": f"Test {suffix}",
    })
    assert pomo_response.status_code == 201
    pomo = pomo_response.json()
    created_ids.append(pomo["id"])
    stopped = await client.post(f"/api/pomodoro/{pomo['id']}/stop", json={
        "interrupted": False,
    })
    assert stopped.status_code == 200
    assert stopped.json()["actual_min"] == 1

    habit_response = await client.post("/api/habits", json={"title": f"Habit {suffix}"})
    assert habit_response.status_code == 201
    habit = habit_response.json()
    created_ids.append(habit["id"])
    checked = await client.post(f"/api/habits/{habit['id']}/check", json={
        "day": date.today().isoformat(), "done": True,
    })
    assert checked.status_code == 200
    assert checked.json()["done_today"] is True

    completed = await client.post(f"/api/todos/{todo['id']}/complete")
    assert completed.status_code == 200
    assert completed.json()["status"] == "done"

    period = date.today().isoformat()
    preview = await client.get("/api/reviews/preview", params={
        "kind": "daily", "period_start": period,
    })
    assert preview.status_code == 200
    assert preview.json()["stats"]["focus"]["minutes"] >= 1

    review_response = await client.post("/api/reviews", json={
        "kind": "daily", "period_start": period, "decisions": {},
    })
    assert review_response.status_code == 201
    created_ids.append(review_response.json()["id"])

    async with engine.begin() as connection:
        await connection.execute(
            text("delete from entity where id = any(cast(:ids as uuid[]))"), {"ids": created_ids})
