"""Kayitli gorunumler (saved views) API sozlesmesi.

- CRUD: olustur, listele, guncelle, sil.
- Siralama: pinned once, sonra position, sonra id.
- POST position = modul icindeki max + 1.
- filter alani dict olmali (pydantic dogrulamasi).
- GET /views?module=... yalniz o modulun gorunumlerini doner.
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


async def _create(client: AsyncClient, name: str, module: str = "bookmark", **extra) -> dict:
    body = {"name": name, "module": module, "filter": {"read_status": "unread"}}
    body.update(extra)
    response = await client.post("/api/views", json=body)
    assert response.status_code == 201, response.text
    return response.json()


async def test_create_and_list(client: AsyncClient) -> None:
    created = await _create(client, "Okunmamis")
    assert created["id"]
    assert created["name"] == "Okunmamis"
    assert created["module"] == "bookmark"
    assert created["filter"] == {"read_status": "unread"}
    assert created["sort"] is None
    assert created["pinned"] is False
    assert created["position"] == 1

    rows = (await client.get("/api/views")).json()
    assert [r["id"] for r in rows] == [created["id"]]


async def test_position_increments_per_module(client: AsyncClient) -> None:
    first = await _create(client, "Birinci")
    second = await _create(client, "Ikinci")
    assert first["position"] == 1
    assert second["position"] == 2

    # Farkli modul kendi sayacindan baslar.
    other = await _create(client, "Diger", module="opportunity")
    assert other["position"] == 1

    rows = (await client.get("/api/views?module=bookmark")).json()
    assert [r["position"] for r in rows] == [1, 2]


async def test_module_filter(client: AsyncClient) -> None:
    bookmark_view = await _create(client, "Okunmamis", module="bookmark")
    opportunity_view = await _create(client, "Yuksek skor", module="opportunity")

    only_bookmarks = (await client.get("/api/views?module=bookmark")).json()
    assert [r["id"] for r in only_bookmarks] == [bookmark_view["id"]]

    only_opportunities = (await client.get("/api/views?module=opportunity")).json()
    assert [r["id"] for r in only_opportunities] == [opportunity_view["id"]]

    empty = (await client.get("/api/views?module=note")).json()
    assert empty == []


async def test_pinned_sorts_first(client: AsyncClient) -> None:
    a = await _create(client, "A")
    b = await _create(client, "B")
    c = await _create(client, "C")

    # En sona ekleneni sabitle: pinned once, konumunu koruyarak basa cekilir.
    patched = await client.patch(f"/api/views/{c['id']}", json={"pinned": True})
    assert patched.status_code == 200
    assert patched.json()["pinned"] is True
    assert patched.json()["position"] == 0

    rows = (await client.get("/api/views?module=bookmark")).json()
    assert [r["id"] for r in rows] == [c["id"], a["id"], b["id"]]

    # Birden fazla pinned: ikisi de position 0'da — id sirayla onlardan sonra
    # digerleri gelir (pinned desc, position asc, id asc).
    await client.patch(f"/api/views/{a['id']}", json={"pinned": True})
    rows = (await client.get("/api/views?module=bookmark")).json()
    ids = [r["id"] for r in rows]
    assert set(ids[:2]) == {a["id"], c["id"]}
    assert ids[2] == b["id"]

    # Sabitlemeyi kaldirmak siralamayi geri kazanir (position korunur).
    await client.patch(f"/api/views/{a['id']}", json={"pinned": False})
    rows = (await client.get("/api/views?module=bookmark")).json()
    assert [r["id"] for r in rows] == [c["id"], a["id"], b["id"]]


async def test_patch_updates_fields(client: AsyncClient) -> None:
    view = await _create(client, "Eski ad")
    response = await client.patch(
        f"/api/views/{view['id']}",
        json={"name": "Yeni ad", "sort": "saved_at.desc", "filter": {"favorite": True}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Yeni ad"
    assert body["sort"] == "saved_at.desc"
    assert body["filter"] == {"favorite": True}
    # Dokunulmayan alanlar korunur.
    assert body["module"] == "bookmark"

    missing = await client.patch(
        "/api/views/00000000-0000-0000-0000-000000000000", json={"name": "x"}
    )
    assert missing.status_code == 404


async def test_delete_removes_view(client: AsyncClient) -> None:
    view = await _create(client, "Silinecek")
    response = await client.delete(f"/api/views/{view['id']}")
    assert response.status_code == 204

    rows = (await client.get("/api/views?module=bookmark")).json()
    assert rows == []

    missing = await client.delete("/api/views/00000000-0000-0000-0000-000000000000")
    assert missing.status_code == 404


async def test_filter_must_be_dict(client: AsyncClient) -> None:
    for bad in (["a", "b"], "unread", 42, None):
        response = await client.post(
            "/api/views", json={"name": "Bozuk", "module": "bookmark", "filter": bad}
        )
        assert response.status_code == 422, f"filter={bad!r} kabul edilmemeli"

    # filter olmadan da 422: zorunlu alan.
    response = await client.post("/api/views", json={"name": "Filtersiz", "module": "bookmark"})
    assert response.status_code == 422


async def test_patch_filter_must_be_dict(client: AsyncClient) -> None:
    view = await _create(client, "Guncellenecek")
    response = await client.patch(f"/api/views/{view['id']}", json={"filter": "yanlis"})
    assert response.status_code == 422
