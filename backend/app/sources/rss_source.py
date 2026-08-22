"""RSS/Atom kaynagi. SourceAdapter protokolune uyar (kural 5).

Conditional GET: ETag / If-Modified-Since gonderilir, 304'te hic parse edilmez.
Bu, 50+ feed'i 30dk'da bir cekerken bant genisligini ve CPU'yu ucuza getirir.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import feedparser
import httpx

from app.sources.base import RawItem

USER_AGENT = "forkOS/0.1 (+local-only personal reader)"
TIMEOUT = httpx.Timeout(20.0, connect=10.0)

OK = "ok"
NOT_MODIFIED = "not_modified"
EMPTY = "empty"
ERROR = "error"


@dataclass
class FetchResult:
    status: str
    items: list[RawItem] = field(default_factory=list)
    etag: str | None = None
    last_modified: str | None = None
    error: str | None = None
    feed_image: str | None = None          # channel logosu (favicon yedegi)


def item_guid(entry_id: str | None, url: str | None, title: str) -> str:
    """GUID yoksa uret. Dedup'in tek dayanagi bu -- bos birakma."""
    if entry_id and entry_id.strip():
        return entry_id.strip()
    return hashlib.sha256(f"{url or ''}|{title}".encode()).hexdigest()


def _published(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed = entry.get(key)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=UTC)
            except (TypeError, ValueError):
                continue
    return None


def _summary(entry) -> str | None:
    text = entry.get("summary") or ""
    if not text and entry.get("content"):
        text = entry["content"][0].get("value", "")
    text = text.strip()
    return text[:4000] or None


def _content(entry) -> str | None:
    """Okuma bolmesi icin tam metin. content:encoded yoksa ozet yeterli."""
    text = ""
    if entry.get("content"):
        text = entry["content"][0].get("value", "")
    if not text:
        text = entry.get("summary") or ""
    text = text.strip()
    return text[:200_000] or None


def parse_entries(raw: bytes) -> list[RawItem]:
    """Bytes -> RawItem. Ag'dan bagimsiz oldugu icin dogrudan test edilebilir."""
    parsed = feedparser.parse(raw)
    items: list[RawItem] = []
    for entry in parsed.entries:
        title = (entry.get("title") or "").strip() or "(basliksiz)"
        url = entry.get("link")
        items.append(RawItem(
            external_id=item_guid(entry.get("id"), url, title),
            title=title,
            url=url,
            summary=_summary(entry),
            published_at=_published(entry),
            extra={
                "author": (entry.get("author") or "").strip() or None,
                "content": _content(entry),
            },
        ))
    return items


def feed_title(raw: bytes, fallback: str) -> tuple[str, str | None, str | None]:
    """(baslik, site_url, logo) -- feed ekleme sirasinda entity.title ve avatar icin."""
    parsed = feedparser.parse(raw)
    title = (parsed.feed.get("title") or "").strip() or fallback
    image = None
    if parsed.feed.get("image"):
        image = parsed.feed["image"].get("href")
    if not image:
        image = parsed.feed.get("logo")
    return title, parsed.feed.get("link"), image


def feed_image(raw: bytes) -> str | None:
    """Channel logosu. Avatari olmayan feed'lerde None -- onyuz harf avatarina duser."""
    parsed = feedparser.parse(raw)
    if parsed.feed.get("image"):
        href = parsed.feed["image"].get("href")
        if href:
            return href
    return parsed.feed.get("logo") or None


def http_date(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).strftime("%a, %d %b %Y %H:%M:%S GMT")


def parse_http_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None


class RssSource:
    """Tek feed icin adapter. Worker bunu bilir, feedparser'i bilmez."""

    def __init__(
        self, feed_id: str, url: str, *,
        etag: str | None = None, last_modified: str | None = None,
        interval_minutes: int = 30,
    ) -> None:
        self.id = f"rss:{feed_id}"
        self.url = url
        self.etag = etag
        self.last_modified = last_modified
        self.interval_minutes = interval_minutes

    def _headers(self) -> dict[str, str]:
        headers = {"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, */*"}
        if self.etag:
            headers["If-None-Match"] = self.etag
        if self.last_modified:
            headers["If-Modified-Since"] = self.last_modified
        return headers

    async def fetch_result(self, client: httpx.AsyncClient | None = None) -> FetchResult:
        owns_client = client is None
        client = client or httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True)
        try:
            response = await client.get(self.url, headers=self._headers())
            if response.status_code == 304:
                return FetchResult(status=NOT_MODIFIED, etag=self.etag,
                                   last_modified=self.last_modified)
            response.raise_for_status()
            items = parse_entries(response.content)
            return FetchResult(
                status=OK if items else EMPTY,
                items=items,
                etag=response.headers.get("ETag"),
                last_modified=response.headers.get("Last-Modified"),
                feed_image=feed_image(response.content),
            )
        except httpx.HTTPError as exc:
            return FetchResult(status=ERROR, error=f"{type(exc).__name__}: {exc}")
        except Exception as exc:                      # bozuk XML, beklenmedik icerik
            return FetchResult(status=ERROR, error=f"{type(exc).__name__}: {exc}")
        finally:
            if owns_client:
                await client.aclose()

    async def fetch(self) -> list[RawItem]:
        """SourceAdapter protokolu. Hata firlatir -- worker source_run'a yazar."""
        result = await self.fetch_result()
        if result.status == ERROR:
            raise RuntimeError(result.error or "fetch failed")
        return result.items
