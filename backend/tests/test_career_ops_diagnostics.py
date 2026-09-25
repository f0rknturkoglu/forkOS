import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_api_career_ops_doctor_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/system/career-ops/doctor")
        assert resp.status_code == 200
        body = resp.json()
        assert "status" in body
        assert body["canonical_state_owner"] == "forkOS PostgreSQL"
        assert body["expected_identity"]["version"] == "1.34.0"
