from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db import SessionLocal, engine
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


async def test_sync_status_reports_persistent_batch_progress(client: AsyncClient):
    batch_id = str(uuid.uuid4())
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """insert into source_sync_batch
                (id, status, source_ids, total_sources, completed_sources,
                 ok_sources, empty_sources, error_sources, items_found, started_at)
                values (
                  cast(:id as uuid), 'running', cast(:sources as jsonb),
                  3, 2, 1, 0, 1, 7, now()
                )"""
            ),
            {"id": batch_id, "sources": '["alpha", "beta", "gamma"]'},
        )
        await connection.execute(
            text(
                """insert into source_run
                (source, status, items_found, batch_id, started_at, finished_at)
                values ('alpha', 'ok', 7, cast(:id as uuid), now(), now()),
                       ('beta', 'error', 0, cast(:id as uuid), now(), now()),
                       ('gamma', 'running', 0, cast(:id as uuid), now(), null)"""
            ),
            {"id": batch_id},
        )
    try:
        response = await client.get("/api/sources/sync")
        assert response.status_code == 200
        payload = response.json()
        assert payload["active"]["id"] == batch_id
        assert payload["active"]["progress_pct"] == 66
        assert payload["active"]["items_found"] == 7
        assert {row["source"]: row["status"] for row in payload["sources"]} == {
            "alpha": "ok",
            "beta": "error",
            "gamma": "running",
        }
    finally:
        async with engine.begin() as connection:
            await connection.execute(
                text("delete from source_run where batch_id = cast(:id as uuid)"),
                {"id": batch_id},
            )
            await connection.execute(
                text("delete from source_sync_batch where id = cast(:id as uuid)"),
                {"id": batch_id},
            )


async def test_extending_active_batch_only_adds_new_sources():
    from app.modules.opportunity.sync import create_or_extend_batch

    async with SessionLocal() as session:
        first, first_new = await create_or_extend_batch(session, ["alpha", "beta"])
        second, second_new = await create_or_extend_batch(session, ["beta", "gamma"])
        assert second.id == first.id
        assert first_new == ["alpha", "beta"]
        assert second_new == ["gamma"]
        assert second.total_sources == 3
        await session.rollback()


async def test_sync_status_keeps_the_latest_completed_summary(client: AsyncClient):
    batch_id = str(uuid.uuid4())
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """insert into source_sync_batch
                (id, status, source_ids, total_sources, completed_sources,
                 ok_sources, items_found, started_at, finished_at)
                values (
                  cast(:id as uuid), 'completed', '["osym"]', 1, 1,
                  1, 12, now() - interval '2 seconds', now()
                )"""
            ),
            {"id": batch_id},
        )
    try:
        payload = (await client.get("/api/sources/sync")).json()
        assert payload["active"] is None
        assert payload["last_completed"]["id"] == batch_id
        assert payload["last_completed"]["items_found"] == 12
    finally:
        async with engine.begin() as connection:
            await connection.execute(
                text("delete from source_sync_batch where id = cast(:id as uuid)"),
                {"id": batch_id},
            )
