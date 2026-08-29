from __future__ import annotations

from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.time import local_today
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def test_project_journal_upserts_one_entity_backed_note_per_day(
    client: AsyncClient,
) -> None:
    project = (await client.post("/api/projects", json={"title": "Günlük projesi"})).json()
    day = local_today().isoformat()

    created = await client.put(
        f"/api/projects/{project['id']}/journal/{day}",
        json={"body": "Bugünün proje notu"},
    )
    assert created.status_code == 200, created.text
    first_note = created.json()["note"]
    assert first_note["body"] == "Bugünün proje notu"
    assert first_note["project_id"] == project["id"]
    assert first_note["journal_day"] == day

    related = (await client.get(f"/api/entities/{first_note['id']}/related")).json()
    assert any(
        row["relation"] == "notes_about" and row["entity"]["id"] == project["id"] for row in related
    )

    updated = await client.put(
        f"/api/projects/{project['id']}/journal/{day}",
        json={"body": "Güncellenmiş günlük"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["note"]["id"] == first_note["id"]
    assert updated.json()["note"]["body"] == "Güncellenmiş günlük"

    journal = (await client.get(f"/api/projects/{project['id']}/journal")).json()
    today = next(group for group in journal if group["day"] == day)
    assert today["note"]["id"] == first_note["id"]
    assert today["note"]["body"] == "Güncellenmiş günlük"
    verbs = {event["verb"] for event in today["events"]}
    assert "project.created" in verbs
    assert not any(verb.startswith("note.") for verb in verbs)

    activity = (await client.get("/api/activity", params={"limit": 100})).json()
    note_events = [
        event
        for event in activity
        if event["entity_id"] == first_note["id"] and event["verb"].startswith("note.")
    ]
    assert {event["verb"] for event in note_events} >= {
        "note.created",
        "note.updated",
    }

    notes = (await client.get("/api/notes")).json()
    assert [note["id"] for note in notes].count(first_note["id"]) == 1


async def test_project_journal_rejects_future_and_empty_body_removes_note(
    client: AsyncClient,
) -> None:
    project = (await client.post("/api/projects", json={"title": "Silinen günlük"})).json()
    today = local_today()
    day = today.isoformat()

    future = await client.put(
        f"/api/projects/{project['id']}/journal/{(today + timedelta(days=1)).isoformat()}",
        json={"body": "Henüz yaşanmadı"},
    )
    assert future.status_code == 400

    created = await client.put(
        f"/api/projects/{project['id']}/journal/{day}",
        json={"body": "Geçici not"},
    )
    note_id = created.json()["note"]["id"]

    removed = await client.put(
        f"/api/projects/{project['id']}/journal/{day}",
        json={"body": "   \n  "},
    )
    assert removed.status_code == 200, removed.text
    assert removed.json() == {"day": day, "note": None}
    assert (await client.get(f"/api/notes/{note_id}")).status_code == 404

    journal = (await client.get(f"/api/projects/{project['id']}/journal")).json()
    today_group = next(group for group in journal if group["day"] == day)
    assert today_group["note"] is None
    assert not any(
        event["verb"].startswith("note.")
        for group in journal
        for event in group["events"]
    )
    activity = (await client.get("/api/activity", params={"limit": 100})).json()
    assert any(
        event["verb"] == "note.deleted"
        and event["payload"].get("project_id") == project["id"]
        for event in activity
    )


async def test_project_journal_returns_404_for_unknown_project(client: AsyncClient) -> None:
    import uuid

    missing = uuid.uuid4()
    day = local_today().isoformat()
    assert (await client.get(f"/api/projects/{missing}/journal")).status_code == 404
    assert (
        await client.put(f"/api/projects/{missing}/journal/{day}", json={"body": "Yok"})
    ).status_code == 404
