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


async def test_health_hides_orphan_rss_runs(client: AsyncClient):
    active_id = uuid.uuid4()
    orphan_id = uuid.uuid4()
    external_source = f"health-test-{uuid.uuid4().hex}"
    active_source = f"rss:{active_id}"
    orphan_source = f"rss:{orphan_id}"
    async with engine.begin() as connection:
        await connection.execute(
            text("insert into entity (id, type, title) values (:id, 'feed', 'Health feed')"),
            {"id": active_id},
        )
        await connection.execute(
            text("insert into feed (id, url) values (:id, 'https://example.com/feed')"),
            {"id": active_id},
        )
        await connection.execute(
            text(
                "insert into source_run (source, status, error, finished_at) "
                "values (:active, 'error', 'active', now()), "
                "(:orphan, 'error', 'orphan', now()), "
                "(:external, 'error', 'external', now())"
            ),
            {"active": active_source, "orphan": orphan_source, "external": external_source},
        )
    try:
        payload = (await client.get("/api/sources/health", params={"limit": 2000})).json()
        sources = {row["source"] for row in payload}
        assert active_source in sources
        assert external_source in sources
        assert orphan_source not in sources
    finally:
        async with engine.begin() as connection:
            await connection.execute(
                text("delete from source_run where source in (:active, :orphan, :external)"),
                {"active": active_source, "orphan": orphan_source, "external": external_source},
            )
            await connection.execute(text("delete from entity where id = :id"), {"id": active_id})
