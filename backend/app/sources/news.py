from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

from app.sources.base import RawItem

USER_AGENT = "forkOS/0.1 local news reader"
TIMEOUT = httpx.Timeout(15.0, connect=8.0)
CACHE_TTL_S = 600
CACHE_MAX_SOURCES = 4


@dataclass
class _CacheEntry:
    at: float
    items: list[RawItem]


_cache: dict[str, _CacheEntry] = {}


def clear_news_cache() -> None:
    _cache.clear()


def cached_items(source_id: str) -> list[RawItem] | None:
    now = time.monotonic()
    cached = _cache.get(source_id)
    if cached and now - cached.at < CACHE_TTL_S:
        return cached.items
    return None


def store_cached_items(source_id: str, items: list[RawItem]) -> None:
    if len(_cache) >= CACHE_MAX_SOURCES and source_id not in _cache:
        oldest = min(_cache, key=lambda key: _cache[key].at)
        _cache.pop(oldest)
    _cache[source_id] = _CacheEntry(at=time.monotonic(), items=items)


class HackerNewsSource:
    id = "news:hacker-news"
    interval_minutes = 15

    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None):
        self.transport = transport

    async def fetch(self) -> list[RawItem]:
        async with httpx.AsyncClient(
            timeout=TIMEOUT,
            transport=self.transport,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            response = await client.get(
                "https://hn.algolia.com/api/v1/search",
                params={"tags": "front_page", "hitsPerPage": 30},
            )
            response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("Hacker News beklenmeyen cevap döndürdü")
        items: list[RawItem] = []
        for hit in payload.get("hits") or []:
            story_id = str(hit.get("objectID") or "").strip()
            title = str(hit.get("title") or "").strip()
            if not story_id or not title:
                continue
            comments_url = f"https://news.ycombinator.com/item?id={story_id}"
            url = hit.get("url") or comments_url
            created_at = hit.get("created_at")
            items.append(
                RawItem(
                    external_id=story_id,
                    title=title,
                    url=url,
                    published_at=_parse_datetime(created_at),
                    extra={
                        "objectID": story_id,
                        "title": title,
                        "url": hit.get("url"),
                        "points": hit.get("points"),
                        "num_comments": hit.get("num_comments"),
                        "created_at": created_at,
                    },
                )
            )
        return items


class GitHubTrendingSource:
    id = "news:github-trending"
    interval_minutes = 360

    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None):
        self.transport = transport

    async def fetch(self) -> list[RawItem]:
        week_ago = (datetime.now(UTC) - timedelta(days=7)).date().isoformat()
        async with httpx.AsyncClient(
            timeout=TIMEOUT,
            transport=self.transport,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": USER_AGENT,
            },
        ) as client:
            response = await client.get(
                "https://api.github.com/search/repositories",
                params={
                    "q": f"created:>{week_ago}",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 20,
                },
            )
            response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("GitHub beklenmeyen cevap döndürdü")
        items: list[RawItem] = []
        for repo in payload.get("items") or []:
            full_name = str(repo.get("full_name") or "").strip()
            url = repo.get("html_url")
            if not full_name or not url:
                continue
            created_at = repo.get("created_at")
            items.append(
                RawItem(
                    external_id=str(repo.get("id") or full_name),
                    title=full_name,
                    url=url,
                    summary=repo.get("description"),
                    published_at=_parse_datetime(created_at),
                    extra={
                        "full_name": full_name,
                        "html_url": url,
                        "description": repo.get("description"),
                        "stargazers_count": repo.get("stargazers_count") or 0,
                        "language": repo.get("language"),
                        "created_at": created_at,
                    },
                )
            )
        return items


def _parse_datetime(value) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
