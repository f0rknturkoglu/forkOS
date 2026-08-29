from __future__ import annotations

import uuid

from sqlalchemy import select

from app.core.entity import create_entity, delete_entity
from app.core.models import Event
from app.db import SessionLocal
from app.modules.opportunity.models import Opportunity
from app.modules.opportunity.service import ingest_jobs, merge_duplicate_clusters
from app.modules.opportunity.worker import NativeJob
from app.sources.base import RawItem


async def _insert_duplicate_pair(session, cluster_key: str, sources: tuple[str, str]):
    ids: list[uuid.UUID] = []
    for source in sources:
        entity = await create_entity(
            session, type="opportunity", title=f"Backend Engineer {source}"
        )
        ids.append(entity.id)
        session.add(
            Opportunity(
                id=entity.id,
                kind="job",
                category="software",
                status="discovered",
                priority=2,
                found_at=entity.created_at,
                source=source,
                external_id=f"{source}-id",
                raw={"forkjob": {"cluster_key": cluster_key}},
            )
        )
    await session.commit()
    return ids


async def test_ingest_tolerates_an_existing_duplicate_cluster():
    cluster_key = f"cluster-{uuid.uuid4().hex}"
    async with SessionLocal() as session:
        ids = await _insert_duplicate_pair(session, cluster_key, ("first", "second"))
        try:
            job = NativeJob(
                RawItem(
                    external_id="third-id",
                    title="Backend Engineer",
                    url="https://example.test/third",
                    extra={
                        "organization": "Example",
                        "forkjob": {"cluster_key": cluster_key},
                    },
                )
            )
            assert await ingest_jobs(session, [job], "third") == 0
            await session.commit()

            rows = (
                await session.execute(
                    select(Opportunity).where(
                        Opportunity.raw["forkjob"]["cluster_key"].astext == cluster_key
                    )
                )
            ).scalars().all()
            assert len(rows) == 2
            canonical = min(rows, key=lambda row: (row.found_at, str(row.id)))
            assert set(canonical.raw["sources"]) == {"first", "second", "third"}
        finally:
            for entity_id in ids:
                await delete_entity(session, entity_id)
            await session.commit()


async def test_safe_duplicate_cleanup_is_idempotent_and_logs_event():
    cluster_key = f"cleanup-{uuid.uuid4().hex}"
    async with SessionLocal() as session:
        ids = await _insert_duplicate_pair(
            session, cluster_key, ("cleanup-first", "cleanup-second")
        )
        try:
            dry_run = await merge_duplicate_clusters(session)
            assert dry_run.safe_groups >= 1
            applied = await merge_duplicate_clusters(session, dry_run=False)
            assert applied.merged_groups >= 1
            assert applied.removed_rows >= 1
            second = await merge_duplicate_clusters(session, dry_run=False)
            assert second.merged_groups == 0

            events = (
                await session.execute(
                    select(Event).where(
                        Event.verb == "opportunity.duplicates_merged",
                        Event.payload["cluster_key"].astext == cluster_key,
                    )
                )
            ).scalars().all()
            assert len(events) == 1
        finally:
            for entity_id in ids:
                await delete_entity(session, entity_id)
            await session.commit()
