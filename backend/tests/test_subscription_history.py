import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_recurring_history_contains_only_paid_subscriptions() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payment = (await client.post("/api/recurring-payments", json={
            "title": "Deneme aboneliği", "amount": "10", "currency": "TRY",
            "frequency": "monthly", "category": "subscriptions",
        })).json()
        assert (await client.post(f"/api/recurring-payments/{payment['id']}/pay")).status_code == 200
        response = await client.get("/api/recurring-payments/history")
        assert response.status_code == 200
        assert response.json()[0]["title"] == "Deneme aboneliği"
        assert response.json()[0]["paid_at"]
