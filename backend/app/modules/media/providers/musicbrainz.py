from __future__ import annotations

import hashlib

from app.modules.media.providers._http import HTTPProvider
from app.modules.media.providers.base import (
    ProviderCapabilities,
    ProviderDetails,
    ProviderResult,
    ProviderUnit,
    deduplicate,
)

USER_AGENT = "forkOS/0.1 (local-only media tracker)"


class MusicBrainzProvider(HTTPProvider):
    id = "musicbrainz"
    kinds = ("music",)
    capabilities = ProviderCapabilities(units=True)
    ready = True
    missing_settings: tuple[str, ...] = ()

    async def _get(self, path: str, **params):
        response = await self.request(
            "GET",
            f"https://musicbrainz.org/ws/2/{path}",
            params={"fmt": "json", **params},
            headers={"User-Agent": USER_AGENT},
        )
        return response.json()

    async def search(self, query: str) -> list[ProviderResult]:
        rows = (await self._get("release-group", query=query, limit=6)).get("release-groups", [])
        results = []
        for row in rows:
            provider_id = row["id"]
            artist = ", ".join(
                part.get("artist", {}).get("name", "")
                for part in row.get("artist-credit", [])
                if isinstance(part, dict)
            )
            first = row.get("first-release-date") or ""
            results.append(
                ProviderResult(
                    provider=self.id,
                    provider_id=provider_id,
                    title=row.get("title") or "(başlıksız)",
                    subtitle=artist or None,
                    year=int(first[:4]) if first[:4].isdigit() else None,
                    progress_measure="track",
                    cover_url=f"https://coverartarchive.org/release-group/{provider_id}/front-500",
                    provider_ids={self.id: provider_id},
                    meta={"primary_type": row.get("primary-type")},
                )
            )
        return deduplicate(results)

    async def details(self, provider_id: str) -> ProviderDetails:
        row = await self._get(f"release-group/{provider_id}", inc="artists+releases")
        return ProviderDetails(
            provider=self.id,
            provider_id=provider_id,
            title=row.get("title") or "(başlıksız)",
            total=None,
            progress_measure="track",
            cover_url=f"https://coverartarchive.org/release-group/{provider_id}/front-500",
            provider_ids={self.id: provider_id},
        )

    async def units(self, provider_id: str) -> list[ProviderUnit]:
        group = await self._get(f"release-group/{provider_id}", inc="releases")
        releases = sorted(
            (row for row in (group.get("releases") or []) if row.get("id")),
            key=lambda row: str(row["id"]),
        )
        if not releases:
            return []
        release_id = str(releases[0]["id"])
        release = await self._get(f"release/{release_id}", inc="recordings")
        units = []
        recording_occurrences: dict[str, int] = {}
        media = sorted(
            enumerate(release.get("media", []), start=1),
            key=lambda value: value[1].get("position") or value[0],
        )
        for medium_index, medium in media:
            disc = medium.get("position") or medium_index
            tracks = sorted(
                enumerate(medium.get("tracks", []), start=1),
                key=lambda value: value[1].get("position") or value[0],
            )
            for track_index, track in tracks:
                length = track.get("length")
                position = track.get("position") or track_index
                recording_id = (track.get("recording") or {}).get("id")
                track_id = track.get("id")
                if recording_id:
                    occurrence = recording_occurrences.get(recording_id, 0) + 1
                    recording_occurrences[recording_id] = occurrence
                    suffix = f":o{occurrence}" if occurrence > 1 else ""
                    unit_provider_id = f"recording:{recording_id}{suffix}"
                else:
                    title_hash = hashlib.sha256(
                        (track.get("title") or "").encode()
                    ).hexdigest()[:12]
                    unit_provider_id = (
                        f"fallback:{provider_id}:d{disc}:t{position}:{title_hash}"
                    )
                units.append(
                    ProviderUnit(
                        provider_id=unit_provider_id,
                        title=track.get("title") or "(başlıksız)",
                        unit_type="track",
                        number=float(position) if position else None,
                        duration_min=round(length / 60000) if length else None,
                        progress_total=1,
                        progress_measure="track",
                        provider_ids={
                            key: value
                            for key, value in {
                                "musicbrainz_track": track_id,
                                "musicbrainz_recording": recording_id,
                            }.items()
                            if value
                        },
                        meta={"disc": disc, "release_id": release_id},
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
        return []
