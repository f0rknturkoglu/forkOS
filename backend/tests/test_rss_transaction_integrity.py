"""Real PostgreSQL rollback/CAS/concurrency gates, never the personal database."""

import asyncio
from uuid import uuid4

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.core.entity import create_entity
from app.core.models import Entity, Event
from app.db import SessionLocal
from app.main import app
from app.modules.bookmark.models import Bookmark
from app.modules.rss import service as rss
from app.modules.rss.models import Feed, FeedItem
from app.modules.rss.schemas import FeedIn
from app.modules.system import experience


async def add(db, name):
    return (
        await rss.add_feed(db, FeedIn(url=f"https://example.com/{name}", title=name), probe=False)
    )[0]


def opml(urls):
    return (
        "<opml><body>"
        + "".join(f'<outline xmlUrl="{url}" title="Import"/>' for url in urls)
        + "</body></opml>"
    ).encode()


async def counts(db):
    return [
        await db.scalar(select(func.count()).select_from(model)) for model in (Feed, Entity, Event)
    ]


@pytest.mark.parametrize("bundles", [1, 3])
async def test_delete_prunes_only_membership_preserves_empty_bundles_and_other_state(bundles):
    async with SessionLocal() as db:
        doomed, kept = await add(db, "deleted"), await add(db, "kept")
        initial = await experience.read(db)
        preferences = experience.FeedPreferences(
            providers=["hn"],
            rss_enabled=True,
            bundles=[
                experience.FeedBundle(
                    id=uuid4(),
                    title=f"Bundle {i}",
                    channels=["hn", "rss"],
                    feed_ids=[doomed.id] if i == 0 else [kept.id, doomed.id],
                )
                for i in range(bundles)
            ],
        )
        before = await experience.update(
            db, experience.ExperienceUpdate(revision=initial.revision, feed=preferences)
        )
        assert await rss.delete_feed(db, doomed.id)
        after = await experience.read(db)
        assert after.onboarding == before.onboarding
        assert after.feed.providers == before.feed.providers
        assert after.feed.rss_enabled
        assert len(after.feed.bundles) == bundles
        assert after.feed.bundles[0].feed_ids == []
        assert all(b.feed_ids == [kept.id] for b in after.feed.bundles[1:])
        assert after.revision != before.revision
        assert not after.invalid_feed_ids
        updated = await experience.update(
            db, experience.ExperienceUpdate(revision=after.revision, feed=after.feed)
        )
        assert updated.feed == after.feed
        assert not await rss.delete_feed(db, doomed.id)


async def test_delete_cannot_delete_an_arbitrary_domain_entity():
    async with SessionLocal() as db:
        entity = await create_entity(db, type="todo", title="Keep")
        await db.commit()
        assert not await rss.delete_feed(db, entity.id)
        assert await db.get(Entity, entity.id)


async def test_old_dangling_memberships_explicit_repair_is_cas_safe_and_idempotent():
    from app.modules.system.models import Setting

    async with SessionLocal() as db:
        kept = await add(db, "kept")
        missing = uuid4()
        state = experience.ExperienceData(
            feed=experience.FeedPreferences(
                providers=["hf"],
                bundles=[
                    experience.FeedBundle(
                        id=uuid4(), title="Keep bundle", feed_ids=[missing, kept.id]
                    )
                ],
            )
        )
        db.add(Setting(key=experience.KEY, value=state.model_dump(mode="json")))
        await db.commit()
        before = await experience.read(db)
        assert before.invalid_feed_ids == [missing] and before.warnings
        assert (await db.get(Setting, experience.KEY)).value["feed"]["bundles"][0]["feed_ids"][
            0
        ] == str(missing)
        repaired = await experience.repair_feed_memberships(db, expected_revision=before.revision)
        assert repaired.feed.bundles[0].feed_ids == [kept.id]
        assert repaired.feed.providers == ["hf"] and repaired.onboarding == before.onboarding
        assert not repaired.invalid_feed_ids
        event_count = (await counts(db))[-1]
        second = await experience.repair_feed_memberships(db, expected_revision=repaired.revision)
        assert second.revision == repaired.revision and (await counts(db))[-1] == event_count
        with pytest.raises(HTTPException) as conflict:
            await experience.repair_feed_memberships(db, expected_revision=before.revision)
        assert conflict.value.status_code == 409


async def test_delete_vs_other_tab_is_serialized_without_dangling_memberships():
    async with SessionLocal() as db:
        doomed = await add(db, "deleted")
        initial = await experience.read(db)
        saved = await experience.update(
            db,
            experience.ExperienceUpdate(
                revision=initial.revision,
                feed=experience.FeedPreferences(
                    bundles=[
                        experience.FeedBundle(id=uuid4(), title="Bundle", feed_ids=[doomed.id])
                    ]
                ),
            ),
        )

    async def delete():
        async with SessionLocal() as db:
            return await rss.delete_feed(db, doomed.id)

    async def update():
        async with SessionLocal() as db:
            try:
                await experience.update(
                    db,
                    experience.ExperienceUpdate(
                        revision=saved.revision,
                        feed=saved.feed.model_copy(update={"providers": ["hn"]}),
                    ),
                )
                return 200
            except HTTPException as exc:
                return exc.status_code

    deleted, status = await asyncio.wait_for(asyncio.gather(delete(), update()), 5)
    assert deleted and status in {200, 409}
    async with SessionLocal() as db:
        after = await experience.read(db)
        assert after.feed.bundles[0].feed_ids == [] and not after.invalid_feed_ids


async def test_delete_failure_rolls_back_feed_entity_event_and_preferences(monkeypatch):
    async with SessionLocal() as db:
        doomed = await add(db, "deleted")
        initial = await experience.read(db)
        before = await experience.update(
            db,
            experience.ExperienceUpdate(
                revision=initial.revision,
                feed=experience.FeedPreferences(
                    bundles=[
                        experience.FeedBundle(id=uuid4(), title="Bundle", feed_ids=[doomed.id])
                    ]
                ),
            ),
        )
        before_counts = await counts(db)
        original = db.delete

        async def fail(entity):
            await original(entity)
            raise RuntimeError("delete fixture fault")

        monkeypatch.setattr(db, "delete", fail)
        with pytest.raises(RuntimeError):
            await rss.delete_feed(db, doomed.id)
        assert await counts(db) == before_counts
        assert (await experience.read(db)).revision == before.revision


async def test_delete_preserves_saved_bookmark_and_historical_events():
    async with SessionLocal() as db:
        feed = await add(db, "saved")
        entity = await create_entity(db, type="feed_item", title="Article")
        db.add(
            FeedItem(id=entity.id, feed_id=feed.id, guid="one", url="https://example.com/article")
        )
        await db.commit()
        bookmark = await rss.save_item(db, entity.id, "read_later")
        bookmark_id = bookmark.id
        before_events = await db.scalar(select(func.count()).select_from(Event))
        assert await rss.delete_feed(db, feed.id)
        assert await db.get(Bookmark, bookmark_id)
        assert await db.get(Entity, entity.id) is None
        assert await db.scalar(select(func.count()).select_from(Event)) >= before_events


async def test_import_200_replay_preserves_existing_metadata_and_is_probe_free(monkeypatch):
    async def forbidden(*args):
        raise AssertionError("OPML must not probe")

    monkeypatch.setattr(rss, "_probe_title", forbidden)
    async with SessionLocal() as db:
        existing = await add(db, "0")
        content = opml([f"https://example.com/{i}" for i in range(200)])
        added, skipped, _ = await rss.import_opml(db, content)
        assert (added, skipped) == (199, 1)
        assert (await experience.read(db)).feed.rss_enabled
        assert (await db.get(Entity, existing.id)).title == "0"
        before = await counts(db)
        assert (await rss.import_opml(db, content))[:2] == (0, 200)
        assert await counts(db) == before


@pytest.mark.parametrize(
    "content",
    [
        opml(["https://example.com/good", "http://127.0.0.1/private"]),
        b"<opml",
        opml([f"https://example.com/{i}" for i in range(201)]),
    ],
)
async def test_invalid_import_has_no_partial_changes(content):
    async with SessionLocal() as db:
        before = await counts(db)
        with pytest.raises((ValueError, SyntaxError)):
            await rss.import_opml(db, content)
        assert await counts(db) == before
        assert not (await experience.read(db)).feed.rss_enabled


async def test_mid_import_db_failure_rolls_back_every_record_and_opt_in(monkeypatch):
    original = rss.add_feed
    calls = 0

    async def fail(*args, **kwargs):
        nonlocal calls
        calls += 1
        result = await original(*args, **kwargs)
        if calls == 2:
            raise RuntimeError("DB fixture fault")
        return result

    monkeypatch.setattr(rss, "add_feed", fail)
    async with SessionLocal() as db:
        before = await counts(db)
        with pytest.raises(RuntimeError):
            await rss.import_opml(db, opml(["https://example.com/a", "https://example.com/b"]))
        assert await counts(db) == before
        assert not (await experience.read(db)).feed.rss_enabled


async def test_parallel_import_does_not_duplicate_or_deadlock():
    async def import_one(urls):
        async with SessionLocal() as db:
            return await rss.import_opml(db, opml(urls))

    results = await asyncio.wait_for(
        asyncio.gather(
            import_one(["https://example.com/a", "https://example.com/b"]),
            import_one(["https://example.com/b", "https://example.com/a"]),
        ),
        5,
    )
    assert sum(result[0] for result in results) == 2
    async with SessionLocal() as db:
        assert (await counts(db))[0] == 2


async def test_import_queues_refresh_only_after_successful_commit(monkeypatch):
    refreshes = []

    async def refresh():
        async with SessionLocal() as db:
            refreshes.append((await counts(db))[0])

    monkeypatch.setattr(rss, "refresh_all", refresh)
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://127.0.0.1",
        headers={"Origin": "http://127.0.0.1:5173", "X-ForkOS-Goal-Studio": "1"},
    ) as http:
        content = opml(["https://example.com/import"])
        assert (
            await http.post("/api/rss/import", files={"file": ("feed.opml", content)})
        ).status_code == 200
        assert refreshes == [1]
        assert (
            await http.post("/api/rss/import", files={"file": ("feed.opml", content)})
        ).status_code == 200
        assert refreshes == [1]
        assert (
            await http.post(
                "/api/rss/import", files={"file": ("bad.opml", opml(["http://127.0.0.1/private"]))}
            )
        ).status_code == 422
        assert refreshes == [1]
