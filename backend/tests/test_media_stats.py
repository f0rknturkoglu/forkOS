from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.time import local_today
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as http:
        yield http


async def _create(client: AsyncClient, **overrides):
    payload = {
        "source": "manual",
        "title": f"Stats {uuid.uuid4().hex[:8]}",
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


async def _consume(client: AsyncClient, item_id: str, **overrides):
    body = {
        "client_uuid": str(uuid.uuid4()),
        "action": "quick",
        "measure": "page",
        "amount": 1,
    }
    body.update(overrides)
    response = await client.post(f"/api/media/{item_id}/consumptions", json=body)
    assert response.status_code == 201, response.text
    return response.json()


async def _stats(client: AsyncClient, range_: str | None = None) -> dict:
    params = {"range": range_} if range_ else None
    response = await client.get("/api/media/stats", params=params)
    assert response.status_code == 200, response.text
    return response.json()


async def test_stats_rounds_average_and_keeps_measures_separate(client: AsyncClient):
    page_book = await _create(client, title="Page book", score=8)
    other_book = await _create(client, title="Other book", score=9)
    show = await _create(
        client, kind="show", title="Show", score=9, total=10, progress_measure=None
    )
    await _consume(client, page_book["id"], amount=10, duration_min=30)
    await _consume(client, other_book["id"], amount=3, duration_min=15)
    await _consume(
        client,
        show["id"],
        measure="episode",
        amount=2,
        duration_min=45,
        meta={"pomodoro_session_id": "session-1"},
    )

    stats = await _stats(client)
    assert stats["total"] == 3
    assert stats["by_kind"] == {"book": 2, "show": 1}
    assert stats["scored_count"] == 3
    # Ham float yasak: 8.666... tek ondaliga yuvarlanir.
    assert stats["average_score"] == 8.7
    expected_distribution = {str(value): 0 for value in range(1, 11)}
    expected_distribution["8"] = 1
    expected_distribution["9"] = 2
    assert stats["score_distribution"] == expected_distribution
    # Sayfa ve bolum ASLA tek toplamda birlesmez.
    assert stats["by_measure"] == {"page": 13.0, "episode": 2.0}
    assert stats["total_duration_min"] == 90
    assert stats["pomodoro_minutes"] == 45
    assert stats["conversion"] == {"planned": 0, "started": 3, "completed": 0}
    assert stats["active_days"] == 1
    assert stats["busiest_day"] == {"day": local_today().isoformat(), "count": 3}


async def test_stats_range_window_hides_older_consumptions(client: AsyncClient):
    item = await _create(client)
    old = datetime.now(UTC) - timedelta(days=8)
    await _consume(
        client, item["id"], amount=5, duration_min=100, occurred_at=old.isoformat()
    )
    await _consume(client, item["id"], amount=2, duration_min=20)

    week = await _stats(client, "week")
    assert week["total_duration_min"] == 20
    assert week["by_measure"] == {"page": 2.0}
    assert week["pomodoro_minutes"] == 0
    assert week["active_days"] == 1
    assert week["busiest_day"] == {"day": local_today().isoformat(), "count": 1}

    everything = await _stats(client, "all")
    assert everything["total_duration_min"] == 120
    assert everything["by_measure"] == {"page": 7.0}
    assert everything["active_days"] == 2
    assert everything["busiest_day"]["count"] == 1


async def test_stats_conversion_funnel_and_completed_in_range(client: AsyncClient):
    await _create(client, title="Planned only")
    started = await _create(client, title="Started")
    await _consume(client, started["id"], amount=1)
    await _create(client, title="Finished", status="completed")

    stats = await _stats(client)
    assert stats["total"] == 3
    assert stats["planned"] == 1
    assert stats["in_progress"] == 1
    assert stats["completed"] == 1
    assert stats["conversion"] == {"planned": 1, "started": 2, "completed": 1}
    assert stats["completed_in_range"] == 1
