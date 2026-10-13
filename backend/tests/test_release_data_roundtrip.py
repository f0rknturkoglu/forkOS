"""Full synthetic content fingerprints across a migrated second PostgreSQL DB."""
import asyncio
import base64
import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import insert, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.core.entity import create_entity
from app.core.events import log_event
from app.core.links import link
from app.core.test_guard import assert_safe_test_database
from app.db import Base, SessionLocal
from app.modules.goal import studio
from app.modules.goal.studio_schemas import StudioProposal, StudioSessionIn
from app.modules.system import export, restore


def fingerprint(payload):
    tables = {"entity": payload["entities"], "link": payload["links"],
              "event": [r for r in payload["events"] if r["verb"] != "backup.restored"],
              **payload["modules"]}
    return {name: hashlib.sha256(json.dumps(sorted(rows, key=lambda r: json.dumps(r, sort_keys=True)),
                sort_keys=True, ensure_ascii=False).encode()).hexdigest() for name, rows in tables.items()}


async def synthetic_data(db):
    now = datetime.now(UTC)
    async def entity_row(name, **values):
        entity = await create_entity(db, type=name, title="Sentetik Türkçe " + name)
        await db.execute(insert(Base.metadata.tables[name]).values(id=entity.id, **values))
        return entity.id
    plan = await entity_row("strategic_plan", start_at=now, end_at=now + timedelta(days=90))
    pillar = await entity_row("strategic_pillar", plan_id=plan)
    goal = await entity_row("goal", strategic_plan_id=plan, pillar_id=pillar)
    await entity_row("goal", parent_goal_id=goal)
    await entity_row("key_result", goal_id=goal, description="Ölçüm", baseline_value=0,
                     target_value=10, manual_value=4, measured_at=now)
    await entity_row("goal_milestone", goal_id=goal, title="Sentetik adım")
    project = await entity_row("project")
    todo = await entity_row("todo")
    await link(db, todo, project, "belongs_to")
    await db.execute(insert(Base.metadata.tables["plan_slot"]).values(id=uuid4(), entity_id=todo,
                    day=now.date(), start_min=600, duration_min=45))
    await link(db, todo, goal, "advances_goal")
    await link(db, project, goal, "advances_goal")
    area = await entity_row("study_area")
    topic = await entity_row("study_topic", area_id=area)
    bookmark = await entity_row("bookmark", url="https://example.org/synthetic",
                    url_hash=hashlib.sha256(b"https://example.org/synthetic").hexdigest())
    await entity_row("learning_resource", topic_id=topic, bookmark_id=bookmark, source="bookmark")
    feed = await entity_row("feed", url="https://example.org/synthetic.xml")
    feed_item = await entity_row("feed_item", feed_id=feed, guid="sentinel-source-identity")
    await link(db, bookmark, feed_item, "saved_from")
    await entity_row("external_event", provider="local_fixture", external_id="sentinel",
                     starts_at=now, synced_at=now)
    opportunity = await entity_row("opportunity", kind="job", found_at=now, source="manual")
    await db.execute(insert(Base.metadata.tables["application"]).values(opportunity_id=opportunity,
                    status="applied", created_at=now, updated_at=now))
    await link(db, todo, opportunity, "application_step")
    await entity_row("review", kind="weekly", period_start=now.date(), period_end=now.date())
    await db.execute(insert(Base.metadata.tables["setting"]).values(key="release.fixture.bundle",
                    value={"sources":["hn", "gh", "hf"], "revision":2}))
    # Retired metadata and attachments must stay portable.
    note = await entity_row("note", body="Historical metadata")
    content = b"synthetic historical attachment"
    from app.modules.note import storage
    digest = storage.store_blob(content)
    await db.execute(insert(Base.metadata.tables["note_attachment"]).values(note_id=note,
                    name="sentinel.txt", mime="text/plain", size=len(content), sha256=digest))
    from app.modules.document import service
    await service.create_local_document(db, title="synthetic.pdf", category="cv",
                    mime="application/pdf", content=b"%PDF-1.4 synthetic")
    await log_event(db, verb="release.fixture", entity_id=todo, entity_type="todo", payload={"kept": True})
    await db.commit()
    session = await studio.start(db, StudioSessionIn(client_uuid=uuid4()))
    await studio.revise(db, await studio.get_session(db, session.id), StudioProposal.model_validate({
        "rationale":"Synthetic retained draft", "operations":[{"type":"goal.create", "key":"goal",
        "data":{"title":"Portable revision"}}]}))
    await entity_row("capture_receipt", client_uuid=uuid4(), fingerprint="a" * 64,
                     destination="todo", result={"entity_id":str(todo)})
    await db.commit()


async def test_second_database_restore_and_migration_preserve_all_content(tmp_path, monkeypatch):
    assert_safe_test_database(settings.database_url)
    name = "forkos_release_" + uuid4().hex + "_test"
    url = settings.database_url.rsplit("/", 1)[0] + "/" + name
    assert_safe_test_database(url)
    admin = create_async_engine(settings.database_url, isolation_level="AUTOCOMMIT")
    target = create_async_engine(url)
    sessions = async_sessionmaker(target, expire_on_commit=False)
    async def migrate(*args):
        await asyncio.to_thread(subprocess.run, ["alembic", *args], check=True,
            capture_output=True, env={**os.environ, "DATABASE_URL":url})
    async with admin.connect() as connection:
        await connection.execute(text('CREATE DATABASE "' + name + '"'))
    try:
        await migrate("upgrade", "0079_retire_media_batches")
        await migrate("upgrade", "head")
        async with SessionLocal() as db:
            await synthetic_data(db)
            payload = await export.full_json(db)
            # Persist/read the real v2 JSON format, including binary fixtures.
            encoded = json.dumps(payload, ensure_ascii=False).encode()
            payload = restore.parse_backup(encoded)
            assert restore.inspect_payload(payload)["integrity_ok"] is True
            expected = fingerprint(payload)
        from app.modules.document import service
        from app.modules.note import storage
        monkeypatch.setattr(service, "DOCUMENTS_DIR", tmp_path / "restored-documents")
        monkeypatch.setattr(storage, "ATTACHMENTS_DIR", tmp_path / "restored-attachments")
        async with sessions() as db:
            await restore.restore(db, payload)
            actual = await export.full_json(db)
            assert fingerprint(actual) == expected
            assert actual["files"] == payload["files"]
            assert actual["attachments"] == payload["attachments"]
            summary = await restore.restore(db, payload)
            assert all(value.get("inserted", 0) == 0 for value in summary.values())
            assert fingerprint(await export.full_json(db)) == expected
        await migrate("downgrade", "0079_retire_media_batches")
        await migrate("upgrade", "head")
        async with sessions() as db:
            assert fingerprint(await export.full_json(db)) == expected
            assert await db.scalar(text("select version_num from alembic_version")) == "0081_goal_roadmap"
        # Binary corruption remains an explicit preflight failure.
        payload["attachments"][next(iter(payload["attachments"]))] = base64.b64encode(b"corrupt").decode()
        assert restore.inspect_payload(payload)["integrity_ok"] is False
    finally:
        await target.dispose()
        async with admin.connect() as connection:
            await connection.execute(text('DROP DATABASE "' + name + '" WITH (FORCE)'))
        await admin.dispose()
