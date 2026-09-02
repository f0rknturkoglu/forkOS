from datetime import date
from decimal import Decimal
from importlib import import_module

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.modules.finance.service import advance, monthly_share

finance_router = import_module("app.modules.finance.router")


async def test_overview_defaults_are_evaluated_per_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, int] = {}

    async def fake_overview(_session, year: int, month: int):
        captured.update(year=year, month=month)
        return {"year": year, "month": month, "currencies": []}

    monkeypatch.setattr(finance_router, "local_today", lambda: date(2031, 2, 1), raising=False)
    monkeypatch.setattr(finance_router.service, "month_overview", fake_overview)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/finance/overview")

    assert response.status_code == 200
    assert captured == {"year": 2031, "month": 2}


def test_monthly_share_spreads_long_periods_over_the_year() -> None:
    assert monthly_share(Decimal("100.00"), "monthly") == Decimal("100.00")
    assert monthly_share(Decimal("300.00"), "quarterly") == Decimal("100.00")
    assert monthly_share(Decimal("1200.00"), "yearly") == Decimal("100.00")


def test_advance_pins_to_billing_day_and_clamps_short_months() -> None:
    # Ödeme günü verilmişse sonraki vade o güne sabitlenir.
    assert advance(date(2026, 1, 15), "monthly", 15) == date(2026, 2, 15)
    # Şubat'ta 31 yok: ayın son gününe kırpılır.
    assert advance(date(2026, 1, 31), "monthly", 31) == date(2026, 2, 28)
    # Ödeme günü yoksa eski davranış korunur: ödendiği günün günü.
    assert advance(date(2026, 1, 10), "yearly") == date(2027, 1, 10)
