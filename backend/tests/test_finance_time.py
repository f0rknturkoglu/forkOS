from datetime import date
from importlib import import_module

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

finance_router = import_module("app.modules.finance.router")


async def test_summary_defaults_are_evaluated_per_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, int] = {}

    async def fake_summary(_session, year: int, month: int):
        captured.update(year=year, month=month)
        return {"year": year, "month": month}

    monkeypatch.setattr(finance_router, "local_today", lambda: date(2031, 2, 1), raising=False)
    monkeypatch.setattr(finance_router.service, "monthly_summary", fake_summary)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/expenses/summary")

    assert response.status_code == 200
    assert captured == {"year": 2031, "month": 2}
