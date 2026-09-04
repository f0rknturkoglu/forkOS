from __future__ import annotations

import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import SessionLocal
from app.main import app
from app.modules.opportunity.models import Opportunity
from app.modules.opportunity.service import backfill_skill_match_ratios


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


async def test_browse_remote_facet_buckets_raw_values(client: AsyncClient):
    """Remote facet ham metni degil kanonik kovalari doner; filtre ayni kovayla eslesir."""
    marker = uuid.uuid4().hex[:10]
    created_ids: list[str] = []
    try:
        for title, remote in (
            (f"Remote Role {marker} 1", "Remote - EU"),
            (f"Remote Role {marker} 2", "remote"),
            (f"Hybrid Role {marker}", "hibrit"),
            (f"Office Role {marker}", "Onsite"),
            (f"Untagged Role {marker}", None),
        ):
            response = await client.post(
                "/api/opportunities",
                json={"title": title, "kind": "job", "remote": remote},
            )
            assert response.status_code == 201
            created_ids.append(response.json()["id"])

        response = await client.get(
            "/api/opportunities/browse",
            params={"section": "jobs", "search": marker},
        )
        assert response.status_code == 200
        facets = response.json()["facets"]["remote"]
        assert facets["remote"] == 2
        assert facets["hybrid"] == 1
        assert facets["onsite"] == 1
        assert facets["unknown"] == 1

        filtered = await client.get(
            "/api/opportunities/browse",
            params={"section": "jobs", "search": marker, "remote": "remote"},
        )
        assert filtered.status_code == 200
        assert filtered.json()["total"] == 2
    finally:
        for item_id in created_ids:
            await client.post(f"/api/opportunities/{item_id}/trash")
            await client.delete(f"/api/opportunities/{item_id}")


async def test_browse_filters_region_with_the_same_value_as_its_facet(client: AsyncClient):
    marker = uuid.uuid4().hex[:10]
    created_ids: list[str] = []
    try:
        for index, region in enumerate(("TR", "EU", "TR")):
            response = await client.post(
                "/api/opportunities", json={"title": f"Region Role {marker} {index}"}
            )
            item_id = response.json()["id"]
            created_ids.append(item_id)
            async with SessionLocal() as session:
                row = await session.get(Opportunity, uuid.UUID(item_id))
                assert row is not None
                row.region = region
                await session.commit()

        response = await client.get(
            "/api/opportunities/browse",
            params={"section": "jobs", "search": marker, "region": "TR"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 2
        assert {item["region"] for item in payload["items"]} == {"TR"}
    finally:
        await _delete_opportunities(client, created_ids)


async def test_browse_filters_and_globally_sorts_cached_cv_match(client: AsyncClient):
    marker = uuid.uuid4().hex[:10]
    created_ids = await _create_scored_jobs(client, marker, (99, 30, 70))
    try:
        payloads = (
            ({"skills": ["python"]}, "Python and Docker role"),
            ({"skills": ["python", "docker"]}, "Python and Docker role"),
            ({"skills": ["python"]}, "Python role"),
        )
        async with SessionLocal() as session:
            for item_id, (reasons, description) in zip(created_ids, payloads, strict=True):
                row = await session.get(Opportunity, uuid.UUID(item_id))
                assert row is not None
                row.raw = {
                    "forkjob": {
                        "score": row.raw["forkjob"]["score"],
                        "reasons": json.dumps(reasons),
                        "description": description,
                    }
                }
                row.skill_match_ratio = None
            await session.commit()
            assert await backfill_skill_match_ratios(session, batch_size=2) == 3

        high = await client.get(
            "/api/opportunities/browse",
            params={
                "section": "jobs",
                "search": marker,
                "min_skill_match": 0.7,
                "limit": 1,
            },
        )
        assert high.status_code == 200
        assert high.json()["total"] == 2
        assert len(high.json()["items"]) == 1

        second_page = await client.get(
            "/api/opportunities/browse",
            params={
                "section": "jobs",
                "search": marker,
                "min_skill_match": 0.7,
                "limit": 1,
                "offset": 1,
            },
        )
        assert second_page.status_code == 200
        assert second_page.json()["total"] == 2
        assert len(second_page.json()["items"]) == 1

        sorted_response = await client.get(
            "/api/opportunities/browse",
            params={"section": "jobs", "search": marker, "sort": "skill_match"},
        )
        assert sorted_response.status_code == 200
        sorted_items = sorted_response.json()["items"]
        assert [item["skill_match"]["match_ratio"] for item in sorted_items] == [1.0, 1.0, 0.5]
        assert [item["score"] for item in sorted_items] == [70, 30, 99]
    finally:
        await _delete_opportunities(client, created_ids)


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
            item["kind"] == "job" and item["status"] == "considering" for item in response.json()
        )
    finally:
        for item_id in created_ids:
            await client.post(f"/api/opportunities/{item_id}/trash")
            await client.delete(f"/api/opportunities/{item_id}")


async def test_browse_filters_by_archetype_and_recommendation(client: AsyncClient):
    marker = uuid.uuid4().hex[:10]
    created_ids: list[str] = []
    try:
        res1 = await client.post(
            "/api/opportunities",
            json={"title": f"Agentic AI Engineer {marker}", "kind": "job"},
        )
        assert res1.status_code == 201
        id1 = res1.json()["id"]
        created_ids.append(id1)

        res2 = await client.post(
            "/api/opportunities",
            json={"title": f"Solutions Architect {marker}", "kind": "job"},
        )
        assert res2.status_code == 201
        id2 = res2.json()["id"]
        created_ids.append(id2)

        async with SessionLocal() as session:
            row1 = await session.get(Opportunity, uuid.UUID(id1))
            assert row1 is not None
            row1.evaluation = {
                "version": 1,
                "score": 85,
                "recommendation": "pursue",
                "archetype": "agentic",
            }
            row2 = await session.get(Opportunity, uuid.UUID(id2))
            assert row2 is not None
            row2.evaluation = {
                "version": 1,
                "score": 40,
                "recommendation": "skip",
                "archetype": "sa",
            }
            await session.commit()

        # Browse with archetype filter
        response = await client.get(
            "/api/opportunities/browse",
            params={"section": "jobs", "search": marker, "archetype": "agentic"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == id1

        # Browse with recommendation filter
        response = await client.get(
            "/api/opportunities/browse",
            params={"section": "jobs", "search": marker, "recommendation": "skip"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == id2

        # Check facets without filters
        response = await client.get(
            "/api/opportunities/browse",
            params={"section": "jobs", "search": marker},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["facets"]["archetypes"].get("agentic") == 1
        assert data["facets"]["archetypes"].get("sa") == 1
        assert data["facets"]["recommendations"].get("pursue") == 1
        assert data["facets"]["recommendations"].get("skip") == 1
    finally:
        await _delete_opportunities(client, created_ids)

