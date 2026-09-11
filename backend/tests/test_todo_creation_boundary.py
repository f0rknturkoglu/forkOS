"""Faz 17: gorev olusturma siniri todo.service.create.

Context adapter'lari (opportunity, learning, project) Todo servisine delege
eder; kendi iliskisini ayni transaction'da yazar. Todo modelini elle
kurmak veya dogrudan entity(type='todo') uretmek yasaktir (koruyan tarama).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from sqlalchemy import text

from app.db import SessionLocal

APP_DIR = Path(__file__).resolve().parents[1] / "app"
TODO_MODULE = APP_DIR / "modules" / "todo"


@pytest.mark.no_database
def test_no_module_builds_todo_outside_todo_service() -> None:
    offenders: list[str] = []
    for path in sorted((APP_DIR / "modules").glob("*/**/*.py")):
        if path.is_relative_to(TODO_MODULE):
            continue
        source = path.read_text(encoding="utf-8")
        if re.search(r"\bTodo\(", source):
            offenders.append(f"{path.relative_to(APP_DIR)}: Todo(...) kurulumu")
        if re.search(r"create_entity\([^)]*type\s*=\s*[\"']todo[\"']", source):
            offenders.append(f"{path.relative_to(APP_DIR)}: create_entity(type='todo')")
    assert not offenders, (
        "Todo yalnizca todo.service.create uzerinden olusur (Faz 17). "
        "Context adapter'lari delege eder:\n" + "\n".join(offenders)
    )


async def test_learning_topic_todo_is_one_transaction_with_link() -> None:
    """Konu -> gorev + prepares_for bagi tek istekte; ara durum yok."""
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        area = (
            await client.post("/api/study/areas", json={"title": "Alan"})
        ).json()
        topic = (
            await client.post(
                "/api/study/topics",
                json={"title": "Türev", "area_id": area["id"]},
            )
        ).json()

        response = await client.post(f"/api/study/topics/{topic['id']}/todos")
        assert response.status_code == 201, response.text
        payload = response.json()
        assert payload["created"] is True
        todo = payload["todo"]
        assert todo["title"] == "Türev"

        listed = (await client.get("/api/todos", params={"limit": 100})).json()
        linked_todo = next(item for item in listed if item["id"] == todo["id"])
        assert linked_todo["learning_topic_id"] == topic["id"]
        assert linked_todo["learning_topic_title"] == "Türev"

        # Bagi dogrula: todo -> topic, prepares_for (tek transaction kaniti).
        async with SessionLocal() as session:
            rows = (
                await session.execute(
                    text(
                        "select relation from link where from_id=:f and to_id=:t"
                    ),
                    {"f": todo["id"], "t": topic["id"]},
                )
            ).all()
        assert [row[0] for row in rows] == ["prepares_for"]

        await client.delete(f"/api/todos/{todo['id']}")
        await client.delete(f"/api/study/topics/{topic['id']}")
        await client.delete(f"/api/study/areas/{area['id']}")



async def test_context_todos_accept_plan_day() -> None:
    """Faz 31: opportunity ve learning context gorevleri plan_day kabul eder."""
    from httpx import ASGITransport, AsyncClient

    from app.core.time import local_today
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        # Opportunity: TodoIn govdesi -> plan_day slot olusturur.
        opp = (await c.post("/api/opportunities", json={
            "title": "Is", "kind": "job",
        })).json()
        step = (await c.post(f"/api/opportunities/{opp['id']}/todos", json={
            "title": "CV hazirla", "plan_day": local_today().isoformat(),
        })).json()
        week = (await c.get("/api/plan", params={"week": local_today().isoformat()})).json()
        assert step["id"] in {row["entity_id"] for row in week}
        assert step["due_at"] is None
        await c.delete(f"/api/todos/{step['id']}")
        await c.delete(f"/api/opportunities/{opp['id']}")

        # Learning: konu gorevi + plan_day.
        area = (await c.post("/api/study/areas", json={"title": "Alan2"})).json()
        topic = (await c.post("/api/study/topics", json={
            "title": "Konu", "area_id": area["id"],
        })).json()
        todo = (await c.post(f"/api/study/topics/{topic['id']}/todos", json={
            "plan_day": local_today().isoformat(),
        })).json()["todo"]
        week2 = (await c.get("/api/plan", params={"week": local_today().isoformat()})).json()
        assert todo["id"] in {row["entity_id"] for row in week2}
        assert todo["due_at"] is None
        await c.delete(f"/api/todos/{todo['id']}")
        await c.delete(f"/api/study/topics/{topic['id']}")
        await c.delete(f"/api/study/areas/{area['id']}")
