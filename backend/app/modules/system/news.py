"""Bugun panelindeki haber akislari.

Neden burada bir proxy var: reddit tarayiciya JSON/CORS vermiyor (403), ama
sunucu tarafindan cekilen .rss 200 donuyor. Hacker News (Algolia) CORS'a acik
oldugu icin dogrudan tarayicidan cekilir -- ona proxy yok.

Bu bir scraper degil, canli okuma gecisi: hicbir sey DB'ye yazilmaz, o yuzden
`source_run` kaydi da yok (kural 6 kalici kaynaklar icin).
"""
from __future__ import annotations

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
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
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

    _cache[key] = _CacheEntry(at=now, items=items)
    return items[:limit]


async def fetch_news_source(session: AsyncSession, source, limit: int) -> list[dict]:
    cached = cached_items(source.id)
    if cached is not None:
        return [item.extra for item in cached[:limit]]

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
        await runs.finish_run(session, run, status=runs.ERROR, error=str(exc))
        await session.commit()
        raise
    return [item.extra for item in items[:limit]]


async def hacker_news(session: AsyncSession, limit: int) -> list[dict]:
    return await fetch_news_source(session, HackerNewsSource(), limit)


async def github_trending(session: AsyncSession, limit: int) -> list[dict]:
    return await fetch_news_source(session, GitHubTrendingSource(), limit)
