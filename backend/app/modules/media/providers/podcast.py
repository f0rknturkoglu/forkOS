from __future__ import annotations

from contextlib import suppress
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime

import feedparser
import httpx

from app.modules.media.providers._http import HTTPProvider
from app.modules.media.providers.base import (
    ProviderCapabilities,
    ProviderDetails,
    ProviderExpectedEmpty,
    ProviderResult,
    ProviderUnit,
    deduplicate,
)


class PodcastProvider(HTTPProvider):
    id = "itunes"
    kinds = ("podcast",)
    capabilities = ProviderCapabilities(units=True, upcoming=True, cache_artwork=False)
    ready = True
    missing_settings: tuple[str, ...] = ()

    async def search(self, query: str) -> list[ProviderResult]:
        response = await self.request(
            "GET",
            "https://itunes.apple.com/search",
            params={"term": query, "media": "podcast", "entity": "podcast", "limit": 6},
        )
        results = []
        for row in response.json().get("results", []):
            provider_id = str(row["collectionId"])
            results.append(
                ProviderResult(
                    provider=self.id,
                    provider_id=provider_id,
                    title=row.get("collectionName") or "(başlıksız)",
                    subtitle=row.get("artistName"),
                    progress_measure="episode",
                    # iTunes promosyon artwork'u görüntülenebilir ama cache_artwork=False.
                    cover_url=row.get("artworkUrl600") or row.get("artworkUrl100"),
                    provider_ids={self.id: provider_id},
                    meta={"feed_url": row.get("feedUrl")},
                )
            )
        return deduplicate(results)

    async def _lookup(self, provider_id: str) -> dict:
        response = await self.request(
            "GET", "https://itunes.apple.com/lookup", params={"id": provider_id}
        )
        rows = response.json().get("results", [])
        return rows[0] if rows else {}

    async def details(self, provider_id: str) -> ProviderDetails | None:
        row = await self._lookup(provider_id)
        if not row or not row.get("feedUrl"):
            return None
        return ProviderDetails(
            provider=self.id,
            provider_id=provider_id,
            title=row.get("collectionName") or "(başlıksız)",
            progress_measure="episode",
            cover_url=row.get("artworkUrl600") or row.get("artworkUrl100"),
            provider_ids={self.id: provider_id},
            meta={"feed_url": row.get("feedUrl")},
        )

    async def units(self, provider_id: str) -> list[ProviderUnit]:
        row = await self._lookup(provider_id)
        feed_url = row.get("feedUrl")
        if not feed_url:
            raise ProviderExpectedEmpty("Podcast feed artık mevcut değil")
        try:
            response = await self.request("GET", feed_url)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {404, 410}:
                raise ProviderExpectedEmpty("Podcast feed artık mevcut değil") from exc
            raise
        parsed = feedparser.parse(response.content)
        publisher_art = (parsed.feed.get("image") or {}).get("href")
        units = []
        for index, entry in enumerate(parsed.entries):
            released = None
            published = entry.get("published")
            if published:
                with suppress(TypeError, ValueError):
                    released = parsedate_to_datetime(published).astimezone(UTC)
            units.append(
                ProviderUnit(
                    provider_id=str(entry.get("id") or entry.get("link") or index),
                    title=entry.get("title") or "(başlıksız)",
                    unit_type="podcast_episode",
                    number=float(len(parsed.entries) - index),
                    release_at=released,
                    progress_total=1,
                    progress_measure="episode",
                    cover_url=publisher_art,
                    meta={"publisher_artwork": bool(publisher_art)},
                )
            )
        return units

    async def upcoming(
        self,
        provider_id: str,
        *,
        days: int,
        units: list[ProviderUnit] | None = None,
    ) -> list[ProviderUnit]:
        now = datetime.now(UTC)
        until = now + timedelta(days=days)
        return [
            unit
            for unit in (
                units if units is not None else await self.units(provider_id)
            )
            if unit.release_at and now <= unit.release_at <= until
        ]
