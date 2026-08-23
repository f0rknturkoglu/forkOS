from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db import engine
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as http:
        yield http


async def _create_media(client: AsyncClient, **overrides):
    payload = {
        "source": "manual",
        "title": f"Today media {uuid.uuid4().hex[:8]}",
        "kind": "book",
        "status": "in_progress",
        "progress": 12,
        "total": 100,
        "progress_measure": "page",
        "cover_url": "https://example.com/remote-cover.jpg",
    }
    payload.update(overrides)
    response = await client.post("/api/media", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def test_today_agenda_returns_planned_media_metadata_without_generic_duplicate(
    client: AsyncClient,
):
    day = date.today()
    item = await _create_media(client, cover_path="local-cover.webp")
    slot = (
        await client.post(
            "/api/plan",
            json={
                "entity_id": item["id"],
                "day": day.isoformat(),
                "start_min": 630,
                "duration_min": 45,
            },
        )
    ).json()

    response = await client.get("/api/today/agenda", params={"day": day.isoformat()})

    assert response.status_code == 200, response.text
    agenda = response.json()
    rows = agenda["timed"] + agenda["checklist"] + agenda["completed"]
    matches = [row for row in rows if row["id"] == item["id"]]
    assert len(matches) == 1
    assert matches[0] == {
        **matches[0],
        "kind": "media",
        "source": "planned",
        "slot_id": slot["id"],
        "title": item["title"],
        "duration_min": 45,
        "media_kind": "book",
        "media_status": "in_progress",
        "progress_label": "12 / 100 sayfa",
        "cover_url": "/api/media/assets/local-cover.webp",
        "completed": False,
        "read_only": False,
        "action": "log_media",
    }
    assert matches[0]["starts_at"].startswith(f"{day.isoformat()}T10:30:00")


async def test_today_agenda_keeps_completed_media_and_excludes_archived_media(
    client: AsyncClient,
):
    day = date.today()
    completed = await _create_media(
        client,
        title="Bitmiş kitap",
        status="completed",
        progress=100,
        total=100,
        cover_path=None,
    )
    archived = await _create_media(client, title="Arşivlenmiş kitap")
    completed_slot = (
        await client.post(
            "/api/plan", json={"entity_id": completed["id"], "day": day.isoformat()}
        )
    ).json()
    await client.post(
        "/api/plan", json={"entity_id": archived["id"], "day": day.isoformat()}
    )
    assert (await client.delete(f"/api/media/{archived['id']}")).status_code == 200

    agenda = (
        await client.get("/api/today/agenda", params={"day": day.isoformat()})
    ).json()

    completed_row = next(row for row in agenda["completed"] if row["id"] == completed["id"])
    assert completed_row["kind"] == "media"
    assert completed_row["slot_id"] == completed_slot["id"]
    assert completed_row["media_status"] == "completed"
    assert completed_row["progress_label"] == "Tamamlandı · 100 / 100 sayfa"
    assert completed_row["cover_url"] == "https://example.com/remote-cover.jpg"
    assert completed_row["completed"] is True
    assert completed_row["read_only"] is True
    assert completed_row["action"] is None
    all_ids = {
        row["id"]
        for bucket in (agenda["timed"], agenda["checklist"], agenda["completed"])
        for row in bucket
    }
    assert archived["id"] not in all_ids


@pytest.mark.parametrize(
    ("status", "completed", "read_only", "action"),
    [
        ("planned", False, False, "log_media"),
        ("in_progress", False, False, "log_media"),
        ("paused", False, False, "log_media"),
        ("completed", True, True, None),
        ("dropped", False, True, None),
    ],
)
async def test_planned_media_action_semantics_follow_media_status(
    client: AsyncClient,
    status: str,
    completed: bool,
    read_only: bool,
    action: str | None,
):
    day = date.today()
    item = await _create_media(
        client,
        status=status,
        progress=0 if status == "planned" else 12,
    )
    await client.post(
        "/api/plan", json={"entity_id": item["id"], "day": day.isoformat()}
    )

    agenda = (
        await client.get("/api/today/agenda", params={"day": day.isoformat()})
    ).json()
    rows = agenda["timed"] + agenda["checklist"] + agenda["completed"]
    row = next(row for row in rows if row["id"] == item["id"])

    assert row["media_status"] == status
    assert row["completed"] is completed
    assert row["read_only"] is read_only
    assert row["action"] == action


async def test_media_progress_label_preserves_decimal_without_float_rounding(
    client: AsyncClient,
):
    day = date.today()
    item = await _create_media(
        client,
        progress="1234567890.12",
        total="9999999999.99",
    )
    await client.post(
        "/api/plan", json={"entity_id": item["id"], "day": day.isoformat()}
    )

    agenda = (
        await client.get("/api/today/agenda", params={"day": day.isoformat()})
    ).json()
    rows = agenda["timed"] + agenda["checklist"] + agenda["completed"]
    row = next(row for row in rows if row["id"] == item["id"])

    assert row["progress_label"] == "1234567890.12 / 9999999999.99 sayfa"


async def test_today_exposes_four_recent_active_media_without_persisting_suggestions(
    client: AsyncClient,
):
    day = date.today()
    items = [
        await _create_media(
            client,
            title=f"Continue {index}",
            kind="show" if index % 2 else "book",
            progress=index + 1,
            total=20,
            progress_measure="episode" if index % 2 else "page",
            cover_path=None,
            cover_url=f"https://example.com/cover-{index}.jpg",
        )
        for index in range(6)
    ]
    await client.post(
        "/api/plan",
        json={"entity_id": items[1]["id"], "day": day.isoformat(), "duration_min": 25},
    )
    assert (await client.delete(f"/api/media/{items[5]['id']}")).status_code == 200
    base = datetime(2026, 1, 1, tzinfo=UTC)
    async with engine.begin() as connection:
        for index, item in enumerate(items):
            await connection.execute(
                text("update entity set updated_at = :updated_at where id = cast(:id as uuid)"),
                {"id": item["id"], "updated_at": base + timedelta(minutes=index)},
            )

    before_slots = (await client.get("/api/plan", params={"week": day.isoformat()})).json()
    agenda = (
        await client.get("/api/today/agenda", params={"day": day.isoformat()})
    ).json()
    after_slots = (await client.get("/api/plan", params={"week": day.isoformat()})).json()

    assert [row["id"] for row in agenda["suggestions"]["media"]] == [
        items[index]["id"] for index in (4, 3, 2, 1)
    ]
    assert all(row["kind"] == "media" for row in agenda["suggestions"]["media"])
    assert all(row["media_kind"] in {"book", "show"} for row in agenda["suggestions"]["media"])
    assert all(row["progress_label"] for row in agenda["suggestions"]["media"])
    assert all(row["cover_url"] for row in agenda["suggestions"]["media"])
    assert any(row["id"] == items[1]["id"] for row in agenda["checklist"])
    assert before_slots == after_slots


async def test_continue_media_is_returned_when_auto_suggestions_are_disabled(
    client: AsyncClient,
):
    item = await _create_media(client, title="Current media state")
    response = await client.put(
        "/api/settings/today.auto_suggestions", json={"value": False}
    )
    assert response.status_code == 200, response.text
    try:
        agenda_response = await client.get(
            "/api/today/agenda", params={"day": date.today().isoformat()}
        )
        assert agenda_response.status_code == 200, agenda_response.text
        agenda = agenda_response.json()
        assert agenda["auto_suggestions"] is False
        assert any(row["id"] == item["id"] for row in agenda["suggestions"]["media"])
        assert agenda["suggestions"]["todos"] == []
        assert agenda["suggestions"]["rss"] == []
    finally:
        await client.put(
            "/api/settings/today.auto_suggestions", json={"value": True}
        )


async def test_media_contributions_only_count_positive_consumption_in_local_day(
    client: AsyncClient,
):
    day = date.today()
    occurred_at = datetime.combine(
        day, time(hour=0, minute=30), tzinfo=ZoneInfo("Europe/Istanbul")
    ).astimezone(UTC)
    events = [
        ("media.consumed", {"case": "positive_integer", "amount": 2}),
        ("media.consumed", {"case": "positive_decimal", "amount": 0.25}),
        ("media.consumed", {"case": "zero", "amount": 0}),
        ("media.consumed", {"case": "negative", "amount": -1}),
        ("media.consumed", {"case": "numeric_string", "amount": "3"}),
        ("media.consumed", {"case": "boolean", "amount": True}),
        ("media.consumed", {"case": "null", "amount": None}),
        ("media.consumed", {"case": "nan_string", "amount": "NaN"}),
        ("media.consumed", ["non-object"]),
        ("media.progress_corrected", {"amount": 4}),
        ("media.release_discovered", {}),
        ("media.sync_completed", {}),
        ("media.cycle_reopened", {}),
    ]
    async with engine.begin() as connection:
        for verb, payload in events:
            await connection.execute(
                text(
                    "insert into event (entity_type, verb, payload, occurred_at) "
                    "values ('media_item', :verb, cast(:payload as jsonb), :occurred_at)"
                ),
                {"verb": verb, "payload": json.dumps(payload), "occurred_at": occurred_at},
            )

    heatmap = (
        await client.get("/api/activity/heatmap", params={"days": 7})
    ).json()
    detail = (
        await client.get("/api/activity/day", params={"day": day.isoformat()})
    ).json()

    today = next(entry for entry in heatmap["days"] if entry["day"] == day.isoformat())
    assert today["kinds"] == {"media": 2}
    assert heatmap["labels"]["media"] == "medya"
    assert detail["kinds"] == today["kinds"]
    media_events = [
        event for event in detail["events"] if event["verb"] == "media.consumed"
    ]
    counted_cases = {
        event["payload"]["case"]
        for event in media_events
        if event["kind"] == "media"
    }
    assert counted_cases == {"positive_integer", "positive_decimal"}
    assert all(
        event["kind"] is None
        for event in media_events
        if not isinstance(event["payload"], dict)
        or event["payload"].get("case") not in counted_cases
    )
    assert detail["other"] == len(events) - 2
