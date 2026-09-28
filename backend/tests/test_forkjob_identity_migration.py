"""Persisted source IDs survive the forkjob_core identity migration."""

from __future__ import annotations

import runpy
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import select

from app.core.models import SourceRun, SourceSyncBatch
from app.db import SessionLocal, engine
from app.modules.opportunity.models import Opportunity, OpportunitySourceObservation
from app.modules.opportunity.service import ingest_jobs
from app.modules.opportunity.worker import NativeJob
from app.modules.system.models import Setting
from app.sources.base import RawItem


async def test_source_identity_migration_preserves_collision_and_history():
    old_id = "jobhunter:greenhouse:acme"
    new_id = "forkjob_core:greenhouse:acme"
    now = datetime.now(UTC)
    item = RawItem(
        external_id="req-42",
        title="Staff Engineer",
        url="https://example.com/jobs/42",
        extra={"organization": "Acme", "sources": [old_id]},
    )
    async with SessionLocal() as session:
        assert await ingest_jobs(session, [NativeJob(item)], old_id) == 1
        opportunity = (await session.execute(select(Opportunity))).scalar_one()
        opportunity.raw = {**(opportunity.raw or {}), "sources": [old_id]}
        old_observation = (
            await session.execute(select(OpportunitySourceObservation))
        ).scalar_one()
        old_observation.first_seen_at = now - timedelta(days=5)
        old_observation.last_seen_at = now - timedelta(days=2)
        old_observation.enrichment = {"legacy_signal": "kept"}
        session.add(
            OpportunitySourceObservation(
                id=uuid.uuid4(),
                opportunity_id=opportunity.id,
                source=new_id,
                external_id="req-42",
                source_status="active",
                first_seen_at=now - timedelta(days=3),
                last_seen_at=now,
                enrichment={"canonical_signal": "kept"},
            )
        )
        batch = SourceSyncBatch(
            id=uuid.uuid4(),
            source_ids=[old_id, new_id],
            total_sources=2,
        )
        session.add(batch)
        await session.flush()
        session.add(SourceRun(source=old_id, status="ok", batch_id=batch.id))
        session.add(Setting(key="migration.source_state", value={"source": old_id}))
        opportunity_id = opportunity.id
        await session.commit()

    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic/versions/0074_forkjob_identity.py"
    )
    migration = runpy.run_path(str(migration_path))

    def apply_migration(connection):
        migration["upgrade"].__globals__["op"] = SimpleNamespace(get_bind=lambda: connection)
        migration["upgrade"]()

    async with engine.begin() as connection:
        await connection.run_sync(apply_migration)
        await connection.run_sync(apply_migration)  # idempotent on already-migrated data

    async with SessionLocal() as session:
        opportunity = await session.get(Opportunity, opportunity_id)
        assert opportunity is not None
        assert opportunity.source == new_id
        assert opportunity.raw["sources"] == [new_id]
        observations = list(
            (
                await session.execute(
                    select(OpportunitySourceObservation).where(
                        OpportunitySourceObservation.opportunity_id == opportunity_id
                    )
                )
            ).scalars()
        )
        assert len(observations) == 1
        observation = observations[0]
        assert observation.source == new_id
        assert observation.first_seen_at == now - timedelta(days=5)
        assert observation.last_seen_at == now
        assert observation.enrichment["canonical_signal"] == "kept"
        assert observation.enrichment["legacy_source_observations"][0]["enrichment"] == {
            "legacy_signal": "kept"
        }
        run = (await session.execute(select(SourceRun))).scalar_one()
        assert run.source == new_id
        saved_batch = await session.get(SourceSyncBatch, batch.id)
        assert saved_batch is not None
        assert saved_batch.source_ids == [new_id]
        assert saved_batch.total_sources == 1
        assert saved_batch.completed_sources == 1
        setting = await session.get(Setting, "migration.source_state")
        assert setting is not None
        assert setting.value == {"source": new_id}
