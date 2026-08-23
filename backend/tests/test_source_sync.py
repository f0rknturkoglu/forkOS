from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from importlib import import_module

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
        assert first.status == "queued"
        assert first.started_at is None
        second, second_new = await create_or_extend_batch(session, ["beta", "gamma"])
        assert second.id == first.id
        assert first_new == ["alpha", "beta"]
        assert second_new == ["gamma"]
        assert second.total_sources == 3
        await session.rollback()


async def test_refresh_endpoint_only_queues_without_in_process_executor(
    client: AsyncClient,
):
    router_module = import_module("app.modules.opportunity.router")
    response = await client.post(
        "/api/sources/refresh", json={"source_ids": ["osym"]}
    )

    assert response.status_code == 200
    assert response.json()["queued"] == 1
    assert not hasattr(router_module, "_refresh_many")
    status = (await client.get("/api/sources/sync")).json()
    assert status["active"]["status"] == "queued"


async def test_stale_running_source_is_abandoned_and_requeued():
    from app.core.models import SourceRun
    from app.modules.opportunity.sync import (
        create_or_extend_batch,
        current_status,
        pending_source_ids,
        reconcile_stale_runs,
    )

    async with SessionLocal() as session:
        batch, _ = await create_or_extend_batch(session, ["osym"])
        batch.status = "running"
        batch.started_at = datetime.now(UTC) - timedelta(minutes=30)
        session.add(
            SourceRun(
                source="osym",
                status="running",
                batch_id=batch.id,
                started_at=datetime.now(UTC) - timedelta(minutes=30),
            )
        )
        await session.commit()

        abandoned = await reconcile_stale_runs(
            session, older_than=datetime.now(UTC) - timedelta(minutes=10)
        )
        await session.commit()

        assert abandoned == 1
        assert await pending_source_ids(session, batch) == ["osym"]
        run = (await session.execute(text("select status from source_run"))).scalar_one()
        assert run == "abandoned"
        status = await current_status(session)
        assert status["sources"][0]["status"] == "queued"


async def test_worker_consumes_a_persistent_batch(monkeypatch: pytest.MonkeyPatch):
    from app.core.models import SourceRun
    from app.modules.opportunity import sync as sync_service
    from app.worker import jobs

    async with SessionLocal() as session:
        batch, _ = await sync_service.create_or_extend_batch(session, ["osym"])
        batch_id = batch.id
        await session.commit()

    async def fake_poll(source_id: str, *, batch_id=None):
        assert source_id == "osym"
        async with SessionLocal() as session:
            session.add(
                SourceRun(
                    source=source_id,
                    status="ok",
                    items_found=3,
                    batch_id=batch_id,
                    finished_at=datetime.now(UTC),
                )
            )
            await sync_service.finish_batch_source(
                session, batch_id, status="ok", items_found=3
            )
            await session.commit()
        return 3

    monkeypatch.setattr(jobs, "poll_named_source", fake_poll)

    assert await jobs.consume_source_sync_batches(limit=4) == 3
    async with SessionLocal() as session:
        status = await sync_service.current_status(session)
    assert status["active"] is None
    assert status["last_completed"]["id"] == str(batch_id)
    assert status["last_completed"]["items_found"] == 3


async def test_batch_counters_are_derived_once_per_source():
    from app.core.models import SourceRun
    from app.modules.opportunity import sync as sync_service

    async with SessionLocal() as session:
        batch, _ = await sync_service.create_or_extend_batch(session, ["alpha", "beta"])
        batch.status = "running"
        session.add(
            SourceRun(
                source="alpha",
                status="ok",
                items_found=2,
                batch_id=batch.id,
                finished_at=datetime.now(UTC),
            )
        )
        await sync_service.finish_batch_source(
            session, batch.id, status="ok", items_found=2
        )
        await sync_service.finish_batch_source(
            session, batch.id, status="ok", items_found=2
        )

        assert batch.status == "running"
        assert batch.completed_sources == 1
        assert batch.ok_sources == 1
        assert batch.items_found == 2


async def test_two_workers_atomically_reserve_distinct_batch_sources():
    from app.core.source_sync import claim_pending_sources, create_or_extend_batch

    async with SessionLocal() as session:
        batch, _ = await create_or_extend_batch(session, ["alpha", "beta"])
        batch_id = batch.id
        await session.commit()

    async def claim_one():
        async with SessionLocal() as session:
            claimed_batch, sources = await claim_pending_sources(session, limit=1)
            return claimed_batch.id if claimed_batch else None, sources

    first, second = await asyncio.gather(claim_one(), claim_one())
    assert first[0] == second[0] == batch_id
    assert set(first[1] + second[1]) == {"alpha", "beta"}
    assert set(first[1]).isdisjoint(second[1])

    async with SessionLocal() as session:
        running = list(
            (
                await session.execute(
                    text(
                        "select source from source_run where batch_id=cast(:id as uuid) "
                        "and status='running' order by source"
                    ),
                    {"id": batch_id},
                )
            ).scalars()
        )
    assert running == ["alpha", "beta"]


async def test_system_status_exposes_worker_heartbeat(client: AsyncClient):
    from app.worker.jobs import record_worker_heartbeat

    await record_worker_heartbeat()
    response = await client.get("/api/system/stats")

    assert response.status_code == 200
    assert response.json()["worker"]["status"] == "healthy"
    assert response.json()["worker"]["heartbeat_at"] is not None


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
