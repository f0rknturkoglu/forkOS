from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.modules.media.providers.anilist import AniListProvider
from app.modules.media.providers.base import MediaProvider
from app.modules.media.providers.igdb import IGDBProvider
from app.modules.media.providers.musicbrainz import MusicBrainzProvider
from app.modules.media.providers.openlibrary import GoogleBooksProvider, OpenLibraryProvider
from app.modules.media.providers.podcast import PodcastProvider
from app.modules.media.providers.tmdb import TMDBProvider


class ProviderRegistry:
    def __init__(
        self,
        providers: Mapping[str, MediaProvider],
        fallbacks: Mapping[tuple[str, str], MediaProvider] | None = None,
    ) -> None:
        self._providers = dict(providers)
        self._fallbacks = dict(fallbacks or {})

    @classmethod
    def from_settings(cls, settings: Mapping[str, Any]) -> ProviderRegistry:
        value = lambda key: settings.get(key) or None  # noqa: E731
        providers = {
            "movie": TMDBProvider("movie", api_key=value("media.tmdb_key")),
            "show": TMDBProvider("show", api_key=value("media.tmdb_key")),
            "anime": AniListProvider("anime"),
            "manga": AniListProvider("manga"),
            "book": OpenLibraryProvider("book", google_books_key=value("media.google_books_key")),
            "audiobook": OpenLibraryProvider(
                "audiobook", google_books_key=value("media.google_books_key")
            ),
            "podcast": PodcastProvider(),
            "music": MusicBrainzProvider(),
            "game": IGDBProvider(
                client_id=value("media.igdb_client_id"),
                client_secret=value("media.igdb_client_secret"),
            ),
        }
        return cls(
            providers,
            {
                ("google_books", "book"): GoogleBooksProvider(
                    "book", api_key=value("media.google_books_key")
                ),
                ("google_books", "audiobook"): GoogleBooksProvider(
                    "audiobook", api_key=value("media.google_books_key")
                ),
            },
        )

    @property
    def kinds(self) -> tuple[str, ...]:
        return tuple(self._providers)

    def for_kind(self, kind: str) -> MediaProvider:
        return self._providers[kind]

    def providers(self) -> list[MediaProvider]:
        unique: dict[str, MediaProvider] = {}
        for provider in [*self._providers.values(), *self._fallbacks.values()]:
            unique.setdefault(provider.id, provider)
        return list(unique.values())

    def provider_groups(self) -> dict[str, list[tuple[str, MediaProvider]]]:
        groups: dict[str, list[tuple[str, MediaProvider]]] = {}
        for kind, provider in self._providers.items():
            groups.setdefault(provider.id, []).append((kind, provider))
        for (provider_id, kind), provider in self._fallbacks.items():
            variants = groups.setdefault(provider_id, [])
            if not any(existing_kind == kind for existing_kind, _ in variants):
                variants.append((kind, provider))
        return groups

    def by_id(self, provider_id: str, *, kind: str | None = None) -> MediaProvider | None:
        candidates = self._providers.items()
        for provider_kind, provider in candidates:
            if provider.id == provider_id and (kind is None or provider_kind == kind):
                return provider
        if kind:
            return self._fallbacks.get((provider_id, kind))
        return next(
            (
                provider
                for (fallback_id, _), provider in self._fallbacks.items()
                if fallback_id == provider_id
            ),
            None,
        )
