from __future__ import annotations

from datetime import date

import httpx

from app.modules.media.providers._http import HTTPProvider
from app.modules.media.providers.base import (
    ProviderCapabilities,
    ProviderDetails,
    ProviderResult,
    ProviderUnit,
    deduplicate,
)


def _partial_date(value: str | None) -> date | None:
    if not value:
        return None
    for candidate in (value, f"{value}-01", f"{value}-01-01"):
        try:
            return date.fromisoformat(candidate)
        except ValueError:
            continue
    return None


class OpenLibraryProvider(HTTPProvider):
    id = "openlibrary"
    kinds = ("book", "audiobook")
    capabilities = ProviderCapabilities(units=False, upcoming=False)
    ready = True
    missing_settings: tuple[str, ...] = ()

    def __init__(
        self,
        kind: str,
        *,
        google_books_key: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(client=client)
        self.kind = kind
        self.google_books_key = google_books_key

    async def search(self, query: str) -> list[ProviderResult]:
        response = await self.request(
            "GET",
            "https://openlibrary.org/search.json",
            params={
                "q": query,
                "limit": 6,
                "fields": "key,title,author_name,first_publish_year,cover_i,number_of_pages_median",
            },
        )
        results = []
        for row in response.json().get("docs", []):
            provider_id = str(row.get("key") or "").removeprefix("/works/")
            if not provider_id:
                continue
            cover = row.get("cover_i")
            results.append(
                ProviderResult(
                    provider=self.id,
                    provider_id=provider_id,
                    title=row.get("title") or "(başlıksız)",
                    subtitle=", ".join(row.get("author_name") or []) or None,
                    year=row.get("first_publish_year"),
                    total=row.get("number_of_pages_median"),
                    progress_measure="minute" if self.kind == "audiobook" else "page",
                    cover_url=(
                        f"https://covers.openlibrary.org/b/id/{cover}-L.jpg" if cover else None
                    ),
                    provider_ids={self.id: provider_id},
                    meta={},
                )
            )
        if results:
            return deduplicate(results)
        return await self._google_books(query)

    async def _google_books(self, query: str) -> list[ProviderResult]:
        return await GoogleBooksProvider(
            self.kind, api_key=self.google_books_key, client=self._client
        ).search(query)

    async def details(self, provider_id: str) -> ProviderDetails:
        response = await self.request("GET", f"https://openlibrary.org/works/{provider_id}.json")
        row = response.json()
        description = row.get("description")
        if isinstance(description, dict):
            description = description.get("value")
        covers = row.get("covers") or []
        return ProviderDetails(
            provider=self.id,
            provider_id=provider_id,
            title=row.get("title") or "(başlıksız)",
            summary=description,
            release_date=_partial_date(row.get("first_publish_date")),
            progress_measure="minute" if self.kind == "audiobook" else "page",
            cover_url=(
                f"https://covers.openlibrary.org/b/id/{covers[0]}-L.jpg" if covers else None
            ),
            provider_ids={self.id: provider_id},
        )

    async def units(self, provider_id: str) -> list[ProviderUnit]:
        return []

    async def upcoming(self, provider_id: str, *, days: int) -> list[ProviderUnit]:
        return []


class GoogleBooksProvider(HTTPProvider):
    id = "google_books"
    kinds = ("book", "audiobook")
    capabilities = ProviderCapabilities(units=False, upcoming=False)
    ready = True
    missing_settings: tuple[str, ...] = ()

    def __init__(
        self,
        kind: str,
        *,
        api_key: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(client=client)
        self.kind = kind
        self.api_key = api_key

    def _result(self, row: dict) -> ProviderResult:
        info = row.get("volumeInfo") or {}
        published = info.get("publishedDate") or ""
        provider_id = str(row["id"])
        images = info.get("imageLinks") or {}
        return ProviderResult(
            provider=self.id,
            provider_id=provider_id,
            title=info.get("title") or "(başlıksız)",
            subtitle=", ".join(info.get("authors") or []) or None,
            year=int(published[:4]) if published[:4].isdigit() else None,
            summary=info.get("description") or None,
            total=info.get("pageCount"),
            progress_measure="minute" if self.kind == "audiobook" else "page",
            cover_url=images.get("thumbnail") or images.get("smallThumbnail"),
            provider_ids={self.id: provider_id},
            meta={},
        )

    async def search(self, query: str) -> list[ProviderResult]:
        params = {"q": query, "maxResults": 6}
        if self.api_key:
            params["key"] = self.api_key
        response = await self.request(
            "GET", "https://www.googleapis.com/books/v1/volumes", params=params
        )
        return deduplicate([self._result(row) for row in response.json().get("items", [])])

    async def details(self, provider_id: str) -> ProviderDetails:
        response = await self.request(
            "GET",
            f"https://www.googleapis.com/books/v1/volumes/{provider_id}",
            params={"key": self.api_key} if self.api_key else None,
        )
        row = response.json()
        result = self._result(row)
        published = (row.get("volumeInfo") or {}).get("publishedDate")
        released = None
        if published:
            try:
                released = date.fromisoformat(published)
            except ValueError:
                if published[:4].isdigit():
                    released = date(int(published[:4]), 1, 1)
        return ProviderDetails(
            provider=self.id,
            provider_id=provider_id,
            title=result.title,
            summary=result.summary,
            release_date=released,
            total=result.total,
            progress_measure=result.progress_measure,
            cover_url=result.cover_url,
            provider_ids=result.provider_ids,
            meta=result.meta,
        )

    async def units(self, provider_id: str) -> list[ProviderUnit]:
        return []

    async def upcoming(self, provider_id: str, *, days: int) -> list[ProviderUnit]:
        return []
