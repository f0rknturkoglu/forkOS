from __future__ import annotations

import httpx
import pytest

from app.modules.media.providers.base import ProviderResult
from app.modules.media.providers.openlibrary import GoogleBooksProvider, OpenLibraryProvider
from app.modules.media.providers.registry import ProviderRegistry
from app.modules.media.providers.tmdb import TMDBProvider


@pytest.mark.no_database
async def test_tmdb_normalizes_and_deduplicates_results():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["api_key"] == "secret"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": 42,
                        "title": "Arrival",
                        "release_date": "2016-11-11",
                        "overview": "First contact.",
                        "poster_path": "/cover.jpg",
                        "backdrop_path": "/backdrop.jpg",
                    },
                    {"id": 42, "title": "Arrival duplicate"},
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = TMDBProvider("movie", api_key="secret", client=client)
        results = await provider.search("arrival")

    assert results == [
        ProviderResult(
            provider="tmdb",
            provider_id="42",
            title="Arrival",
            year=2016,
            summary="First contact.",
            total=1,
            progress_measure="item",
            cover_url="https://image.tmdb.org/t/p/original/cover.jpg",
            backdrop_url="https://image.tmdb.org/t/p/original/backdrop.jpg",
            provider_ids={"tmdb": "42"},
            meta={"tmdb_type": "movie"},
        )
    ]


@pytest.mark.no_database
async def test_openlibrary_uses_google_books_only_when_primary_is_empty():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.host)
        if request.url.host == "openlibrary.org":
            return httpx.Response(200, json={"docs": []})
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "gb-1",
                        "volumeInfo": {
                            "title": "Dune",
                            "authors": ["Frank Herbert"],
                            "publishedDate": "1965",
                            "pageCount": 412,
                        },
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = OpenLibraryProvider("book", google_books_key="optional", client=client)
        results = await provider.search("dune")

    assert calls == ["openlibrary.org", "www.googleapis.com"]
    assert results[0].provider == "google_books"
    assert results[0].provider_id == "gb-1"
    assert results[0].total == 412
    assert results[0].progress_measure == "page"


@pytest.mark.no_database
def test_registry_maps_all_kinds_and_reports_missing_credentials():
    registry = ProviderRegistry.from_settings({})

    assert set(registry.kinds) == {
        "movie",
        "show",
        "anime",
        "manga",
        "book",
        "audiobook",
        "podcast",
        "music",
        "game",
    }
    assert registry.for_kind("book").ready is True
    assert registry.for_kind("movie").ready is False
    assert registry.for_kind("movie").missing_settings == ("media.tmdb_key",)
    assert registry.for_kind("game").missing_settings == (
        "media.igdb_client_id",
        "media.igdb_client_secret",
    )


@pytest.mark.no_database
async def test_google_books_fallback_identity_can_be_synced_later():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/books/v1/volumes/gb-1"
        return httpx.Response(
            200,
            json={
                "id": "gb-1",
                "volumeInfo": {
                    "title": "Dune",
                    "description": "Arrakis.",
                    "publishedDate": "1965-08-01",
                    "pageCount": 412,
                },
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        details = await GoogleBooksProvider("book", client=client).details("gb-1")

    assert details.provider == "google_books"
    assert details.provider_id == "gb-1"
    assert details.total == 412
