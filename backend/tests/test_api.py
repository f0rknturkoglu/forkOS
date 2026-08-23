"""Uctan uca capture testi -- Postgres gerektirir.

DB yoksa TUM dosya atlanir, boylece `pytest` DB'siz makinede de yesil kalir.
Compose icinde calistir:  make test
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

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


async def _seed_external_event(title: str, starts_at: datetime, ends_at: datetime) -> uuid.UUID:
    entity_id = uuid.uuid4()
    async with engine.begin() as connection:
        await connection.execute(text(
            "insert into entity (id, type, title, search_text) "
            "values (:id, 'external_event', :title, '')"
        ), {"id": entity_id, "title": title})
        await connection.execute(text(
            "insert into external_event "
            "(id, provider, external_id, starts_at, ends_at, all_day, synced_at) "
            "values (:id, 'google', :external_id, :starts_at, :ends_at, false, now())"
        ), {
            "id": entity_id,
            "external_id": f"test-{entity_id}",
            "starts_at": starts_at,
            "ends_at": ends_at,
        })
    return entity_id


async def _delete_entities(*entity_ids: uuid.UUID) -> None:
    async with engine.begin() as connection:
        for entity_id in entity_ids:
            await connection.execute(
                text("delete from entity where id = :id"), {"id": entity_id}
            )


async def _seed_feed_items(hours_old: list[int]) -> tuple[uuid.UUID, list[uuid.UUID]]:
    feed_id = uuid.uuid4()
    item_ids = [uuid.uuid4() for _ in hours_old]
    async with engine.begin() as connection:
        await connection.execute(text(
            "insert into entity (id, type, title, search_text) "
            "values (:id, 'feed', 'Agenda feed', '')"
        ), {"id": feed_id})
        await connection.execute(text(
            "insert into feed (id, url, active, error_count) "
            "values (:id, :url, true, 0)"
        ), {"id": feed_id, "url": f"https://example.com/feed/{feed_id}"})
        for index, (item_id, age) in enumerate(zip(item_ids, hours_old, strict=True)):
            published_at = datetime.now(UTC) - timedelta(hours=age)
            await connection.execute(text(
                "insert into entity (id, type, title, search_text) "
                "values (:id, 'feed_item', :title, '')"
            ), {"id": item_id, "title": f"Agenda article {index}"})
            await connection.execute(text(
                "insert into feed_item "
                "(id, feed_id, guid, url, published_at, fetched_at) "
                "values (:id, :feed_id, :guid, :url, :published_at, :fetched_at)"
            ), {
                "id": item_id,
                "feed_id": feed_id,
                "guid": f"agenda-{item_id}",
                "url": f"https://example.com/article/{item_id}",
                "published_at": published_at,
                "fetched_at": published_at,
            })
    return feed_id, item_ids


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


async def test_overdue_recurring_todo_advances_to_future_and_keeps_context(client: AsyncClient):
    suffix = uuid.uuid4().hex[:8]
    project = (await client.post("/api/projects", json={"title": f"Future {suffix}"})).json()
    milestone = (await client.post(
        f"/api/projects/{project['id']}/milestones", json={"title": "Future target"}
    )).json()
    parent = (await client.post("/api/todos", json={
        "title": f"Routine parent {suffix}", "project_id": project["id"],
        "milestone_id": milestone["id"],
    })).json()
    title = f"Overdue routine {suffix}"
    original = (await client.post("/api/todos", json={
        "title": title,
        "parent_id": parent["id"],
        "recur": "daily",
        "due_at": (datetime.now(UTC) - timedelta(days=10)).isoformat(),
        "tags": ["routine-test"],
    })).json()

    completed = await client.post(f"/api/todos/{original['id']}/complete")
    assert completed.status_code == 200
    open_todos = (await client.get("/api/todos", params={"status": "open", "limit": 500})).json()
    generated = next(item for item in open_todos if item["title"] == title)
    assert datetime.fromisoformat(generated["due_at"]) > datetime.now(UTC)
    assert generated["parent_id"] == parent["id"]
    assert generated["project_id"] == project["id"]
    assert generated["milestone_id"] == milestone["id"]
    assert generated["tags"] == ["routine-test"]

    events = (await client.get("/api/activity", params={"limit": 500})).json()
    event = next(
        item for item in events
        if item["verb"] == "todo.completed" and item["entity_id"] == original["id"]
    )
    assert event["payload"]["title"] == title
    assert event["payload"]["recur"] == "daily"

    await client.delete(f"/api/todos/{generated['id']}")
    await client.delete(f"/api/todos/{parent['id']}")
    await client.delete(f"/api/projects/{project['id']}")


async def test_heatmap_classifies_routine_todos_and_legacy_habits(client: AsyncClient):
    suffix = uuid.uuid4().hex[:8]
    before = (await client.get("/api/activity/heatmap", params={"days": 7})).json()
    before_today = before["days"][-1]["kinds"]

    normal = (await client.post("/api/todos", json={"title": f"Normal {suffix}"})).json()
    routine = (await client.post("/api/todos", json={
        "title": f"Routine {suffix}", "recur": "daily",
    })).json()
    habit = (await client.post("/api/habits", json={"title": f"Legacy {suffix}"})).json()

    await client.post(f"/api/todos/{normal['id']}/complete")
    await client.post(f"/api/todos/{routine['id']}/complete")
    await client.post(f"/api/habits/{habit['id']}/check", json={"day": date.today().isoformat()})

    after = (await client.get("/api/activity/heatmap", params={"days": 7})).json()
    after_today = after["days"][-1]["kinds"]
    assert after_today.get("task", 0) - before_today.get("task", 0) == 1
    assert after_today.get("routine", 0) - before_today.get("routine", 0) == 2
    assert after["labels"]["routine"] == "rutin"

    detail = (await client.get(
        "/api/activity/day", params={"day": date.today().isoformat()}
    )).json()
    routine_event = next(
        item for item in detail["events"]
        if item["verb"] == "todo.completed" and item["entity_id"] == routine["id"]
    )
    assert routine_event["kind"] == "routine"
    assert routine_event["payload"]["title"] == f"Routine {suffix}"

    generated = next(
        item for item in (await client.get(
            "/api/todos", params={"status": "open", "limit": 500}
        )).json()
        if item["title"] == f"Routine {suffix}"
    )
    await client.delete(f"/api/todos/{generated['id']}")
    await client.delete(f"/api/todos/{normal['id']}")
    await client.delete(f"/api/todos/{routine['id']}")
    await client.delete(f"/api/habits/{habit['id']}")


async def test_today_agenda_deduplicates_planned_due_todo(client: AsyncClient):
    day = date.today()
    todo = (await client.post("/api/todos", json={
        "title": f"Agenda dedupe {uuid.uuid4().hex[:8]}",
        "due_at": f"{day.isoformat()}T09:00:00+03:00",
    })).json()
    slot = (await client.post("/api/plan", json={
        "entity_id": todo["id"], "day": day.isoformat(),
    })).json()

    response = await client.get("/api/today/agenda", params={"day": day.isoformat()})
    assert response.status_code == 200
    agenda = response.json()
    rows = agenda["timed"] + agenda["checklist"] + agenda["completed"]
    matches = [row for row in rows if row["id"] == todo["id"]]
    assert len(matches) == 1
    assert matches[0]["source"] == "planned"
    assert matches[0]["slot_id"] == slot["id"]

    await client.delete(f"/api/todos/{todo['id']}")


async def test_today_agenda_nests_due_child_under_context_parent(client: AsyncClient):
    day = date.today()
    parent = (await client.post("/api/todos", json={
        "title": f"Agenda parent {uuid.uuid4().hex[:8]}",
    })).json()
    child = (await client.post("/api/todos", json={
        "title": f"Agenda child {uuid.uuid4().hex[:8]}",
        "parent_id": parent["id"],
        "due_at": f"{day.isoformat()}T10:00:00+03:00",
    })).json()

    agenda = (await client.get(
        "/api/today/agenda", params={"day": day.isoformat()}
    )).json()
    parent_row = next(row for row in agenda["checklist"] if row["id"] == parent["id"])
    assert parent_row["context_only"] is True
    assert parent_row["action"] is None
    assert [row["id"] for row in parent_row["children"]] == [child["id"]]
    assert all(row["id"] != child["id"] for row in agenda["checklist"])

    await client.delete(f"/api/todos/{parent['id']}")


async def test_today_agenda_uses_istanbul_day_boundaries(client: AsyncClient):
    day = date.today()
    zone = ZoneInfo("Europe/Istanbul")
    midnight = datetime.combine(day, datetime.min.time(), tzinfo=zone)
    previous = await _seed_external_event(
        "Previous local day", midnight - timedelta(minutes=30), midnight - timedelta(minutes=10)
    )
    inside = await _seed_external_event(
        "Inside local day", midnight + timedelta(minutes=30), midnight + timedelta(minutes=50)
    )
    following = await _seed_external_event(
        "Following local day",
        midnight + timedelta(days=1, minutes=30),
        midnight + timedelta(days=1, minutes=50),
    )

    agenda = (await client.get(
        "/api/today/agenda", params={"day": day.isoformat()}
    )).json()
    seeded = {str(previous), str(inside), str(following)}
    visible = {row["id"] for row in agenda["timed"]} & seeded
    assert visible == {str(inside)}

    await _delete_entities(previous, inside, following)


async def test_today_agenda_returns_bounded_project_and_recent_rss_suggestions(
    client: AsyncClient,
):
    day = date.today()
    projects = []
    todos = []
    for index in range(5):
        project = (await client.post(
            "/api/projects", json={"title": f"Suggested project {index} {uuid.uuid4().hex[:6]}"}
        )).json()
        projects.append(project)
        todo = (await client.post("/api/todos", json={
            "title": f"Suggested task {index}",
            "project_id": project["id"],
            "priority": 3 - (index % 4),
        })).json()
        todos.append(todo)
    feed_id, item_ids = await _seed_feed_items([1, 2, 3, 4, 5, 25])
    before_slots = (await client.get("/api/plan", params={"week": day.isoformat()})).json()

    agenda = (await client.get(
        "/api/today/agenda", params={"day": day.isoformat()}
    )).json()
    assert agenda["auto_suggestions"] is True
    assert len(agenda["suggestions"]["todos"]) == 4
    assert all(row["project_title"] for row in agenda["suggestions"]["todos"])
    assert len({row["project_title"] for row in agenda["suggestions"]["todos"]}) == 4
    assert [row["id"] for row in agenda["suggestions"]["rss"]] == [
        str(item_id) for item_id in item_ids[:4]
    ]
    after_slots = (await client.get("/api/plan", params={"week": day.isoformat()})).json()
    assert after_slots == before_slots

    for todo in todos:
        await client.delete(f"/api/todos/{todo['id']}")
    for project in projects:
        await client.delete(f"/api/projects/{project['id']}")
    await _delete_entities(*item_ids, feed_id)


async def test_today_agenda_keeps_read_planned_rss_in_completed(client: AsyncClient):
    day = date.today()
    feed_id, item_ids = await _seed_feed_items([1])
    item_id = item_ids[0]
    slot = (await client.post("/api/plan", json={
        "entity_id": str(item_id), "day": day.isoformat(), "duration_min": 20,
    })).json()
    marked = await client.post(f"/api/rss/items/{item_id}/read")
    assert marked.status_code == 200

    agenda = (await client.get(
        "/api/today/agenda", params={"day": day.isoformat()}
    )).json()
    row = next(item for item in agenda["completed"] if item["id"] == str(item_id))
    assert row["kind"] == "rss"
    assert row["source"] == "planned"
    assert row["slot_id"] == slot["id"]
    assert row["completed"] is True
    assert row["action"] is None

    await _delete_entities(item_id, feed_id)


async def test_todos_recur_only_filters_normal_tasks(client: AsyncClient):
    suffix = uuid.uuid4().hex[:8]
    normal = (await client.post("/api/todos", json={"title": f"Normal filter {suffix}"})).json()
    routine = (await client.post("/api/todos", json={
        "title": f"Routine filter {suffix}", "recur": "weekdays",
    })).json()

    rows = (await client.get(
        "/api/todos", params={"status": "open", "recur_only": True, "limit": 500}
    )).json()
    returned = {row["id"] for row in rows}
    assert routine["id"] in returned
    assert normal["id"] not in returned

    await client.delete(f"/api/todos/{normal['id']}")
    await client.delete(f"/api/todos/{routine['id']}")


async def test_plan_reschedule_and_unschedule_append_events(client: AsyncClient):
    day = date.today()
    next_day = day + timedelta(days=1)
    todo = (await client.post("/api/todos", json={
        "title": f"Plan events {uuid.uuid4().hex[:8]}"
    })).json()
    slot = (await client.post("/api/plan", json={
        "entity_id": todo["id"], "day": day.isoformat(),
    })).json()

    moved = await client.patch(
        f"/api/plan/{slot['id']}", json={"day": next_day.isoformat(), "start_min": 600}
    )
    assert moved.status_code == 200
    removed = await client.delete(f"/api/plan/{slot['id']}")
    assert removed.status_code == 204

    events = (await client.get("/api/activity", params={"limit": 500})).json()
    related = [item for item in events if item["entity_id"] == todo["id"]]
    rescheduled = next(item for item in related if item["verb"] == "plan.rescheduled")
    assert rescheduled["payload"]["from"] == day.isoformat()
    assert rescheduled["payload"]["to"] == next_day.isoformat()
    unscheduled = next(item for item in related if item["verb"] == "plan.unscheduled")
    assert unscheduled["payload"]["day"] == next_day.isoformat()

    await client.delete(f"/api/todos/{todo['id']}")


async def test_today_agenda_hides_suggestions_when_auto_mode_is_disabled(client: AsyncClient):
    todo = (await client.post("/api/todos", json={
        "title": f"Hidden suggestion {uuid.uuid4().hex[:8]}"
    })).json()
    await client.put("/api/settings/today.auto_suggestions", json={"value": False})
    try:
        agenda = (await client.get(
            "/api/today/agenda", params={"day": date.today().isoformat()}
        )).json()
        assert agenda["auto_suggestions"] is False
        assert agenda["suggestions"] == {"todos": [], "rss": []}
    finally:
        await client.put("/api/settings/today.auto_suggestions", json={"value": True})
        await client.delete(f"/api/todos/{todo['id']}")


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
