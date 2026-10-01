"""Catalog availability, official scheduling and exact FreeHire run counters."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import BackgroundTasks
from sqlalchemy import func, select

from app.core.models import SourceRun, SourceSyncBatch
from app.db import SessionLocal
from app.modules.opportunity import sources_router, worker
from app.sources.base import (
    FetchOutcome,
    RawItem,
    ScrapeTelemetry,
    SourceClass,
    is_runnable,
    source_class,
    source_timeout_seconds,
)
from app.sources.catalog import opportunity_sources


@pytest.mark.no_database
def test_catalogued_is_not_runnable_and_classes_keep_overrides():
    catalog = {s.id: s for s in opportunity_sources()}
    assert not is_runnable(catalog["forkjob_core:linkedin"])
    assert is_runnable(catalog["forkjob_core:eures"])
    assert is_runnable(SimpleNamespace(id="unflagged"))
    assert source_class(catalog["forkjob_core:arbeidsplassen"]) is SourceClass.CRITICAL
    assert source_class(catalog["forkjob_core:workindenmark"]) is SourceClass.CRITICAL
    assert source_class(catalog["forkjob_core:eures"]) is SourceClass.SLOW_OPTIN
    assert source_class(catalog["forkjob_core:linkedin"]) is SourceClass.SLOW_OPTIN
    assert source_class(catalog["forkjob_core:freehire"]) is SourceClass.NORMAL
    for key in ["arbeidsplassen", "workindenmark", "eures", "linkedin", "freehire"]:
        source = catalog["forkjob_core:" + key]
        assert source_timeout_seconds(source) == source_timeout_seconds(source.id)


async def test_catalog_availability_is_explicit():
    async with SessionLocal() as session:
        rows = {r["id"]: r for r in await sources_router.source_catalog(session)}
    assert rows["forkjob_core:linkedin"]["runnable"] is False
    assert "robots" in rows["forkjob_core:linkedin"]["unavailable_reason"]
    assert rows["forkjob_core:linkedin"]["class"] == "slow_optin"
    assert rows["forkjob_core:linkedin"]["opt_in"] is True
    assert rows["forkjob_core:eures"]["runnable"] is True


@pytest.mark.parametrize("explicit_list", [False, True])
async def test_explicit_unavailable_rejected_before_mutation(explicit_list, monkeypatch):
    from httpx import ASGITransport, AsyncClient

    from app.main import app
    from app.worker import jobs

    mutation = AsyncMock()
    monkeypatch.setattr(jobs, "reclaim_stale_source_runs", mutation)
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        response = (
            await client.post(
                "/api/sources/refresh", json={"source_ids": ["osym", "forkjob_core:linkedin"]}
            )
            if explicit_list
            else await client.post("/api/sources/forkjob_core:linkedin/refresh")
        )
    assert response.status_code == 409 and "robots" in response.json()["detail"]
    mutation.assert_not_awaited()
    async with SessionLocal() as session:
        assert await session.scalar(select(func.count()).select_from(SourceSyncBatch)) == 0
        assert await session.scalar(select(func.count()).select_from(SourceRun)) == 0


@pytest.mark.no_database
@pytest.mark.parametrize("mode", ["critical", "general", "full"])
async def test_generic_unavailable_excluded_from_all_implicit_modes(mode, monkeypatch):
    sources = [
        SimpleNamespace(id="blocked-official", source_class="critical", runnable=False),
        SimpleNamespace(id="available-opt-in", source_class="slow_optin", runnable=True),
        SimpleNamespace(id="normal", source_class="normal"),
    ]
    monkeypatch.setattr(sources_router, "_catalog_sources", lambda: sources)
    mutation = AsyncMock(side_effect=RuntimeError("queue intercepted"))
    monkeypatch.setattr(sources_router.sync_service, "create_or_extend_batch", mutation)
    from app.worker import jobs

    monkeypatch.setattr(jobs, "reclaim_stale_source_runs", AsyncMock())
    session = AsyncMock()
    if mode == "critical":
        result = await sources_router.refresh_sources(
            sources_router.SourceRefreshIn(mode=mode), BackgroundTasks(), session
        )
        assert result["queued"] == 0
        mutation.assert_not_awaited()
    else:
        with pytest.raises(RuntimeError, match="queue intercepted"):
            await sources_router.refresh_sources(
                sources_router.SourceRefreshIn(mode=mode), BackgroundTasks(), session
            )
        assert mutation.call_args.args[1] == (
            ["normal", "available-opt-in"] if mode == "full" else ["normal"]
        )


@pytest.mark.parametrize("count,added", [(3, 2), (3, 3), (3, 0), (0, 0)])
async def test_freehire_persisted_exact_payload_counters(count, added, monkeypatch):
    outcome = FetchOutcome(
        items=[
            RawItem(
                external_id=str(i),
                title="Software Engineer",
                url=f"https://employer.example/jobs/{i}",
                extra={"organization": "Employer"},
            )
            for i in range(count)
        ],
        partial=True,
        telemetry=ScrapeTelemetry(
            items_seen=count + 7 if count else 0,
            metadata={"freehire_seen": count + 7 if count else 0, "freehire_unique": count},
        ),
    )
    source = SimpleNamespace(id="forkjob_core:freehire", fetch=AsyncMock(return_value=outcome))
    ingest = AsyncMock(return_value=added)
    monkeypatch.setattr(worker.service, "ingest_jobs", ingest)
    monkeypatch.setattr(worker, "_run_health_check", AsyncMock())
    assert await worker.poll_source(source) == added
    async with SessionLocal() as session:
        run = (await session.execute(select(SourceRun))).scalar_one()
        data = run.telemetry["metadata"]
    assert data["freehire_new_canonical"] == added
    assert data["freehire_not_new_canonical"] == data["freehire_overlap"] == count - added
    assert data["freehire_new_canonical"] + data["freehire_not_new_canonical"] == count
    assert "freehire_existing_strengthened" not in data
    if count:
        assert len(ingest.call_args.args[1]) == count
    else:
        ingest.assert_not_awaited()


async def test_freehire_three_payloads_two_new_one_existing_real_ingestion(monkeypatch):
    items = [
        RawItem(
            external_id=str(i),
            title="Software Engineer",
            url=f"https://employer.example/jobs/{i}",
            extra={"organization": "Employer"},
        )
        for i in range(3)
    ]
    async with SessionLocal() as session:
        assert (
            await worker.service.ingest_jobs(
                session, [worker.NativeJob(items[0])], "forkjob_core:employer"
            )
            == 1
        )
        await session.commit()
    outcome = FetchOutcome(
        items=items,
        partial=True,
        telemetry=ScrapeTelemetry(
            items_seen=10, metadata={"freehire_seen": 10, "freehire_unique": 3}
        ),
    )
    source = SimpleNamespace(id="forkjob_core:freehire", fetch=AsyncMock(return_value=outcome))
    monkeypatch.setattr(worker, "_run_health_check", AsyncMock())
    assert await worker.poll_source(source) == 2
    async with SessionLocal() as session:
        run = (await session.execute(select(SourceRun))).scalar_one()
        data = run.telemetry["metadata"]
    assert data["freehire_new_canonical"] == 2
    assert data["freehire_not_new_canonical"] == data["freehire_overlap"] == 1
    assert "freehire_existing_strengthened" not in data


@pytest.mark.parametrize("explicit_list", [False, True])
async def test_unknown_source_still_404_without_queue(explicit_list):
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        response = (
            await client.post("/api/sources/refresh", json={"source_ids": ["unknown-source"]})
            if explicit_list
            else await client.post("/api/sources/unknown-source/refresh")
        )
    assert response.status_code == 404
    async with SessionLocal() as session:
        assert await session.scalar(select(func.count()).select_from(SourceSyncBatch)) == 0
        assert await session.scalar(select(func.count()).select_from(SourceRun)) == 0
