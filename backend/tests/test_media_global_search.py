from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.media import search as media_search
from app.modules.media import service
from app.modules.media.progress import MediaCommandError
from app.modules.media.providers.base import ProviderResult


@pytest.fixture(autouse=True)
def _isolated_search_cache():
    """Katalog arama onbellegi surec genelinde; her test temiz baslasin."""
    media_search.clear_search_cache()
    yield
    media_search.clear_search_cache()


def _provider(
    provider_id: str,
    results: list[ProviderResult] | None = None,
    *,
    ready: bool = True,
    missing: tuple[str, ...] = (),
    error: Exception | None = None,
    delay: float | None = None,
) -> SimpleNamespace:
    async def search(_query: str) -> list[ProviderResult]:
        if delay is not None:
            await asyncio.sleep(delay)
        if error is not None:
            raise error
        return list(results or [])

    return SimpleNamespace(
        id=provider_id,
        ready=ready,
        missing_settings=missing,
        search=AsyncMock(side_effect=search),
    )


def _registry(groups: dict[str, list[tuple[str, SimpleNamespace]]]) -> SimpleNamespace:
    return SimpleNamespace(provider_groups=lambda: groups)


def _single_result(provider: str, provider_id: str, title: str = "Dune") -> ProviderResult:
    return ProviderResult(provider=provider, provider_id=provider_id, title=title)


class FakeRegistry:
    kinds = ("movie", "book", "game")

    def __init__(self):
        self.movie = _provider(
            "tmdb",
            [
                ProviderResult(provider="tmdb", provider_id="movie:1", title="Dune"),
                ProviderResult(provider="tmdb", provider_id="movie:1", title="Dune duplicate"),
            ],
        )
        self.book = _provider("openlibrary", error=RuntimeError("upstream unavailable"))
        self.game = _provider("igdb", missing=("media.igdb_client_id",), ready=False)

    def provider_groups(self):
        return {
            self.movie.id: [("movie", self.movie)],
            self.book.id: [("book", self.book)],
            self.game.id: [("game", self.game)],
        }


class RegistryWithFallbackVariants:
    def __init__(self):
        self.primary_book = _provider(
            "openlibrary",
            [
                ProviderResult(
                    provider="shared-catalog", provider_id="same-id", title="Primary result"
                )
            ],
        )
        self.fallback_book = _provider(
            "google_books",
            [
                ProviderResult(
                    provider="google_books", provider_id="book-only", title="Book result"
                )
            ],
        )
        self.fallback_audiobook = _provider(
            "google_books",
            [
                ProviderResult(
                    provider="shared-catalog",
                    provider_id="same-id",
                    title="Duplicate in another kind",
                )
            ],
        )

    def provider_groups(self):
        return {
            "openlibrary": [("book", self.primary_book)],
            "google_books": [
                ("book", self.fallback_book),
                ("audiobook", self.fallback_audiobook),
            ],
        }


@pytest.mark.no_database
async def test_global_search_keeps_successes_and_reports_partial_failures(monkeypatch):
    registry = FakeRegistry()
    monkeypatch.setattr(service, "provider_registry", AsyncMock(return_value=registry))

    result = await service.search_all_metadata(SimpleNamespace(), "dune")

    assert [(row.kind, row.provider, row.provider_id) for row in result.results] == [
        ("movie", "tmdb", "movie:1")
    ]
    assert {(row.kind, row.provider) for row in result.warnings} == {
        ("book", "openlibrary"),
        ("game", "igdb"),
    }
    registry.game.search.assert_not_awaited()


@pytest.mark.no_database
async def test_global_search_sanitizes_provider_exception_messages(monkeypatch):
    registry = FakeRegistry()
    raw_url = "https://api.themoviedb.org/3/search/movie?api_key=super-secret"
    registry.book.search.side_effect = RuntimeError(f"Request failed: {raw_url}")
    monkeypatch.setattr(service, "provider_registry", AsyncMock(return_value=registry))

    result = await service.search_all_metadata(SimpleNamespace(), "dune")

    warning = next(warning for warning in result.warnings if warning.provider == "openlibrary")
    assert warning.message == "Provider araması başarısız"
    assert "super-secret" not in warning.message
    assert raw_url not in warning.message


@pytest.mark.no_database
async def test_global_search_deduplicates_per_provider_id_and_kind(monkeypatch):
    registry = RegistryWithFallbackVariants()
    monkeypatch.setattr(service, "provider_registry", AsyncMock(return_value=registry))

    result = await service.search_all_metadata(SimpleNamespace(), "dune")

    # Ayni provider_id farkli kind'da ayri sonuctur; siralama ilgi skoru sonra
    # provider adi + basliktir (kayit sirasi degil).
    assert [(row.kind, row.provider, row.provider_id) for row in result.results] == [
        ("book", "google_books", "book-only"),
        ("audiobook", "shared-catalog", "same-id"),
        ("book", "shared-catalog", "same-id"),
    ]
    registry.primary_book.search.assert_awaited_once_with("dune")
    registry.fallback_book.search.assert_awaited_once_with("dune")
    registry.fallback_audiobook.search.assert_awaited_once_with("dune")


@pytest.mark.no_database
async def test_global_search_filters_variants_by_kind_and_provider(monkeypatch):
    movie = _provider("tmdb", [_single_result("tmdb", "movie:1")])
    book = _provider("openlibrary", [_single_result("openlibrary", "OL1")])
    anime = _provider("anilist", [_single_result("anilist", "anime:1")])
    registry = _registry(
        {
            "tmdb": [("movie", movie), ("show", movie)],
            "openlibrary": [("book", book)],
            "anilist": [("anime", anime)],
        }
    )
    monkeypatch.setattr(service, "provider_registry", AsyncMock(return_value=registry))

    by_kind = await service.search_all_metadata(SimpleNamespace(), "dune", kind="book")
    assert [row.kind for row in by_kind.results] == ["book"]
    book.search.assert_awaited_once_with("dune")
    movie.search.assert_not_awaited()
    anime.search.assert_not_awaited()

    media_search.clear_search_cache()
    by_provider = await service.search_all_metadata(SimpleNamespace(), "dune", provider="anilist")
    assert [row.provider for row in by_provider.results] == ["anilist"]
    anime.search.assert_awaited_once_with("dune")


@pytest.mark.no_database
async def test_global_search_rejects_unknown_kind_and_provider(monkeypatch):
    registry = FakeRegistry()
    monkeypatch.setattr(service, "provider_registry", AsyncMock(return_value=registry))

    with pytest.raises(MediaCommandError):
        await service.search_all_metadata(SimpleNamespace(), "dune", kind="bogus")
    with pytest.raises(MediaCommandError):
        await service.search_all_metadata(SimpleNamespace(), "dune", provider="nope")
    registry.movie.search.assert_not_awaited()


@pytest.mark.no_database
async def test_global_search_limits_results_per_provider(monkeypatch):
    provider = _provider(
        "tmdb",
        [
            ProviderResult(provider="tmdb", provider_id=f"movie:{index}", title=f"Dune {index}")
            for index in range(1, 6)
        ],
    )
    monkeypatch.setattr(
        service, "provider_registry", AsyncMock(return_value=_registry({"tmdb": [("movie", provider)]}))
    )

    result = await service.search_all_metadata(SimpleNamespace(), "dune", limit=2)

    assert [row.provider_id for row in result.results] == ["movie:1", "movie:2"]


@pytest.mark.no_database
async def test_global_search_caches_repeated_query_and_marks_cached(monkeypatch):
    provider = _provider("tmdb", [_single_result("tmdb", "movie:1")])
    monkeypatch.setattr(
        service, "provider_registry", AsyncMock(return_value=_registry({"tmdb": [("movie", provider)]}))
    )

    first = await service.search_all_metadata(SimpleNamespace(), "dune")
    assert first.cached is False
    provider.search.reset_mock()

    second = await service.search_all_metadata(SimpleNamespace(), "DUNE")

    assert second.cached is True
    provider.search.assert_not_awaited()
    assert [row.provider_id for row in second.results] == ["movie:1"]


@pytest.mark.no_database
async def test_global_search_slow_provider_times_out_without_blocking_others(monkeypatch):
    monkeypatch.setattr(media_search, "SEARCH_TIMEOUT_SECONDS", 0.05)
    slow = _provider("igdb", [_single_result("igdb", "game:1")], delay=5.0)
    fast = _provider("tmdb", [_single_result("tmdb", "movie:1")])
    registry = _registry({"tmdb": [("movie", fast)], "igdb": [("game", slow)]})
    monkeypatch.setattr(service, "provider_registry", AsyncMock(return_value=registry))

    started = time.monotonic()
    result = await service.search_all_metadata(SimpleNamespace(), "dune")
    elapsed = time.monotonic() - started

    assert elapsed < 1.0
    assert [row.provider for row in result.results] == ["tmdb"]
    timeout_warning = next(warning for warning in result.warnings if warning.provider == "igdb")
    assert timeout_warning.message == "Sağlayıcı zaman aşımına uğradı"


@pytest.mark.no_database
async def test_global_search_orders_exact_title_before_partial_matches(monkeypatch):
    provider = _provider(
        "tmdb",
        [
            ProviderResult(
                provider="tmdb",
                provider_id="movie:2",
                title="Dune Messiah",
                summary="dune devami",
            ),
            ProviderResult(
                provider="tmdb",
                provider_id="movie:3",
                title="Other",
                summary="dune uzerine notlar",
            ),
            ProviderResult(provider="tmdb", provider_id="movie:1", title="dune"),
        ],
    )
    monkeypatch.setattr(
        service, "provider_registry", AsyncMock(return_value=_registry({"tmdb": [("movie", provider)]}))
    )

    result = await service.search_all_metadata(SimpleNamespace(), "Dune")

    assert [row.provider_id for row in result.results] == ["movie:1", "movie:2", "movie:3"]


@pytest.mark.no_database
async def test_global_search_warning_messages_are_human_readable(monkeypatch):
    tmdb = _provider("tmdb", ready=False, missing=("media.tmdb_key",))
    igdb = _provider(
        "igdb",
        ready=False,
        missing=("media.igdb_client_id", "media.igdb_client_secret"),
    )
    mystery = _provider("mystery", ready=False, missing=("media.mystery_key",))
    registry = _registry(
        {
            "tmdb": [("movie", tmdb)],
            "igdb": [("game", igdb)],
            "mystery": [("book", mystery)],
        }
    )
    monkeypatch.setattr(service, "provider_registry", AsyncMock(return_value=registry))

    result = await service.search_all_metadata(SimpleNamespace(), "dune")

    messages = {warning.provider: warning.message for warning in result.warnings}
    assert messages == {
        "tmdb": "TMDB anahtarı tanımlı değil",
        "igdb": "IGDB kimlik bilgileri eksik",
        "mystery": "Medya sağlayıcı ayarı eksik",
    }
    assert "media." not in " ".join(messages.values())
