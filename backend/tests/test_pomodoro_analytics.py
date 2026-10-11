from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


@pytest.mark.asyncio
async def test_pomodoro_analytics_groups_daily_minutes_and_topics(client: AsyncClient, monkeypatch):
    from app.modules.pomodoro import service

    now = datetime(2026, 1, 14, 12, tzinfo=UTC)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return now.astimezone(tz) if tz else now.replace(tzinfo=None)

    original_today = service.local_today
    monkeypatch.setattr(service, "datetime", FixedDateTime)
    monkeypatch.setattr(service, "local_today", lambda at=None: original_today(at or now))
    for hours, minutes in ((3, 50), (2, 25)):
        response = await client.post(
            "/api/pomodoro",
            json={
                "started_at": (now - timedelta(hours=hours)).isoformat(),
                "minutes": minutes,
                "topic": "forkOS Odak sayfası",
            },
        )
        assert response.status_code == 201

    response = await client.get("/api/pomodoro/analytics?range=week")
    assert response.status_code == 200
    body = response.json()

    assert body["range"] == "week"
    assert body["minutes"] == 75
    assert body["sessions"] == 2
    assert body["completed"] == 2
    assert body["interrupted"] == 0
    assert sum(point["minutes"] for point in body["daily"]) == 75
    assert body["contexts"][0] == {
        "context_entity_id": None,
        "title": "forkOS Odak sayfası",
        "context_type": None,
        "minutes": 75,
        "sessions": 2,
        "share": 100.0,
    }


@pytest.mark.asyncio
async def test_pomodoro_analytics_rejects_unknown_range(client: AsyncClient):
    response = await client.get("/api/pomodoro/analytics?range=year")
    assert response.status_code == 422
