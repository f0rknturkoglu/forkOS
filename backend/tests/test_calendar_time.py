
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.modules.calendar import service as calendar_service


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def test_plan_slot_is_pushed_as_istanbul_wall_clock(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    todo = (await client.post("/api/todos", json={"title": "Saat testi"})).json()
    slot = (
        await client.post(
            "/api/plan",
            json={"entity_id": todo["id"], "day": "2026-01-15", "start_min": 9 * 60},
        )
    ).json()
    captured: dict = {}

    async def fake_access_token(_session):
        return "token"

    async def fake_upsert_event(_token, payload, _event_id):
        captured.update(payload)
        return {"id": "google-event"}

    monkeypatch.setattr(calendar_service, "access_token", fake_access_token)
    monkeypatch.setattr(calendar_service, "upsert_event", fake_upsert_event)

    response = await client.post(f"/api/plan/{slot['id']}/push")

    assert response.status_code == 200
    assert captured["start"] == {
        "dateTime": "2026-01-15T09:00:00+03:00",
        "timeZone": "Europe/Istanbul",
    }
    assert captured["end"]["dateTime"] == "2026-01-15T09:30:00+03:00"

    events = (
        await client.get(
            "/api/calendar/events",
            params={
                "from": "2026-01-14T21:00:00Z",
                "to": "2026-01-15T21:00:00Z",
            },
        )
    ).json()
    plan_event = next(item for item in events if item["source"] == "plan")
    assert plan_event["starts_at"] == "2026-01-15T09:00:00+03:00"

    calendar_export = await client.get("/api/export/ics")
    assert "DTSTART:20260115T060000Z" in calendar_export.text
