"""Canonical consent, first-run evidence, CAS and durable product progress."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.entity import create_entity
from app.core.models import SourceRun
from app.db import SessionLocal
from app.main import app
from app.modules.rss import service as rss
from app.modules.rss.schemas import FeedIn
from app.modules.system import experience
from app.modules.system.models import Setting
from app.worker import jobs

HEADERS = {"Origin": "http://127.0.0.1:5173", "X-ForkOS-Goal-Studio": "1"}


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://127.0.0.1", headers=HEADERS
    ) as http:
        yield http


async def test_first_run_is_proven_only_from_empty_backend_and_never_autowrites(client):
    state = (await client.get("/api/system/experience")).json()
    assert state["first_run"] is True
    assert state["feed"]["providers"] == [] and state["feed"]["rss_enabled"] is False
    async with SessionLocal() as db:
        assert await db.get(Setting, experience.KEY) is None
        await create_entity(db, type="todo", title="Gerçek görev")
        await db.commit()
    assert (await client.get("/api/system/experience")).json()["first_run"] is False


async def test_legacy_explicit_rss_and_reddit_are_preserved_not_defaults(client):
    async with SessionLocal() as db:
        await rss.add_feed(db, FeedIn(url="https://example.com/rss", title="Kişisel"), probe=False)
        db.add(Setting(key="news.subreddits", value=["python"]))
        await db.commit()
    state = (await client.get("/api/system/experience")).json()
    assert not state["first_run"]
    assert state["feed"]["rss_enabled"] and state["feed"]["providers"] == ["reddit"]
    assert state["feed"]["subreddits"] == ["python"]


async def test_settings_only_existing_installation_is_not_new(client):
    async with SessionLocal() as db:
        db.add(Setting(key="modules.disabled", value=["rss"]))
        await db.commit()
    assert not (await client.get("/api/system/experience")).json()["first_run"]


async def test_corrupt_future_state_is_dismissed_and_external_providers_stay_off(client):
    async with SessionLocal() as db:
        db.add(Setting(key=experience.KEY, value={"version": 99}))
        await db.commit()
    state = (await client.get("/api/system/experience")).json()
    assert state["warnings"] and not state["first_run"]
    assert state["onboarding"]["status"] == "dismissed"
    assert state["feed"]["providers"] == []


async def test_revision_prevents_two_tabs_overwriting_and_generic_bypass(client):
    state = (await client.get("/api/system/experience")).json()
    feed = state["feed"] | {
        "providers": ["hf", "hn"],
        "bundles": [
            {"id": str(uuid.uuid4()), "title": "AI", "channels": ["hf", "hn"], "feed_ids": []}
        ],
    }
    first = await client.put(
        "/api/system/experience", json={"revision": state["revision"], "feed": feed}
    )
    assert first.status_code == 200
    collision = await client.put(
        "/api/system/experience", json={"revision": state["revision"], "feed": state["feed"]}
    )
    assert collision.status_code == 409
    assert (await client.get("/api/system/experience")).json()["feed"] == first.json()["feed"]
    assert (
        await client.put("/api/settings/" + experience.KEY, json={"value": {}})
    ).status_code == 422


async def test_completion_requires_view_and_canonical_record_and_feed_decision(client):
    state = (await client.get("/api/system/experience")).json()
    progress = state["onboarding"] | {
        "status": "completed",
        "journey": "planning",
        "visited_steps": ["planning"],
        "feed_setup": "skipped",
        "phase": "checklist",
    }
    response = await client.put(
        "/api/system/experience", json={"revision": state["revision"], "onboarding": progress}
    )
    assert response.status_code == 422
    async with SessionLocal() as db:
        from app.modules.todo.schemas import TodoIn
        from app.modules.todo.service import create

        await create(db, TodoIn(title="Gerçek görev"))
    assert (
        await client.put(
            "/api/system/experience", json={"revision": state["revision"], "onboarding": progress}
        )
    ).status_code == 200
    saved = (await client.get("/api/system/experience")).json()
    assert saved["onboarding"] == progress and not saved["first_run"]


async def test_disabled_sources_never_construct_adapters_or_poll_even_manual(client, monkeypatch):
    from app.modules.system import news

    def unexpected(*args, **kwargs):
        raise AssertionError("Unselected provider was contacted")

    monkeypatch.setattr(news, "HackerNewsSource", unexpected)
    monkeypatch.setattr(news, "GitHubTrendingSource", unexpected)
    monkeypatch.setattr(news, "reddit_posts", unexpected)
    # HF import is inside endpoint, patch canonical class too.
    monkeypatch.setattr("app.sources.news.HuggingFacePapersSource", unexpected)
    for path in ["hacker-news", "github-trending", "huggingface-papers", "reddit"]:
        response = await client.get("/api/news/" + path)
        assert response.status_code == 200 and response.json() == []
    async with SessionLocal() as db:
        feed, _ = await rss.add_feed(
            db, FeedIn(url="https://example.com/rss", title="RSS"), probe=False
        )
        current = await experience.read(db)
        await experience.update(
            db,
            experience.ExperienceUpdate(
                revision=current.revision, feed=experience.FeedPreferences()
            ),
        )
        monkeypatch.setattr(rss, "source_for", unexpected)
        assert await rss.due_feeds(db, interval_minutes=0) == []
        assert await rss.poll_feed(db, feed) == ("disabled", 0)
        assert list(await db.scalars(select(SourceRun))) == []
    assert await jobs.catch_up() == 0
    assert await rss.refresh_all(ignore_interval=True) == 0


async def test_bundle_rejects_unknown_feed_and_repeated_channels(client):
    current = (await client.get("/api/system/experience")).json()
    feed = current["feed"] | {
        "bundles": [
            {
                "id": str(uuid.uuid4()),
                "title": "Test",
                "feed_ids": [str(uuid.uuid4())],
                "channels": [],
            }
        ]
    }
    assert (
        await client.put(
            "/api/system/experience", json={"revision": current["revision"], "feed": feed}
        )
    ).status_code == 422

    feed["bundles"][0]["feed_ids"] = []
    feed["bundles"][0]["channels"] = ["hn", "hn"]
    assert (
        await client.put(
            "/api/system/experience", json={"revision": current["revision"], "feed": feed}
        )
    ).status_code == 422


async def test_pending_rss_add_is_network_free_and_reader_add_is_explicit_consent(
    client, monkeypatch
):
    current = (await client.get("/api/system/experience")).json()
    await client.put(
        "/api/system/experience", json={"revision": current["revision"], "feed": current["feed"]}
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("Pending gallery must not probe")

    monkeypatch.setattr(rss, "_probe_title", forbidden)
    result = await client.post(
        "/api/rss/feeds", json={"url": "https://example.com/feed", "probe": False}
    )
    assert result.status_code == 201
    after = (await client.get("/api/system/experience")).json()
    assert after["feed"]["rss_enabled"] is False
    assert (
        await client.post(
            "/api/rss/feeds", json={"url": "https://example.com/feed", "probe": False}
        )
    ).json()["id"] == result.json()["id"]

    async def probe(url):
        return "Public feed", None, None

    monkeypatch.setattr(rss, "_probe_title", probe)
    assert (
        await client.post("/api/rss/feeds", json={"url": "https://example.com/reader"})
    ).status_code == 201
    assert (await client.get("/api/system/experience")).json()["feed"]["rss_enabled"] is True


async def test_legacy_empty_reddit_preserves_other_choices_and_cannot_be_saved(client):
    async with SessionLocal() as db:
        value = experience.ExperienceData(
            feed=experience.FeedPreferences(providers=["hn", "reddit"])
        )
        db.add(Setting(key=experience.KEY, value=value.model_dump(mode="json")))
        await db.commit()
        assert await experience.enabled(db, "hn") is True
        assert await experience.enabled(db, "reddit") is False
    state = (await client.get("/api/system/experience")).json()
    assert not state["warnings"]
    assert state["feed"]["providers"] == ["hn", "reddit"]
    assert (
        await client.put(
            "/api/system/experience", json={"revision": state["revision"], "feed": state["feed"]}
        )
    ).status_code == 422
