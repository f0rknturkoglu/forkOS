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
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from app.sources.base import ScrapeTelemetry, retry_after_seconds

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
    max_response_bytes: int = 8 * 1024 * 1024


class HttpClient:
    """httpx wrapper with a concurrency cap, per-host spacing and backoff."""

    def __init__(self, config: HttpConfig | None = None) -> None:
        self.config = config or HttpConfig()
        self._semaphore = asyncio.Semaphore(self.config.concurrency)
        self._host_locks: dict[str, asyncio.Lock] = {}
        self._host_last: dict[str, float] = {}
        self._client: httpx.AsyncClient | None = None
        self._robots = {}

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

        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise PermanentError("ATS requires a public HTTPS source URL")
        host = parsed.netloc
        await self._check_robots(url)
        last_error: Exception | None = None

        for attempt in range(self.config.max_retries):
            response: httpx.Response | None = None
            async with self._semaphore:
                await self._space_out(host)
                try:
                    response = await self._bounded_response(method, url, **kwargs)
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    last_error = TransientError(f"{type(exc).__name__}: {exc}")
                else:
                    if response.status_code < 400:
                        return response
                    last_error = _classify(response)
                    if isinstance(last_error, PermanentError):
                        raise last_error

            delay = self.config.backoff_base * (2**attempt)
            if response is not None and response.status_code in {429, 503}:
                retry_after = retry_after_seconds(response.headers.get("Retry-After"))
                if retry_after is not None:
                    # Sunucunun soyledigi sureye uy; kotu baslik kosuyu kilitlemesin.
                    if retry_after > 300:
                        raise TransientError("Retry-After exceeds bounded run wait; no early retry")
                    delay = retry_after
            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(delay)

        raise last_error or TransientError("request failed")

    async def _check_robots(self, url):
        parsed = urlsplit(url)
        root = f"{parsed.scheme}://{parsed.netloc}"
        if root not in self._robots:
            await self._space_out(parsed.netloc)
            response = await self._bounded_response("GET", root + "/robots.txt", timeout=10)
            if response.status_code == 404:
                self._robots[root] = None
            elif response.status_code == 200 and "user-agent:" in response.text.lower() and "<html" not in response.text.lower():
                parser = RobotFileParser(root + "/robots.txt")
                parser.parse(response.text.splitlines())
                self._robots[root] = parser
            else:
                raise PermanentError("ATS robots policy could not be verified")
        parser = self._robots[root]
        if parser and not parser.can_fetch(self.config.user_agent, url):
            raise PermanentError("ATS robots policy denies requested route")

    async def _bounded_response(self, method, url, **kwargs):
        original = urlsplit(url)
        for index in range(6):
            parsed = urlsplit(url)
            if parsed.scheme != "https" or parsed.hostname != original.hostname or parsed.port not in {None, 443} or parsed.username or parsed.password:
                raise PermanentError("ATS redirect outside original public host")
            if index and parsed.path != "/robots.txt" and original.path != "/robots.txt":
                await self._check_robots(url)
                await self._space_out(parsed.netloc)
            response = await self._read_response(method, url, **{**kwargs, "follow_redirects": False})
            if response.status_code not in {301, 302, 303, 307, 308}:
                return response
            location = response.headers.get("location")
            if not location:
                raise PermanentError("ATS redirect without Location")
            url = urljoin(url, location)
            if response.status_code == 303:
                method = "GET"
                kwargs.pop("json", None)
        raise PermanentError("ATS redirect limit reached")

    async def _read_response(self, method, url, **kwargs):
        async with self._client.stream(method, url, **kwargs) as response:
            chunks, size = [], 0
            async for chunk in response.aiter_bytes():
                size += len(chunk)
                if size > self.config.max_response_bytes:
                    raise PermanentError("ATS decoded response exceeds byte budget")
                chunks.append(chunk)
            headers = dict(response.headers)
            headers.pop("content-encoding", None)
            headers.pop("content-length", None)
            return httpx.Response(response.status_code, content=b"".join(chunks), headers=headers, request=response.request)

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
        self.telemetry = None
        self.parse_errors = 0

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

    def parse_record(self, entry, *args):
        """A malformed record must not erase other valid employer postings."""
        if not isinstance(entry, dict):
            self.parse_errors += 1
            return None
        try:
            job = self._parse_one(entry, *args)
        except (AttributeError, TypeError, ValueError, OverflowError):
            self.parse_errors += 1
            return None
        if job is None:
            self.parse_errors += 1
        return job

    async def collect(self, client: HttpClient) -> list[Job]:
        raw = await self.fetch_raw(client)
        jobs = self.parse(raw)
        records = raw if isinstance(raw, list) else next((raw[k] for k in ("jobs", "offers", "data", "content") if isinstance(raw, dict) and isinstance(raw.get(k), list)), [])
        if records and not jobs:
            raise PermanentError(f"{self.source}: nonempty response has no valid jobs")
        if self.telemetry is None:
            complete = self.ats in {"greenhouse", "lever", "ashby", "recruitee", "personio"}
            self.telemetry = ScrapeTelemetry(items_seen=len(jobs), items_returned=len(jobs), pages_fetched=1,
                cap_hit=not complete, partial_reason=None if complete else "upstream_window_unverified",
                stop_reason="exhausted" if complete else "upstream_window_unverified",
                metadata={"listing_completeness": "complete_contract" if complete else "unverified"})
        else:
            self.telemetry.items_returned = len(jobs)
        if self.parse_errors:
            self.telemetry.partial_reason = "malformed_job_records"
            self.telemetry.metadata["malformed_records"] = self.parse_errors
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
