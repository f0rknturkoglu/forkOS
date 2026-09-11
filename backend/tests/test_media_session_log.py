"""Pomodoro seansi -> medya tuketimi koprusu (action='session').

Sure kaydi ilerlemeyi artirmamali ve ayni seans iki kez aktarilamamali:
Pomodoro seansi ile medya tuketimi arasindaki iliski `client_uuid` ile
`meta.pomodoro_session_id` uzerinden kurulur (kural: idempotency).
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.models import Event
from app.db import SessionLocal
from app.main import app
from app.modules.media.models import MediaConsumption


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as value:
        yield value


async def _create(client: AsyncClient, **overrides) -> dict:
    body = {
        "title": "Session Kitabi",
        "kind": "book",
        "status": "in_progress",
        "progress_measure": "page",
        **overrides,
    }
    response = await client.post("/api/media", json=body)
    assert response.status_code == 201, response.text
    return response.json()


async def test_session_log_keeps_progress_and_records_duration(client):
    item = await _create(client, total=300)
    before = float(item["progress"] or 0)
    session_id = uuid.uuid4()

    response = await client.post(
        f"/api/media/{item['id']}/consumptions",
        json={
            "client_uuid": str(session_id),
            "action": "session",
            "duration_min": 25,
            "measure": "page",
            "meta": {"pomodoro_session_id": str(session_id)},
        },
    )
    assert response.status_code == 201, response.text
    row = response.json()
    assert row["action"] == "session"
    assert row["duration_min"] == 25
    assert float(row["amount"] or 0) == 0.0
    assert float(row["progress_after"]) == before

    detail = (await client.get(f"/api/media/{item['id']}")).json()
    # Ilerleme degismedi: sure kaydi ilerlemeyi otomatik ARTIRMAZ.
    assert float(detail["item"]["progress"] or 0) == before
    assert detail["item"]["status"] == "in_progress"


async def test_session_replay_is_idempotent(client):
    item = await _create(client, total=120)
    session_id = uuid.uuid4()
    body = {
        "client_uuid": str(session_id),
        "action": "session",
        "duration_min": 50,
        "measure": "page",
        "meta": {"pomodoro_session_id": str(session_id)},
    }
    first = await client.post(f"/api/media/{item['id']}/consumptions", json=body)
    second = await client.post(f"/api/media/{item['id']}/consumptions", json=body)
    assert first.status_code == 201
    assert second.status_code in (200, 201)
    # Ayni seans ikinci kez yazilmaz: ayni tuketim satiri doner.
    assert second.json()["id"] == first.json()["id"]

    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(MediaConsumption).where(
                    MediaConsumption.client_uuid == session_id
                )
            )
        ).scalars().all()
    assert len(rows) == 1


async def test_session_requires_duration(client):
    item = await _create(client)
    response = await client.post(
        f"/api/media/{item['id']}/consumptions",
        json={"client_uuid": str(uuid.uuid4()), "action": "session", "measure": "page"},
    )
    assert response.status_code == 422
    assert "duration_min" in response.text


async def test_session_logs_its_own_event_not_consumed(client):
    item = await _create(client, total=80)
    session_id = uuid.uuid4()
    await client.post(
        f"/api/media/{item['id']}/consumptions",
        json={
            "client_uuid": str(session_id),
            "action": "session",
            "duration_min": 30,
            "measure": "page",
            "meta": {"pomodoro_session_id": str(session_id)},
        },
    )
    async with SessionLocal() as session:
        verbs = (
            await session.execute(select(Event.verb).where(Event.entity_id == uuid.UUID(item["id"])))
        ).scalars().all()
    assert "media.session_logged" in verbs
    # Ilerleme artmadigi icin tuketim sayaci (pozitif amount) tetiklenmez:
    # pomodoro istatistigi ile medya istatistigi cift saymaz.
    assert "media.consumed" not in verbs
