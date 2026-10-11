import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db import engine
from app.integrations.career_ops.models import (
    CareerOpsJobExtractionResult,
    CareerOpsLivenessReceipt,
)
from app.main import app
from app.modules.opportunity.listing_service import OpportunityListingService


async def _database_ready() -> bool:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("select 1 from opportunity limit 1"))
        return True
    except Exception:
        return False


@pytest.fixture
async def client():
    if not await _database_ready():
        pytest.skip("Postgres yok veya migration calismamis")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


class MockAdapter:
    async def check_liveness(self, url: str, **kwargs):
        return CareerOpsLivenessReceipt(
            url=url,
            status="active",
            code="test_ok",
            reason="Mock live",
            method="api",
            checked_at=datetime.now(UTC).isoformat(),
        )

    async def extract_job(self, url: str, **kwargs):
        return CareerOpsJobExtractionResult(
            url=url,
            title="Senior Test Engineer",
            text="Substantive job description extracted for test purposes with more than two hundred chars. " * 3,
        )


async def _seed_opp_with_obs(*, url: str = "https://example.com/job/test") -> uuid.UUID:
    item_id = uuid.uuid4()
    obs_id = uuid.uuid4()
    now = datetime.now(UTC)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "insert into entity (id, type, title, search_text) values "
                "(:id, 'opportunity', 'Test Role', '')"
            ),
            {"id": item_id},
        )
        await conn.execute(
            text(
                "insert into opportunity (id, kind, organization, url, status, source_status, found_at, raw) values "
                "(:id, 'job', 'Test Corp', :url, 'discovered', 'active', :now, '{}'::jsonb)"
            ),
            {"id": item_id, "url": url, "now": now},
        )
        await conn.execute(
            text(
                "insert into opportunity_source_observation (id, opportunity_id, source, canonical_url, source_status, first_seen_at, last_seen_at, enrichment) values "
                "(:id, :opp_id, 'careerops:greenhouse', :url, 'active', :now, :now, '{}'::jsonb)"
            ),
            {"id": obs_id, "opp_id": item_id, "url": url, "now": now},
        )
    return item_id


@pytest.mark.asyncio
async def test_trigger_liveness_check_endpoint(client, monkeypatch):
    opp_id = await _seed_opp_with_obs()
    monkeypatch.setattr(
        OpportunityListingService,
        "__init__",
        lambda self, adapter=None: setattr(self, "adapter", MockAdapter()),
    )

    resp = await client.post(f"/api/opportunities/{opp_id}/liveness")
    assert resp.status_code == 200
    data = resp.json()
    assert data["opportunity_id"] == str(opp_id)
    assert data["source_status"] == "active"
    assert len(data["observations"]) == 1


@pytest.mark.asyncio
async def test_trigger_jd_extraction_endpoint(client, monkeypatch):
    opp_id = await _seed_opp_with_obs()
    monkeypatch.setattr(
        OpportunityListingService,
        "__init__",
        lambda self, adapter=None: setattr(self, "adapter", MockAdapter()),
    )

    resp = await client.post(f"/api/opportunities/{opp_id}/extract-jd")
    assert resp.status_code == 200
    data = resp.json()
    assert data["promoted"] is True
    assert data["title"] == "Senior Test Engineer"


@pytest.mark.asyncio
async def test_endpoints_return_404_for_nonexistent_opportunity(client):
    nonexistent = uuid.uuid4()
    r1 = await client.post(f"/api/opportunities/{nonexistent}/liveness")
    assert r1.status_code == 404

    r2 = await client.post(f"/api/opportunities/{nonexistent}/extract-jd")
    assert r2.status_code == 404
