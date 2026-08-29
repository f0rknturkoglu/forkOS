from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


async def test_browse_filters_jobs_and_paginates(client: AsyncClient):
    marker = uuid.uuid4().hex[:10]
    created_ids: list[str] = []
    try:
        for title in (
            f"MLOps Engineer {marker}",
            f"Data Scientist {marker}",
            f"Product Designer {marker}",
        ):
            response = await client.post("/api/opportunities", json={"title": title})
            assert response.status_code == 201
            created_ids.append(response.json()["id"])

        response = await client.get(
            "/api/opportunities/browse",
            params={"section": "jobs", "category": "data-ai", "search": marker, "limit": 1},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 2
        assert payload["limit"] == 1
        assert len(payload["items"]) == 1
        assert payload["items"][0]["category"] == "data-ai"
        assert payload["facets"]["categories"]["data-ai"] == 2
    finally:
        for item_id in created_ids:
            await client.post(f"/api/opportunities/{item_id}/trash")
            await client.delete(f"/api/opportunities/{item_id}")


async def test_legacy_list_enforces_kind_status_and_limit(client: AsyncClient):
    marker = uuid.uuid4().hex[:10]
    created_ids: list[str] = []
    try:
        for index in range(3):
            response = await client.post(
                "/api/opportunities",
                json={"title": f"Backend Engineer {marker} {index}", "status": "considering"},
            )
            created_ids.append(response.json()["id"])
        response = await client.get(
            "/api/opportunities", params={"kind": "job", "status": "considering", "limit": 2}
        )
        assert response.status_code == 200
        assert len(response.json()) == 2
        assert all(
            item["kind"] == "job" and item["status"] == "considering"
            for item in response.json()
        )
    finally:
        for item_id in created_ids:
            await client.post(f"/api/opportunities/{item_id}/trash")
            await client.delete(f"/api/opportunities/{item_id}")
