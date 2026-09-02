from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.media import service
from app.modules.media.providers.base import ProviderResult


class FakeRegistry:
    kinds = ("movie", "book", "game")

    def __init__(self):
        self.movie = SimpleNamespace(
            id="tmdb",
            ready=True,
            missing_settings=(),
            search=AsyncMock(
                return_value=[
                    ProviderResult(provider="tmdb", provider_id="movie:1", title="Dune"),
                    ProviderResult(
                        provider="tmdb", provider_id="movie:1", title="Dune duplicate"
                    ),
                ]
            ),
        )
        self.book = SimpleNamespace(
            id="openlibrary",
            ready=True,
            missing_settings=(),
            search=AsyncMock(side_effect=RuntimeError("upstream unavailable")),
        )
        self.game = SimpleNamespace(
            id="igdb",
            ready=False,
            missing_settings=("media.igdb_client_id",),
            search=AsyncMock(),
        )

    def for_kind(self, kind):
        return getattr(self, kind)

    def provider_groups(self):
        return {
            self.movie.id: [("movie", self.movie)],
            self.book.id: [("book", self.book)],
            self.game.id: [("game", self.game)],
        }


class RegistryWithFallbackVariants:
    def __init__(self):
        self.primary_book = SimpleNamespace(
            id="openlibrary",
            ready=True,
            missing_settings=(),
            search=AsyncMock(
                return_value=[
                    ProviderResult(
                        provider="shared-catalog",
                        provider_id="same-id",
                        title="Primary result",
                    )
                ]
            ),
        )
        self.fallback_book = SimpleNamespace(
            id="google_books",
            ready=True,
            missing_settings=(),
            search=AsyncMock(
                return_value=[
                    ProviderResult(
                        provider="google_books",
                        provider_id="book-only",
                        title="Book result",
                    )
                ]
            ),
        )
        self.fallback_audiobook = SimpleNamespace(
            id="google_books",
            ready=True,
            missing_settings=(),
            search=AsyncMock(
                return_value=[
                    ProviderResult(
                        provider="shared-catalog",
                        provider_id="same-id",
                        title="Duplicate in another kind",
                    )
                ]
            ),
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
async def test_global_search_runs_each_ready_registered_variant_once_and_deduplicates_identity(
    monkeypatch,
):
    registry = RegistryWithFallbackVariants()
    monkeypatch.setattr(service, "provider_registry", AsyncMock(return_value=registry))

    result = await service.search_all_metadata(SimpleNamespace(), "dune")

    assert [(row.kind, row.provider, row.provider_id) for row in result.results] == [
        ("book", "shared-catalog", "same-id"),
        ("book", "google_books", "book-only"),
    ]
    registry.primary_book.search.assert_awaited_once_with("dune")
    registry.fallback_book.search.assert_awaited_once_with("dune")
    registry.fallback_audiobook.search.assert_awaited_once_with("dune")

