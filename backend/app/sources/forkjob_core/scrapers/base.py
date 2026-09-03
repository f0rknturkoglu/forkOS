"""Layer B foundation: rate-limited HTTP, robots.txt, caching, mock replay.

Layer B scrapers are inherently fragile — HTML changes break selectors, portals
rate-limit aggressively, and some sites block non-browser user agents. This
module isolates that fragility: one dead scraper records an error and the rest
of the sync carries on.

Key differences from Layer A's HttpClient:
  - Per-host delay defaults to 2.0 s (vs 0.25 s for ATS APIs).
  - robots.txt is checked and cached before the first scrape of a host.
  - Responses can be cached to disk for offline development.
  - Mock mode replays cached responses without network access.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha1
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx
from selectolax.parser import HTMLParser

from ..models import Job

USER_AGENT = "forkjob/0.1 (personal job search bot; +https://github.com/f0rkjob)"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ScraperError(Exception):
    """Base for anything that makes one scraper unusable this run."""


class ScraperTransientError(ScraperError):
    """Worth retrying: timeouts, 5xx, 429."""


class ScraperPermanentError(ScraperError):
    """Not worth retrying: 403/404, robots.txt disallow, broken layout."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RobotsPolicy(StrEnum):
    RESPECT = "respect"  # check robots.txt, obey disallow
    IGNORE = "ignore"  # skip the check entirely
    WARN = "warn"  # check but only log disallowed paths


class CacheMode(StrEnum):
    OFF = "off"  # never cache
    WRITE = "write"  # cache every fresh response
    READ = "read"  # replay from cache, never hit the network


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ScraperConfig:
    """Per-scraper configuration, overridable per source."""

    #: Minimum seconds between two requests to the same host.
    min_interval: float = 2.0
    #: Request timeout in seconds.
    timeout: float = 30.0
    #: Max retries on transient failures.
    max_retries: int = 3
    #: Exponential backoff base (seconds).
    backoff_base: float = 1.0
    #: robots.txt policy.
    robots: RobotsPolicy = RobotsPolicy.RESPECT
    #: Caching mode.
    cache: CacheMode = CacheMode.WRITE
    #: User-Agent header.
    user_agent: str = USER_AGENT
    #: Where cached responses live for offline replay. Absolute so a run works
    #: regardless of the process working directory.
    cache_dir: Path = Path(__file__).resolve().parents[4] / "data" / "cache"


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------


class ScraperHttpClient:
    """httpx wrapper with per-host rate limiting, robots.txt, and caching.

    Usage:
        async with ScraperHttpClient(config) as client:
            html = await client.get_html("https://example.com/jobs")
            data = await client.get_json("https://example.com/api/jobs")
    """

    def __init__(self, config: ScraperConfig | None = None) -> None:
        self.config = config or ScraperConfig()
        self._client: httpx.AsyncClient | None = None
        self._host_last: dict[str, float] = {}
        self._host_locks: dict[str, asyncio.Lock] = {}
        self._robots_cache: dict[str, RobotFileParser | None] = {}

    async def __aenter__(self) -> ScraperHttpClient:
        self._client = httpx.AsyncClient(
            timeout=self.config.timeout,
            follow_redirects=True,
            headers={
                "User-Agent": self.config.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/json,*/*",
                "Accept-Language": "en,es;q=0.9",
            },
        )
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # -- public --------------------------------------------------------------

    async def get_html(self, url: str, **kwargs: Any) -> str:
        """Fetch a page and return its HTML text."""
        response = await self._request("GET", url, **kwargs)
        return response.text

    async def get_json(self, url: str, **kwargs: Any) -> Any:
        """Fetch JSON from an API endpoint."""
        response = await self._request("GET", url, **kwargs)
        return response.json()

    async def post_json(self, url: str, payload: Any, **kwargs: Any) -> Any:
        """POST a JSON body and return the JSON response.

        Some portals only expose search through POST — EURES is one. The cache
        key includes the payload, so two different searches against the same
        URL do not collide.
        """
        response = await self._request("POST", url, json=payload, **kwargs)
        return response.json()

    async def parse_page(self, url: str, **kwargs: Any) -> HTMLParser:
        """Fetch a page and return a selectolax HTMLParser."""
        html = await self.get_html(url, **kwargs)
        return HTMLParser(html)

    # -- internal ------------------------------------------------------------

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        if self._client is None:
            raise RuntimeError("ScraperHttpClient must be used as an async context manager")

        host = urlsplit(url).netloc

        # robots.txt check
        if self.config.robots is RobotsPolicy.RESPECT:
            await self._check_robots(host, url)

        # A POST search sends its query in the body, so the body has to be part
        # of the cache key — otherwise every EURES search would collide on the
        # single search URL and replay the first one.
        cache_key = url
        if method != "GET" and "json" in kwargs:
            cache_key = f"{url}#{json.dumps(kwargs['json'], sort_keys=True)}"

        # Cache read
        if self.config.cache is CacheMode.READ:
            cached = self._load_cache(cache_key)
            if cached is not None:
                return _cached_response(cached)

        # Actual request with retries
        last_error: Exception | None = None
        for attempt in range(self.config.max_retries):
            await self._rate_limit(host)
            try:
                response = await self._client.request(method, url, **kwargs)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = ScraperTransientError(f"{type(exc).__name__}: {exc}")
                response = None
            else:
                if response.status_code < 400:
                    # Cache write
                    if self.config.cache is CacheMode.WRITE:
                        self._save_cache(cache_key, response)
                    return response
                last_error = _classify_scraper(response)
                if isinstance(last_error, ScraperPermanentError):
                    raise last_error

            delay = self.config.backoff_base * (2**attempt)
            if response is not None and response.status_code == 429:
                retry_after = _retry_after_seconds(response.headers.get("Retry-After"))
                if retry_after is not None:
                    # The server said how long to wait; honour it, capped so a
                    # bad header cannot stall the whole run.
                    delay = min(retry_after, 300)
            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(delay)

        raise last_error or ScraperTransientError("request failed")

    async def _rate_limit(self, host: str) -> None:
        lock = self._host_locks.setdefault(host, asyncio.Lock())
        async with lock:
            gap = self.config.min_interval
            elapsed = time.monotonic() - self._host_last.get(host, 0.0)
            if elapsed < gap:
                await asyncio.sleep(gap - elapsed)
            self._host_last[host] = time.monotonic()

    async def _check_robots(self, host: str, url: str) -> None:
        if host in self._robots_cache:
            rp = self._robots_cache[host]
            if rp is not None and not rp.can_fetch(self.config.user_agent, url):
                raise ScraperPermanentError(f"robots.txt disallows {url}")
            return

        if self._client is None:
            return

        robots_url = f"https://{host}/robots.txt"
        await self._rate_limit(host)
        try:
            resp = await self._client.get(robots_url, timeout=10.0)
            if resp.status_code == 200:
                rp = RobotFileParser()
                rp.parse(resp.text.splitlines())
            else:
                rp = None  # no robots.txt → allow all
        except Exception:
            rp = None

        self._robots_cache[host] = rp
        if rp is not None and not rp.can_fetch(self.config.user_agent, url):
            if self.config.robots is RobotsPolicy.WARN:
                print(f"[warn] robots.txt disallows {url}", file=sys.stderr)
            else:
                raise ScraperPermanentError(f"robots.txt disallows {url}")

    # -- cache ---------------------------------------------------------------

    def _cache_path(self, cache_key: str) -> Path:
        """Cache filename. `cache_key` is the URL, plus the body for a POST."""
        key = sha1(cache_key.encode()).hexdigest()[:16]
        return self.config.cache_dir / key

    def _load_cache(self, url: str) -> dict[str, Any] | None:
        path = self._cache_path(url)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def _save_cache(self, url: str, response: httpx.Response) -> None:
        try:
            self.config.cache_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "url": url,
                "status": response.status_code,
                "headers": dict(response.headers),
                "text": response.text,
            }
            self._cache_path(url).write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )
        except OSError:
            pass  # cache failure must never break the scrape


def _cached_response(data: dict[str, Any]) -> httpx.Response:
    """Reconstruct an httpx.Response from cached data."""
    return httpx.Response(
        status_code=data["status"],
        headers=data.get("headers", {}),
        text=data.get("text", ""),
        request=httpx.Request("GET", data.get("url", "")),
    )


def _classify_scraper(response: httpx.Response) -> ScraperError:
    code = response.status_code
    url = str(response.request.url)
    if code in (401, 403):
        return ScraperPermanentError(f"HTTP {code} (blocked) for {url}")
    if code in (404, 410):
        return ScraperPermanentError(f"HTTP {code} (gone) for {url}")
    if code == 429 or code >= 500:
        return ScraperTransientError(f"HTTP {code} for {url}")
    return ScraperPermanentError(f"HTTP {code} for {url}")


def _retry_after_seconds(value: str | None) -> int | None:
    """Seconds from a Retry-After header, or None when it is not a number.

    Only the integer-seconds form is handled; the HTTP-date form is rare on
    429s. Callers cap the result so a bad header cannot stall a run.
    """
    if not value:
        return None
    try:
        return int(value.strip())
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Base scraper class
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ScrapeBatch:
    """Jobs collected across one or more independently failing profiles."""

    jobs: list[Job]
    errors: list[str]
    attempted: int
    succeeded: int

    @classmethod
    def ok(cls, jobs: list[Job]) -> ScrapeBatch:
        return cls(jobs=jobs, errors=[], attempted=1, succeeded=1)


class ScraperBase(ABC):
    """One Layer B source.

    Subclasses implement `scrape` which receives a pre-configured
    ScraperHttpClient and returns jobs directly or as a partial-aware batch.

    The scraper must set `date_source` honestly. An HTML scraper that cannot
    find a publish date must say `DISCOVERED` — guessing produces fake
    freshness and buries genuinely new postings.
    """

    @property
    def scope(self) -> str:
        """What this run is asking the source for.

        Closing a posting means "the source stopped listing it". For a source
        that answers a *filtered* question, that inference only holds when the
        question has not changed — widening EURES from 7 countries to 31, or
        narrowing it to entry-level, changes which postings can appear at all.
        `db.apply_missed_syncs` compares this against the previous successful
        run and declines to close anything when it differs.

        The default is empty, which is correct for a source that always returns
        its whole feed.
        """
        return ""

    #: Key matching the registry, e.g. "tecnoempleo", "infojobs".
    source_key: str = ""
    #: Display name for reporting.
    label: str = ""
    #: Base URL for the source (used for robots.txt and reporting).
    base_url: str = ""
    #: Registry keys this class answers for. Defaults to `(source_key,)`; a
    #: class that serves several portals (Consider) lists them all.
    registry_keys: ClassVar[tuple[str, ...] | None] = None

    def __init__(self, config: ScraperConfig | None = None) -> None:
        self.config = config or ScraperConfig()
        #: Permanent failures recorded by `isolate`, one entry per dead slice.
        #: Read by the caller when a run returns fewer jobs than expected.
        self.errors: list[str] = []

    @property
    def source(self) -> str:
        """Source name stamped onto every Job, e.g. "infojobs", "tecnoempleo"."""
        return self.source_key or self.label.lower().replace(" ", "_")

    @abstractmethod
    async def scrape(self, client: ScraperHttpClient) -> list[Job] | ScrapeBatch:
        """Fetch and parse all available jobs. Pure — no side effects."""

    async def isolate(self, label: str, fn: Callable[[], Awaitable[Any]]) -> Any:
        """Run one slice that may permanently fail; record the reason.

        The "one dead page must not sink the run" pattern without every
        scraper re-writing the try/except. `fn` is a zero-argument coroutine
        (usually a fetch). On a ScraperPermanentError the reason is recorded
        on `self.errors` under `label` and None comes back — the caller's
        existing `if … is None: break/continue` keeps the old control flow.
        Transient errors propagate because the client already retried them.
        """
        try:
            return await fn()
        except ScraperPermanentError as exc:
            self.errors.append(f"{label}: {exc}")
            return None

    def dedup_seen(self, seen: set[str], jobs: list[Job]) -> list[Job]:
        """The jobs in `jobs` whose key is not in `seen`; `seen` gains them.

        The pagination dedup every scraper used to write by hand. The key is
        `external_id`, falling back to the URL; `seen` is mutated in place
        because the caller owns it across the loop.
        """
        fresh: list[Job] = []
        for job in jobs:
            key = job.external_id or job.url
            if key in seen:
                continue
            seen.add(key)
            fresh.append(job)
        return fresh

    async def collect(self, client: ScraperHttpClient | None = None) -> list[Job] | ScrapeBatch:
        """Convenience wrapper that creates a client if one is not provided."""
        if client is not None:
            return await self.scrape(client)
        async with ScraperHttpClient(self.config) as c:
            return await self.scrape(c)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.source}>"


# ---------------------------------------------------------------------------
# HTML helpers (shared across all HTML scrapers)
# ---------------------------------------------------------------------------


def css_first(parser: HTMLParser, selector: str, *, attr: str | None = None) -> str | None:
    """Return text or attribute of the first element matching a CSS selector."""
    node = parser.css_first(selector)
    if node is None:
        return None
    if attr:
        return node.attributes.get(attr)
    return node.text(deep=True, separator=" ").strip() or None


def css_all(parser: HTMLParser, selector: str, *, attr: str | None = None) -> list[str]:
    """Return text or attribute of all elements matching a CSS selector."""
    results: list[str] = []
    for node in parser.css(selector):
        if attr:
            val = node.attributes.get(attr)
            if val:
                results.append(val.strip())
        else:
            text = node.text(deep=True, separator=" ").strip()
            if text:
                results.append(text)
    return results
