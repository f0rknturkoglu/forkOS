from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.core.models import SourceRun
from app.db import SessionLocal
from app.main import app
from app.modules.media import service
from app.modules.media.models import MediaCycle, MediaItem, MediaUnit
from app.modules.media.schemas import MediaItemIn, MediaUnitUpsert


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as http:
        yield http


async def test_provider_identity_prevents_same_number_unit_collision():
    async with SessionLocal() as session:
        item = await service.create_item(
            session, MediaItemIn(title="Series", kind="show")
        )
        season_one = await service.upsert_unit(
            session,
            item.id,
            MediaUnitUpsert(
                title="S1E1",
                unit_type="episode",
                number=1,
                provider="tmdb",
                provider_id="tv:10:s1:e1",
                meta={"season": 1},
            ),
        )
        season_two = await service.upsert_unit(
            session,
            item.id,
            MediaUnitUpsert(
                title="S2E1",
                unit_type="episode",
                number=1,
                provider="tmdb",
                provider_id="tv:10:s2:e1",
                meta={"season": 2},
            ),
        )

        assert season_one.id != season_two.id
        assert await session.scalar(
            select(func.count()).select_from(MediaUnit).where(MediaUnit.media_id == item.id)
        ) == 2


async def test_future_unit_release_transition_reopens_once_but_backfill_does_not(
    client: AsyncClient,
):
    created = await client.post(
        "/api/media",
        json={"title": "Series", "kind": "show", "total": 1, "monitored": True},
    )
    item_id = uuid.UUID(created.json()["id"])
    finished = await client.post(
        f"/api/media/{item_id}/consumptions",
        json={"client_uuid": str(uuid.uuid4()), "action": "finish"},
    )
    assert finished.status_code == 201

    async with SessionLocal() as session:
        future = await service.upsert_unit(
            session,
            item_id,
            MediaUnitUpsert(
                title="Future",
                unit_type="episode",
                number=2,
                provider="tmdb",
                provider_id="tv:1:s1:e2",
                release_at=datetime.now(UTC) + timedelta(days=1),
            ),
        )
        assert future.cycle_reopened is False

        cycle = (
            await session.execute(
                select(MediaCycle).where(MediaCycle.media_id == item_id)
            )
        ).scalar_one()
        cycle.completed_at = datetime.now(UTC) - timedelta(days=2)
        await session.commit()

        # Provider timestamps normally stay constant while wall time crosses them.
        # Simulate the next day's poll with an already-crossed persisted timestamp.
        unit = await session.get(MediaUnit, future.id)
        released_at = datetime.now(UTC) - timedelta(minutes=1)
        unit.release_at = released_at
        await session.commit()

        released = await service.upsert_unit(
            session,
            item_id,
            MediaUnitUpsert(
                title="Future",
                unit_type="episode",
                number=2,
                provider="tmdb",
                provider_id="tv:1:s1:e2",
                release_at=released_at,
            ),
        )
        assert released.created is False
        assert released.cycle_reopened is True

        repeated = await service.upsert_unit(
            session,
            item_id,
            MediaUnitUpsert(
                title="Future",
                unit_type="episode",
                number=2,
                provider="tmdb",
                provider_id="tv:1:s1:e2",
                release_at=datetime.now(UTC) - timedelta(minutes=2),
            ),
        )
        assert repeated.cycle_reopened is False

        # Aynı cycle yeniden tamamlanınca eski bir backfill yeni yayın sayılmaz.
        cycle = (
            await session.execute(
                select(MediaCycle).where(MediaCycle.media_id == item_id)
            )
        ).scalar_one()
        cycle.status = "completed"
        cycle.completed_at = datetime.now(UTC)
        item = await session.get(MediaItem, item_id)
        item.status = "completed"
        item.finished_at = datetime.now(UTC)
        await session.commit()
        backfill = await service.upsert_unit(
            session,
            item_id,
            MediaUnitUpsert(
                title="Historical",
                unit_type="episode",
                number=1,
                provider="tmdb",
                provider_id="tv:1:s1:e1",
                release_at=datetime.now(UTC) - timedelta(days=100),
            ),
        )
        assert backfill.created is True
        assert backfill.cycle_reopened is False


async def test_missed_release_reopens_only_when_after_latest_cycle_completion(
    client: AsyncClient,
):
    async def completed_item(title: str) -> tuple[uuid.UUID, datetime]:
        created = await client.post(
            "/api/media",
            json={"title": title, "kind": "show", "total": 1, "monitored": True},
        )
        item_id = uuid.UUID(created.json()["id"])
        await client.post(
            f"/api/media/{item_id}/consumptions",
            json={"client_uuid": str(uuid.uuid4()), "action": "finish"},
        )
        completed_at = datetime.now(UTC) - timedelta(days=2)
        async with SessionLocal() as session:
            cycle = await session.scalar(
                select(MediaCycle).where(MediaCycle.media_id == item_id)
            )
            cycle.completed_at = completed_at
            item = await session.get(MediaItem, item_id)
            item.finished_at = completed_at
            await session.commit()
        return item_id, completed_at

    missed_id, completed_at = await completed_item("Missed")
    async with SessionLocal() as session:
        missed = await service.upsert_unit(
            session,
            missed_id,
            MediaUnitUpsert(
                title="Released during downtime",
                unit_type="episode",
                provider="tmdb",
                provider_id="tv:2:s1:e2",
                release_at=completed_at + timedelta(days=1),
            ),
        )
        assert missed.created is True
        assert missed.cycle_reopened is True

    historical_id, completed_at = await completed_item("Historical")
    async with SessionLocal() as session:
        historical = await service.upsert_unit(
            session,
            historical_id,
            MediaUnitUpsert(
                title="Old backfill",
                unit_type="episode",
                provider="tmdb",
                provider_id="tv:3:s1:e1",
                release_at=completed_at - timedelta(seconds=1),
            ),
        )
        assert historical.created is True
        assert historical.cycle_reopened is False


async def test_tmdb_item_identity_is_kind_qualified_on_create(client: AsyncClient):
    movie = await client.post(
        "/api/media",
        json={
            "source": "provider",
            "title": "Movie",
            "kind": "movie",
            "provider": "tmdb",
            "provider_id": "42",
        },
    )
    show = await client.post(
        "/api/media",
        json={
            "source": "provider",
            "title": "Show",
            "kind": "show",
            "provider": "tmdb",
            "provider_id": "42",
        },
    )
    assert movie.status_code == show.status_code == 201
    assert movie.json()["provider_id"] == "movie:42"
    assert show.json()["provider_id"] == "tv:42"
    assert movie.json()["provider_ids"]["tmdb"] == "42"
    assert show.json()["provider_ids"]["tmdb"] == "42"


async def test_tmdb_legacy_raw_identity_still_deduplicates_same_kind(
    client: AsyncClient,
):
    created = await client.post(
        "/api/media",
        json={
            "source": "provider",
            "title": "Legacy",
            "kind": "show",
            "provider": "tmdb",
            "provider_id": "42",
        },
    )
    async with SessionLocal() as session:
        item = await session.get(MediaItem, uuid.UUID(created.json()["id"]))
        item.provider_id = "42"
        await session.commit()

    duplicate = await client.post(
        "/api/media",
        json={
            "source": "provider",
            "title": "Duplicate",
            "kind": "show",
            "provider": "tmdb",
            "provider_id": "tv:42",
        },
    )
    assert duplicate.status_code == 409


async def test_media_operational_endpoints_have_typed_openapi_and_not_ready_error(
    client: AsyncClient,
):
    created = await client.post(
        "/api/media",
        json={
            "source": "provider",
            "title": "Movie",
            "kind": "movie",
            "provider": "tmdb",
            "provider_id": "7",
            "monitored": True,
        },
    )
    response = await client.post("/api/media/sync", params={"provider": "tmdb"})
    assert response.status_code == 422
    assert "hazır değil" in response.text

    schema = app.openapi()["paths"]
    assert "$ref" in schema["/api/media/providers"]["get"]["responses"]["200"][
        "content"
    ]["application/json"]["schema"]["items"]
    assert "anyOf" in schema["/api/media/sync"]["post"]["responses"]["200"][
        "content"
    ]["application/json"]["schema"]

    await client.delete(f"/api/media/{created.json()['id']}")


async def test_provider_endpoint_unions_capabilities_across_kind_adapters(
    client: AsyncClient,
):
    providers = (await client.get("/api/media/providers")).json()
    tmdb = next(row for row in providers if row["id"] == "tmdb")
    assert tmdb["kinds"] == ["movie", "show"]
    assert tmdb["capabilities"]["units"] is True
    assert tmdb["capabilities"]["upcoming"] is True


async def test_provider_endpoint_exposes_latest_source_run_item_count(
    client: AsyncClient,
):
    async with SessionLocal() as session:
        session.add_all(
            [
                SourceRun(
                    source="media:tmdb:first-item",
                    status="ok",
                    items_found=2,
                    started_at=datetime(2026, 1, 1, tzinfo=UTC),
                    finished_at=datetime(2026, 1, 1, 0, 1, tzinfo=UTC),
                ),
                SourceRun(
                    source="media:tmdb:second-item",
                    status="ok",
                    items_found=7,
                    started_at=datetime(2026, 1, 2, tzinfo=UTC),
                    finished_at=datetime(2026, 1, 2, 0, 1, tzinfo=UTC),
                ),
            ]
        )
        await session.commit()

    providers = (await client.get("/api/media/providers")).json()
    tmdb = next(row for row in providers if row["id"] == "tmdb")

    assert tmdb["last_items_found"] == 7
