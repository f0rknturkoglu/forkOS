"""Layer A foundation: HTTP client and the ATS adapter contract.

No browser automation anywhere in this project — httpx and a parser, nothing
else. Public board endpoints only: nothing here authenticates, and nothing here
touches a page a logged-out visitor could not see.
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar
from urllib.parse import urlsplit

import httpx

from ..geo import region_for
from ..models import Company, Job, Region

USER_AGENT = "forkjob/0.1 (personal job search bot)"


class SourceError(Exception):
    """Base class for anything that makes one source unusable this run."""


class TransientError(SourceError):
    """Worth retrying: timeouts, 5xx, 429."""


class PermanentError(SourceError):
    """Not worth retrying this run: 401/403/404, malformed payload."""


@dataclass(slots=True)
class HttpConfig:
    #: Adapters run concurrently; this caps total in-flight requests.
    concurrency: int = 12
    timeout: float = 20.0
    max_retries: int = 3
    backoff_base: float = 0.5
    #: Minimum gap between two requests to the same host. Layer A talks to a
    #: handful of API hosts on behalf of many companies, so politeness here is
    #: per-host, not per-company. Layer B raises this to 2s in its own base.
    min_interval_per_host: float = 0.25
    user_agent: str = USER_AGENT


class HttpClient:
    """httpx wrapper with a concurrency cap, per-host spacing and backoff."""

    def __init__(self, config: HttpConfig | None = None) -> None:
        self.config = config or HttpConfig()
        self._semaphore = asyncio.Semaphore(self.config.concurrency)
        self._host_locks: dict[str, asyncio.Lock] = {}
        self._host_last: dict[str, float] = {}
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> HttpClient:
        self._client = httpx.AsyncClient(
            timeout=self.config.timeout,
            follow_redirects=True,
            headers={"User-Agent": self.config.user_agent, "Accept": "application/json"},
        )
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """One request, retried with exponential backoff on transient failures."""
        if self._client is None:
            raise RuntimeError("HttpClient must be used as an async context manager")

        host = urlsplit(url).netloc
        last_error: Exception | None = None

        for attempt in range(self.config.max_retries):
            async with self._semaphore:
                await self._space_out(host)
                try:
                    response = await self._client.request(method, url, **kwargs)
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    last_error = TransientError(f"{type(exc).__name__}: {exc}")
                else:
                    if response.status_code < 400:
                        return response
                    last_error = _classify(response)
                    if isinstance(last_error, PermanentError):
                        raise last_error

            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(self.config.backoff_base * (2**attempt))

        raise last_error or TransientError("request failed")

    async def get_json(self, url: str, **kwargs: Any) -> Any:
        response = await self.request("GET", url, **kwargs)
        try:
            return response.json()
        except ValueError as exc:
            raise PermanentError(f"{url} did not return JSON: {exc}") from exc

    async def get_text(self, url: str, **kwargs: Any) -> str:
        response = await self.request("GET", url, **kwargs)
        return response.text

    async def _space_out(self, host: str) -> None:
        lock = self._host_locks.setdefault(host, asyncio.Lock())
        async with lock:
            gap = self.config.min_interval_per_host
            elapsed = time.monotonic() - self._host_last.get(host, 0.0)
            if elapsed < gap:
                await asyncio.sleep(gap - elapsed)
            self._host_last[host] = time.monotonic()


def _classify(response: httpx.Response) -> SourceError:
    code = response.status_code
    if code in (401, 403, 404, 410):
        return PermanentError(f"HTTP {code} for {response.request.url}")
    if code == 429 or code >= 500:
        return TransientError(f"HTTP {code} for {response.request.url}")
    return PermanentError(f"HTTP {code} for {response.request.url}")


class ATSAdapter(ABC):
    """One company on one ATS platform.

    Subclasses must fill `external_id` and `date_source` honestly. Whether a
    board reports a publish date or only an edit timestamp is a decision made
    when writing the adapter, with the reasoning in a comment — never guessed
    at scoring time.
    """

    #: Registry key this adapter serves, e.g. "greenhouse".
    ats: ClassVar[str]

    def __init__(self, company: Company) -> None:
        self.company = company

    @property
    def token(self) -> str:
        return self.company.token

    @property
    def source(self) -> str:
        """Source name stamped onto every Job, e.g. "greenhouse:cabify"."""
        return self.company.source

    @abstractmethod
    async def fetch_raw(self, client: HttpClient) -> Any:
        """Return the untouched payload. `probe` reuses this."""

    @abstractmethod
    def parse(self, raw: Any) -> list[Job]:
        """Turn a payload into Jobs. Pure — no network, so mocks can drive it."""

    async def collect(self, client: HttpClient) -> list[Job]:
        jobs = self.parse(await self.fetch_raw(client))
        for job in jobs:
            self.apply_company_fallback(job)
        return jobs

    def apply_company_fallback(self, job: Job) -> None:
        """Fill an unknown location from the registry entry's own country.

        Only when the posting said nothing usable. Peak Games fills its entire
        Lever board's location field with "Full-time", which leaves 20 real
        Istanbul postings in no quota bucket at all; the registry already knows
        the company is in Turkey. A posting that *did* state a location is
        never overridden — Trendyol's Riyadh roles stay in Saudi Arabia.
        """
        if job.country or job.region is not Region.UNKNOWN:
            return
        if not self.company.country:
            return
        job.country = self.company.country
        job.region = region_for(job.country)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.source}>"
