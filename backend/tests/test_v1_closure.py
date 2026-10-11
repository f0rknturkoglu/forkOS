"""Operational truth, preserved audit, Vault retries and retired work contracts."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from app.config import settings
from app.core import contributions
from app.core.entity import create_entity
from app.core.models import Event, SourceRun, SourceSyncBatch
from app.core.retention import prune_source_runs, prune_source_sync_batches
from app.core.source_sync import claim_pending_batch, create_or_extend_batch
from app.core.time import local_day_bounds, local_today
from app.db import SessionLocal
from app.integrations.obsidian import service as vault_service
from app.integrations.obsidian.frontmatter import parse_frontmatter
from app.main import app
from app.modules.pomodoro.models import PomodoroSession


async def test_backdated_work_edit_delete_all_live_projections_and_snapshot():
    day = local_today() - timedelta(days=2)
    # 23:50 local start, crosses midnight; the entire session belongs to start day.
    started = local_day_bounds(day)[0] + timedelta(hours=23, minutes=50)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        task = (await client.post("/api/todos", json={"title": "Old context"})).json()
        other = (await client.post("/api/todos", json={"title": "New context"})).json()
        data = {
            "started_at": started.isoformat(),
            "minutes": 40,
            "topic": "Old",
            "context_entity_id": task["id"],
        }
        created = await client.post("/api/pomodoro", json=data)
        assert created.status_code == 201, created.text
        session_id = created.json()["id"]

        async def check(expected, date_value):
            daily = (
                await client.get(
                    "/api/reviews/preview",
                    params={"kind": "daily", "period_start": date_value.isoformat()},
                )
            ).json()
            weekly = (
                await client.get(
                    "/api/reviews/preview",
                    params={"kind": "weekly", "period_start": date_value.isoformat()},
                )
            ).json()
            assert daily["stats"]["focus"]["minutes"] == expected
            assert weekly["stats"]["focus"]["minutes"] == expected
            analytics = (await client.get("/api/pomodoro/analytics?range=all")).json()
            assert analytics["minutes"] == expected
            summary = (await client.get("/api/statistics/summary")).json()
            assert summary["counters"]["pomodoros"]["total"] == int(expected > 0)
            assert summary["counters"]["pomodoros"]["today"] == 0
            assert summary["counters"]["pomodoros"]["week"] == int(expected > 0)
            monthly = (await client.get("/api/statistics/monthly?months=6")).json()
            assert sum(p["pomodoros"] for p in monthly) == int(expected > 0)
            async with SessionLocal() as db:
                heat = await contributions.heatmap(db, days=7)
                point = next(p for p in heat["days"] if p["day"] == date_value.isoformat())
                assert point["kinds"].get("focus", 0) == int(expected > 0)
                detail = await contributions.day_detail(db, date_value)
                assert detail["kinds"].get("focus", 0) == int(expected > 0)
                assert detail["other"] >= 0
                assert (date_value in await contributions.active_days(db)) == bool(expected)

        await check(40, day)
        snapshot = (
            await client.post(
                "/api/reviews", json={"kind": "daily", "period_start": day.isoformat()}
            )
        ).json()
        changed = await client.put(
            f"/api/pomodoro/{session_id}",
            json={**data, "minutes": 55, "topic": "New", "context_entity_id": other["id"]},
        )
        assert changed.json()["context_title"] == "New context"
        await check(55, day)
        new_day = day - timedelta(days=1)
        changed_data = {
            **data,
            "started_at": (started - timedelta(days=1)).isoformat(),
            "minutes": 55,
        }
        assert (
            await client.put(f"/api/pomodoro/{session_id}", json=changed_data)
        ).status_code == 200
        await check(55, new_day)
        async with SessionLocal() as db:
            assert day not in await contributions.active_days(db)
        saved = next(
            item
            for item in (await client.get("/api/reviews")).json()
            if item["id"] == snapshot["id"]
        )
        assert saved["stats"] == snapshot["stats"]  # Saved snapshot owns its original evidence.
        assert (
            await client.put(
                f"/api/pomodoro/{session_id}", json={**changed_data, "kind": "short_break"}
            )
        ).status_code == 200
        await check(0, new_day)
        assert (await client.delete(f"/api/pomodoro/{session_id}")).status_code == 204
        async with SessionLocal() as db:
            events = (
                (await db.execute(select(Event).where(Event.verb.like("pomodoro.%"))))
                .scalars()
                .all()
            )
            assert {e.verb for e in events} >= {
                "pomodoro.completed",
                "pomodoro.updated",
                "pomodoro.deleted",
            }
            assert all(e.occurred_at.date() == datetime.now(UTC).date() for e in events)


async def test_interrupted_timer_preserves_metadata_but_updates_recorded_effort():
    async with SessionLocal() as db:
        entity = await create_entity(db, type="pomodoro_session", title="Timer")
        start = local_day_bounds(local_today() - timedelta(days=1))[0] + timedelta(hours=1)
        record = PomodoroSession(
            id=entity.id,
            started_at=start,
            ended_at=start + timedelta(minutes=45),
            kind="focus",
            planned_min=50,
            actual_min=40,
            source="timer",
            interrupted=True,
            paused_s=300,
        )
        db.add(record)
        await db.commit()
        record_id = record.id
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        changed = await client.put(
            f"/api/pomodoro/{record_id}", json={"started_at": start.isoformat(), "minutes": 60}
        )
        assert changed.status_code == 200, changed.text
        assert changed.json()["source"] == "timer"
        assert changed.json()["interrupted"] is True
        assert changed.json()["paused_s"] == 300
        preview = (
            await client.get(
                "/api/reviews/preview",
                params={
                    "kind": "daily",
                    "period_start": (local_today() - timedelta(days=1)).isoformat(),
                },
            )
        ).json()
        assert preview["stats"]["focus"]["minutes"] == 60
        assert preview["stats"]["focus"]["interrupted"] == 1


async def test_vault_capture_retry_collision_and_lookup(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "obsidian_vault_path", str(tmp_path))
    monkeypatch.setattr(settings, "obsidian_vault_name", "Fixture")
    vault_service.refresh_vault_index()
    client_id = str(uuid.uuid4())
    payload = {
        "client_uuid": client_id,
        "title": "Captured",
        "body": "Important text",
        "tags": ["work"],
        "source_url": "https://example.invalid/article",
        "folder": "legacy",
        "pinned": True,
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        task = (await client.post("/api/todos", json={"title": "Related task"})).json()
        payload["relate_to"] = task["id"]
        first = await client.post("/api/obsidian/capture", json=payload)
        assert first.status_code == 201, first.text
        second = await client.post("/api/obsidian/capture", json=payload)
        assert second.status_code == 201, second.text
        assert first.json()["forkos_id"] == second.json()["forkos_id"] == client_id
        files = list(tmp_path.rglob("*.md"))
        assert len(files) == 1
        metadata, body = parse_frontmatter(files[0].read_text())
        assert "Important text" in body and metadata["tags"] == ["work"]
        assert metadata["source_url"] == payload["source_url"]
        assert metadata["capture_folder"] == "legacy" and metadata["pinned"] is True
        assert metadata["forkos_relations"][0]["target_id"] == task["id"]
        assert (await client.get(f"/api/obsidian/items/{client_id}")).status_code == 200
        assert (
            await client.post("/api/obsidian/capture", json={**payload, "body": "Different"})
        ).status_code == 409
        assert (await client.get(f"/api/obsidian/items/{uuid.uuid4()}")).status_code == 404
        assert (await client.get("/api/obsidian/items/invalid")).status_code == 422
        monkeypatch.setattr(settings, "obsidian_vault_path", str(tmp_path / "missing"))
        assert (await client.get(f"/api/obsidian/items/{client_id}")).status_code == 503
        assert (await client.post("/api/obsidian/capture", json=payload)).status_code == 503
    vault_service.vault_index._last_scanned = None


async def test_retire_media_batches_idempotently_preserve_diagnostics_and_retention(monkeypatch):
    old = datetime.now(UTC) - timedelta(days=200)
    async with SessionLocal() as db:
        batches = [
            SourceSyncBatch(
                scope=scope,
                status=status,
                source_ids=[f"media:fixture-{status}"],
                total_sources=1,
                created_at=old,
            )
            for scope, status in [
                ("media", "queued"),
                ("media", "running"),
                ("media", "completed"),
                ("opportunity", "queued"),
            ]
        ]
        db.add_all(batches)
        await db.flush()
        for i in range(25):
            db.add(
                SourceRun(
                    source="media:fixture-running",
                    status="running" if i == 24 else "ok",
                    batch_id=batches[1].id,
                    started_at=old,
                )
            )
        await db.commit()
        # Execute the migration's exact SQL twice, in the isolated database.
        import importlib.util
        from pathlib import Path

        spec = importlib.util.spec_from_file_location(
            "media_retirement",
            Path(__file__).parents[1] / "alembic/versions/0079_retire_media_batches.py",
        )
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        statements = []
        monkeypatch.setattr(migration.op, "execute", statements.append)
        migration.upgrade()
        for _ in range(2):
            for statement in statements:
                await db.execute(text(statement))
            await db.commit()
        for batch in batches:
            await db.refresh(batch)
        assert [b.status for b in batches] == [
            "completed_with_errors",
            "completed_with_errors",
            "completed",
            "queued",
        ]
        events = (
            (await db.execute(select(Event).where(Event.verb == "source_sync.retired")))
            .scalars()
            .all()
        )
        assert len(events) == 2 and all("retired" in e.payload["reason"] for e in events)
        assert (
            await db.execute(select(SourceRun.status).order_by(SourceRun.id.desc()).limit(1))
        ).scalar_one() == "abandoned"
        claimed = await claim_pending_batch(db)
        assert claimed.id == batches[3].id
        with pytest.raises(ValueError):
            await create_or_extend_batch(db, ["media:new"], scope="media")
        assert await prune_source_sync_batches(db, now=datetime.now(UTC) + timedelta(days=200)) == 0
        assert await prune_source_runs(db, now=datetime.now(UTC) + timedelta(days=200)) == 0
        assert (await db.execute(select(SourceRun))).scalars().all()


@pytest.mark.no_database
async def test_mcp_retained_tools_and_no_retired_operations():
    from tests.agent_test_utils import mcp_session

    async with mcp_session() as session:
        tools = (await session.list_tools()).tools
        names = {tool.name for tool in tools}
        assert {
            "brain_capture",
            "brain_read",
            "forkos_project_context",
            "forkos_review_intelligence",
            "forkos_execution",
            "forkos_todo_create",
        } <= names
        assert not any(
            name.startswith(
                ("media_", "finance_", "drive_", "forkos_media", "forkos_finance", "forkos_drive")
            )
            for name in names
        )
        from app.integrations.agent.capabilities import FAMILIES

        assert names == {name for family in FAMILIES for name in family.tools}


async def test_learning_resource_effort_moves_with_context_and_disappears_on_delete():
    from app.modules.learning import service as learning
    from app.modules.learning.models import LearningResource, StudyArea, StudyTopic
    from app.modules.review import service as reviews

    async with SessionLocal() as db:
        area = await create_entity(db, type="study_area", title="Learning fixture")
        db.add(StudyArea(id=area.id))
        await db.flush()
        topics = []
        for title in ["First", "Second"]:
            entity = await create_entity(db, type="study_topic", title=title)
            db.add(StudyTopic(id=entity.id, area_id=area.id))
            topics.append(entity.id)
        await db.flush()
        resource = await create_entity(db, type="learning_resource", title="Source")
        db.add(LearningResource(id=resource.id, topic_id=topics[0]))
        await db.commit()
        area_id, resource_id = area.id, resource.id
    start = local_day_bounds(local_today() - timedelta(days=1))[0] + timedelta(hours=12)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        data = {
            "started_at": start.isoformat(),
            "minutes": 30,
            "context_entity_id": str(resource_id),
        }
        created = await client.post("/api/pomodoro", json=data)
        assert created.status_code == 201, created.text
        record_id = created.json()["id"]

        async def verify(first, second):
            async with SessionLocal() as db:
                tree = (await learning.area_tree(db, area_id))["nodes"]
                focus = {row["id"]: row["focus_minutes"] for row in tree}
                assert focus[topics[0]] == first and focus[topics[1]] == second
                areas = await learning.list_areas(db, include_stats=True)
                assert areas[0]["focus_minutes"] == first + second
                for topic_id, expected in zip(topics, [first, second], strict=True):
                    assert (await learning._topic_metrics(db, topic_id))["minutes"] == expected
                stats = await learning.study_stats(db, value="all")
                assert stats["focus_minutes"] == first + second
                assert sum(row["minutes"] for row in stats["by_area"]) == first + second
                preview = await reviews.preview(db, "daily", local_today() - timedelta(days=1))
                assert (
                    sum(preview.stats.model_dump()["study"]["minutes_by_area"].values())
                    == first + second
                )

        await verify(30, 0)
        assert (
            await client.put(
                f"/api/pomodoro/{record_id}",
                json={**data, "context_entity_id": str(topics[1]), "minutes": 45},
            )
        ).status_code == 200
        await verify(0, 45)
        assert (await client.delete(f"/api/pomodoro/{record_id}")).status_code == 204
        await verify(0, 0)
