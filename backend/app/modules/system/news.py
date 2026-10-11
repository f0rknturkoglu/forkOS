"""Bugun panelindeki haber akislari.

Reddit RSS, Hacker News ve GitHub tarayıcıdan değil backend'den çekilir.
TTL cache ve kaynak kilidi dış isteği sınırlar. Tüm seçilmiş haber sağlayıcıları
SourceAdapter üzerinden source_run üretir; Reddit RSS proxy sözleşmesini korur.
"""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime

import feedparser
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import runs
from app.sources.news import (
    GitHubTrendingSource,
    HackerNewsSource,
    cached_items,
    cooldown_remaining,
    record_cooldown,
    store_cached_items,
)

USER_AGENT = "forkOS/0.1 (+local-only personal reader)"
TIMEOUT = httpx.Timeout(15.0, connect=8.0)

# Tech / computer science kulvarindaki varsayilan subredditler.
# Ayarlardaki "news.subreddits" anahtari bunu ezer.
DEFAULT_SUBREDDITS = [
    "programming",
    "compsci",
    "technology",
    "MachineLearning",
    "webdev",
    "ExperiencedDevs",
]

CACHE_TTL_S = 600  # reddit'i her sayfa yenilemesinde dovmemek icin

# Icerik HTML'indeki "[link]" cipasi disari giden gercek URL'i tasir.
_OUT_LINK = re.compile(r'href="([^"]+)"[^>]*>\s*\[link\]', re.IGNORECASE)


@dataclass
class _CacheEntry:
    at: float
    items: list[dict]


_cache: dict[str, _CacheEntry] = {}


def _subreddit_of(entry) -> str | None:
    for tag in entry.get("tags") or []:
        term = tag.get("term")
        if term:
            return term
    return None


def _external_url(entry) -> str | None:
    """Gonderi bir baglantiysa hedef URL; self-post ise None."""
    html = ""
    if entry.get("content"):
        html = entry["content"][0].get("value", "")
    match = _OUT_LINK.search(html)
    if not match:
        return None
    url = match.group(1)
    return None if "reddit.com/r/" in url else url


def _published(entry) -> str | None:
    for key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(key)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=UTC).isoformat()
            except (TypeError, ValueError):
                continue
    return None


async def reddit_posts(subreddits: list[str], limit: int) -> list[dict]:
    """Coklu subreddit'in "hot" akisi. TTL cache'li, hata yutulmaz."""
    subs = [s.strip().lstrip("r/") for s in subreddits if s.strip()]
    if not subs:
        return []

    key = "+".join(subs)
    cached = _cache.get(key)
    now = time.monotonic()
    if cached and now - cached.at < CACHE_TTL_S:
        return cached.items[:limit]

    url = f"https://www.reddit.com/r/{key}/hot/.rss?limit=40"
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, trust_env=False) as client:
        response = await client.get(url, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()

    parsed = feedparser.parse(response.text)
    items: list[dict] = []
    for entry in parsed.entries:
        title = (entry.get("title") or "").strip()
        comments_url = entry.get("link")
        if not title or not comments_url:
            continue
        items.append(
            {
                "id": entry.get("id") or comments_url,
                "title": title,
                "url": _external_url(entry) or comments_url,
                "comments_url": comments_url,
                "subreddit": _subreddit_of(entry),
                "author": (entry.get("author") or "").lstrip("/"),
                "published_at": _published(entry),
            }
        )

    if len(_cache) >= 32 and key not in _cache:
        _cache.pop(min(_cache, key=lambda identity: _cache[identity].at))
    _cache[key] = _CacheEntry(at=now, items=items)
    return items[:limit]


_source_locks: dict[str, asyncio.Lock] = {}


async def fetch_news_source(session: AsyncSession, source, limit: int) -> list[dict]:
    if source.id not in _source_locks:
        if len(_source_locks) >= 32:
            unused = next((key for key, lock in _source_locks.items() if not lock.locked()), None)
            if unused is not None:
                _source_locks.pop(unused)
        _source_locks[source.id] = asyncio.Lock()
    async with _source_locks[source.id]:
        return await _fetch_news_source(session, source, limit)


async def _fetch_news_source(session: AsyncSession, source, limit: int) -> list[dict]:
    cached = cached_items(source.id, ttl=source.interval_minutes * 60)
    if cached is not None:
        return [item.extra for item in cached[:limit]]
    remaining = cooldown_remaining(source.id)
    if remaining:
        raise RuntimeError(
            f"Kaynak hız sınırı: yaklaşık {int(remaining) + 1} saniye sonra yeniden dene"
        )

    run = await runs.start_run(session, source.id)
    try:
        items = await source.fetch()
        store_cached_items(source.id, items)
        status = runs.OK if items else runs.EMPTY
        await runs.finish_run(session, run, status=status, items_found=len(items))
        await session.commit()
        if status == runs.EMPTY:
            await runs.check_stalled(session, source.id)
            await session.commit()
    except Exception as exc:
        if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in (429, 503):
            record_cooldown(source.id, exc.response)
        await runs.finish_run(session, run, status=runs.ERROR, error=str(exc))
        await session.commit()
        raise
    return [item.extra for item in items[:limit]]


async def hacker_news(session: AsyncSession, limit: int) -> list[dict]:
    return await fetch_news_source(session, HackerNewsSource(), limit)


async def github_trending(session: AsyncSession, limit: int) -> list[dict]:
    return await fetch_news_source(session, GitHubTrendingSource(), limit)


class RedditNewsSource:
    """Optional existing Reddit RSS proxy, participating in canonical SourceRun health."""

    interval_minutes = 10

    def __init__(self, subreddits):
        import hashlib

        self.subreddits = subreddits
        self.id = "news:reddit:" + hashlib.sha256(",".join(subreddits).encode()).hexdigest()[:12]

    async def fetch(self):
        from app.sources.base import RawItem

        return [
            RawItem(external_id=item["id"], title=item["title"], url=item["url"], extra=item)
            for item in await reddit_posts(self.subreddits, 40)
        ]
