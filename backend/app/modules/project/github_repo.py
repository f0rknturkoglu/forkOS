"""Proje detayindaki GitHub paneli.

Commit akisi `github.py`'de (GraphQL, katki takvimi). Burasi TEK BIR DEPO
hakkinda: ozet, acik issue'lar, acik PR'lar, son commit'ler. REST v3 yeter --
GraphQL sorgusu yazmak icin sebep yok.

Token varsa kullanilir (ozel depolar + 5000/saat limit); yoksa public depo
yine okunur, sadece limit 60/saat olur. Bu yuzden yanit TTL cache'li.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

API = "https://api.github.com"
TIMEOUT = httpx.Timeout(20.0, connect=8.0)
CACHE_TTL_S = 300


@dataclass
class _Entry:
    at: float
    data: dict


_cache: dict[str, _Entry] = {}


def _headers(token: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "forkOS/0.1 (+local-only personal os)",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _issue(raw: dict) -> dict:
    return {
        "number": raw["number"],
        "title": raw["title"],
        "url": raw["html_url"],
        "state": raw["state"],
        "labels": [label["name"] for label in raw.get("labels", [])],
        "assignee": (raw.get("assignee") or {}).get("login"),
        "comments": raw.get("comments", 0),
        "created_at": raw.get("created_at"),
        "updated_at": raw.get("updated_at"),
        "author": (raw.get("user") or {}).get("login"),
        "draft": bool(raw.get("draft")),
    }


async def overview(repo: str, token: str | None, *, refresh: bool = False) -> dict:
    """`owner/name` deposunun paneli. Hata yutulmaz -- cagiran 502'ye cevirir."""
    key = repo.casefold()
    cached = _cache.get(key)
    now = time.monotonic()
    if cached and not refresh and now - cached.at < CACHE_TTL_S:
        return cached.data

    headers = _headers(token)
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        meta = await client.get(f"{API}/repos/{repo}", headers=headers)
        meta.raise_for_status()
        info = meta.json()

        # issues ucu PR'lari da dondurur; ayirmak icin `pull_request` alanina bakilir.
        issues_response = await client.get(
            f"{API}/repos/{repo}/issues",
            params={"state": "open", "per_page": 30, "sort": "updated"},
            headers=headers,
        )
        issues_response.raise_for_status()
        raw_issues = issues_response.json()

        pulls_response = await client.get(
            f"{API}/repos/{repo}/pulls",
            params={"state": "open", "per_page": 20, "sort": "updated"},
            headers=headers,
        )
        pulls_response.raise_for_status()

        commits_response = await client.get(
            f"{API}/repos/{repo}/commits",
            params={"per_page": 10},
            headers=headers,
        )
        commits = commits_response.json() if commits_response.status_code == 200 else []

    data = {
        "repo": info["full_name"],
        "url": info["html_url"],
        "description": info.get("description"),
        "stars": info.get("stargazers_count", 0),
        "forks": info.get("forks_count", 0),
        "watchers": info.get("subscribers_count", 0),
        "language": info.get("language"),
        "open_issues": info.get("open_issues_count", 0),
        "default_branch": info.get("default_branch"),
        "pushed_at": info.get("pushed_at"),
        "private": bool(info.get("private")),
        "issues": [_issue(item) for item in raw_issues if "pull_request" not in item],
        "pulls": [_issue(item) for item in pulls_response.json()],
        "commits": [
            {
                "sha": item["sha"][:7],
                "message": (item.get("commit", {}).get("message") or "").split("\n")[0],
                "url": item["html_url"],
                "author": ((item.get("author") or {}).get("login")
                           or (item.get("commit", {}).get("author") or {}).get("name")),
                "committed_at": (item.get("commit", {}).get("author") or {}).get("date"),
            }
            for item in commits
        ],
        "authenticated": bool(token),
    }
    _cache[key] = _Entry(at=now, data=data)
    return data


async def issue(repo: str, number: int, token: str | None) -> dict:
    """Tek issue -- gorevle eslerken basligi ve govdesi lazim."""
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        response = await client.get(f"{API}/repos/{repo}/issues/{number}", headers=_headers(token))
        response.raise_for_status()
        raw = response.json()
    detail = _issue(raw)
    detail["body"] = raw.get("body")
    return detail
