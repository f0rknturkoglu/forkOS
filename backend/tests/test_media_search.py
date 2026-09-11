from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def _create(client: AsyncClient, **overrides):
    payload = {
        "source": "manual",
        "title": f"Media {uuid.uuid4().hex[:8]}",
        "kind": "book",
    }
    payload.update(overrides)
    response = await client.post("/api/media", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def test_list_filters_by_provider_case_insensitively(client: AsyncClient):
    await _create(
        client, title="Open Library Kitabı", provider="openlibrary", provider_id="OL1"
    )
    await _create(
        client, title="TMDB Filmi", kind="movie", provider="tmdb", provider_id="movie:1"
    )

    page = (await client.get("/api/media", params={"provider": "OpenLibrary"})).json()

    assert page["total"] == 1
    assert [row["title"] for row in page["items"]] == ["Open Library Kitabı"]


async def test_list_filters_by_favorite(client: AsyncClient):
    await _create(client, title="Favori Kitap", favorite=True)
    await _create(client, title="Favorisiz Kitap", favorite=False)

    page = (await client.get("/api/media", params={"favorite": True})).json()

    assert page["total"] == 1
    assert [row["title"] for row in page["items"]] == ["Favori Kitap"]


async def test_list_query_defaults_to_relevance_ordering(client: AsyncClient):
    await _create(client, title="Dune Messiah", summary="devam kitabı")
    await _create(client, title="Sessiz Kitap", summary="dune üzerine notlar")
    await _create(client, title="Dune")

    page = (await client.get("/api/media", params={"q": "dune"})).json()

    assert page["total"] == 3
    assert [row["title"] for row in page["items"]] == ["Dune", "Dune Messiah", "Sessiz Kitap"]


async def test_list_relevance_ordering_is_cursor_stable(client: AsyncClient):
    for title in ("Dune", "Dune Messiah", "Dune Chronicles", "Dune Encyclopedia"):
        await _create(client, title=title)

    first = (await client.get("/api/media", params={"q": "dune", "limit": 2})).json()
    second = (
        await client.get(
            "/api/media",
            params={"q": "dune", "limit": 2, "cursor": first["next_cursor"]},
        )
    ).json()

    assert first["total"] == 4
    ids = [row["id"] for row in first["items"]] + [row["id"] for row in second["items"]]
    assert len(set(ids)) == 4
    assert second["next_cursor"] is None


async def test_list_relevance_sort_without_query_falls_back_to_updated(client: AsyncClient):
    await _create(client, title="Birinci Kitap")
    await _create(client, title="İkinci Kitap")

    relevance = (await client.get("/api/media", params={"sort": "relevance"})).json()
    updated = (await client.get("/api/media", params={"sort": "updated"})).json()

    assert relevance["total"] == 2
    assert [row["id"] for row in relevance["items"]] == [row["id"] for row in updated["items"]]


async def test_list_search_is_accent_and_case_insensitive(client: AsyncClient):
    await _create(client, title="Kırmızı Kitap")
    await _create(client, title="Evrim")
    await _create(client, title="ベルセルク")

    upper = (await client.get("/api/media", params={"q": "KIRMIZI"})).json()
    folded = (await client.get("/api/media", params={"q": "kirmizi"})).json()
    dotless = (await client.get("/api/media", params={"q": "evrım"})).json()
    non_latin = (await client.get("/api/media", params={"q": "berserk"})).json()

    assert [row["title"] for row in upper["items"]] == ["Kırmızı Kitap"]
    assert [row["title"] for row in folded["items"]] == ["Kırmızı Kitap"]
    # immutable_unaccent Turkce 'ı' harfini de 'i' yapar -> aksan duyarsiz eslesir.
    assert [row["title"] for row in dotless["items"]] == ["Evrim"]
    assert non_latin["total"] == 0


async def test_list_search_requires_every_token(client: AsyncClient):
    await _create(client, title="Dune Messiah", summary="Çöl gezegeni")
    await _create(client, title="Dune", summary="Okyanus")

    both = (await client.get("/api/media", params={"q": "Dune Çöl"})).json()
    reordered = (await client.get("/api/media", params={"q": "çöl dune"})).json()
    missing = (await client.get("/api/media", params={"q": "Dune Okyanus Kitap"})).json()

    assert [row["title"] for row in both["items"]] == ["Dune Messiah"]
    assert [row["title"] for row in reordered["items"]] == ["Dune Messiah"]
    assert missing["total"] == 0
