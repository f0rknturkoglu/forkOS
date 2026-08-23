from __future__ import annotations

from datetime import UTC, date, datetime

import httpx

from app.modules.media.providers._http import HTTPProvider
from app.modules.media.providers.base import (
    ProviderCapabilities,
    ProviderDetails,
    ProviderResult,
    ProviderUnit,
    deduplicate,
)


class IGDBProvider(HTTPProvider):
    id = "igdb"
    kinds = ("game",)
    capabilities = ProviderCapabilities(
        units=False,
        upcoming=False,
        requires_settings=("media.igdb_client_id", "media.igdb_client_secret"),
    )

    def __init__(
        self,
        *,
        client_id: str | None,
        client_secret: str | None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(client=client)
        self.client_id = client_id
        self.client_secret = client_secret
        self.ready = bool(client_id and client_secret)
        self.missing_settings = tuple(
            key
            for key, value in (
                ("media.igdb_client_id", client_id),
                ("media.igdb_client_secret", client_secret),
            )
            if not value
        )
        self._token: str | None = None

    async def _access_token(self) -> str:
        if self._token:
            return self._token
        response = await self.request(
            "POST",
            "https://id.twitch.tv/oauth2/token",
            params={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            },
        )
        self._token = response.json()["access_token"]
        return self._token

    async def _games(self, body: str) -> list[dict]:
        token = await self._access_token()
        response = await self.request(
            "POST",
            "https://api.igdb.com/v4/games",
            content=body,
            headers={"Client-ID": str(self.client_id), "Authorization": f"Bearer {token}"},
        )
        return response.json()

    @staticmethod
    def _image(image_id: str | None) -> str | None:
        return (
            f"https://images.igdb.com/igdb/image/upload/t_cover_big/{image_id}.jpg"
            if image_id
            else None
        )

    def _result(self, row: dict) -> ProviderResult:
        provider_id = str(row["id"])
        timestamp = row.get("first_release_date")
        released = datetime.fromtimestamp(timestamp, UTC) if timestamp else None
        return ProviderResult(
            provider=self.id,
            provider_id=provider_id,
            title=row.get("name") or "(başlıksız)",
            year=released.year if released else None,
            summary=row.get("summary"),
            progress_measure="hour",
            cover_url=self._image((row.get("cover") or {}).get("image_id")),
            provider_ids={self.id: provider_id},
            meta={"genres": [genre.get("name") for genre in row.get("genres", [])]},
        )

    async def search(self, query: str) -> list[ProviderResult]:
        safe = query.replace('"', "")
        fields = "name,summary,first_release_date,cover.image_id,genres.name"
        rows = await self._games(f'search "{safe}"; fields {fields}; limit 6;')
        return deduplicate([self._result(row) for row in rows])

    async def details(self, provider_id: str) -> ProviderDetails:
        fields = "name,summary,first_release_date,cover.image_id,genres.name"
        row = (await self._games(f"fields {fields}; where id={int(provider_id)};"))[0]
        result = self._result(row)
        released = (
            date.fromtimestamp(row["first_release_date"]) if row.get("first_release_date") else None
        )
        return ProviderDetails(
            provider=result.provider,
            provider_id=result.provider_id,
            title=result.title,
            summary=result.summary,
            release_date=released,
            progress_measure=result.progress_measure,
            cover_url=result.cover_url,
            provider_ids=result.provider_ids,
            meta=result.meta,
        )

    async def units(self, provider_id: str) -> list[ProviderUnit]:
        return []

    async def upcoming(self, provider_id: str, *, days: int) -> list[ProviderUnit]:
        return []
