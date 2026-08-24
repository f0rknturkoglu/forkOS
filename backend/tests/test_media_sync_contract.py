from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.source_sync import batch_out, create_or_extend_batch
from app.db import SessionLocal
from app.main import app
from app.modules.system.models import Setting


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


async def test_source_sync_batches_are_isolated_by_scope():
    async with SessionLocal() as session:
        opportunity, _ = await create_or_extend_batch(session, ["osym"], scope="opportunity")
        media, added = await create_or_extend_batch(session, ["media:tmdb"], scope="media")

        assert opportunity.id != media.id
        assert added == ["media:tmdb"]
        assert batch_out(opportunity)["scope"] == "opportunity"
        assert batch_out(media)["scope"] == "media"
        await session.rollback()


async def test_media_sync_endpoint_queues_one_monitored_item(client):
    async with SessionLocal() as session:
        session.add(Setting(key="media.tmdb_key", value="test-key"))
        await session.commit()
    created = await client.post(
        "/api/media",
        json={
            "source": "provider",
            "title": "Arrival",
            "kind": "movie",
            "provider": "tmdb",
            "provider_id": "42",
            "monitored": True,
        },
    )
    item_id = created.json()["id"]
    try:
        response = await client.post(f"/api/media/sync?item_id={item_id}")
        assert response.status_code == 200
        payload = response.json()
        assert payload["scope"] == "media"
        assert payload["source_ids"] == [f"media:tmdb:{item_id}"]
    finally:
        await client.delete(f"/api/media/{item_id}")
        await client.delete(f"/api/media/{item_id}/permanent")


async def test_sources_status_filters_scope(client):
    async with SessionLocal() as session:
        media, _ = await create_or_extend_batch(session, ["media:anilist"], scope="media")
        opportunity, _ = await create_or_extend_batch(session, ["osym"], scope="opportunity")
        media_id = media.id
        opportunity_id = opportunity.id
        await session.commit()
    try:
        assert (await client.get("/api/sources/sync?scope=media")).json()["active"]["id"] == str(
            media_id
        )
        assert (await client.get("/api/sources/sync")).json()["active"]["id"] == str(opportunity_id)
    finally:
        async with SessionLocal() as session:
            for batch_id in (media_id, opportunity_id):
                batch = await session.get(
                    __import__("app.core.models", fromlist=["SourceSyncBatch"]).SourceSyncBatch,
                    batch_id,
                )
                if batch:
                    await session.delete(batch)
            await session.commit()
