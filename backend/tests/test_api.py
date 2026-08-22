"""Uctan uca capture testi -- Postgres gerektirir.

DB yoksa TUM dosya atlanir, boylece `pytest` DB'siz makinede de yesil kalir.
Compose icinde calistir:  make test
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

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
    payload = {
        "url": url,
        "title": "Test yazisi",
        "client_uuid": client_uuid,
        "collection": "inbox",
        "source": "manual",
    }

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
    created = (
        await client.post(
            "/api/capture",
            json={
                "url": url,
                "title": "Tasinacak",
                "client_uuid": str(uuid.uuid4()),
            },
        )
    ).json()

    moved = await client.patch(
        f"/api/bookmarks/{created['id']}/collection", params={"collection": "learning"}
    )
    assert moved.status_code == 200
    assert moved.json()["collection"] == "learning"

    events = (await client.get("/api/activity", params={"limit": 50})).json()
    moves = [e for e in events if e["verb"] == "bookmark.moved" and e["entity_id"] == created["id"]]
    assert moves and moves[0]["payload"]["to"] == "learning"

    await client.delete(f"/api/bookmarks/{created['id']}")


async def test_tags_and_search(client: AsyncClient):
    title = f"Turkce arama testi {uuid.uuid4().hex[:8]}"
    created = (
        await client.post(
            "/api/capture",
            json={
                "url": f"https://example.com/forkos-search/{uuid.uuid4()}",
                "title": title,
                "tags": ["ai", "okunacak"],
                "client_uuid": str(uuid.uuid4()),
            },
        )
    ).json()

    listed = (await client.get("/api/bookmarks", params={"tag": "ai"})).json()
    assert any(b["id"] == created["id"] for b in listed)
    assert set((await client.get(f"/api/bookmarks/{created['id']}")).json()["tags"]) == {
        "ai",
        "okunacak",
    }

    hits = (await client.get("/api/search", params={"q": title.split()[0]})).json()
    assert any(h["id"] == created["id"] for h in hits)

    await client.delete(f"/api/bookmarks/{created['id']}")


async def test_health_lists_modules():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        body = (await http.get("/health")).json()
    assert body["status"] == "ok"
    assert {"bookmark", "rss"} <= set(body["modules"])


async def test_todo_creation_atomically_links_project_and_milestone(client: AsyncClient):
    suffix = uuid.uuid4().hex[:8]
    project = (await client.post("/api/projects", json={"title": f"Atomic {suffix}"})).json()
    milestone = (await client.post(
        f"/api/projects/{project['id']}/milestones", json={"title": "Release"}
    )).json()
    response = await client.post("/api/todos", json={
        "title": f"Ship {suffix}", "project_id": project["id"],
        "milestone_id": milestone["id"],
    })
    assert response.status_code == 201
    todo = response.json()
    assert todo["project_id"] == project["id"]
    assert todo["milestone_id"] == milestone["id"]
    linked = (await client.get(f"/api/projects/{project['id']}/todos")).json()
    assert todo["id"] in {item["id"] for item in linked}
    await client.delete(f"/api/todos/{todo['id']}")
    await client.delete(f"/api/projects/{project['id']}")


async def test_todo_rejects_cross_project_milestone_without_a_record(client: AsyncClient):
    suffix = uuid.uuid4().hex[:8]
    first = (await client.post("/api/projects", json={"title": f"First {suffix}"})).json()
    second = (await client.post("/api/projects", json={"title": f"Second {suffix}"})).json()
    milestone = (await client.post(
        f"/api/projects/{first['id']}/milestones", json={"title": "First only"}
    )).json()
    title = f"Rollback {suffix}"
    response = await client.post("/api/todos", json={
        "title": title, "project_id": second["id"], "milestone_id": milestone["id"],
    })
    assert response.status_code == 400
    todos = (await client.get("/api/todos", params={"limit": 500})).json()
    assert title not in {item["title"] for item in todos}
    await client.delete(f"/api/projects/{first['id']}")
    await client.delete(f"/api/projects/{second['id']}")


async def test_todo_rejects_child_of_multi_project_parent_without_a_record(client: AsyncClient):
    suffix = uuid.uuid4().hex[:8]
    first = (await client.post("/api/projects", json={"title": f"First {suffix}"})).json()
    second = (await client.post("/api/projects", json={"title": f"Second {suffix}"})).json()
    parent = (await client.post("/api/todos", json={"title": f"Parent {suffix}"})).json()
    for project in (first, second):
        linked = await client.post(
            f"/api/projects/{project['id']}/todos", json={"todo_id": parent["id"]}
        )
        assert linked.status_code == 201
    title = f"Multi-project child {suffix}"
    response = await client.post("/api/todos", json={"title": title, "parent_id": parent["id"]})
    assert response.status_code == 400
    todos = (await client.get("/api/todos", params={"limit": 500})).json()
    assert title not in {item["title"] for item in todos}
    await client.delete(f"/api/todos/{parent['id']}")
    await client.delete(f"/api/projects/{first['id']}")
    await client.delete(f"/api/projects/{second['id']}")


async def test_subtask_inherits_parent_project_and_milestone(client: AsyncClient):
    suffix = uuid.uuid4().hex[:8]
    project = (await client.post("/api/projects", json={"title": f"Parent {suffix}"})).json()
    milestone = (await client.post(
        f"/api/projects/{project['id']}/milestones", json={"title": "Inherited"}
    )).json()
    parent = (await client.post("/api/todos", json={
        "title": f"Parent todo {suffix}", "project_id": project["id"],
        "milestone_id": milestone["id"],
    })).json()
    child = (await client.post("/api/todos", json={
        "title": f"Child {suffix}", "parent_id": parent["id"],
    })).json()
    assert child["project_id"] == project["id"]
    assert child["milestone_id"] == milestone["id"]
    linked = (await client.get(f"/api/projects/{project['id']}/todos")).json()
    assert child["id"] in {item["id"] for item in linked}
    await client.delete(f"/api/todos/{parent['id']}")
    await client.delete(f"/api/projects/{project['id']}")


async def test_subtask_rejects_conflicting_project_context(client: AsyncClient):
    suffix = uuid.uuid4().hex[:8]
    first = (await client.post("/api/projects", json={"title": f"Parent {suffix}"})).json()
    second = (await client.post("/api/projects", json={"title": f"Other {suffix}"})).json()
    parent = (await client.post("/api/todos", json={
        "title": f"Parent {suffix}", "project_id": first["id"],
    })).json()
    response = await client.post("/api/todos", json={
        "title": f"Conflicting child {suffix}", "parent_id": parent["id"],
        "project_id": second["id"],
    })
    assert response.status_code == 400
    await client.delete(f"/api/todos/{parent['id']}")
    await client.delete(f"/api/projects/{first['id']}")
    await client.delete(f"/api/projects/{second['id']}")


async def test_recurring_todo_keeps_project_and_milestone(client: AsyncClient):
    suffix = uuid.uuid4().hex[:8]
    project = (await client.post("/api/projects", json={"title": f"Routine {suffix}"})).json()
    milestone = (await client.post(
        f"/api/projects/{project['id']}/milestones", json={"title": "Routine target"}
    )).json()
    title = f"Recurring {suffix}"
    original = (await client.post("/api/todos", json={
        "title": title, "project_id": project["id"], "milestone_id": milestone["id"],
        "recur": "daily", "due_at": "2026-08-23T09:00:00Z",
    })).json()
    await client.post(f"/api/todos/{original['id']}/complete")
    open_todos = (await client.get("/api/todos", params={"status": "open", "limit": 500})).json()
    generated = next(item for item in open_todos if item["title"] == title)
    assert generated["project_id"] == project["id"]
    assert generated["milestone_id"] == milestone["id"]
    await client.delete(f"/api/todos/{generated['id']}")
    await client.delete(f"/api/todos/{original['id']}")
    await client.delete(f"/api/projects/{project['id']}")


async def test_project_last_activity_follows_linked_todo_updates(client: AsyncClient):
    suffix = uuid.uuid4().hex[:8]
    project = (await client.post("/api/projects", json={"title": f"Active {suffix}"})).json()
    todo = (await client.post("/api/todos", json={
        "title": f"Work {suffix}", "project_id": project["id"],
    })).json()
    current = next(item for item in (await client.get("/api/projects")).json()
                   if item["id"] == project["id"])
    assert current["last_activity_at"] is not None
    before = datetime.fromisoformat(current["last_activity_at"])
    await client.patch(f"/api/todos/{todo['id']}", json={"title": f"Updated {suffix}"})
    refreshed = next(item for item in (await client.get("/api/projects")).json()
                     if item["id"] == project["id"])
    assert datetime.fromisoformat(refreshed["last_activity_at"]) > before
    await client.delete(f"/api/todos/{todo['id']}")
    await client.delete(f"/api/projects/{project['id']}")


async def test_project_timeline_records_milestone_actions(client: AsyncClient):
    suffix = uuid.uuid4().hex[:8]
    project = (await client.post("/api/projects", json={"title": f"Milestone {suffix}"})).json()
    milestone = (await client.post(
        f"/api/projects/{project['id']}/milestones", json={"title": "Visible event"}
    )).json()
    await client.patch(f"/api/milestones/{milestone['id']}", json={"completed": True})
    await client.delete(f"/api/milestones/{milestone['id']}")
    timeline = (await client.get(f"/api/projects/{project['id']}/timeline")).json()
    verbs = {item["verb"] for item in timeline}
    assert {
        "project.milestone_added", "project.milestone_updated", "project.milestone_deleted",
    } <= verbs
    await client.delete(f"/api/projects/{project['id']}")


async def test_project_timeline_includes_pomodoro_for_linked_todo(client: AsyncClient):
    suffix = uuid.uuid4().hex[:8]
    project = (await client.post("/api/projects", json={"title": f"Focus {suffix}"})).json()
    todo = (await client.post("/api/todos", json={
        "title": f"Focus todo {suffix}", "project_id": project["id"],
    })).json()
    pomo = (await client.post("/api/pomodoro/start", json={
        "planned_min": 1, "context_entity_id": todo["id"],
    })).json()
    await client.post(f"/api/pomodoro/{pomo['id']}/stop", json={"interrupted": False})
    timeline = (await client.get(f"/api/projects/{project['id']}/timeline")).json()
    focus = [item for item in timeline if item["verb"] == "pomodoro.completed"]
    assert focus
    assert focus[0]["payload"]["context_entity_id"] == todo["id"]
    await client.delete(f"/api/pomodoro/{pomo['id']}")
    await client.delete(f"/api/todos/{todo['id']}")
    await client.delete(f"/api/projects/{project['id']}")


async def test_project_timeline_excludes_pomodoro_for_linked_non_todo(client: AsyncClient):
    suffix = uuid.uuid4().hex[:8]
    project = (await client.post(
        "/api/projects", json={"title": f"Non-todo focus {suffix}"}
    )).json()
    area = (await client.post(
        "/api/study/areas", json={"title": f"Non-todo area {suffix}"}
    )).json()
    topic = (await client.post("/api/study/topics", json={
        "title": f"Non-todo topic {suffix}", "area_id": area["id"],
    })).json()
    linked = await client.post(
        f"/api/projects/{project['id']}/todos", json={"todo_id": topic["id"]}
    )
    assert linked.status_code == 201
    pomo = (await client.post("/api/pomodoro/start", json={
        "planned_min": 1, "context_entity_id": topic["id"],
    })).json()
    await client.post(f"/api/pomodoro/{pomo['id']}/stop", json={"interrupted": False})
    timeline = (await client.get(f"/api/projects/{project['id']}/timeline")).json()
    assert not any(item["entity_id"] == pomo["id"] for item in timeline)
    await client.delete(f"/api/pomodoro/{pomo['id']}")
    await client.delete(f"/api/study/topics/{topic['id']}")
    await client.delete(f"/api/study/areas/{area['id']}")
    await client.delete(f"/api/projects/{project['id']}")


async def test_interrupted_pomodoro_event_includes_context(client: AsyncClient):
    suffix = uuid.uuid4().hex[:8]
    todo = (await client.post(
        "/api/todos", json={"title": f"Interrupted context {suffix}"}
    )).json()
    pomo = (await client.post("/api/pomodoro/start", json={
        "planned_min": 1, "context_entity_id": todo["id"],
    })).json()
    await client.post(f"/api/pomodoro/{pomo['id']}/stop", json={"interrupted": True})
    activity = (await client.get("/api/activity", params={"limit": 50})).json()
    event = next(item for item in activity
                 if item["entity_id"] == pomo["id"]
                 and item["verb"] == "pomodoro.interrupted")
    assert event["payload"]["context_entity_id"] == todo["id"]
    assert event["payload"]["context_type"] == "todo"
    await client.delete(f"/api/pomodoro/{pomo['id']}")
    await client.delete(f"/api/todos/{todo['id']}")


async def test_manual_pomodoro_event_includes_context(client: AsyncClient):
    suffix = uuid.uuid4().hex[:8]
    todo = (await client.post(
        "/api/todos", json={"title": f"Manual context {suffix}"}
    )).json()
    pomo = (await client.post("/api/pomodoro", json={
        "started_at": (datetime.now(UTC) - timedelta(minutes=5)).isoformat(),
        "minutes": 1,
        "context_entity_id": todo["id"],
    })).json()
    activity = (await client.get("/api/activity", params={"limit": 50})).json()
    event = next(item for item in activity
                 if item["entity_id"] == pomo["id"]
                 and item["verb"] == "pomodoro.completed")
    assert event["payload"]["context_entity_id"] == todo["id"]
    assert event["payload"]["context_type"] == "todo"
    await client.delete(f"/api/pomodoro/{pomo['id']}")
    await client.delete(f"/api/todos/{todo['id']}")


async def test_phase2_productivity_flow(client: AsyncClient):
    """Todo -> plan -> pomodoro -> habit -> review dikey dilimi."""
    suffix = uuid.uuid4().hex[:8]
    created_ids: list[str] = []

    todo_response = await client.post(
        "/api/todos",
        json={
            "title": f"Faz 2 test {suffix}",
            "priority": 3,
        },
    )
    assert todo_response.status_code == 201
    todo = todo_response.json()
    created_ids.append(todo["id"])

    plan = await client.post(
        "/api/plan",
        json={
            "entity_id": todo["id"],
            "day": date.today().isoformat(),
            "duration_min": 25,
        },
    )
    assert plan.status_code == 201
    assert plan.json()["entity_type"] == "todo"

    pomo_response = await client.post(
        "/api/pomodoro/start",
        json={
            "planned_min": 1,
            "context_entity_id": todo["id"],
            "topic": f"Test {suffix}",
        },
    )
    assert pomo_response.status_code == 201
    pomo = pomo_response.json()
    created_ids.append(pomo["id"])
    stopped = await client.post(
        f"/api/pomodoro/{pomo['id']}/stop",
        json={
            "interrupted": False,
        },
    )
    assert stopped.status_code == 200
    assert stopped.json()["actual_min"] == 1

    habit_response = await client.post("/api/habits", json={"title": f"Habit {suffix}"})
    assert habit_response.status_code == 201
    habit = habit_response.json()
    created_ids.append(habit["id"])
    checked = await client.post(
        f"/api/habits/{habit['id']}/check",
        json={
            "day": date.today().isoformat(),
            "done": True,
        },
    )
    assert checked.status_code == 200
    assert checked.json()["done_today"] is True

    completed = await client.post(f"/api/todos/{todo['id']}/complete")
    assert completed.status_code == 200
    assert completed.json()["status"] == "done"

    period = date.today().isoformat()
    preview = await client.get(
        "/api/reviews/preview",
        params={
            "kind": "daily",
            "period_start": period,
        },
    )
    assert preview.status_code == 200
    assert preview.json()["stats"]["focus"]["minutes"] >= 1

    review_response = await client.post(
        "/api/reviews",
        json={
            "kind": "daily",
            "period_start": period,
            "decisions": {},
        },
    )
    assert review_response.status_code == 201
    created_ids.append(review_response.json()["id"])

    async with engine.begin() as connection:
        await connection.execute(
            text("delete from entity where id = any(cast(:ids as uuid[]))"), {"ids": created_ids}
        )


async def test_phase4_learning_flow(client: AsyncClient):
    """Study context -> Pomodoro stats plus course/book and graceful Google state."""
    suffix = uuid.uuid4().hex[:8]
    created_ids: list[str] = []

    area_response = await client.post(
        "/api/study/areas", json={"title": f"Area {suffix}", "color": "#38bdf8"}
    )
    assert area_response.status_code == 201
    area = area_response.json()
    created_ids.append(area["id"])

    topic_response = await client.post(
        "/api/study/topics",
        json={"title": f"Topic {suffix}", "area_id": area["id"], "target_min": 60},
    )
    assert topic_response.status_code == 201
    topic = topic_response.json()
    created_ids.append(topic["id"])

    pomo = (
        await client.post(
            "/api/pomodoro/start",
            json={"planned_min": 1, "context_entity_id": topic["id"]},
        )
    ).json()
    created_ids.append(pomo["id"])
    assert (await client.post(f"/api/pomodoro/{pomo['id']}/stop", json={})).status_code == 200
    stats = (await client.get(f"/api/study/topics/{topic['id']}/stats")).json()
    assert stats == {"minutes": 1, "sessions": 1}

    course = (await client.post("/api/courses", json={"title": f"Course {suffix}"})).json()
    book = (await client.post("/api/books", json={"title": f"Book {suffix}"})).json()
    created_ids.extend([course["id"], book["id"]])
    assert (await client.patch(f"/api/courses/{course['id']}", json={"progress_pct": 35})).json()[
        "progress_pct"
    ] == 35
    assert (await client.get("/api/auth/google/status")).status_code == 200
    assert (await client.get("/api/calendar/events")).status_code == 200

    async with engine.begin() as connection:
        await connection.execute(
            text("delete from entity where id = any(cast(:ids as uuid[]))"), {"ids": created_ids}
        )


async def test_phase5_projects_finance_settings_and_exports(client: AsyncClient):
    suffix = uuid.uuid4().hex[:8]
    created_ids: list[str] = []
    project = (
        await client.post(
            "/api/projects",
            json={
                "title": f"Project {suffix}",
                "stack": ["FastAPI", "React"],
                "next_action": "İlk testi yaz",
            },
        )
    ).json()
    created_ids.append(project["id"])
    milestone = await client.post(
        f"/api/projects/{project['id']}/milestones", json={"title": "Alpha"}
    )
    assert milestone.status_code == 201
    updated = await client.patch(f"/api/projects/{project['id']}", json={"status": "maintenance"})
    assert updated.json()["status"] == "maintenance"

    recurring = (
        await client.post(
            "/api/recurring-payments",
            json={
                "title": f"Service {suffix}",
                "amount": "149.90",
                "next_due_at": date.today().isoformat(),
            },
        )
    ).json()
    created_ids.append(recurring["id"])
    paid = (await client.post(f"/api/recurring-payments/{recurring['id']}/pay")).json()
    created_ids.append(paid["expense"]["id"])
    assert paid["expense"]["amount"] == 149.9
    assert paid["next_due_at"] != date.today().isoformat()

    key = f"test.{suffix}"
    response = await client.put(f"/api/settings/{key}", json={"value": {"ok": True}})
    assert response.status_code == 200
    assert (await client.get("/api/settings")).json()[key] == {"ok": True}
    grouped = (
        await client.get("/api/search", params={"q": f"Project {suffix}", "grouped": True})
    ).json()
    assert any(item["id"] == project["id"] for item in grouped["Projects"])
    assert (await client.get("/api/export/csv", params={"module": "expense"})).status_code == 200
    assert (await client.get("/api/export/ics")).status_code == 200

    async with engine.begin() as connection:
        await connection.execute(text("delete from setting where key=:key"), {"key": key})
        await connection.execute(
            text("delete from entity where id = any(cast(:ids as uuid[]))"), {"ids": created_ids}
        )
