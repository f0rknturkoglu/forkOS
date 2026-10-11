from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.models import SourceRun
from app.db import SessionLocal
from app.main import app
from app.modules.system import news as news_service
from app.sources.news import GitHubTrendingSource, HackerNewsSource, clear_news_cache

FIXTURES = Path(__file__).parent / "sources" / "fixtures"


def fixture_transport(name: str) -> httpx.MockTransport:
    payload = json.loads((FIXTURES / name).read_text())
    return httpx.MockTransport(lambda _request: httpx.Response(200, json=payload))


async def test_news_adapters_normalize_fixtures_and_record_source_runs():
    clear_news_cache()
    hn = HackerNewsSource(transport=fixture_transport("hacker_news.json"))
    github = GitHubTrendingSource(transport=fixture_transport("github_trending.json"))

    async with SessionLocal() as session:
        hn_items = await news_service.fetch_news_source(session, hn, limit=10)
        gh_items = await news_service.fetch_news_source(session, github, limit=10)
        runs = list((await session.execute(select(SourceRun).order_by(SourceRun.id))).scalars())

    assert hn_items[0]["objectID"] == "123"
    assert hn_items[0]["points"] == 321
    assert gh_items[0]["full_name"] == "acme/local-first"
    assert gh_items[0]["stargazers_count"] == 812
    assert [(run.source, run.status, run.items_found) for run in runs] == [
        ("news:hacker-news", "ok", 1),
        ("news:github-trending", "ok", 1),
    ]


async def test_news_endpoint_uses_backend_owned_adapter(
    monkeypatch: pytest.MonkeyPatch,
):
    clear_news_cache()
    from app.modules.system.experience import KEY, ExperienceData, FeedPreferences
    from app.modules.system.models import Setting
    async with SessionLocal() as db:
        db.add(Setting(key=KEY,value=ExperienceData(feed=FeedPreferences(providers=["hn"])).model_dump(mode="json")))
        await db.commit()
    monkeypatch.setattr(
        news_service,
        "HackerNewsSource",
        lambda: HackerNewsSource(transport=fixture_transport("hacker_news.json")),
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/news/hacker-news?limit=5")

    assert response.status_code == 200
    assert response.json()[0]["title"] == "SQLite on the edge"

async def test_saved_empty_reddit_preference_never_fetches_defaults(monkeypatch):
    from httpx import ASGITransport, AsyncClient

    from app.db import SessionLocal
    from app.main import app
    from app.modules.system import news
    from app.modules.system.models import Setting

    async with SessionLocal() as db:
        db.add(Setting(key="news.subreddits", value=[]))
        await db.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        def unexpected_outbound(*args, **kwargs):
            raise AssertionError("Disabled Reddit must not construct an outbound client")

        monkeypatch.setattr(news.httpx, "AsyncClient", unexpected_outbound)
        response = await client.get("/api/news/reddit")
        assert response.status_code == 200
        assert response.json() == []
