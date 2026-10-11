"""V1 boundaries and retained product contracts, using only the isolated test DB."""
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.models import Event
from app.db import Base, SessionLocal
from app.integrations.google_auth import SCOPES
from app.main import app
from app.modules import MODULES
from app.modules.system import automation, maintenance


@pytest.mark.no_database
def test_retired_runtime_and_preserved_archive():
    for module in MODULES:
        if module.id in {"media", "finance", "note"}:
            assert not module.router.routes
            assert module.deadline_provider is None
            assert all(not spec.searchable and not spec.linkable for spec in module.entity_types)
    paths = set(app.openapi()["paths"])
    assert not any(p.startswith(("/api/media", "/api/finance")) for p in paths)
    assert "/api/documents/sync" not in paths
    assert "/api/documents/usages" not in paths
    assert {"/api/documents", "/api/documents/upload", "/api/documents/{id}/file"} <= paths
    assert {"/api/rss/feeds", "/api/bookmarks", "/api/calendar/events", "/api/pomodoro/active"} <= paths
    assert {"media_item", "expense", "income", "document", "note", "pomodoro_session"} <= set(Base.metadata.tables)
    assert {"/api/flashcard/decks", "/api/obsidian/capture", "/api/auth/google/status", "/api/system/stats"} <= paths
    assert not any("drive" in path for path in paths)
    assert "drive" not in SCOPES
    assert "calendar.events" in SCOPES
    assert "media" not in automation.DOMAINS
    assert "artwork" not in dict(maintenance.STEPS)


async def test_manual_history_crud_persistence_and_timer_safety():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        task = (await client.post("/api/todos", json={"title": "V1 history task"})).json()
        payload = {"started_at": (datetime.now(UTC) - timedelta(hours=4)).isoformat(),
                   "minutes": 25, "topic": "Manual", "context_entity_id": task["id"]}
        created = await client.post("/api/pomodoro", json=payload)
        assert created.status_code == 201, created.text
        record = created.json()
        assert record["source"] == "manual"
        record_id = record["id"]
        changed = await client.put(f"/api/pomodoro/{record_id}", json={**payload, "minutes": 40, "topic": "Edited"})
        assert changed.status_code == 200, changed.text
        assert changed.json()["actual_min"] == 40
        assert changed.json()["context_title"] == "V1 history task"
        assert (await client.get("/api/pomodoro/sessions")).json()[0]["topic"] == "Edited"
        assert (await client.get("/api/pomodoro/analytics?range=all")).json()["minutes"] == 40
        async with SessionLocal() as session:
            verbs = list((await session.execute(select(Event.verb).where(Event.entity_id == record_id))).scalars())
            assert "pomodoro.completed" in verbs and "pomodoro.updated" in verbs
        assert (await client.delete(f"/api/pomodoro/{record_id}")).status_code == 204
        assert (await client.get("/api/pomodoro/sessions")).json() == []
        assert (await client.get("/api/pomodoro/analytics?range=all")).json()["minutes"] == 0
        # A new HTTP client still sees persisted state (no browser/session-local data model).
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        timer = (await client.post("/api/pomodoro/start", json={"planned_min": 1})).json()
        assert timer["source"] == "timer"
        assert (await client.put(f"/api/pomodoro/{timer['id']}", json=payload)).status_code == 400
        assert (await client.delete(f"/api/pomodoro/{timer['id']}")).status_code == 400
        await client.post(f"/api/pomodoro/{timer['id']}/pause")
        await client.post(f"/api/pomodoro/{timer['id']}/resume")
        await client.post(f"/api/pomodoro/{timer['id']}/stop", json={"interrupted": False})
        assert len((await client.get("/api/pomodoro/sessions")).json()) == 1
        assert (await client.put(f"/api/pomodoro/{timer['id']}", json=payload)).status_code == 200
        assert (await client.get("/api/pomodoro/sessions")).json()[0]["source"] == "timer"
        # Never permit deleting arbitrary entities through the session endpoint.
        assert (await client.delete(f"/api/pomodoro/{task['id']}")).status_code == 404


@pytest.mark.parametrize("change", [
    {"minutes": 0}, {"minutes": 601}, {"kind": "invalid"},
    {"started_at": "2026-01-01T00:00:00"},
    {"started_at": (datetime.now(UTC) + timedelta(days=1)).isoformat()},
    {"started_at": datetime.now(UTC).isoformat()},
])
async def test_manual_invalid_times_and_durations(change):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/pomodoro", json={
            "started_at": (datetime.now(UTC) - timedelta(hours=2)).isoformat(), "minutes": 25, **change})
        assert response.status_code in (400, 422)


async def test_source_migration_preserves_populated_history():
    import os
    import subprocess
    import sys
    from pathlib import Path

    from sqlalchemy import text

    from app.config import settings
    from app.core.entity import create_entity
    from app.core.events import log_event
    from app.db import engine

    def migrate(target):
        subprocess.run([sys.executable, "-m", "alembic", target[0], target[1]],
                       cwd=Path(__file__).resolve().parents[1],
                       env={**os.environ, "DATABASE_URL": settings.database_url}, check=True,
                       capture_output=True)

    await engine.dispose()
    migrate(("downgrade", "0077_goals_strategy"))
    try:
        ids = []
        async with SessionLocal() as session:
            for source in ("manual", "timer"):
                entity = await create_entity(session, type="pomodoro_session", title=source)
                ids.append(entity.id)
                await session.execute(text("""insert into pomodoro_session
                    (id, started_at, ended_at, planned_min, actual_min, kind, interrupted)
                    values (:id, now() - interval '2 hours', now() - interval '1 hour', 60, 60, 'focus', false)"""), {"id": entity.id})
                await log_event(session, verb="pomodoro.completed", entity_id=entity.id,
                                entity_type="pomodoro_session", payload={"manual": source == "manual"})
            archive = await create_entity(session, type="media_item", title="Historical archive")
            await session.execute(text("insert into media_item (id, kind, status) values (:id, 'book', 'planned')"), {"id": archive.id})
            await session.commit()
        await engine.dispose()
        migrate(("upgrade", "head"))
        async with SessionLocal() as session:
            records = dict((await session.execute(text("select id, source from pomodoro_session where id = any(:ids)"), {"ids": ids})).all())
            assert records == {ids[0]: "manual", ids[1]: "timer"}
            assert (await session.execute(text("select count(*) from media_item where id = :id"), {"id": archive.id})).scalar_one() == 1
            assert (await session.execute(text("select sum(actual_min) from pomodoro_session where id = any(:ids)"), {"ids": ids})).scalar_one() == 120
            assert (await session.execute(text("select count(*) from event where entity_id = any(:ids)"), {"ids": ids})).scalar_one() == 2
    finally:
        await engine.dispose()
        migrate(("upgrade", "head"))


@pytest.mark.no_database
async def test_worker_registers_only_retained_jobs(monkeypatch):
    from app.worker import main as worker

    job_ids = []

    class RegistrationComplete(Exception):
        pass

    class Scheduler:
        def add_job(self, func, *args, **kwargs):
            assert callable(func)
            job_ids.append(kwargs["id"])

        def start(self):
            raise RegistrationComplete

    monkeypatch.setattr(worker, "AsyncIOScheduler", Scheduler)
    with pytest.raises(RegistrationComplete):
        await worker.main()
    assert "poll_media" not in job_ids
    assert {"poll_feeds", "sync_calendar", "sync_github", "source_sync_queue", "nightly_backup"} <= set(job_ids)


async def test_calendar_task_creation_keeps_todo_and_plan_persistent():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/api/todos", json={"title": "Calendar task", "plan_day": "2026-10-10"})
        assert created.status_code == 201, created.text
        todo_id = created.json()["id"]
        events = (await client.get("/api/calendar/events", params={
            "from": "2026-10-10T00:00:00+03:00", "to": "2026-10-11T00:00:00+03:00",
        })).json()
        event = next(item for item in events if item.get("entity_id") == todo_id)
        assert event["entity_type"] == "todo" and event["all_day"] is True
        assert event["starts_at"].startswith("2026-10-10T00:00:00+03:00")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert any(item["id"] == todo_id and item["title"] == "Calendar task" for item in (await client.get("/api/todos")).json())
