from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db import engine
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


async def test_opportunity_trash_restore_and_permanent_delete(client: AsyncClient):
    title = f"Trash lifecycle {uuid.uuid4().hex[:8]}"
    created = await client.post(
        "/api/opportunities",
        json={"title": title, "kind": "job", "status": "shortlisted"},
    )
    assert created.status_code == 201
    item = created.json()
    assert item["category"] == "other"
    assert item["published_at"] is None
    assert item["status"] == "shortlisted"

    trashed = await client.post(f"/api/opportunities/{item['id']}/trash")
    assert trashed.status_code == 200
    assert trashed.json()["status"] == "dismissed"
    assert trashed.json()["trashed_at"] is not None

    normal = (await client.get("/api/opportunities", params={"limit": 2000})).json()
    assert all(row["id"] != item["id"] for row in normal)
    trash = (
        await client.get(
            "/api/opportunities", params={"limit": 2000, "trashed_only": "true"}
        )
    ).json()
    assert any(row["id"] == item["id"] for row in trash)

    restored = await client.post(f"/api/opportunities/{item['id']}/restore")
    assert restored.status_code == 200
    assert restored.json()["status"] == "shortlisted"
    assert restored.json()["trashed_at"] is None

    assert (await client.post(f"/api/opportunities/{item['id']}/trash")).status_code == 200
    deleted = await client.delete(f"/api/opportunities/{item['id']}")
    assert deleted.status_code == 204
    assert (await client.get(f"/api/opportunities/{item['id']}")).status_code == 404

    events = (await client.get("/api/activity", params={"limit": 200})).json()
    matching = [
        event
        for event in events
        if event["verb"] == "opportunity.deleted"
        and event["payload"].get("opportunity_id") == item["id"]
    ]
    assert matching
    assert matching[0]["entity_id"] is None


async def test_general_patch_cannot_bypass_trash_lifecycle(client: AsyncClient):
    created = (
        await client.post(
            "/api/opportunities",
            json={"title": f"No bypass {uuid.uuid4().hex[:8]}", "kind": "job"},
        )
    ).json()
    try:
        response = await client.patch(
            f"/api/opportunities/{created['id']}", json={"status": "trashed"}
        )
        assert response.status_code == 422
    finally:
        async with engine.begin() as connection:
            await connection.execute(
                text("delete from entity where id = cast(:id as uuid)"), {"id": created["id"]}
            )


async def test_permanent_delete_requires_trash_first(client: AsyncClient):
    created = (
        await client.post(
            "/api/opportunities",
            json={"title": f"Safe delete {uuid.uuid4().hex[:8]}", "kind": "job"},
        )
    ).json()
    try:
        response = await client.delete(f"/api/opportunities/{created['id']}")
        assert response.status_code == 409
        assert (await client.get(f"/api/opportunities/{created['id']}")).status_code == 200
    finally:
        async with engine.begin() as connection:
            await connection.execute(
                text("delete from entity where id = cast(:id as uuid)"), {"id": created["id"]}
            )
