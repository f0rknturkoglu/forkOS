from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update

from app.core.models import Entity, Event
from app.db import SessionLocal
from app.main import app
from app.modules.media import MODULE, service
from app.modules.media import schemas as media_schemas
from app.modules.media.models import (
    MediaCollection,
    MediaConsumption,
    MediaCycle,
    MediaItem,
)


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as http:
        yield http


async def _create(client: AsyncClient, **overrides):
    payload = {
        "source": "manual",
        "title": f"Media {uuid.uuid4().hex[:8]}",
        "kind": "book",
        "progress": 0,
        "total": 100.5,
        "progress_measure": "page",
        "summary": "Aranabilir özet",
        "meta": {"language": "tr"},
        "provider_ids": {},
    }
    payload.update(overrides)
    response = await client.post("/api/media", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def test_media_library_is_cursor_paged_searchable_and_provider_deduplicated(
    client: AsyncClient,
):
    first = await _create(
        client,
        source="provider",
        title="Dune Messiah",
        provider="openlibrary",
        provider_id="OL123M",
        provider_ids={"openlibrary": "OL123M"},
        owned=True,
        monitored=True,
    )
    await _create(client, title="Unrelated title")

    duplicate = await client.post(
        "/api/media",
        json={
            "source": "provider",
            "title": "Dune Messiah duplicate",
            "kind": "book",
            "provider": "openlibrary",
            "provider_id": "OL123M",
        },
    )
    assert duplicate.status_code == 409

    page = await client.get(
        "/api/media",
        params={"q": "Aranabilir Dune", "owned": True, "limit": 1},
    )
    assert page.status_code == 200, page.text
    body = page.json()
    assert set(body) == {"items", "total", "next_cursor"}
    assert [item["id"] for item in body["items"]] == [first["id"]]
    assert isinstance(body["items"][0]["total"], (int, float))

    all_items = (await client.get("/api/media", params={"limit": 1})).json()
    assert all_items["total"] == 2
    assert all_items["next_cursor"]
    second_page = (
        await client.get(
            "/api/media", params={"limit": 1, "cursor": all_items["next_cursor"]}
        )
    ).json()
    assert len(second_page["items"]) == 1
    assert second_page["items"][0]["id"] != all_items["items"][0]["id"]


async def test_patch_preserves_unchanged_search_text(client: AsyncClient):
    item = await _create(client, title="Search cache", summary="needle phrase")
    patched = await client.patch(
        f"/api/media/{item['id']}", json={"status": "paused"}
    )
    assert patched.status_code == 200
    page = (await client.get("/api/media", params={"q": "needle"})).json()
    assert [row["id"] for row in page["items"]] == [item["id"]]


async def test_media_detail_lifecycle_preserves_child_first_delete_events(
    client: AsyncClient,
):
    item = await _create(client, title="Lifecycle book")
    item_id = item["id"]

    consumption = await client.post(
        f"/api/media/{item_id}/consumptions",
        json={"client_uuid": str(uuid.uuid4()), "action": "quick", "amount": 2.5},
    )
    assert consumption.status_code == 201, consumption.text

    trashed = await client.delete(f"/api/media/{item_id}")
    assert trashed.status_code == 200
    assert trashed.json()["archived_at"] is not None
    assert (await client.get("/api/media")).json()["total"] == 0
    trash_page = (await client.get("/api/media", params={"trashed": True})).json()
    assert [row["id"] for row in trash_page["items"]] == [item_id]

    restored = await client.post(f"/api/media/{item_id}/restore")
    assert restored.status_code == 200
    assert restored.json()["archived_at"] is None

    assert (await client.delete(f"/api/media/{item_id}/permanent")).status_code == 409
    assert (await client.delete(f"/api/media/{item_id}")).status_code == 200
    assert (await client.delete(f"/api/media/{item_id}/permanent")).status_code == 204
    assert (await client.get(f"/api/media/{item_id}")).status_code == 404

    async with SessionLocal() as session:
        rows = list(
            (
                await session.execute(
                    select(Event)
                    .where(Event.payload["title"].astext == "Lifecycle book")
                    .order_by(Event.id)
                )
            ).scalars()
        )
        assert {row.verb for row in rows} >= {
            "media.item_added",
            "media.item_trashed",
            "media.item_restored",
            "media.item_deleted",
        }
        deleted = next(row for row in rows if row.verb == "media.item_deleted")
        assert deleted.entity_id is None
        assert deleted.payload["kind"] == "book"


async def test_consumptions_are_idempotent_and_keep_correction_history(client: AsyncClient):
    item = await _create(client, kind="show", total=3, progress_measure=None)
    item_id = item["id"]
    command_id = str(uuid.uuid4())
    quick = {
        "client_uuid": command_id,
        "action": "quick",
        "duration_min": 42,
    }

    first = await client.post(f"/api/media/{item_id}/consumptions", json=quick)
    replay = await client.post(f"/api/media/{item_id}/consumptions", json=quick)
    assert first.status_code == replay.status_code == 201
    assert first.json()["id"] == replay.json()["id"]
    assert first.json()["measure"] == "episode"
    assert first.json()["amount"] == 1

    correction = await client.post(
        f"/api/media/{item_id}/consumptions",
        json={
            "client_uuid": str(uuid.uuid4()),
            "action": "set",
            "progress_after": 0.5,
        },
    )
    assert correction.status_code == 201, correction.text
    detail = (await client.get(f"/api/media/{item_id}")).json()
    assert detail["item"]["progress"] == 0.5
    assert len(detail["cycles"]) == 1
    assert len(detail["consumptions"]) == 2

    async with SessionLocal() as session:
        verbs = list(
            (
                await session.execute(
                    select(Event.verb).where(Event.entity_id == uuid.UUID(item_id))
                )
            ).scalars()
        )
        assert verbs.count("media.consumed") == 1
        assert verbs.count("media.progress_corrected") == 1


async def test_consumption_history_route_is_newest_first_and_in_openapi(
    client: AsyncClient,
):
    item = await _create(client, progress=0)
    item_id = item["id"]
    first_time = datetime.now(UTC) - timedelta(hours=1)
    second_time = datetime.now(UTC)
    for occurred_at in (first_time, second_time):
        response = await client.post(
            f"/api/media/{item_id}/consumptions",
            json={
                "client_uuid": str(uuid.uuid4()),
                "action": "quick",
                "occurred_at": occurred_at.isoformat(),
            },
        )
        assert response.status_code == 201, response.text

    history = await client.get(f"/api/media/{item_id}/consumptions")
    assert history.status_code == 200, history.text
    assert [row["occurred_at"] for row in history.json()] == sorted(
        [row["occurred_at"] for row in history.json()], reverse=True
    )
    assert (await client.get(f"/api/media/{uuid.uuid4()}/consumptions")).status_code == 404

    operation = app.openapi()["paths"]["/api/media/{item_id}/consumptions"]["get"]
    schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert schema["type"] == "array"
    assert schema["items"]["$ref"].endswith("/MediaConsumptionOut")


async def test_concurrent_distinct_consumptions_serialize_progress_and_first_cycle():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as setup_client:
        item = await _create(setup_client, kind="show", progress=0, total=10)
    item_id = uuid.UUID(item["id"])

    async def consume_once(command_id: uuid.UUID):
        async with SessionLocal() as session:
            return await service.consume(
                session,
                item_id,
                media_schemas.MediaConsumptionIn(
                    client_uuid=command_id, action="quick"
                ),
            )

    first, second = await asyncio.gather(
        consume_once(uuid.uuid4()), consume_once(uuid.uuid4())
    )
    assert first.id != second.id
    async with SessionLocal() as session:
        item_row = await session.get(MediaItem, item_id)
        cycle_count = len(
            list(
                (
                    await session.execute(
                        select(MediaCycle).where(MediaCycle.media_id == item_id)
                    )
                ).scalars()
            )
        )
        assert float(item_row.progress) == 2
        assert cycle_count == 1


async def test_concurrent_same_client_uuid_replays_single_winner():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as setup_client:
        item = await _create(setup_client, kind="show", progress=0, total=10)
    item_id = uuid.UUID(item["id"])
    command_id = uuid.uuid4()

    async def consume_once():
        async with SessionLocal() as session:
            return await service.consume(
                session,
                item_id,
                media_schemas.MediaConsumptionIn(
                    client_uuid=command_id, action="quick"
                ),
            )

    first, second = await asyncio.gather(consume_once(), consume_once())
    assert first.id == second.id
    async with SessionLocal() as session:
        rows = list(
            (
                await session.execute(
                    select(MediaConsumption).where(
                        MediaConsumption.client_uuid == command_id
                    )
                )
            ).scalars()
        )
        item_row = await session.get(MediaItem, item_id)
        assert len(rows) == 1
        assert float(item_row.progress) == 1


async def test_movie_quick_uses_item_measure_and_finishes_the_cycle(client: AsyncClient):
    item = await _create(client, kind="movie", total=None, progress_measure=None)
    response = await client.post(
        f"/api/media/{item['id']}/consumptions",
        json={"client_uuid": str(uuid.uuid4()), "action": "quick"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["measure"] == "item"
    detail = (await client.get(f"/api/media/{item['id']}")).json()
    assert detail["item"]["progress"] == detail["item"]["total"] == 1
    assert detail["item"]["status"] == "completed"
    assert detail["cycles"][0]["status"] == "completed"


async def test_unit_completion_is_stateful_and_rejects_future_release(client: AsyncClient):
    item = await _create(client, kind="anime", total=2, monitored=True)
    item_id = uuid.UUID(item["id"])
    async with SessionLocal() as session:
        released = await service.upsert_unit(
            session,
            item_id,
            media_schemas.MediaUnitUpsert(
                title="Episode 1",
                unit_type="episode",
                number=1,
                provider="anilist",
                provider_id="ep-1",
                release_at=datetime.now(UTC) - timedelta(days=1),
            ),
        )
        future = await service.upsert_unit(
            session,
            item_id,
            media_schemas.MediaUnitUpsert(
                title="Episode 2",
                unit_type="episode",
                number=2,
                provider="anilist",
                provider_id="ep-2",
                release_at=datetime.now(UTC) + timedelta(days=1),
            ),
        )

    async def command(action: str, unit_id: str):
        return await client.post(
            f"/api/media/{item_id}/consumptions",
            json={
                "client_uuid": str(uuid.uuid4()),
                "action": action,
                "unit_id": unit_id,
            },
        )

    assert (await command("complete_unit", str(released.id))).json()["progress_after"] == 1
    assert (await command("complete_unit", str(released.id))).json()["progress_after"] == 1
    assert (await command("uncomplete_unit", str(released.id))).json()["progress_after"] == 0
    blocked = await command("complete_unit", str(future.id))
    assert blocked.status_code == 409


async def test_unit_completion_state_is_scoped_to_each_repeat_cycle(client: AsyncClient):
    item = await _create(client, kind="show", total=10, progress=0)
    item_id = uuid.UUID(item["id"])
    async with SessionLocal() as session:
        unit = await service.upsert_unit(
            session,
            item_id,
            media_schemas.MediaUnitUpsert(
                title="Episode 1",
                unit_type="episode",
                number=1,
                provider="serial",
                provider_id="episode-1",
                release_at=datetime.now(UTC) - timedelta(days=1),
            ),
        )

    cycle_one = await client.post(
        f"/api/media/{item_id}/consumptions",
        json={
            "client_uuid": str(uuid.uuid4()),
            "action": "complete_unit",
            "unit_id": str(unit.id),
        },
    )
    assert cycle_one.json()["progress_after"] == 1
    assert (
        await client.post(
            f"/api/media/{item_id}/consumptions",
            json={"client_uuid": str(uuid.uuid4()), "action": "finish"},
        )
    ).status_code == 201
    assert (await client.post(f"/api/media/{item_id}/cycles", json={})).status_code == 201

    cycle_two = await client.post(
        f"/api/media/{item_id}/consumptions",
        json={
            "client_uuid": str(uuid.uuid4()),
            "action": "complete_unit",
            "unit_id": str(unit.id),
        },
    )
    assert cycle_two.status_code == 201, cycle_two.text
    assert cycle_two.json()["progress_after"] == 1
    assert cycle_two.json()["cycle_id"] != cycle_one.json()["cycle_id"]


@pytest.mark.parametrize(
    ("kind", "measure"),
    [
        ("show", "episode"),
        ("anime", "episode"),
        ("podcast", "episode"),
        ("manga", "chapter"),
        ("music", "track"),
        ("book", "page"),
        ("audiobook", "minute"),
        ("game", "hour"),
    ],
)
async def test_quick_defaults_to_one_in_the_kind_measure(
    client: AsyncClient, kind: str, measure: str
):
    item = await _create(client, kind=kind, progress=0, total=100, progress_measure=None)
    response = await client.post(
        f"/api/media/{item['id']}/consumptions",
        json={"client_uuid": str(uuid.uuid4()), "action": "quick"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["measure"] == measure
    assert response.json()["amount"] == 1


async def test_cycles_repeat_finish_and_released_unit_reopens_same_cycle(client: AsyncClient):
    item = await _create(client, kind="show", total=1, monitored=True)
    item_id = uuid.UUID(item["id"])
    finished = await client.post(
        f"/api/media/{item_id}/consumptions",
        json={"client_uuid": str(uuid.uuid4()), "action": "finish"},
    )
    assert finished.status_code == 201
    cycles = (await client.get(f"/api/media/{item_id}/cycles")).json()
    assert cycles[0]["status"] == "completed"

    repeated = await client.post(f"/api/media/{item_id}/cycles", json={})
    assert repeated.status_code == 201
    assert repeated.json()["ordinal"] == 2
    assert (await client.get(f"/api/media/{item_id}")).json()["item"]["progress"] == 0
    assert (await client.post(f"/api/media/{item_id}/cycles", json={})).status_code == 409

    await client.post(
        f"/api/media/{item_id}/consumptions",
        json={"client_uuid": str(uuid.uuid4()), "action": "finish"},
    )
    async with SessionLocal() as session:
        reopened = await service.upsert_unit(
            session,
            item_id,
            media_schemas.MediaUnitUpsert(
                title="Newly released episode",
                unit_type="episode",
                provider="tmdb",
                provider_id="new-episode",
                release_at=datetime.now(UTC) - timedelta(minutes=1),
            ),
        )
        assert reopened.created is True
        assert reopened.cycle_reopened is True
        latest = (
            await session.execute(
                select(MediaCycle)
                .where(MediaCycle.media_id == item_id)
                .order_by(MediaCycle.ordinal.desc())
            )
        ).scalars().first()
        media = await session.get(MediaItem, item_id)
        assert latest.ordinal == 2
        assert latest.status == "active"
        assert latest.last_caught_up_at is not None
        assert media.status == "in_progress"


async def test_collection_crud_membership_detail_dashboard_and_rebuild(client: AsyncClient):
    item = await _create(client, title="Collection title", kind="game", progress=0)
    item_id = item["id"]
    collection = await client.post(
        "/api/media/collections",
        json={"title": "Favorites", "description": "Hand-picked", "color": "#abc"},
    )
    assert collection.status_code == 201, collection.text
    collection_id = collection.json()["id"]

    member_path = f"/api/media/collections/{collection_id}/items/{item_id}"
    assert (await client.post(member_path)).status_code == 204
    assert (await client.post(member_path)).status_code == 204
    detail = (await client.get(f"/api/media/{item_id}")).json()
    assert [row["id"] for row in detail["collections"]] == [collection_id]
    filtered = (
        await client.get("/api/media", params={"collection_id": collection_id})
    ).json()
    assert filtered["total"] == 1

    await client.post(
        f"/api/media/{item_id}/consumptions",
        json={
            "client_uuid": str(uuid.uuid4()),
            "action": "quick",
            "amount": 2.25,
            "duration_min": 30,
        },
    )
    dashboard = (await client.get("/api/media/dashboard")).json()
    assert len(dashboard["continue_items"]) <= 4
    assert dashboard["recent_consumptions"]
    assert dashboard["stats"]["total_duration_min"] == 30

    async with SessionLocal() as session:
        media = await session.get(MediaItem, uuid.UUID(item_id))
        media.progress = 99
        await session.commit()
        result = await service.validate_progress(session, uuid.UUID(item_id), rebuild=True)
        assert result.valid is False
        assert result.expected == 2.25
        await session.refresh(media)
        assert media.progress == 2.25

    assert (await client.delete(member_path)).status_code == 204
    assert (await client.delete(f"/api/media/collections/{collection_id}")).status_code == 204
    async with SessionLocal() as session:
        assert await session.get(MediaCollection, uuid.UUID(collection_id)) is None
        assert await session.get(Entity, uuid.UUID(item_id)) is not None


async def test_nonzero_create_builds_matching_initial_cycle_and_consumption(
    client: AsyncClient,
):
    for source, identity in (
        ("manual", {}),
        ("provider", {"provider": "openlibrary", "provider_id": str(uuid.uuid4())}),
    ):
        item = await _create(client, source=source, progress=12.5, **identity)
        detail = (await client.get(f"/api/media/{item['id']}")).json()
        assert len(detail["cycles"]) == 1
        assert len(detail["consumptions"]) == 1
        assert detail["consumptions"][0]["action"] == "set"
        assert detail["consumptions"][0]["progress_after"] == 12.5
        async with SessionLocal() as session:
            validation = await service.validate_progress(
                session, uuid.UUID(item["id"])
            )
            assert validation.valid is True


async def test_patch_rejects_progress_completed_status_nulls_and_unknown_fields(
    client: AsyncClient,
):
    item = await _create(client, progress=0)
    path = f"/api/media/{item['id']}"
    for payload in (
        {"progress": 5},
        {"status": "completed"},
        {"status": None},
        {"kind": None},
        {"title": None},
        {"favorite": None},
        {"owned": None},
        {"ownership": None},
        {"monitored": None},
        {"meta": None},
        {"provider_ids": None},
        {"surprise": True},
    ):
        response = await client.patch(path, json=payload)
        assert response.status_code == 422, (payload, response.text)


async def test_patch_status_keeps_open_cycle_state_in_sync(client: AsyncClient):
    item = await _create(client, progress=0)
    path = f"/api/media/{item['id']}"

    assert (await client.patch(path, json={"status": "in_progress"})).status_code == 200
    detail = (await client.get(path)).json()
    assert detail["cycles"][0]["status"] == "active"
    assert detail["cycles"][0]["completed_at"] is None

    assert (await client.patch(path, json={"status": "paused"})).status_code == 200
    assert (await client.get(path)).json()["cycles"][0]["status"] == "paused"

    assert (await client.patch(path, json={"status": "in_progress"})).status_code == 200
    assert (await client.get(path)).json()["cycles"][0]["status"] == "active"

    assert (await client.patch(path, json={"status": "dropped"})).status_code == 200
    detail = (await client.get(path)).json()
    assert detail["cycles"][0]["status"] == "dropped"
    assert detail["cycles"][0]["completed_at"] is not None


async def test_provider_identity_is_required_unique_and_patchable(client: AsyncClient):
    missing_provider = await client.post(
        "/api/media",
        json={"source": "provider", "title": "Missing", "kind": "book"},
    )
    assert missing_provider.status_code == 422

    first = await _create(
        client,
        source="provider",
        provider="openlibrary",
        provider_id="provider-identity-1",
    )
    second = await _create(client, title="Second identity", progress=0)
    duplicate_patch = await client.patch(
        f"/api/media/{second['id']}",
        json={"provider": "openlibrary", "provider_id": "provider-identity-1"},
    )
    assert duplicate_patch.status_code == 409, duplicate_patch.text

    patched = await client.patch(
        f"/api/media/{second['id']}",
        json={"provider": "openlibrary", "provider_id": "provider-identity-2"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["provider_id"] == "provider-identity-2"
    assert first["provider_id"] == "provider-identity-1"


async def test_concurrent_provider_create_maps_database_race_to_conflict():
    identity = f"race-{uuid.uuid4()}"
    payloads = [
        media_schemas.MediaItemIn(
            source="provider",
            title=f"Provider race {index}",
            kind="book",
            provider="openlibrary",
            provider_id=identity,
        )
        for index in range(2)
    ]

    async def create(data: media_schemas.MediaItemIn):
        async with SessionLocal() as session:
            try:
                return await service.create_item(session, data)
            except service.MediaConflictError:
                return "conflict"

    results = await asyncio.gather(*(create(payload) for payload in payloads))
    assert sum(result == "conflict" for result in results) == 1
    assert sum(result != "conflict" for result in results) == 1


async def test_archived_media_does_not_leak_into_dashboard_upcoming_or_stats(
    client: AsyncClient,
):
    item = await _create(client, kind="show", progress=0, total=10)
    item_id = uuid.UUID(item["id"])
    await client.post(
        f"/api/media/{item_id}/consumptions",
        json={
            "client_uuid": str(uuid.uuid4()),
            "action": "quick",
            "duration_min": 44,
        },
    )
    async with SessionLocal() as session:
        await service.upsert_unit(
            session,
            item_id,
            media_schemas.MediaUnitUpsert(
                title="Archived future episode",
                unit_type="episode",
                release_at=datetime.now(UTC) + timedelta(days=1),
            ),
        )
    assert (await client.delete(f"/api/media/{item_id}")).status_code == 200

    dashboard = (await client.get("/api/media/dashboard")).json()
    assert all(row["id"] != str(item_id) for row in dashboard["continue_items"])
    assert all(row["media_id"] != str(item_id) for row in dashboard["upcoming"])
    assert all(
        row["media_id"] != str(item_id) for row in dashboard["recent_consumptions"]
    )
    assert dashboard["stats"]["total"] == 0
    assert dashboard["stats"]["total_duration_min"] == 0
    assert (await client.get("/api/media/upcoming")).json() == []


async def test_mutation_schema_and_cursor_validation_is_strict(client: AsyncClient):
    collection = await client.post("/api/media/collections", json={"title": "Strict"})
    collection_id = collection.json()["id"]
    for payload in ({"position": None}, {"title": None}, {"unknown": 1}):
        response = await client.patch(
            f"/api/media/collections/{collection_id}", json=payload
        )
        assert response.status_code == 422, (payload, response.text)

    for cursor in ("a", "____", "bm90LWpzb24"):
        response = await client.get("/api/media", params={"cursor": cursor})
        assert response.status_code == 422, (cursor, response.text)


@pytest.mark.parametrize("sort", ["score", "progress"])
async def test_equal_value_sorts_use_entity_id_as_final_tie_breaker(
    client: AsyncClient, sort: str
):
    rows = [
        await _create(client, progress=0, score=8, title=f"Tie {index}")
        for index in range(3)
    ]
    row_ids = [uuid.UUID(row["id"]) for row in rows]
    async with SessionLocal() as session:
        await session.execute(
            update(Entity)
            .where(Entity.id.in_(row_ids))
            .values(updated_at=datetime(2026, 1, 1, tzinfo=UTC))
        )
        await session.commit()
    page = (await client.get("/api/media", params={"sort": sort})).json()
    expected = sorted((row["id"] for row in rows), reverse=True)
    assert [row["id"] for row in page["items"]] == expected


@pytest.mark.no_database
def test_media_registers_complete_event_contract_and_restoration_helper():
    assert set(MODULE.event_verbs) == {
        "media.item_added",
        "media.item_updated",
        "media.item_trashed",
        "media.item_restored",
        "media.item_deleted",
        "media.cycle_started",
        "media.cycle_completed",
        "media.cycle_reopened",
        "media.consumed",
        "media.progress_corrected",
        "media.collection_created",
        "media.collection_updated",
        "media.collection_deleted",
        "media.collection_item_added",
        "media.collection_item_removed",
    }
    from app.core import entity

    assert callable(entity.restore_entity)
