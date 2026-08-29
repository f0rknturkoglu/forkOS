from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest

from app.modules.project import github_repo

pytestmark = pytest.mark.no_database


class _Clock:
    values = iter(
        (
            datetime(2026, 8, 29, 10, 0, tzinfo=UTC),
            datetime(2026, 8, 29, 10, 5, tzinfo=UTC),
        )
    )

    @classmethod
    def now(cls, _timezone):
        return next(cls.values)


class _GithubClient:
    calls: list[tuple[str, dict[str, str]]] = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, url: str, *, headers: dict[str, str], params=None):
        self.calls.append((url, headers))
        if url.endswith("/repos/owner/repo"):
            payload = {
                "full_name": "owner/repo",
                "html_url": "https://github.com/owner/repo",
                "description": "Private workspace",
                "stargazers_count": 0,
                "forks_count": 0,
                "subscribers_count": 1,
                "language": "Python",
                "open_issues_count": 0,
                "default_branch": "main",
                "pushed_at": "2026-08-29T09:59:00Z",
                "private": True,
            }
        elif url.endswith("/issues") or url.endswith("/pulls"):
            payload = []
        else:
            payload = [
                {
                    "sha": "abcdef123456",
                    "html_url": "https://github.com/owner/repo/commit/abcdef1",
                    "author": {"login": "owner"},
                    "commit": {
                        "message": "Improve sync",
                        "author": {"name": "Owner", "date": "2026-08-29T09:58:00Z"},
                    },
                }
            ]
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))


async def test_overview_keeps_fetch_time_for_cache_and_renews_on_forced_refresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    github_repo._cache.clear()
    _GithubClient.calls.clear()
    _Clock.values = iter(
        (
            datetime(2026, 8, 29, 10, 0, tzinfo=UTC),
            datetime(2026, 8, 29, 10, 5, tzinfo=UTC),
        )
    )
    monkeypatch.setattr(github_repo.httpx, "AsyncClient", _GithubClient)
    monkeypatch.setattr(github_repo, "datetime", _Clock, raising=False)

    first = await github_repo.overview("owner/repo", "secret")
    cached = await github_repo.overview("owner/repo", "secret")
    refreshed = await github_repo.overview("owner/repo", "secret", refresh=True)

    assert first["fetched_at"] == "2026-08-29T10:00:00+00:00"
    assert cached["fetched_at"] == first["fetched_at"]
    assert refreshed["fetched_at"] == "2026-08-29T10:05:00+00:00"
    assert len(_GithubClient.calls) == 8
    assert all(headers["Authorization"] == "Bearer secret" for _, headers in _GithubClient.calls)
    assert "secret" not in repr(first)

