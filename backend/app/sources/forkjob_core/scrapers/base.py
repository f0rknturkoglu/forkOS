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
import gzip
import json
import sys
import time
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha1
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx
from selectolax.parser import HTMLParser

from app.sources.base import ScrapeTelemetry, retry_after_seconds

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
    OFF = "off"  # never cache (default)
    WRITE = "write"  # write-on-miss + conditional revalidation
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
    #: Optional decoded response bound; zero preserves existing source behavior.
    max_response_bytes: int = 8 * 1024 * 1024
    #: Optional fixed public hosts; redirects are checked before following.
    allowed_hosts: tuple[str, ...] = ()
    #: Max retries on transient failures.
    max_retries: int = 3
    #: Exponential backoff base (seconds).
    backoff_base: float = 1.0
    #: robots.txt policy.
    robots: RobotsPolicy = RobotsPolicy.RESPECT
    #: Caching mode. OFF by default: caching is opt-in, never a silent 441 MB
    #: directory that grows forever.
    cache: CacheMode = CacheMode.OFF
    #: User-Agent header.
    user_agent: str = USER_AGENT
    #: Where cached responses live for offline replay. Absolute so a run works
    #: regardless of the process working directory.
    cache_dir: Path = Path(__file__).resolve().parents[4] / "data" / "cache"
    #: Toplam disk butcesi; asilinca en eski (LRU) kayitlar silinir. 0 = sinirsiz.
    cache_max_bytes: int = 256 * 1024 * 1024
    #: Kayit omru; bu sureden eski kayitlar okunmaz ve budanir. 0 = sinirsiz.
    cache_max_age_seconds: int = 7 * 24 * 3600
    #: Govdeyi diskte gzip'le.
    cache_compress: bool = True
    #: Butce/temizlik kontrolunu bu kadar saniyede birden fazla calistirma.
    cache_prune_interval_seconds: float = 60.0


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
        #: Butce/TTL kontrolunu her yazimda degil, araliklarla calistir.
        self._last_prune = 0.0
        self.empty_contracts: list[bool] = []

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
        body = response.text
        stripped = body.lstrip().lower()
        xml = False
        if stripped.startswith(("<?xml", "<rss", "<feed", "<urlset", "<sitemapindex")):
            from xml.etree import ElementTree as ET
            try:
                root = ET.fromstring(body)
                tag = root.tag.rsplit("}", 1)[-1]
                xml = tag in {"rss", "feed", "RDF", "urlset", "sitemapindex"} and not any(
                    n.tag.rsplit("}", 1)[-1] in {"item", "entry", "url", "sitemap"} for n in root.iter()
                )
            except ET.ParseError:
                pass
        empty = bool(HTMLParser(body).css_first("[data-empty-results], .jobs-search__no-results"))
        self.empty_contracts.append(xml or empty)
        return body

    async def get_json(self, url: str, **kwargs: Any) -> Any:
        """Fetch JSON from an API endpoint."""
        response = await self._request("GET", url, **kwargs)
        data = response.json()
        self.empty_contracts.append(_recognized_json_empty(data))
        return data

    async def post_json(self, url: str, payload: Any, **kwargs: Any) -> Any:
        """POST a JSON body and return the JSON response.

        Some portals only expose search through POST — EURES is one. The cache
        key includes the payload, so two different searches against the same
        URL do not collide.
        """
        response = await self._request("POST", url, json=payload, **kwargs)
        data = response.json()
        self.empty_contracts.append(_recognized_json_empty(data))
        return data

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

        cached = None
        if self.config.cache is not CacheMode.OFF:
            cached = self._load_cache(cache_key, url)
        if cached is not None and self.config.cache is CacheMode.READ:
            return _cached_response(cached)

        # Acik onbellekte kosullu istek: ETag/Last-Modified ile 304 bekle.
        request_kwargs = kwargs
        if cached is not None and self.config.cache is CacheMode.WRITE:
            headers = dict(kwargs.get("headers") or {})
            if cached.get("etag"):
                headers.setdefault("If-None-Match", cached["etag"])
            if cached.get("last_modified"):
                headers.setdefault("If-Modified-Since", cached["last_modified"])
            if headers:
                request_kwargs = {**kwargs, "headers": headers}

        # Actual request with retries
        last_error: Exception | None = None
        for attempt in range(self.config.max_retries):
            await self._rate_limit(host)
            try:
                response = await self._bounded_request(method, url, **request_kwargs)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = ScraperTransientError(f"{type(exc).__name__}: {exc}")
                response = None
            else:
                if response.status_code == 304 and cached is not None:
                    self._touch_cache(cache_key, cached)
                    return _cached_response(cached)
                if response.status_code < 400:
                    # Cache write
                    if self.config.cache is CacheMode.WRITE:
                        self._save_cache(cache_key, url, response)
                    return response
                last_error = _classify_scraper(response)
                if isinstance(last_error, ScraperPermanentError):
                    raise last_error

            delay = self.config.backoff_base * (2**attempt)
            if response is not None and response.status_code in {429, 503}:
                retry_after = _retry_after_seconds(response.headers.get("Retry-After"))
                if retry_after is not None:
                    # The server said how long to wait; honour it, capped so a
                    # bad header cannot stall the whole run.
                    if retry_after > 300:
                        raise ScraperTransientError("Retry-After exceeds bounded wait; no early retry")
                    delay = retry_after
            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(delay)

        raise last_error or ScraperTransientError("request failed")

    async def _bounded_request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        initial_url = urlsplit(url)
        initial_host = initial_url.hostname
        if not initial_host or initial_url.scheme not in {"http", "https"}:
            raise ScraperPermanentError("invalid public source URL")
        allowed_hosts = self.config.allowed_hosts or (initial_host, ("www." + initial_host.removeprefix("www.")), initial_host.removeprefix("www."))
        if allowed_hosts:
            kwargs = {**kwargs, "follow_redirects": False}
            for redirect_index in range(6):
                parsed = urlsplit(url)
                if (parsed.scheme not in {"http", "https"}
                    or parsed.hostname not in allowed_hosts
                    or parsed.username or parsed.password or parsed.port not in {None, 80, 443}):
                    raise ScraperPermanentError("source URL is outside fixed public host scope")
                if redirect_index:
                    if self.config.robots is RobotsPolicy.RESPECT and initial_url.path != "/robots.txt":
                        await self._check_robots(parsed.netloc, url)
                    await self._rate_limit(parsed.netloc)
                response = await self._read_bounded_response(method, url, **kwargs)
                if response.status_code not in {301, 302, 303, 307, 308}:
                    return response
                location = response.headers.get("location")
                if not location:
                    raise ScraperPermanentError("redirect without Location")
                url = urljoin(url, location)
                if response.status_code == 303:
                    method = "GET"
                # New source endpoints are read-only GETs. A redirect is never
                # allowed to turn a board into an arbitrary network target.
            raise ScraperPermanentError("source redirect limit reached")
        return await self._read_bounded_response(method, url, **kwargs)

    async def _read_bounded_response(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        if self.config.max_response_bytes <= 0:
            return await self._client.request(method, url, **kwargs)
        async with self._client.stream(method, url, **kwargs) as response:
            chunks: list[bytes] = []
            size = 0
            async for chunk in response.aiter_bytes():
                size += len(chunk)
                if size > self.config.max_response_bytes:
                    raise ScraperPermanentError(
                        f"response exceeds {self.config.max_response_bytes} decoded bytes: {url}"
                    )
                chunks.append(chunk)
            # aiter_bytes has already decompressed the transport body.
            headers = dict(response.headers)
            headers.pop("content-encoding", None)
            headers.pop("content-length", None)
            return httpx.Response(response.status_code, headers=headers,
                                  content=b"".join(chunks), request=response.request)

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
            resp = await self._bounded_request("GET", robots_url, timeout=10.0)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise ScraperTransientError("robots policy unavailable") from exc
        except ScraperPermanentError:
            self._robots_cache[host] = None
            return

        if resp.status_code in {401, 403, 404}:
            # RFC 9309: 4xx indicates no robots restriction
            rp = None
        elif resp.status_code == 200 and "user-agent:" in resp.text.lower() and "<html" not in resp.text.lower():
            rp = RobotFileParser()
            rp.parse(resp.text.splitlines())
        elif resp.status_code == 200 and "<html" in resp.text.lower():
            rp = None
        else:
            rp = None

        self._robots_cache[host] = rp
        if rp is not None and not rp.can_fetch(self.config.user_agent, url):
            if self.config.robots is RobotsPolicy.WARN:
                print(f"[warn] robots.txt disallows {url}", file=sys.stderr)
            else:
                raise ScraperPermanentError(f"robots.txt disallows {url}")

    # -- cache ---------------------------------------------------------------

    def _cache_path(self, cache_key: str, url: str) -> Path:
        """Cache filename: `<host>--<sha1>.json[.gz]`.

        Host oneki dosya adinda kalir; istatistik ve host bazli kullanim
        dosyalari ACMADAN hesaplanabilsin.
        """
        host = urlsplit(url).netloc or "unknown"
        host = "".join(ch if (ch.isalnum() or ch in "._-") else "_" for ch in host)
        digest = sha1(cache_key.encode()).hexdigest()[:16]
        suffix = ".json.gz" if self.config.cache_compress else ".json"
        return self.config.cache_dir / f"{host}--{digest}{suffix}"

    def _legacy_cache_path(self, cache_key: str) -> Path:
        """Eski surumun uzantisiz sha1 dosyasi -- hala okunur."""
        return self.config.cache_dir / sha1(cache_key.encode()).hexdigest()[:16]

    def _load_cache(self, cache_key: str, url: str) -> dict[str, Any] | None:
        for path in (self._cache_path(cache_key, url), self._legacy_cache_path(cache_key)):
            if not path.exists():
                continue
            data = _read_cache_entry(path)
            if data is None:
                continue
            max_age = self.config.cache_max_age_seconds
            # mtime, prune ile ayni saati kullanir: yazma/304 tazeleme mtime'i
            # gunceller, boylece TTL ve LRU tek bir olcut uzerinden calisir.
            try:
                saved_at = path.stat().st_mtime
            except OSError:
                saved_at = data.get("saved_at") or time.time()
            if max_age > 0 and (time.time() - saved_at) > max_age:
                _unlink(path)
                return None
            data["_path"] = str(path)
            return data
        return None

    def _save_cache(self, cache_key: str, url: str, response: httpx.Response) -> None:
        try:
            self.config.cache_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "url": url,
                "status": response.status_code,
                "headers": dict(response.headers),
                "text": response.text,
                "saved_at": time.time(),
                "etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified"),
            }
            _write_cache_entry(self._cache_path(cache_key, url), payload, self.config)
            self._enforce_budget()
        except OSError:
            pass  # cache failure must never break the scrape

    def _touch_cache(self, cache_key: str, data: dict[str, Any]) -> None:
        """304 yanitinda kaydin tazeligini isaretle (yeniden indirmeden)."""
        path = Path(data.get("_path") or self._cache_path(cache_key, data.get("url", "")))
        try:
            payload = {key: value for key, value in data.items() if not key.startswith("_")}
            payload["saved_at"] = time.time()
            _write_cache_entry(path, payload, self.config)
        except OSError:
            pass

    def _enforce_budget(self) -> None:
        """TTL ve toplam byte butcesini uygula; sik cagrilmasin (throttle)."""
        now = time.monotonic()
        if now - self._last_prune < self.config.cache_prune_interval_seconds:
            return
        self._last_prune = now
        prune_cache(
            self.config,
            max_bytes=self.config.cache_max_bytes,
            max_age_seconds=self.config.cache_max_age_seconds,
        )


def _cached_response(data: dict[str, Any]) -> httpx.Response:
    """Reconstruct an httpx.Response from cached data."""
    return httpx.Response(
        status_code=data["status"],
        headers=data.get("headers", {}),
        text=data.get("text", ""),
        request=httpx.Request("GET", data.get("url", "")),
    )


# ---------------------------------------------------------------------------
# On-disk onbellek yardimcilari
#
# Bunlarin hepsi YALNIZCA dosya sistemiyle calisir; PostgreSQL'e hicbir
# erisimleri yoktur ve olmamalidir.
# ---------------------------------------------------------------------------


def _iter_cache_files(cache_dir: Path):
    if not cache_dir.exists():
        return
    try:
        entries = list(cache_dir.iterdir())
    except OSError:
        return
    for path in entries:
        if path.is_file() and not path.name.startswith("."):
            yield path


def _unlink(path: Path) -> bool:
    try:
        path.unlink()
        return True
    except OSError:
        return False


def _read_cache_entry(path: Path) -> dict[str, Any] | None:
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    try:
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        return json.loads(raw.decode("utf-8"))
    except (OSError, gzip.BadGzipFile, json.JSONDecodeError, UnicodeDecodeError):
        return None


def _write_cache_entry(path: Path, payload: dict[str, Any], config: ScraperConfig) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    if config.cache_compress:
        body = gzip.compress(body)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(body)
    tmp.replace(path)


def prune_cache(
    config: ScraperConfig | None = None,
    *,
    max_bytes: int | None = None,
    max_age_seconds: int | None = None,
) -> dict[str, Any]:
    """TTL'i gecenleri sil, sonra byte butcesine inene kadar en eskileri (LRU).

    Yalnizca bellek dosyalarina dokunur; PostgreSQL satirlari etkilenmez.
    """
    cfg = config or ScraperConfig()
    max_bytes = cfg.cache_max_bytes if max_bytes is None else max_bytes
    max_age_seconds = cfg.cache_max_age_seconds if max_age_seconds is None else max_age_seconds
    now = time.time()
    entries: list[tuple[Path, float, int]] = []
    total = 0
    for path in _iter_cache_files(cfg.cache_dir):
        try:
            stat = path.stat()
        except OSError:
            continue
        entries.append((path, stat.st_mtime, stat.st_size))
        total += stat.st_size

    removed = 0
    freed = 0
    if max_age_seconds and max_age_seconds > 0:
        for path, mtime, size in entries:
            if now - mtime > max_age_seconds and _unlink(path):
                removed += 1
                freed += size
                total -= size
        entries = [entry for entry in entries if entry[0].exists()]

    if max_bytes and max_bytes > 0 and total > max_bytes:
        for path, _mtime, size in sorted(entries, key=lambda entry: entry[1]):
            if total <= max_bytes:
                break
            if _unlink(path):
                removed += 1
                freed += size
                total -= size

    return {
        "removed": removed,
        "bytes_freed": freed,
        "bytes_remaining": max(total, 0),
        "max_bytes": max_bytes,
        "max_age_seconds": max_age_seconds,
    }


def clear_cache(config: ScraperConfig | None = None) -> dict[str, Any]:
    """Onbellek dizinindeki TUM dosyalari sil. PostgreSQL'e dokunmaz."""
    cfg = config or ScraperConfig()
    removed = 0
    freed = 0
    for path in _iter_cache_files(cfg.cache_dir):
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        if _unlink(path):
            removed += 1
            freed += size
    return {"removed": removed, "bytes_freed": freed, "dir": str(cfg.cache_dir)}


def cache_stats(config: ScraperConfig | None = None) -> dict[str, Any]:
    """Boyut, dosya sayisi, en eski kayit ve host basina kullanim."""
    cfg = config or ScraperConfig()
    files = 0
    total = 0
    oldest: float | None = None
    hosts: dict[str, int] = {}
    for path in _iter_cache_files(cfg.cache_dir):
        try:
            stat = path.stat()
        except OSError:
            continue
        files += 1
        total += stat.st_size
        oldest = stat.st_mtime if oldest is None else min(oldest, stat.st_mtime)
        host = path.name.split("--", 1)[0] if "--" in path.name else "legacy"
        hosts[host] = hosts.get(host, 0) + stat.st_size
    return {
        "dir": str(cfg.cache_dir),
        "mode": cfg.cache.value,
        "files": files,
        "bytes": total,
        "oldest": datetime.fromtimestamp(oldest, UTC).isoformat() if oldest else None,
        "hosts": dict(sorted(hosts.items(), key=lambda item: -item[1])),
        "max_bytes": cfg.cache_max_bytes,
        "max_age_seconds": cfg.cache_max_age_seconds,
    }


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
    """Retry-After: hem tamsayi saniye hem HTTP-date bicimini destekler."""
    return retry_after_seconds(value)


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
    telemetry: ScrapeTelemetry | None = None

    @classmethod
    def ok(cls, jobs: list[Job], telemetry: ScrapeTelemetry | None = None) -> ScrapeBatch:
        return cls(jobs=jobs, errors=[], attempted=1, succeeded=1, telemetry=telemetry)


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
        self.telemetry: ScrapeTelemetry | None = None

    def record_telemetry(
        self,
        *,
        items_seen: int | None = None,
        items_returned: int | None = None,
        pages_fetched: int | None = None,
        page_limit: int | None = None,
        result_limit: int | None = None,
        cap_hit: bool | None = None,
        partial_reason: str | None = None,
        stop_reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ScrapeTelemetry:
        self.telemetry = ScrapeTelemetry(
            items_seen=items_seen,
            items_returned=items_returned,
            pages_fetched=pages_fetched,
            page_limit=page_limit,
            result_limit=result_limit,
            cap_hit=cap_hit,
            partial_reason=partial_reason,
            stop_reason=stop_reason,
            metadata=metadata or {},
        )
        return self.telemetry

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
        Exhausted transient errors are also recorded, preserving earlier pages.
        """
        try:
            return await fn()
        except ScraperError as exc:
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
            result = await self.scrape(client)
        else:
            async with ScraperHttpClient(self.config) as c:
                result = await self.scrape(c)

        if self.errors and not isinstance(result, ScrapeBatch):
            result = ScrapeBatch(result, list(self.errors), len(self.errors) + 1, int(bool(result)), self.telemetry)
        jobs = result.jobs if isinstance(result, ScrapeBatch) else result
        contracts = getattr(client if client is not None else c, "empty_contracts", [])
        if not jobs and contracts and not all(contracts):
            raise ScraperPermanentError(f"{self.source}: unrecognized empty response (schema drift/block/malformed records)")
        if self.telemetry is None:
            self.record_telemetry(
                items_seen=len(jobs), items_returned=len(jobs),
                pages_fetched=len(contracts) if contracts else None,
                cap_hit=bool(jobs), partial_reason="upstream_window_unknown" if jobs else None,
                stop_reason="upstream_window_unknown" if jobs else "recognized_empty",
                metadata={"listing_completeness": "unverified" if jobs else "recognized_empty"},
            )
        if isinstance(result, ScrapeBatch):
            if result.telemetry is not None:
                self.telemetry = result.telemetry
            else:
                result.telemetry = self.telemetry
        return result

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


def _recognized_json_empty(data):
    """Only explicit empty collections can establish legitimate API exhaustion."""
    if isinstance(data, list):
        return not data
    if isinstance(data, dict):
        nested = (data.get("data") or {}).get("searchJobs") if isinstance(data.get("data"), dict) else None
        if isinstance(nested, dict):
            return _recognized_json_empty(nested)
        total = data.get("total")
        if isinstance(total, dict) and isinstance(total.get("value"), (int, float)) and total["value"] > 0:
            return False
        if any(isinstance(data.get(k), (int, float)) and data[k] > 0 for k in ("total", "totalCount", "totalFound", "numberRecords")):
            return False
        for key in ("jobs", "data", "results", "hits", "jobAds", "postings", "content", "offers", "jvs", "nodes"):
            if isinstance(data.get(key), list):
                return not data[key]
    return False
