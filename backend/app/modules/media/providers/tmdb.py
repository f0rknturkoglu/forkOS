from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import httpx

from app.modules.media.providers._http import HTTPProvider
from app.modules.media.providers.base import (
    ProviderCapabilities,
    ProviderDetails,
    ProviderResult,
    ProviderUnit,
    canonical_provider_id,
    deduplicate,
)

IMAGE = "https://image.tmdb.org/t/p/original"


def _date(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


class TMDBProvider(HTTPProvider):
    id = "tmdb"
    kinds = ("movie", "show")
    capabilities = ProviderCapabilities(
        units=True,
        upcoming=True,
        requires_settings=("media.tmdb_key",),
    )

    def __init__(
        self, kind: str, *, api_key: str | None, client: httpx.AsyncClient | None = None
    ) -> None:
        super().__init__(client=client)
        self.kind = kind
        if kind == "movie":
            self.capabilities = ProviderCapabilities(
                units=False,
                upcoming=False,
                requires_settings=("media.tmdb_key",),
            )
        self.api_key = api_key
        self.ready = bool(api_key)
        self.missing_settings = () if self.ready else self.capabilities.requires_settings

    @property
    def table(self) -> str:
        return "movie" if self.kind == "movie" else "tv"

    def canonical_id(self, provider_id: str | int) -> str:
        return canonical_provider_id(self.id, self.kind, str(provider_id)) or str(provider_id)

    @staticmethod
    def raw_id(provider_id: str) -> str:
        prefix, separator, raw = provider_id.partition(":")
        return raw if separator and prefix in {"movie", "tv"} else provider_id

    async def _get(self, path: str, **params):
        response = await self.request(
            "GET",
            f"https://api.themoviedb.org/3/{path}",
            params={"api_key": self.api_key, "language": "tr-TR", **params},
        )
        return response.json()

    async def search(self, query: str) -> list[ProviderResult]:
        data = await self._get(f"search/{self.table}", query=query)
        results: list[ProviderResult] = []
        for row in data.get("results", [])[:6]:
            raw_id = str(row["id"])
            provider_id = self.canonical_id(raw_id)
            released = row.get("release_date") or row.get("first_air_date")
            results.append(
                ProviderResult(
                    provider=self.id,
                    provider_id=provider_id,
                    title=row.get("title") or row.get("name") or "(başlıksız)",
                    year=int(released[:4]) if released and released[:4].isdigit() else None,
                    summary=row.get("overview") or None,
                    total=1 if self.kind == "movie" else row.get("number_of_episodes"),
                    progress_measure="item" if self.kind == "movie" else "episode",
                    cover_url=IMAGE + row["poster_path"] if row.get("poster_path") else None,
                    backdrop_url=(
                        IMAGE + row["backdrop_path"] if row.get("backdrop_path") else None
                    ),
                    provider_ids={self.id: raw_id, "tmdb_kind": self.table},
                    meta={"tmdb_type": self.table},
                )
            )
        return deduplicate(results)

    async def details(self, provider_id: str) -> ProviderDetails:
        raw_id = self.raw_id(provider_id)
        row = await self._get(f"{self.table}/{raw_id}")
        released = _date(row.get("release_date") or row.get("first_air_date"))
        return ProviderDetails(
            provider=self.id,
            provider_id=self.canonical_id(raw_id),
            title=row.get("title") or row.get("name") or "(başlıksız)",
            summary=row.get("overview") or None,
            release_date=released,
            total=1 if self.kind == "movie" else row.get("number_of_episodes"),
            progress_measure="item" if self.kind == "movie" else "episode",
            cover_url=IMAGE + row["poster_path"] if row.get("poster_path") else None,
            backdrop_url=IMAGE + row["backdrop_path"] if row.get("backdrop_path") else None,
            provider_ids={self.id: raw_id, "tmdb_kind": self.table},
            meta={"tmdb_type": self.table},
        )

    async def units(self, provider_id: str) -> list[ProviderUnit]:
        if self.kind == "movie":
            return []
        raw_id = self.raw_id(provider_id)
        canonical_id = self.canonical_id(raw_id)
        details = await self._get(f"tv/{raw_id}")
        units: list[ProviderUnit] = []
        for season in details.get("seasons", []):
            number = season.get("season_number")
            season_data = await self._get(f"tv/{raw_id}/season/{number}")
            for episode in season_data.get("episodes", []):
                released = _date(episode.get("air_date"))
                units.append(
                    ProviderUnit(
                        provider_id=f"{canonical_id}:s{number}:e{episode.get('episode_number')}",
                        title=episode.get("name") or f"Bölüm {episode.get('episode_number')}",
                        unit_type="episode",
                        number=episode.get("episode_number"),
                        duration_min=episode.get("runtime"),
                        release_at=(
                            datetime.combine(released, datetime.min.time(), tzinfo=UTC)
                            if released
                            else None
                        ),
                        progress_total=1,
                        progress_measure="episode",
                        meta={"season": number},
                    )
                )
        return units

    async def upcoming(self, provider_id: str, *, days: int) -> list[ProviderUnit]:
        now = datetime.now(UTC)
        until = now + timedelta(days=days)
        return [
            unit
            for unit in await self.units(provider_id)
            if unit.release_at and now <= unit.release_at <= until
        ]
