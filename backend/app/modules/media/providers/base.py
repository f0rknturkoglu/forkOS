from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class ProviderCapabilities:
    search: bool = True
    details: bool = True
    units: bool = False
    upcoming: bool = False
    cache_artwork: bool = True
    requires_settings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProviderResult:
    provider: str
    provider_id: str
    title: str
    subtitle: str | None = None
    year: int | None = None
    summary: str | None = None
    total: float | None = None
    progress_measure: str | None = None
    cover_url: str | None = None
    backdrop_url: str | None = None
    provider_ids: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderDetails:
    provider: str
    provider_id: str
    title: str
    summary: str | None = None
    release_date: date | None = None
    total: float | None = None
    progress_measure: str | None = None
    cover_url: str | None = None
    backdrop_url: str | None = None
    provider_ids: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderUnit:
    provider_id: str
    title: str
    unit_type: str
    number: float | None = None
    duration_min: int | None = None
    release_at: datetime | None = None
    progress_total: float | None = None
    progress_measure: str | None = None
    cover_url: str | None = None
    provider_ids: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)


class MediaProvider(Protocol):
    id: str
    kinds: tuple[str, ...]
    capabilities: ProviderCapabilities
    ready: bool
    missing_settings: tuple[str, ...]

    async def search(self, query: str) -> list[ProviderResult]: ...

    async def details(self, provider_id: str) -> ProviderDetails: ...

    async def units(self, provider_id: str) -> list[ProviderUnit]: ...

    async def upcoming(self, provider_id: str, *, days: int) -> list[ProviderUnit]: ...


def deduplicate(results: list[ProviderResult]) -> list[ProviderResult]:
    seen: set[tuple[str, str]] = set()
    unique: list[ProviderResult] = []
    for result in results:
        key = (result.provider, result.provider_id)
        if key not in seen:
            seen.add(key)
            unique.append(result)
    return unique
