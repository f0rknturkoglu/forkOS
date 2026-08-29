"""Faz 18: link API sozlesmesi.

- Kendine baglama no-op'tur.
- Ayni (from, to, relation) ikinci kez baglanamaz (link_uniq).
- /entities/{id}/related yon fark etmeksizin iliski etiketi + yon doner.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as http:
        yield http


async def _seed_pair(client: AsyncClient) -> tuple[str, str]:
    a = (await client.post("/api/todos", json={"title": "Bag kaynagi"})).json()
    b = (await client.post("/api/todos", json={"title": "Bag hedefi"})).json()
    return a["id"], b["id"]


async def test_duplicate_link_is_noop(client: AsyncClient) -> None:
    a, b = await _seed_pair(client)
    body = {"from_id": a, "to_id": b, "relation": "related"}

    first = await client.post("/api/links", json=body)
    assert first.status_code == 201
    second = await client.post("/api/links", json=body)
    assert second.status_code == 201

    related = (await client.get(f"/api/entities/{a}/related")).json()
    assert len(related) == 1

    await client.delete(f"/api/todos/{a}")
    await client.delete(f"/api/todos/{b}")


async def test_self_link_is_noop(client: AsyncClient) -> None:
    a, _ = await _seed_pair(client)
    response = await client.post(
        "/api/links", json={"from_id": a, "to_id": a, "relation": "related"}
    )
    assert response.status_code == 201
    related = (await client.get(f"/api/entities/{a}/related")).json()
    assert related == []
    await client.delete(f"/api/todos/{a}")


async def test_related_reports_direction_and_labels(client: AsyncClient) -> None:
    a, b = await _seed_pair(client)
    await client.post("/api/links", json={"from_id": a, "to_id": b, "relation": "learns_from"})

    from_a = (await client.get(f"/api/entities/{a}/related")).json()
    row_a = next(row for row in from_a if row["entity"]["id"] == b)
    assert row_a["direction"] == "outgoing"
    assert row_a["label"] == "Kaynakları"  # RELATIONS ileri etiketi

    from_b = (await client.get(f"/api/entities/{b}/related")).json()
    row_b = next(row for row in from_b if row["entity"]["id"] == a)
    assert row_b["direction"] == "incoming"
    assert row_b["label"] == "Çalışıldığı konu"  # RELATIONS geri etiketi

    await client.delete(f"/api/todos/{a}")
    await client.delete(f"/api/todos/{b}")
