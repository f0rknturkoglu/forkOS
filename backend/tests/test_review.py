from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def test_review_combines_legacy_habits_and_recurring_todos(client: AsyncClient) -> None:
    routine = (
        await client.post("/api/todos", json={"title": "Su iç", "recur": "daily"})
    ).json()
    normal = (await client.post("/api/todos", json={"title": "Tek seferlik"})).json()
    habit = (await client.post("/api/habits", json={"title": "Eski yürüyüş"})).json()

    assert (await client.post(f"/api/todos/{routine['id']}/complete")).status_code == 200
    assert (await client.post(f"/api/todos/{normal['id']}/complete")).status_code == 200
    assert (
        await client.post(
            f"/api/habits/{habit['id']}/check",
            json={"day": date.today().isoformat(), "done": True},
        )
    ).status_code == 200

    response = await client.get(
        "/api/reviews/preview",
        params={"kind": "daily", "period_start": date.today().isoformat()},
    )

    assert response.status_code == 200
    assert response.json()["stats"]["habits"] == {"Eski yürüyüş": 1, "Su iç": 1}

    created = await client.post(
        "/api/reviews",
        json={
            "kind": "daily",
            "period_start": date.today().isoformat(),
            "decisions": {},
        },
    )
    assert created.status_code == 201
    assert created.json()["stats"]["habits"] == {"Eski yürüyüş": 1, "Su iç": 1}
