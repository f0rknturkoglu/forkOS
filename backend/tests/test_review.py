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


async def test_review_reports_flashcard_reviews(client: AsyncClient) -> None:
    """Degerlendirme, donemde tekrar edilen kartlari deste kirilimiyla gosterir."""
    deck = (await client.post("/api/flashcard/decks", json={"title": "Almanca"})).json()
    card = (
        await client.post(
            f"/api/flashcard/decks/{deck['id']}/cards", json={"front": "Haus", "back": "Ev"}
        )
    ).json()
    await client.post(f"/api/flashcard/cards/{card['id']}/review", json={"grade": 2})
    await client.post(f"/api/flashcard/cards/{card['id']}/review", json={"grade": 3})

    preview = (
        await client.get(
            "/api/reviews/preview",
            params={"kind": "daily", "period_start": local_today().isoformat()},
        )
    ).json()

    assert preview["stats"]["flashcards"]["reviewed"] == 2
    assert preview["stats"]["flashcards"]["decks"] == {"Almanca": 2}
