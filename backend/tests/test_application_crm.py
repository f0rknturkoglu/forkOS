"""Application CRM uctan uca testleri — Postgres gerektirir (lifeos_test)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db import engine
from app.main import app


async def _database_ready() -> bool:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("select 1 from application limit 1"))
        return True
    except Exception:
        return False


async def _seed_opportunity() -> uuid.UUID:
    item_id = uuid.uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "insert into entity (id, type, title, search_text) values "
                "(:id, 'opportunity', :title, '')"
            ),
            {"id": item_id, "title": "CRM Test"},
        )
        await connection.execute(
            text(
                "insert into opportunity (id, kind, status, found_at, source) values "
                "(:id, 'job', 'discovered', now(), 'test')"
            ),
            {"id": item_id},
        )
    return item_id


async def _delete_entities(*entity_ids: uuid.UUID) -> None:
    async with engine.begin() as connection:
        for entity_id in entity_ids:
            await connection.execute(text("delete from entity where id = :id"), {"id": entity_id})


@pytest.fixture
async def client():
    if not await _database_ready():
        pytest.skip("Postgres yok veya migration calismamis")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


async def test_apply_snapshot_and_history(client: AsyncClient):
    item_id = await _seed_opportunity()
    try:
        response = await client.post(
            f"/api/opportunities/{item_id}/apply", json={"cover_letter": "merhaba"}
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "applied"
        history = (await client.get(f"/api/opportunities/{item_id}/history")).json()
        assert any(
            h["from_status"] == "discovered" and h["to_status"] == "applied" for h in history
        )
        application = (await client.get(f"/api/opportunities/{item_id}/application")).json()
        assert application["cover_letter"] == "merhaba"
    finally:
        await _delete_entities(item_id)


async def test_transition_rules_and_terminal_lock(client: AsyncClient):
    item_id = await _seed_opportunity()
    try:
        bad = await client.post(f"/api/opportunities/{item_id}/transition", json={"to": "offer"})
        assert bad.status_code == 400
        ok = await client.post(f"/api/opportunities/{item_id}/transition", json={"to": "applied"})
        assert ok.status_code == 200
        offer = await client.post(f"/api/opportunities/{item_id}/transition", json={"to": "offer"})
        assert offer.status_code == 200
        accepted = await client.post(
            f"/api/opportunities/{item_id}/transition", json={"to": "accepted"}
        )
        assert accepted.status_code == 200
        locked = await client.post(
            f"/api/opportunities/{item_id}/transition", json={"to": "interview"}
        )
        assert locked.status_code == 400
    finally:
        await _delete_entities(item_id)


async def test_rejection_reason_and_funnel(client: AsyncClient):
    item_id = await _seed_opportunity()
    try:
        await client.post(f"/api/opportunities/{item_id}/transition", json={"to": "applied"})
        rejected = await client.post(
            f"/api/opportunities/{item_id}/transition",
            json={"to": "rejected", "rejection_reason": "maas uyumsuz"},
        )
        assert rejected.status_code == 200
        funnel = (await client.get("/api/applications/funnel")).json()
        assert any(r["reason"] == "maas uyumsuz" for r in funnel["rejection_reasons"])
        detail = (await client.get(f"/api/opportunities/{item_id}")).json()
        assert detail["rejection_reason"] == "maas uyumsuz"
    finally:
        await _delete_entities(item_id)


async def test_followups_listing(client: AsyncClient):
    item_id = await _seed_opportunity()
    try:
        future = datetime.now(UTC) + timedelta(days=5)
        update = await client.patch(
            f"/api/opportunities/{item_id}",
            json={"follow_up_at": future.isoformat()},
        )
        assert update.status_code == 200
        followups = (await client.get("/api/opportunities/followups")).json()
        assert any(f["id"] == str(item_id) for f in followups)
    finally:
        await _delete_entities(item_id)


async def test_interview_crud(client: AsyncClient):
    item_id = await _seed_opportunity()
    try:
        created = await client.post(
            f"/api/opportunities/{item_id}/interviews",
            json={"stage": "teknik", "mode": "video"},
        )
        assert created.status_code == 201, created.text
        interview_id = created.json()["id"]
        listed = (await client.get(f"/api/opportunities/{item_id}/interviews")).json()
        assert len(listed) == 1 and listed[0]["stage"] == "teknik"
        assert (await client.delete(f"/api/interviews/{interview_id}")).status_code == 204
    finally:
        await _delete_entities(item_id)
