from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.time import local_end_of_day, local_today
from app.db import SessionLocal
from app.main import app
from app.modules.media import schemas as media_schemas
from app.modules.media import service
from app.modules.system.models import Setting


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as http:
        yield http


async def _create(client: AsyncClient, **overrides):
    payload = {
        "source": "manual",
        "title": f"Deadline {uuid.uuid4().hex[:8]}",
        "kind": "book",
        "progress": 0,
        "total": 100,
        "progress_measure": "page",
        "provider_ids": {},
    }
    payload.update(overrides)
    response = await client.post("/api/media", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def _deadlines(client: AsyncClient) -> list[dict]:
    response = await client.get("/api/deadlines")
    assert response.status_code == 200, response.text
    return response.json()


async def _upcoming(client: AsyncClient) -> dict:
    response = await client.get("/api/media/upcoming")
    assert response.status_code == 200, response.text
    return response.json()


async def test_item_release_date_deadline_is_timezone_aware_end_of_day(client: AsyncClient):
    release_day = local_today() + timedelta(days=5)
    item = await _create(client, release_date=release_day.isoformat(), monitored=False)

    row = next(entry for entry in await _deadlines(client) if entry["entity_id"] == item["id"])
    assert row["module"] == "media"
    assert row["type"] == "media_item"
    due_at = datetime.fromisoformat(row["due_at"])
    assert due_at.tzinfo is not None
    assert due_at == local_end_of_day(release_day)

    upcoming = await _upcoming(client)
    assert upcoming["total"] == 1
    entry = upcoming["entries"][0]
    assert entry["entry_type"] == "item"
    assert entry["entity_id"] == item["id"]
    assert entry["media_title"] == item["title"]
    assert datetime.fromisoformat(entry["release_at"]) == due_at


async def test_unit_release_supersedes_item_release_for_same_media(client: AsyncClient):
    release_day = local_today() + timedelta(days=5)
    item = await _create(client, release_date=release_day.isoformat())
    unit_release = datetime.now(UTC) + timedelta(days=2)
    async with SessionLocal() as session:
        await service.upsert_unit(
            session,
            uuid.UUID(item["id"]),
            media_schemas.MediaUnitUpsert(
                title="Bölüm 1",
                unit_type="episode",
                number=1,
                release_at=unit_release,
                cover_path="/api/media/assets/episode-1.jpg",
            ),
        )

    rows = [entry for entry in await _deadlines(client) if entry["module"] == "media"]
    assert rows, rows
    assert all(entry["type"] == "media_unit" for entry in rows), rows
    assert item["id"] not in {entry["entity_id"] for entry in rows}

    upcoming = await _upcoming(client)
    assert upcoming["total"] == 1
    entry = upcoming["entries"][0]
    assert entry["entry_type"] == "unit"
    assert entry["entity_id"] == item["id"] or entry["media_id"] == item["id"]
    assert entry["media_id"] == item["id"]
    assert entry["media_title"] == item["title"]
    assert entry["title"] == "Bölüm 1"
    assert entry["unit_type"] == "episode"
    assert entry["number"] == 1
    assert entry["cover_url"] == "/api/media/assets/episode-1.jpg"
    assert datetime.fromisoformat(entry["release_at"]) == unit_release


async def test_upcoming_window_uses_setting_when_days_absent(client: AsyncClient):
    await _create(
        client, release_date=(local_today() + timedelta(days=10)).isoformat()
    )
    # Varsayilan pencere 30 gun.
    assert (await _upcoming(client))["total"] == 1

    async with SessionLocal() as session:
        session.add(Setting(key="media.upcoming_days", value=3))
        await session.commit()
    assert (await _upcoming(client))["total"] == 0
    explicit = await client.get("/api/media/upcoming", params={"days": 30})
    assert explicit.json()["total"] == 1


async def test_upcoming_filters_by_kind_and_provider(client: AsyncClient):
    await _create(client, kind="book", release_date=(local_today() + timedelta(days=5)).isoformat())
    await _create(
        client,
        kind="show",
        source="provider",
        provider="tmdb",
        provider_id="tv:1",
        release_date=(local_today() + timedelta(days=6)).isoformat(),
    )
    assert (await _upcoming(client))["total"] == 2
    by_kind = await client.get("/api/media/upcoming", params={"kind": "show"})
    assert by_kind.json()["total"] == 1
    assert by_kind.json()["entries"][0]["kind"] == "show"
    by_provider = await client.get("/api/media/upcoming", params={"provider": "tmdb"})
    assert by_provider.json()["total"] == 1
    assert by_provider.json()["entries"][0]["provider"] == "tmdb"


async def test_deadlines_endpoint_orders_media_date_rows_beside_datetime_rows(
    client: AsyncClient,
):
    release_day = local_today() + timedelta(days=3)
    media = await _create(client, release_date=release_day.isoformat())

    project = await client.post("/api/projects", json={"title": "Karma proje"})
    assert project.status_code == 201, project.text
    milestone = await client.post(
        f"/api/projects/{project.json()['id']}/milestones",
        json={
            "title": "Karma kilometre taşı",
            "due_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        },
    )
    assert milestone.status_code == 201, milestone.text

    rows = await _deadlines(client)
    by_entity = {entry["entity_id"]: entry for entry in rows}
    assert media["id"] in by_entity
    assert milestone.json()["id"] in by_entity
    # date/datetime karisimi TypeError uretmemeli; siralama zaman ekseninde.
    ordered = [datetime.fromisoformat(entry["due_at"]) for entry in rows]
    assert ordered == sorted(ordered)
    assert datetime.fromisoformat(by_entity[media["id"]]["due_at"]) == local_end_of_day(
        release_day
    )
