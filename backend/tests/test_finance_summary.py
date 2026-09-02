"""GET /finance/summary: son N ayin gelir/gider toplamlari (grafik serisi).

- Bos veri: aylar sifirli gelir, eksen surekli (bugun dahil son 6 satir).
- Iki aylik veri: ay toplamlari dogru toplanir (expense + income ayri ayri).
- Siralama eskiden yeniye; verisi olmayan ay da listede yer alir.
- months parametresi sinirli ve dogrulanir.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.time import local_today
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


def _month_key(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def _expected_months(months: int) -> list[str]:
    """Service ile ayni hesap: bugun dahil son `months` ay, eskiden yeniye."""
    today = local_today()
    end_index = today.year * 12 + today.month  # gelecek ayin basi (haric)
    start_index = end_index - months
    return [_month_key(i // 12, i % 12 + 1) for i in range(start_index, end_index)]


async def test_summary_empty_returns_zeroed_months(client: AsyncClient) -> None:
    response = await client.get("/api/finance/summary")
    assert response.status_code == 200, response.text
    rows = response.json()
    assert [row["month"] for row in rows] == _expected_months(6)
    assert all(row["income"] == 0 and row["expense"] == 0 for row in rows)


async def test_summary_aggregates_two_months(client: AsyncClient) -> None:
    today = local_today()
    prev_year, prev_month = _shift_month(today.year, today.month, -1)
    prev = f"{_month_key(prev_year, prev_month)}-10"
    current = f"{_month_key(today.year, today.month)}-05"

    for payload in [
        # Onceki ay: 2 gider + 1 gelir.
        {"title": "Market", "amount": "150.50", "category": "food", "spent_on": prev},
        {"title": "Kira", "amount": "18000.00", "category": "rent", "spent_on": prev},
        {"title": "Maaş", "amount": "45000.00", "category": "salary", "received_on": prev},
        # Bu ay: 1 gider + 2 gelir.
        {"title": "Ulaşım", "amount": "300.25", "category": "transport", "spent_on": current},
        {"title": "Serbest iş", "amount": "1200.00", "category": "freelance", "received_on": current},
        {"title": "Hediye", "amount": "500.00", "category": "gift", "received_on": current},
    ]:
        endpoint = "/api/incomes" if "received_on" in payload else "/api/expenses"
        created = await client.post(endpoint, json=payload)
        assert created.status_code == 201, created.text

    rows = (await client.get("/api/finance/summary")).json()
    by_month = {row["month"]: row for row in rows}
    prev_key = _month_key(prev_year, prev_month)
    current_key = _month_key(today.year, today.month)

    assert by_month[prev_key]["expense"] == 18150.5  # 150.50 + 18000.00
    assert by_month[prev_key]["income"] == 45000.0
    assert by_month[current_key]["expense"] == 300.25
    assert by_month[current_key]["income"] == 1700.0  # 1200.00 + 500.00

    # Degerler rakam olarak gelir (Decimal -> JSON sayisi), metin degil.
    assert isinstance(by_month[prev_key]["expense"], (int, float))


async def test_summary_orders_oldest_first(client: AsyncClient) -> None:
    today = local_today()
    # Veri yalnizca donemin ilk ayinda: siralamayi ve bos aylarin varligini olcer.
    first_year, first_month = _shift_month(today.year, today.month, -3)
    first_day = f"{_month_key(first_year, first_month)}-01"

    expense = await client.post(
        "/api/expenses",
        json={"title": "Eski borç", "amount": "99.99", "category": "other", "spent_on": first_day},
    )
    assert expense.status_code == 201, expense.text

    rows = (await client.get("/api/finance/summary", params={"months": 4})).json()
    assert [row["month"] for row in rows] == _expected_months(4)
    assert rows[0]["expense"] == 99.99
    assert rows[0]["income"] == 0
    # Aradaki ve son ay sifirli; sirasi bozulmamis.
    assert all(row["expense"] == 0 for row in rows[1:])


async def test_summary_accepts_single_month(client: AsyncClient) -> None:
    today = local_today()
    day = f"{_month_key(today.year, today.month)}-15"
    created = await client.post(
        "/api/expenses",
        json={"title": "Fatura", "amount": "75.00", "category": "bills", "spent_on": day},
    )
    assert created.status_code == 201, created.text

    rows = (await client.get("/api/finance/summary", params={"months": 1})).json()
    assert [row["month"] for row in rows] == [_month_key(today.year, today.month)]
    assert rows[0]["expense"] == 75.0


async def test_summary_rejects_out_of_range_months(client: AsyncClient) -> None:
    for months in (0, -1, 25):
        response = await client.get("/api/finance/summary", params={"months": months})
        assert response.status_code == 422, response.text
