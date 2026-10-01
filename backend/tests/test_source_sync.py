from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta
from importlib import import_module

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

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


async def test_sync_status_accepts_partial_source_progress(client: AsyncClient):
    """Kismi tarama terminal ve gorunur bir durumdur; response modeli 500 vermemeli."""
    batch_id = str(uuid.uuid4())
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """insert into source_sync_batch
                (id, status, source_ids, total_sources, completed_sources,
                 ok_sources, partial_sources, empty_sources, error_sources,
                 items_found, started_at)
                values (
                  cast(:id as uuid), 'running', cast(:sources as jsonb),
                  2, 1, 0, 1, 0, 0, 4, now()
                )"""
            ),
            {"id": batch_id, "sources": '["partial-source", "queued-source"]'},
        )
        await connection.execute(
            text(
                """insert into source_run
                (source, status, items_found, batch_id, started_at, finished_at)
                values ('partial-source', 'partial', 4, cast(:id as uuid), now(), now())"""
            ),
            {"id": batch_id},
        )
    try:
        response = await client.get("/api/sources/sync")
        assert response.status_code == 200
        payload = response.json()
        assert payload["active"]["partial_sources"] == 1
        assert {row["source"]: row["status"] for row in payload["sources"]} == {
            "partial-source": "partial",
            "queued-source": "queued",
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


async def test_refresh_endpoint_queues_and_starts_api_background_consumer(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    router_module = import_module("app.modules.opportunity.router")
    jobs = import_module("app.worker.jobs")
    consumed = 0

    async def fake_drain():
        nonlocal consumed
        consumed += 1
        return 0

    monkeypatch.setattr(jobs, "drain_source_sync_batches", fake_drain)
    response = await client.post(
        "/api/sources/refresh", json={"source_ids": ["osym"]}
    )

    assert response.status_code == 200
    assert response.json()["queued"] == 1
    assert consumed == 1
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


async def test_manual_drain_consumes_every_queue_slice(monkeypatch: pytest.MonkeyPatch):
    from app.worker import jobs

    slices = iter(((4, 2), (3, 5), (0, 0)))

    async def fake_consume(*, limit: int):
        assert limit == 4
        return next(slices)

    monkeypatch.setattr(jobs, "_consume_source_sync_batch", fake_consume)

    assert await jobs.drain_source_sync_batches(limit=4) == 7


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


async def test_concurrent_batch_creation_serializes_per_scope_and_unions_sources():
    from app.core.models import SourceSyncBatch
    from app.core.source_sync import ACTIVE_STATUSES, create_or_extend_batch

    async def queue(source_id: str):
        async with SessionLocal() as session:
            batch, _ = await create_or_extend_batch(
                session, [source_id], scope="media"
            )
            await session.commit()
            return batch.id

    first, second = await asyncio.gather(queue("media:tmdb"), queue("media:anilist"))
    assert first == second
    async with SessionLocal() as session:
        batches = list(
            (
                await session.execute(
                    select(SourceSyncBatch).where(
                        SourceSyncBatch.scope == "media",
                        SourceSyncBatch.status.in_(ACTIVE_STATUSES),
                    )
                )
            ).scalars()
        )
    assert len(batches) == 1
    assert set(batches[0].source_ids) == {"media:tmdb", "media:anilist"}


async def test_system_status_exposes_worker_heartbeat(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    from app.worker.jobs import record_worker_heartbeat

    system_router = import_module("app.modules.system.router")
    monkeypatch.setattr(system_router.app_settings, "worker_enabled", True)
    await record_worker_heartbeat()
    response = await client.get("/api/system/stats")

    assert response.status_code == 200
    assert response.json()["worker"]["status"] == "healthy"
    assert response.json()["worker"]["heartbeat_at"] is not None


async def test_system_status_marks_intentionally_disabled_worker(client: AsyncClient):
    response = await client.get("/api/system/stats")

    assert response.status_code == 200
    assert response.json()["worker"]["status"] == "disabled"


async def test_worker_heartbeat_tolerates_the_write_interval(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    """Bayatlik esigi kalp atisi ARALIGINDAN buyuk olmali.

    Aralik 5 dakika (app.core.heartbeat). Esik eskiden 3 dakikaydi; o
    kombinasyonda saglikli bir worker her iki yazim arasinda arayuzde
    "durdu" gorunurdu.
    """
    system_router = import_module("app.modules.system.router")
    monkeypatch.setattr(system_router.app_settings, "worker_enabled", True)

    async def status_for(age: timedelta) -> str:
        value = json.dumps({"at": (datetime.now(UTC) - age).isoformat()})
        async with SessionLocal() as session:
            await session.execute(
                text(
                    "insert into setting (key, value) values ('worker.heartbeat', cast(:v as jsonb)) "
                    "on conflict (key) do update set value = cast(:v as jsonb)"
                ),
                {"v": value},
            )
            await session.commit()
        response = await client.get("/api/system/stats")
        assert response.status_code == 200
        return response.json()["worker"]["status"]

    assert await status_for(timedelta(minutes=10)) == "healthy"
    assert await status_for(timedelta(minutes=20)) == "stale"


async def test_idle_source_queue_consume_writes_nothing():
    """Bos kuyrukta drain hicbir sey yazmamali -- ne kalp atisi ne satir.

    Kalp atisi yalnizca aktif bir batch'in sahipligini korumak icin okunur
    (bkz. `drain_is_alive`). Eskiden bos kuyrukta da dakikada bir
    UPDATE+COMMIT yaziliyordu.
    """
    from app.worker.jobs import DRAIN_HEARTBEAT_KEY, consume_source_sync_batches

    assert await consume_source_sync_batches() == 0

    async with SessionLocal() as session:
        drain = (
            await session.execute(
                text("select count(*) from setting where key = :key"),
                {"key": DRAIN_HEARTBEAT_KEY},
            )
        ).scalar_one()
        runs = (await session.execute(text("select count(*) from source_run"))).scalar_one()
        batches = (
            await session.execute(text("select count(*) from source_sync_batch"))
        ).scalar_one()

    assert (drain, runs, batches) == (0, 0, 0)


async def test_active_source_queue_consume_stamps_drain_heartbeat():
    """Batch AKTIFKEN kalp atisi yazilir: devralma karari buna bakar.

    Bir kaynak bitmis, digeri hala calisiyor: alinacak is yok ama sahiplik
    korunmali -- aksi halde her okuma yeni bir drain baslatirdi.
    """
    from app.worker.jobs import DRAIN_HEARTBEAT_KEY, consume_source_sync_batches

    batch_id = str(uuid.uuid4())
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """insert into source_sync_batch
                (id, status, source_ids, total_sources, started_at)
                values (cast(:id as uuid), 'running', cast(:sources as jsonb), 2, now())"""
            ),
            {"id": batch_id, "sources": '["alpha", "beta"]'},
        )
        for source, status in (("alpha", "ok"), ("beta", "running")):
            await connection.execute(
                text(
                    """insert into source_run (source, status, batch_id, started_at)
                    values (:source, :status, cast(:id as uuid), now())"""
                ),
                {"source": source, "status": status, "id": batch_id},
            )

    assert await consume_source_sync_batches() == 0

    async with SessionLocal() as session:
        owner = (
            await session.execute(
                text("select value->>'batch_id' from setting where key = :key"),
                {"key": DRAIN_HEARTBEAT_KEY},
            )
        ).scalar_one_or_none()
        batch_status = (
            await session.execute(
                text("select status from source_sync_batch where id = cast(:id as uuid)"),
                {"id": batch_id},
            )
        ).scalar_one()

    assert owner == batch_id, "aktif batch varken drain kalp atisi yazilmali"
    assert batch_status == "running"


async def test_manual_refresh_status_defaults_to_idle(client: AsyncClient):
    response = await client.get("/api/system/refresh")

    assert response.status_code == 200
    assert response.json() == {
        "status": "idle",
        "scope": "standard",
        "batch_id": None,
        "started": False,
        "started_at": None,
        "finished_at": None,
        "results": {},
        "errors": [],
    }


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


async def test_sync_read_reconciles_and_resumes_abandoned_batch(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    """10 saat `running` kalan batch gibi: okuma geri alir ve tuketimi devralir."""
    jobs = import_module("app.worker.jobs")
    drained = {"count": 0}

    async def fake_drain():
        drained["count"] += 1

    monkeypatch.setattr(jobs, "drain_source_sync_batches", fake_drain)

    batch_id = str(uuid.uuid4())
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """insert into source_sync_batch
                (id, status, source_ids, total_sources, completed_sources,
                 ok_sources, empty_sources, error_sources, items_found, created_at, started_at)
                values (cast(:id as uuid), 'running', '["osym"]', 1, 0, 0, 0, 0, 0,
                        now() - interval '10 hours', now() - interval '10 hours')"""
            ),
            {"id": batch_id},
        )
        await connection.execute(
            text(
                "insert into source_run (source, status, batch_id, started_at) "
                "values ('osym', 'running', cast(:id as uuid), now() - interval '10 hours')"
            ),
            {"id": batch_id},
        )

    payload = (await client.get("/api/sources/sync")).json()

    assert payload["active"]["id"] == batch_id
    assert payload["active"]["status"] == "queued"
    assert payload["sources"][0]["status"] == "queued"
    assert drained["count"] == 1


async def test_cache_endpoints_wire_stats_prune_and_confirm(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    router_module = import_module("app.modules.opportunity.sources_router")
    calls: dict[str, bool] = {}

    def fake_stats(config=None):
        calls["stats"] = True
        return {"files": 0}

    monkeypatch.setattr(router_module, "cache_stats", fake_stats)
    monkeypatch.setattr(router_module, "prune_cache", lambda config=None, **kwargs: {"removed": 0})
    monkeypatch.setattr(router_module, "clear_cache", lambda config=None: {"removed": 0})

    assert (await client.get("/api/sources/cache")).json() == {"files": 0}
    assert (await client.post("/api/sources/cache/prune", json={})).json() == {"removed": 0}
    assert calls.get("stats") is True

    refused = await client.post("/api/sources/cache/clear", json={"confirm": False})
    assert refused.status_code == 400
    allowed = await client.post("/api/sources/cache/clear", json={"confirm": True})
    assert allowed.status_code == 200
    assert allowed.json() == {"removed": 0}


async def test_exhausted_abandoned_source_finalizes_without_a_live_run():
    """Uc kez terk edilmis, hic canli kosumu olmayan kaynak batch'i kapatir."""
    from app.core.models import SourceRun
    from app.core.source_sync import (
        MAX_CLAIM_ATTEMPTS,
        claim_pending_sources,
        create_or_extend_batch,
    )
    from app.modules.opportunity import sync as sync_service

    async with SessionLocal() as session:
        batch, _ = await create_or_extend_batch(session, ["osym"])
        batch.status = "running"
        moment = datetime.now(UTC)
        for step in range(MAX_CLAIM_ATTEMPTS):
            session.add(
                SourceRun(
                    source="osym",
                    status="abandoned",
                    batch_id=batch.id,
                    started_at=moment - timedelta(minutes=step + 1),
                    finished_at=moment - timedelta(minutes=step),
                )
            )
        await session.commit()
        batch_id = batch.id

    async with SessionLocal() as session:
        claimed, pending = await claim_pending_sources(session, limit=4)
        assert claimed is not None
        assert pending == []

    async with SessionLocal() as session:
        status = await sync_service.current_status(session)
    assert status["active"] is None
    assert status["last_completed"]["id"] == str(batch_id)
    assert status["last_completed"]["status"] == "completed_with_errors"


async def test_partial_source_is_not_reclaimed_or_marked_exhausted():
    """Kismi basari terminaldir; ayni batch'te tekrar taranmaz."""
    from app.core.models import SourceRun
    from app.core.source_sync import claim_pending_sources, create_or_extend_batch
    from app.modules.opportunity import sync as sync_service

    async with SessionLocal() as session:
        batch, _ = await create_or_extend_batch(session, ["careerops:boards", "forkjob_core:remoteok"])
        batch.status = "running"
        for _ in range(3):
            session.add(SourceRun(source="careerops:boards", status="partial", batch_id=batch.id))
        await session.commit()
        batch_id = batch.id

    async with SessionLocal() as session:
        claimed, pending = await claim_pending_sources(session, limit=4)
        assert claimed is not None
        assert pending == ["forkjob_core:remoteok"]

    async with SessionLocal() as session:
        status = await sync_service.current_status(session)
    assert status["active"]["id"] == str(batch_id)
    assert {row["source"]: row["status"] for row in status["sources"]} == {
        "careerops:boards": "partial",
        "forkjob_core:remoteok": "running",
    }


async def test_reclaim_uses_per_source_lease():
    """Critical kaynak 90 sn'de, EURES 930 sn'de geri alinir."""
    from app.core.models import SourceRun
    from app.core.source_sync import create_or_extend_batch, pending_source_ids
    from app.modules.opportunity.sync import current_status
    from app.worker.jobs import reclaim_stale_source_runs

    async with SessionLocal() as session:
        batch, _ = await create_or_extend_batch(session, ["osym", "forkjob_core:eures"])
        batch.status = "running"
        started = datetime.now(UTC) - timedelta(minutes=10)
        session.add(SourceRun(source="osym", status="running", batch_id=batch.id, started_at=started))
        session.add(
            SourceRun(
                source="forkjob_core:eures", status="running", batch_id=batch.id, started_at=started
            )
        )
        await session.commit()

        changed = await reclaim_stale_source_runs(session)
        await session.commit()

        assert changed == 1
        assert await pending_source_ids(session, batch) == ["osym"]
        status = await current_status(session)
        by_source = {row["source"]: row["status"] for row in status["sources"]}
        assert by_source == {"osym": "queued", "forkjob_core:eures": "running"}


async def test_crashed_batch_reaches_terminal_state_without_worker():
    """Drain olmus olsa bile okuma/reconcile sonrasi batch terminal olur."""
    from app.core.models import SourceRun
    from app.core.source_sync import create_or_extend_batch
    from app.modules.opportunity import sync as sync_service
    from app.worker import jobs

    async with SessionLocal() as session:
        batch, _ = await create_or_extend_batch(session, ["alpha"])
        batch.status = "running"
        batch.started_at = datetime.now(UTC) - timedelta(hours=2)
        session.add(
            SourceRun(
                source="alpha",
                status="running",
                batch_id=batch.id,
                started_at=datetime.now(UTC) - timedelta(hours=2),
            )
        )
        await session.commit()
        batch_id = batch.id

    assert await jobs.drain_source_sync_batches(limit=2) == 0

    async with SessionLocal() as session:
        status = await sync_service.current_status(session)
    assert status["active"] is None
    assert status["last_completed"]["id"] == str(batch_id)
    assert status["last_completed"]["status"] == "completed_with_errors"


async def test_repeated_abandonment_errors_and_completes_batch():
    """Butcesini asan kaynak `error` yazilir; batch `running` kalmaz."""
    from app.core.models import SourceRun
    from app.core.source_sync import MAX_CLAIM_ATTEMPTS, create_or_extend_batch
    from app.worker.jobs import reclaim_stale_source_runs

    async with SessionLocal() as session:
        batch, _ = await create_or_extend_batch(session, ["osym"])
        batch.status = "running"
        moment = datetime.now(UTC)
        for step in range(MAX_CLAIM_ATTEMPTS - 1):
            session.add(
                SourceRun(
                    source="osym",
                    status="abandoned",
                    batch_id=batch.id,
                    started_at=moment - timedelta(minutes=step + 5),
                    finished_at=moment - timedelta(minutes=step + 4),
                )
            )
        stale = SourceRun(
            source="osym",
            status="running",
            batch_id=batch.id,
            started_at=moment - timedelta(minutes=10),
        )
        session.add(stale)
        await session.commit()

        changed = await reclaim_stale_source_runs(session)
        await session.commit()

        assert changed == 1
        assert stale.status == "error"
        await session.refresh(batch)
        assert batch.status == "completed_with_errors"


async def test_catalog_exposes_class_estimate_and_circuit(client: AsyncClient):
    rows = (await client.get("/api/sources/catalog")).json()
    by_id = {row["id"]: row for row in rows}

    assert by_id["osym"]["class"] == "critical"
    assert by_id["forkjob_core:linkedin"]["class"] == "slow_optin"
    assert by_id["forkjob_core:linkedin"]["opt_in"] is True
    assert by_id["forkjob_core:eures"]["class"] == "slow_optin"
    assert by_id["osym"]["circuit_open"] is False
    assert by_id["osym"]["estimated_seconds"] > 0
    assert by_id["osym"]["timeout_seconds"] == 60.0


async def test_general_refresh_excludes_opt_in_sources(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    jobs = import_module("app.worker.jobs")

    async def fake_drain():
        return 0

    monkeypatch.setattr(jobs, "drain_source_sync_batches", fake_drain)

    response = await client.post("/api/sources/refresh", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "general"
    assert body["estimated_seconds"] > 0

    status = (await client.get("/api/sources/sync")).json()
    queued = status["active"]["source_ids"]
    assert "forkjob_core:linkedin" not in queued
    assert "forkjob_core:eures" not in queued
    assert "osym" in queued
    # critical once gelir: ilk kaynak ATS/duyuru olmali
    assert queued[0] in {"osym", "ylsy", "yok-msc"} or queued[0].startswith("forkjob_core:greenhouse")
    assert body["total_sources"] == len(queued)


async def test_explicit_runnable_opt_in_selection_is_still_allowed(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    jobs = import_module("app.worker.jobs")

    async def fake_drain():
        return 0

    monkeypatch.setattr(jobs, "drain_source_sync_batches", fake_drain)

    response = await client.post(
        "/api/sources/refresh", json={"source_ids": ["forkjob_core:eures"]}
    )
    assert response.status_code == 200
    assert response.json()["queued"] == 1

    status = (await client.get("/api/sources/sync")).json()
    assert status["active"]["source_ids"] == ["forkjob_core:eures"]


async def test_full_mode_deliberately_includes_opt_in_sources(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    jobs = import_module("app.worker.jobs")

    async def fake_drain():
        return 0

    monkeypatch.setattr(jobs, "drain_source_sync_batches", fake_drain)

    response = await client.post("/api/sources/refresh", json={"mode": "full"})
    assert response.status_code == 200
    assert response.json()["mode"] == "full"

    status = (await client.get("/api/sources/sync")).json()
    assert "forkjob_core:linkedin" not in status["active"]["source_ids"]
    assert "forkjob_core:eures" in status["active"]["source_ids"]
    assert status["active"]["total_sources"] > 77
