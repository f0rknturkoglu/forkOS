from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.modules.media.providers.anilist import AniListProvider
from app.modules.media.providers.base import ProviderResult
from app.modules.media.providers.igdb import IGDBProvider
from app.modules.media.providers.musicbrainz import MusicBrainzProvider
from app.modules.media.providers.openlibrary import GoogleBooksProvider, OpenLibraryProvider
from app.modules.media.providers.podcast import PodcastProvider
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
            provider_id="movie:42",
            title="Arrival",
            year=2016,
            summary="First contact.",
            total=1,
            progress_measure="item",
            cover_url="https://image.tmdb.org/t/p/original/cover.jpg",
            backdrop_url="https://image.tmdb.org/t/p/original/backdrop.jpg",
            provider_ids={"tmdb": "42", "tmdb_kind": "movie"},
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


@pytest.mark.no_database
async def test_tmdb_identity_is_kind_qualified_and_api_requests_use_raw_id():
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if "/search/" in request.url.path:
            return httpx.Response(200, json={"results": [{"id": 42, "title": "Same"}]})
        return httpx.Response(200, json={"id": 42, "title": "Same"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        movie = TMDBProvider("movie", api_key="key", client=client)
        show = TMDBProvider("show", api_key="key", client=client)
        movie_result = (await movie.search("same"))[0]
        show_result = (await show.search("same"))[0]
        await movie.details(movie_result.provider_id)
        await show.details(show_result.provider_id)

    assert movie_result.provider_id == "movie:42"
    assert show_result.provider_id == "tv:42"
    assert paths[-2:] == ["/3/movie/42", "/3/tv/42"]


@pytest.mark.no_database
async def test_anilist_upcoming_honors_days_window():
    provider = AniListProvider("anime")
    future = datetime.now(UTC) + timedelta(days=40)

    async def fake_units(provider_id: str):
        from app.modules.media.providers.base import ProviderUnit

        return [
            ProviderUnit(
                provider_id="1:2",
                title="Episode 2",
                unit_type="episode",
                release_at=future,
            )
        ]

    provider.units = fake_units
    assert await provider.upcoming("1", days=30) == []


@pytest.mark.no_database
def test_igdb_does_not_advertise_unimplemented_upcoming():
    provider = IGDBProvider(client_id="id", client_secret="secret")
    assert provider.capabilities.upcoming is False


def test_tmdb_movie_does_not_advertise_serial_unit_capabilities():
    provider = TMDBProvider("movie", api_key="key")
    assert provider.capabilities.units is False
    assert provider.capabilities.upcoming is False


@pytest.mark.no_database
async def test_musicbrainz_track_identity_includes_disc_position():
    provider = MusicBrainzProvider()

    async def fake_get(path: str, **params):
        if path == "release-group/group":
            return {"releases": [{"id": "release"}]}
        return {
            "media": [
                {"position": 1, "tracks": [{"id": "a", "position": 1, "title": "Intro"}]},
                {"position": 2, "tracks": [{"id": "b", "position": 1, "title": "Intro"}]},
            ]
        }

    provider._get = fake_get
    units = await provider.units("group")
    assert [unit.provider_id for unit in units] == ["track:a", "track:b"]


@pytest.mark.no_database
async def test_musicbrainz_release_order_does_not_change_track_identity():
    provider = MusicBrainzProvider()
    release_orders = [
        [{"id": "release-b"}, {"id": "release-a"}],
        [{"id": "release-a"}, {"id": "release-b"}],
    ]

    async def fake_get(path: str, **params):
        if path == "release-group/group":
            return {"releases": release_orders.pop(0)}
        assert path == "release/release-a"
        return {
            "media": [
                {
                    "position": 1,
                    "tracks": [
                        {
                            "position": 1,
                            "title": "Stable",
                            "recording": {"id": "recording-1"},
                        },
                        {"position": 2, "title": "No IDs"},
                    ],
                }
            ]
        }

    provider._get = fake_get
    first = await provider.units("group")
    second = await provider.units("group")
    assert [unit.provider_id for unit in first] == [
        "recording:recording-1",
        "fallback:group:d1:t2:3a6e1ae822b9",
    ]
    assert [unit.provider_id for unit in second] == [
        unit.provider_id for unit in first
    ]


@pytest.mark.no_database
async def test_itunes_vanished_lookup_is_expected_empty():
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"resultCount": 0, "results": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = PodcastProvider(client=client)
        assert await provider.details("gone") is None


@pytest.mark.no_database
async def test_openlibrary_partial_publish_date_is_safe():
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"title": "Partial", "first_publish_date": "1965", "covers": []},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        details = await OpenLibraryProvider("book", client=client).details("OL1W")
    assert details.release_date.isoformat() == "1965-01-01"
