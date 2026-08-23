from __future__ import annotations

from contextlib import suppress
from datetime import UTC, date, datetime, timedelta

import httpx

from app.modules.media.providers._http import HTTPProvider
from app.modules.media.providers.base import (
    ProviderCapabilities,
    ProviderDetails,
    ProviderResult,
    ProviderUnit,
    deduplicate,
)

QUERY = """
query ($q: String, $id: Int, $type: MediaType) {
  Page(page: 1, perPage: 6) { media(search: $q, id: $id, type: $type) {
    id title { romaji english } description episodes chapters volumes
    startDate { year month day } coverImage { extraLarge large } bannerImage
    nextAiringEpisode { episode airingAt }
  }}
}
"""


class AniListProvider(HTTPProvider):
    id = "anilist"
    kinds = ("anime", "manga")
    capabilities = ProviderCapabilities(units=True, upcoming=True)
    ready = True
    missing_settings: tuple[str, ...] = ()

    def __init__(self, kind: str, *, client: httpx.AsyncClient | None = None) -> None:
        super().__init__(client=client)
        self.kind = kind

    async def _query(self, variables: dict):
        response = await self.request(
            "POST", "https://graphql.anilist.co", json={"query": QUERY, "variables": variables}
        )
        return ((response.json().get("data") or {}).get("Page") or {}).get("media", [])

    def _result(self, row: dict) -> ProviderResult:
        total = row.get("episodes") if self.kind == "anime" else row.get("chapters")
        provider_id = str(row["id"])
        return ProviderResult(
            provider=self.id,
            provider_id=provider_id,
            title=(row.get("title") or {}).get("english")
            or (row.get("title") or {}).get("romaji")
            or "(başlıksız)",
            year=(row.get("startDate") or {}).get("year"),
            summary=row.get("description") or None,
            total=total,
            progress_measure="episode" if self.kind == "anime" else "chapter",
            cover_url=(row.get("coverImage") or {}).get("extraLarge")
            or (row.get("coverImage") or {}).get("large"),
            backdrop_url=row.get("bannerImage"),
            provider_ids={self.id: provider_id},
            meta={"volumes": row.get("volumes")},
        )

    async def search(self, query: str) -> list[ProviderResult]:
        rows = await self._query({"q": query, "type": "ANIME" if self.kind == "anime" else "MANGA"})
        return deduplicate([self._result(row) for row in rows])

    async def details(self, provider_id: str) -> ProviderDetails:
        row = (await self._query({"id": int(provider_id)}))[0]
        result = self._result(row)
        start = row.get("startDate") or {}
        released = None
        with suppress(KeyError, TypeError, ValueError):
            released = date(start["year"], start.get("month") or 1, start.get("day") or 1)
        return ProviderDetails(
            provider=result.provider,
            provider_id=result.provider_id,
            title=result.title,
            summary=result.summary,
            release_date=released,
            total=result.total,
            progress_measure=result.progress_measure,
            cover_url=result.cover_url,
            backdrop_url=result.backdrop_url,
            provider_ids=result.provider_ids,
            meta=result.meta,
        )

    async def units(self, provider_id: str) -> list[ProviderUnit]:
        rows = await self._query({"id": int(provider_id)})
        if not rows:
            return []
        row = rows[0]
        next_airing = row.get("nextAiringEpisode")
        if not next_airing:
            return []
        number = next_airing.get("episode")
        return [
            ProviderUnit(
                provider_id=f"{provider_id}:{number}",
                title=f"Bölüm {number}",
                unit_type="episode",
                number=number,
                release_at=datetime.fromtimestamp(next_airing["airingAt"], UTC),
                progress_total=1,
                progress_measure="episode",
            )
        ]

    async def upcoming(self, provider_id: str, *, days: int) -> list[ProviderUnit]:
        now = datetime.now(UTC)
        until = now + timedelta(days=days)
        return [
            unit
            for unit in await self.units(provider_id)
            if unit.release_at and now <= unit.release_at <= until
        ]
