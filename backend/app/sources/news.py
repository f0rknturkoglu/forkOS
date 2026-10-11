from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

from app.sources.base import RawItem

USER_AGENT = "forkOS/0.1 local news reader"
TIMEOUT = httpx.Timeout(15.0, connect=8.0)
CACHE_TTL_S = 600
CACHE_MAX_SOURCES = 32


@dataclass
class _CacheEntry:
    at: float
    items: list[RawItem]


_cache: dict[str, _CacheEntry] = {}
_cooldowns: dict[str, float] = {}


def clear_news_cache() -> None:
    _cache.clear()
    _cooldowns.clear()


def cooldown_remaining(source_id: str) -> float:
    return max(0, _cooldowns.get(source_id, 0) - time.monotonic())


def record_cooldown(source_id: str, response: httpx.Response) -> None:
    from email.utils import parsedate_to_datetime

    value = response.headers.get("retry-after", "60")
    try:
        delay = float(value)
    except ValueError:
        try:
            delay = (parsedate_to_datetime(value) - datetime.now(UTC)).total_seconds()
        except (ValueError, TypeError, OverflowError):
            delay = 60
    if len(_cooldowns) >= CACHE_MAX_SOURCES and source_id not in _cooldowns:
        _cooldowns.pop(min(_cooldowns, key=_cooldowns.get))
    _cooldowns[source_id] = time.monotonic() + max(1, min(delay, 86400))


def cached_items(source_id: str, ttl: int = CACHE_TTL_S) -> list[RawItem] | None:
    now = time.monotonic()
    cached = _cache.get(source_id)
    if cached and now - cached.at < ttl:
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


class HuggingFacePapersSource:
    """Official Hub daily_papers contract; no token, images, generated abstracts or fixed date."""

    interval_minutes = 1440

    def __init__(self, *, date: str | None = None, transport=None):
        from datetime import date as calendar_date

        if date is not None and calendar_date.fromisoformat(date).isoformat() != date:
            raise ValueError("Tarih YYYY-MM-DD olmalı")
        self.date = date
        self.id = "news:huggingface-papers" + (":" + date if date else "")
        self.transport = transport

    async def fetch(self):
        params = {"limit": 30}
        if self.date:
            params["date"] = self.date
        async with (
            httpx.AsyncClient(timeout=TIMEOUT, transport=self.transport, trust_env=False) as client,
            client.stream(
                "GET",
                "https://huggingface.co/api/daily_papers",
                params=params,
                headers={"User-Agent": USER_AGENT},
            ) as response,
        ):
            response.raise_for_status()
            content = bytearray()
            async for chunk in response.aiter_bytes():
                content.extend(chunk)
                if len(content) > 2_000_000:
                    raise RuntimeError("Daily Papers yanıt sınırı aşıldı")
        import json

        payload = json.loads(content)
        if not isinstance(payload, list):
            raise RuntimeError("Daily Papers beklenmeyen yanıt")
        items = []
        import re

        for entry in payload[:30]:
            paper = entry.get("paper", {}) if isinstance(entry, dict) else {}
            identity = str(paper.get("id") or "")
            title = paper.get("title")
            if (
                not re.fullmatch(r"\d{4}\.\d{4,5}(v\d+)?", identity)
                or not isinstance(title, str)
                or not title.strip()
            ):
                raise RuntimeError("Daily Papers kimlik/başlık sözleşmesi değişti")
            featured = paper.get("submittedOnDailyAt")
            publication = paper.get("publishedAt")
            extra = {
                "id": identity,
                "title": title[:600],
                "authors": [
                    a["name"][:150]
                    for a in paper.get("authors", [])[:30]
                    if isinstance(a, dict) and isinstance(a.get("name"), str)
                ],
                "summary": str(paper.get("summary") or "")[:4000] or None,
                "featured_at": featured,
                "published_at": publication,
                "url": f"https://huggingface.co/papers/{identity}",
                "arxiv_url": f"https://arxiv.org/abs/{identity}",
                "upvotes": paper.get("upvotes") if isinstance(paper.get("upvotes"), int) else None,
                "num_comments": entry.get("numComments")
                if isinstance(entry.get("numComments"), int)
                else None,
            }
            items.append(
                RawItem(
                    external_id=identity,
                    title=extra["title"],
                    url=extra["url"],
                    summary=extra["summary"],
                    published_at=_parse_datetime(publication),
                    extra=extra,
                )
            )
        return items
