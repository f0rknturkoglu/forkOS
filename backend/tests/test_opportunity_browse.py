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
    """Skoru KANONIK kolona yazar (raw yalnizca aciklama tasir)."""
    ids: list[str] = []
    for index, score in enumerate(scores):
        response = await client.post(
            "/api/opportunities", json={"title": f"Backend Engineer {marker} {index}"}
        )
        assert response.status_code == 201
        item_id = response.json()["id"]
        ids.append(item_id)
        async with SessionLocal() as session:
            row = await session.get(Opportunity, uuid.UUID(item_id))
            assert row is not None
            row.score = score
            row.score_source = "forkjob-rules" if score is not None else None
            row.raw = {"forkjob": {"score": score}} if score is not None else {}
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
                json={"title": f"Backend Engineer {marker} {index}", "status": "shortlisted"},
            )
            created_ids.append(response.json()["id"])
        response = await client.get(
            "/api/opportunities", params={"kind": "job", "status": "shortlisted", "limit": 2}
        )
        assert response.status_code == 200
        assert len(response.json()) == 2
        assert all(
            item["kind"] == "job" and item["status"] == "shortlisted" for item in response.json()
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



# ── Skor / uyum sınır ve regresyon testleri (Faz 7) ────────────────────
#
# Kapsanan sözleşme:
#   * skor aralığı KAPSAYICIDIR (min <= skor <= max)
#   * null (hesaplanmadı) · 0 (eşleşme yok) · -1 (elendi) AYRI değerlerdir
#   * profil uyumu 0..1; null "hesaplanmadı" demektir, %0 değil

SCORE_BOUNDARIES = (-1, 0, 39, 39.9, 40, 69, 69.9, 70, 79.9, 80, 100)


@pytest.mark.parametrize("bound", SCORE_BOUNDARIES)
async def test_score_range_boundaries_are_inclusive(client: AsyncClient, bound: float):
    """Sınır değerlerinin TAMAMEN içeride olduğunu doğrular."""
    marker = uuid.uuid4().hex[:10]
    created = await _create_scored_jobs(client, marker, (bound,))
    try:
        below = await client.get(
            "/api/opportunities/browse",
            params={"section": "jobs", "search": marker, "min_score": bound},
        )
        assert below.status_code == 200
        assert below.json()["total"] == 1, f"min_score={bound} kaydı dışladı"

        above = await client.get(
            "/api/opportunities/browse",
            params={"section": "jobs", "search": marker, "max_score": bound},
        )
        assert above.status_code == 200
        assert above.json()["total"] == 1, f"max_score={bound} kaydı dışladı"

        both = await client.get(
            "/api/opportunities/browse",
            params={
                "section": "jobs",
                "search": marker,
                "min_score": bound,
                "max_score": bound,
            },
        )
        assert both.json()["total"] == 1
    finally:
        await _delete_opportunities(client, created)


async def test_score_range_excludes_neighbours_and_keeps_decimals(client: AsyncClient):
    marker = uuid.uuid4().hex[:10]
    created = await _create_scored_jobs(client, marker, (39.9, 40, 69.9, 70, 100))
    try:
        mid = await client.get(
            "/api/opportunities/browse",
            params={"section": "jobs", "search": marker, "min_score": 40, "max_score": 69.9},
        )
        assert [item["score"] for item in mid.json()["items"]] == [69.9, 40]

        high = await client.get(
            "/api/opportunities/browse",
            params={"section": "jobs", "search": marker, "min_score": 70, "max_score": 100},
        )
        assert [item["score"] for item in high.json()["items"]] == [100, 70]

        low = await client.get(
            "/api/opportunities/browse",
            params={"section": "jobs", "search": marker, "min_score": 0, "max_score": 39.9},
        )
        assert [item["score"] for item in low.json()["items"]] == [39.9]
    finally:
        await _delete_opportunities(client, created)


async def test_null_zero_and_minus_one_stay_distinct(client: AsyncClient):
    marker = uuid.uuid4().hex[:10]
    created = await _create_scored_jobs(client, marker, (None, 0, -1, 55))
    try:
        async def total(**params) -> int:
            response = await client.get(
                "/api/opportunities/browse",
                params={"section": "jobs", "search": marker, **params},
            )
            assert response.status_code == 200
            return response.json()["total"]

        assert await total() == 4  # null dahil hepsi
        assert await total(min_score=0, max_score=100) == 2  # null ve -1 hariç
        assert await total(min_score=-1, max_score=-1) == 1  # yalnız elenen
        assert await total(max_score=-1) == 1  # null girmez
        assert await total(min_score=0, max_score=0) == 1  # 0 korunur
        assert await total(min_score=56) == 0
        # null skorlu kayıt skor aralığı filtresine hiçbir zaman girmez
        assert await total(min_score=-1, max_score=100) == 3
    finally:
        await _delete_opportunities(client, created)


async def test_score_range_paginates_without_gaps_or_repeats(client: AsyncClient):
    marker = uuid.uuid4().hex[:10]
    created = await _create_scored_jobs(client, marker, tuple(float(n) for n in range(1, 8)))
    try:
        seen: list[float] = []
        offset = 0
        while True:
            page = await client.get(
                "/api/opportunities/browse",
                params={
                    "section": "jobs",
                    "search": marker,
                    "min_score": 1,
                    "max_score": 7,
                    "sort": "score_asc",
                    "limit": 3,
                    "offset": offset,
                },
            )
            payload = page.json()
            assert payload["total"] == 7
            if not payload["items"]:
                break
            seen.extend(item["score"] for item in payload["items"])
            offset += len(payload["items"])
        assert seen == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
    finally:
        await _delete_opportunities(client, created)


async def test_score_filter_combines_with_source_region_and_remote(client: AsyncClient):
    marker = uuid.uuid4().hex[:10]
    created = await _create_scored_jobs(client, marker, (10, 60, 90))
    try:
        async with SessionLocal() as session:
            rows = [await session.get(Opportunity, uuid.UUID(item_id)) for item_id in created]
            rows[0].source = "manual"
            rows[0].region = "TR"
            rows[0].remote = "remote"
            rows[1].source = "jobhunter:greenhouse:acme"
            rows[1].region = "EU"
            rows[1].remote = "hybrid"
            rows[2].source = "jobhunter:greenhouse:acme"
            rows[2].region = "EU"
            rows[2].remote = "remote"
            await session.commit()

        async def ids(**params) -> set[str]:
            response = await client.get(
                "/api/opportunities/browse",
                params={"section": "jobs", "search": marker, **params},
            )
            assert response.status_code == 200
            return {item["id"] for item in response.json()["items"]}

        assert await ids(min_score=50, source="jobhunter:greenhouse:acme") == {
            created[1],
            created[2],
        }
        assert await ids(min_score=50, region="EU") == {created[1], created[2]}
        assert await ids(min_score=50, remote="remote") == {created[2]}
        assert await ids(min_score=50, remote="hybrid") == {created[1]}
        assert await ids(max_score=50, region="TR") == {created[0]}
    finally:
        await _delete_opportunities(client, created)


async def test_canonical_score_column_matches_raw_payload(client: AsyncClient):
    """Kolon ile raw arasında sapma olmadığını doğrular (Faz 7.2)."""
    marker = uuid.uuid4().hex[:10]
    created = await _create_scored_jobs(client, marker, (12, 88))
    try:
        async with SessionLocal() as session:
            rows = [await session.get(Opportunity, uuid.UUID(item_id)) for item_id in created]
            for row in rows:
                assert row is not None
                assert row.score == row.raw["forkjob"]["score"]
                assert row.score_source == "forkjob-rules"
    finally:
        await _delete_opportunities(client, created)


async def test_profile_match_boundaries_at_0700_and_0400(client: AsyncClient):
    marker = uuid.uuid4().hex[:10]
    created = await _create_scored_jobs(client, marker, (50, 50, 50))
    try:
        async with SessionLocal() as session:
            rows = [await session.get(Opportunity, uuid.UUID(item_id)) for item_id in created]
            for row, ratio in zip(rows, (0.699, 0.700, 0.0), strict=True):
                assert row is not None
                row.skill_match_ratio = ratio
            await session.commit()

        async def total(**params) -> int:
            response = await client.get(
                "/api/opportunities/browse",
                params={"section": "jobs", "search": marker, **params},
            )
            assert response.status_code == 200
            return response.json()["total"]

        assert await total(min_skill_match=0.7) == 1
        assert await total(min_skill_match=0.699) == 2
        assert await total(min_skill_match=0.0, max_skill_match=0.0) == 1
        assert await total(min_skill_match=0.0) == 3
        assert await total(max_skill_match=0.5) == 1
    finally:
        await _delete_opportunities(client, created)


async def test_uncomputed_profile_match_is_selectable(client: AsyncClient):
    """null (hesaplanmadı) ayrı bir durumdur; %0 ile karışmaz."""
    marker = uuid.uuid4().hex[:10]
    created = await _create_scored_jobs(client, marker, (50, 50))
    try:
        async with SessionLocal() as session:
            rows = [await session.get(Opportunity, uuid.UUID(item_id)) for item_id in created]
            rows[0].skill_match_ratio = None
            rows[1].skill_match_ratio = 0.0
            await session.commit()

        uncomputed = await client.get(
            "/api/opportunities/browse",
            params={"section": "jobs", "search": marker, "skill_match_state": "uncomputed"},
        )
        assert uncomputed.json()["total"] == 1

        computed = await client.get(
            "/api/opportunities/browse",
            params={"section": "jobs", "search": marker, "skill_match_state": "computed"},
        )
        assert computed.json()["total"] == 1
    finally:
        await _delete_opportunities(client, created)


async def test_high_profile_match_returns_real_totals_not_zero(client: AsyncClient):
    """Regresyon: '%70+' filtresi 0/0 göstermemeli (Faz 7.7)."""
    marker = uuid.uuid4().hex[:10]
    created = await _create_scored_jobs(client, marker, (95, 85, 30, 10))
    try:
        async with SessionLocal() as session:
            rows = [await session.get(Opportunity, uuid.UUID(item_id)) for item_id in created]
            for row, ratio in zip(rows, (0.95, 0.85, 0.30, 0.10), strict=True):
                assert row is not None
                row.skill_match_ratio = ratio
            await session.commit()

        response = await client.get(
            "/api/opportunities/browse",
            params={"section": "jobs", "search": marker, "min_skill_match": 0.7},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 2
        assert len(payload["items"]) == 2
        assert {item["profile_match_ratio"] for item in payload["items"]} == {0.85, 0.95}

        # Aynı filtre sıralama değişince de kayıtları korur.
        sorted_response = await client.get(
            "/api/opportunities/browse",
            params={
                "section": "jobs",
                "search": marker,
                "min_skill_match": 0.7,
                "sort": "score_asc",
            },
        )
        assert sorted_response.json()["total"] == 2

        # Facet'lar sayfa değişince kaybolmaz (offset > 0 facets boş döner, ilk sayfa dolu).
        first = await client.get(
            "/api/opportunities/browse",
            params={"section": "jobs", "search": marker, "min_skill_match": 0.7, "limit": 1},
        )
        assert first.json()["facets"]
        second = await client.get(
            "/api/opportunities/browse",
            params={
                "section": "jobs",
                "search": marker,
                "min_skill_match": 0.7,
                "limit": 1,
                "offset": 1,
            },
        )
        assert second.json()["total"] == 2
        assert len(second.json()["items"]) == 1
    finally:
        await _delete_opportunities(client, created)


async def test_skill_match_sort_is_stable_with_null_last(client: AsyncClient):
    marker = uuid.uuid4().hex[:10]
    created = await _create_scored_jobs(client, marker, (90, 20, 70, 40))
    try:
        async with SessionLocal() as session:
            rows = [await session.get(Opportunity, uuid.UUID(item_id)) for item_id in created]
            for row, ratio in zip(rows, (0.8, 0.8, 0.5, None), strict=True):
                assert row is not None
                row.skill_match_ratio = ratio
            await session.commit()

        response = await client.get(
            "/api/opportunities/browse",
            params={"section": "jobs", "search": marker, "sort": "skill_match"},
        )
        items = response.json()["items"]
        assert [item["profile_match_ratio"] for item in items] == [0.8, 0.8, 0.5, None]
        # Eşit oranda ikincil sıralama genel skordur (90 > 20).
        assert [item["score"] for item in items[:2]] == [90, 20]
    finally:
        await _delete_opportunities(client, created)


async def test_facet_counts_match_filtered_totals(client: AsyncClient):
    """Chip sayısı ile chip'e tıklayınca gelen kayıt sayısı aynı olmalı."""
    marker = uuid.uuid4().hex[:10]
    created = await _create_scored_jobs(client, marker, (10, 60, 90))
    try:
        async with SessionLocal() as session:
            rows = [await session.get(Opportunity, uuid.UUID(item_id)) for item_id in created]
            for row, region in zip(rows, ("TR", "EU", "EU"), strict=True):
                assert row is not None
                row.region = region
            await session.commit()

        response = await client.get(
            "/api/opportunities/browse",
            params={"section": "jobs", "search": marker},
        )
        facets = response.json()["facets"]["regions"]
        assert facets["EU"] == 2

        clicked = await client.get(
            "/api/opportunities/browse",
            params={"section": "jobs", "search": marker, "region": "EU"},
        )
        assert clicked.json()["total"] == facets["EU"]
    finally:
        await _delete_opportunities(client, created)
