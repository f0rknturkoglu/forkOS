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
async def test_single_kind_search_still_returns_kind(monkeypatch):
    registry = FakeRegistry()
    monkeypatch.setattr(service, "provider_registry", AsyncMock(return_value=registry))

    rows = await service.search_metadata(SimpleNamespace(), "dune", "movie")

    assert rows[0].kind == "movie"
