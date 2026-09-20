"""Öğrenme ↔ çekirdek entegrasyon testleri.

Kapsam:
1. Pomodoro bir KAYNAK bağlamında bitince üst konunun (ve atalarının)
   `last_studied_at` güncellenir (alt kaynak çalışılınca üst konu "stale" görünmez).
2. Today ajandasında öğrenme satırları entity tipi taşır (rota registry'den çözülür).
3. Tekrar zamanı gelen konu Today önerilerinde (`suggestions.study`) görünür.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db import SessionLocal
from app.main import app
from app.modules.learning.models import StudyTopic as TopicModel


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as value:
        yield value


async def _area(client: AsyncClient, title: str) -> dict:
    response = await client.post("/api/study/areas", json={"title": title})
    assert response.status_code == 201, response.text
    return response.json()


async def _topic(client: AsyncClient, area_id: str, title: str, parent_id: str | None = None) -> dict:
    body = {"title": title, "area_id": area_id}
    if parent_id:
        body["parent_id"] = parent_id
    response = await client.post("/api/study/topics", json=body)
    assert response.status_code == 201, response.text
    return response.json()


async def test_resource_pomodoro_updates_parent_topic_and_ancestors(client):
    area = await _area(client, f"Entegrasyon {uuid.uuid4().hex[:6]}")
    root = await _topic(client, area["id"], "Kök Konu")
    child = await _topic(client, area["id"], "Alt Konu", parent_id=root["id"])
    resource = await client.post(
        f"/api/study/topics/{child['id']}/resources",
        json={"title": "Bölüm videosu", "url": "https://example.com/video", "kind": "video"},
    )
    assert resource.status_code == 201, resource.text
    resource_id = resource.json()["id"]

    started = await client.post(
        "/api/pomodoro/start",
        json={"planned_min": 1, "context_entity_id": resource_id, "kind": "focus"},
    )
    assert started.status_code in (200, 201), started.text
    stopped = await client.post(f"/api/pomodoro/{started.json()['id']}/stop", json={"interrupted": False})
    assert stopped.status_code in (200, 201), stopped.text

    for topic_id in (child["id"], root["id"]):
        detail = (await client.get(f"/api/study/topics/{topic_id}")).json()
        assert detail["topic"]["last_studied_at"] is not None or detail["stats"]["last_studied_at"] is not None, (
            topic_id,
            detail["topic"],
        )

    async with SessionLocal() as session:
        rows = {
            row.id: row.last_studied_at
            for row in (
                await session.execute(
                    select(TopicModel).where(TopicModel.id.in_([uuid.UUID(root["id"]), uuid.UUID(child["id"])]))
                )
            ).scalars()
        }
    assert rows[uuid.UUID(child["id"])] is not None
    assert rows[uuid.UUID(root["id"])] is not None, "üst konu da güncellenmeli (ata zinciri)"


async def test_topic_pomodoro_updates_ancestor_chain(client):
    area = await _area(client, f"Zincir {uuid.uuid4().hex[:6]}")
    root = await _topic(client, area["id"], "Üst")
    mid = await _topic(client, area["id"], "Orta", parent_id=root["id"])
    leaf = await _topic(client, area["id"], "Yaprak", parent_id=mid["id"])

    started = await client.post(
        "/api/pomodoro/start",
        json={"planned_min": 1, "context_entity_id": leaf["id"], "kind": "focus"},
    )
    assert started.status_code in (200, 201), started.text
    await client.post(f"/api/pomodoro/{started.json()['id']}/stop", json={"interrupted": False})

    for topic_id in (leaf["id"], mid["id"], root["id"]):
        async with SessionLocal() as session:
            row = await session.get(TopicModel, uuid.UUID(topic_id))
        assert row is not None and row.last_studied_at is not None, topic_id


async def test_agenda_rows_carry_entity_type_for_learning(client):
    area = await _area(client, f"Bugün {uuid.uuid4().hex[:6]}")
    topic = await _topic(client, area["id"], "Planlanan Konu")
    today = datetime.now(UTC).date().isoformat()

    slot = await client.post("/api/plan", json={"entity_id": topic["id"], "day": today})
    assert slot.status_code in (200, 201), slot.text

    agenda = (await client.get("/api/today/agenda", params={"day": today})).json()
    rows = [*agenda["timed"], *agenda["checklist"]]
    study_rows = [row for row in rows if row["id"] == topic["id"]]
    assert study_rows, "planlanan konu ajandada görünmeli"
    assert study_rows[0]["kind"] == "study"
    assert study_rows[0]["entity_type"] == "study_topic"


async def test_due_topic_appears_in_today_suggestions(client):
    area = await _area(client, f"Tekrar {uuid.uuid4().hex[:6]}")
    topic = await _topic(client, area["id"], "Tekrar Edilecek Konu")
    # "forgot" aralığı 0 gün yapar → konu bugün tekrar kuyruğuna girer.
    reviewed = await client.post(f"/api/study/topics/{topic['id']}/review", json={"grade": "forgot"})
    assert reviewed.status_code in (200, 201), reviewed.text
    queue = (await client.get("/api/study/review", params={"window": 14})).json()
    due_ids = {row["id"] for row in [*queue["due_today"], *queue["overdue"]]}
    assert topic["id"] in due_ids, queue

    today = datetime.now(UTC).date().isoformat()
    agenda = (await client.get("/api/today/agenda", params={"day": today})).json()
    study_suggestions = agenda["suggestions"]["study"]
    assert any(row["id"] == topic["id"] for row in study_suggestions), study_suggestions
    row = next(row for row in study_suggestions if row["id"] == topic["id"])
    assert row["entity_type"] == "study_topic"
    assert row["source"] == "suggestion"


async def test_review_reschedules_into_the_future(client):
    area = await _area(client, f"SRS {uuid.uuid4().hex[:6]}")
    topic = await _topic(client, area["id"], "Aralık Testi")
    first = await client.post(f"/api/study/topics/{topic['id']}/review", json={"grade": "medium"})
    assert first.status_code in (200, 201), first.text
    interval = first.json()["interval_days"]
    assert interval >= 1

    second = await client.post(f"/api/study/topics/{topic['id']}/review", json={"grade": "easy"})
    assert second.json()["interval_days"] > interval
    detail = (await client.get(f"/api/study/topics/{topic['id']}")).json()
    next_at = detail["review"]["next_review_at"]
    assert next_at is not None
    assert datetime.fromisoformat(next_at.replace("Z", "+00:00")) > datetime.now(UTC) - timedelta(minutes=1)
