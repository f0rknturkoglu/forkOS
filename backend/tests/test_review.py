import pytest
from httpx import ASGITransport, AsyncClient

from app.core.time import local_today
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def test_review_counts_recurring_todo_completions(client: AsyncClient) -> None:
    routine = (
        await client.post("/api/todos", json={"title": "Su iç", "recur": "daily"})
    ).json()
    normal = (await client.post("/api/todos", json={"title": "Tek seferlik"})).json()

    assert (await client.post(f"/api/todos/{routine['id']}/complete")).status_code == 200
    assert (await client.post(f"/api/todos/{normal['id']}/complete")).status_code == 200

    response = await client.get(
        "/api/reviews/preview",
        params={"kind": "daily", "period_start": local_today().isoformat()},
    )

    assert response.status_code == 200
    preview = response.json()
    assert preview["stats"]["habits"] == {"Su iç": 1}
    assert preview["stats"]["focus"]["active_days"] >= 0
    assert {item["id"] for item in preview["completed_todos"]} >= {routine["id"], normal["id"]}

    created = await client.post(
        "/api/reviews",
        json={
            "kind": "daily",
            "period_start": local_today().isoformat(),
            "decisions": {},
        },
    )
    assert created.status_code == 201
    assert created.json()["stats"]["habits"] == {"Su iç": 1}
