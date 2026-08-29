from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import SessionLocal
from app.main import app
from app.modules.opportunity.models import Opportunity


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


async def _create_scored_jobs(
    client: AsyncClient, marker: str, scores: tuple[float | None, ...]
) -> list[str]:
    ids: list[str] = []
    for index, score in enumerate(scores):
        response = await client.post(
            "/api/opportunities", json={"title": f"Backend Engineer {marker} {index}"}
        )
        assert response.status_code == 201
        item_id = response.json()["id"]
        ids.append(item_id)
        if score is not None:
            async with SessionLocal() as session:
                row = await session.get(Opportunity, uuid.UUID(item_id))
                assert row is not None
                row.raw = {"forkjob": {"score": score}}
                await session.commit()
    return ids


async def _delete_opportunities(client: AsyncClient, item_ids: list[str]) -> None:
    for item_id in item_ids:
        await client.post(f"/api/opportunities/{item_id}/trash")
        await client.delete(f"/api/opportunities/{item_id}")


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


async def test_browse_filters_an_inclusive_score_range(client: AsyncClient):
    marker = uuid.uuid4().hex[:10]
    created_ids = await _create_scored_jobs(client, marker, (20, 40, 80, None))
    try:
        response = await client.get(
            "/api/opportunities/browse",
            params={
                "section": "jobs",
                "search": marker,
                "min_score": 40,
                "max_score": 80,
            },
        )
        assert response.status_code == 200
        assert [item["score"] for item in response.json()["items"]] == [80, 40]
    finally:
        await _delete_opportunities(client, created_ids)


async def test_browse_sorts_scores_ascending_with_unscored_items_last(
    client: AsyncClient,
):
    marker = uuid.uuid4().hex[:10]
    created_ids = await _create_scored_jobs(client, marker, (80, None, 20, 40))
    try:
        response = await client.get(
            "/api/opportunities/browse",
            params={"section": "jobs", "search": marker, "sort": "score_asc"},
        )
        assert response.status_code == 200
        assert [item["score"] for item in response.json()["items"]] == [
            20,
            40,
            80,
            None,
        ]
    finally:
        await _delete_opportunities(client, created_ids)


async def test_browse_rejects_an_inverted_score_range(client: AsyncClient):
    response = await client.get(
        "/api/opportunities/browse",
        params={"section": "jobs", "min_score": 80, "max_score": 40},
    )
    assert response.status_code == 422


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
