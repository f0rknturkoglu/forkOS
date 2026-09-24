"""Current entity/event/Vault revisions, with no personal source files."""

import uuid
from datetime import UTC, datetime

import pytest

from app.config import settings
from app.core.entity import create_entity, touch_entity
from app.core.models import Entity, Event
from app.db import SessionLocal
from app.integrations.agent.evidence import retrieve_evidence
from app.integrations.agent.evidence_models import EvidenceItem, EvidenceLocator
from app.integrations.judgment.policy import revalidate_snapshots
from app.integrations.judgment.snapshots import SnapshotUnavailable, capture_snapshot


async def test_entity_snapshot_detects_change_and_disappearance():
    entity_id = uuid.uuid4()
    async with SessionLocal() as session:
        entity = Entity(id=entity_id, type="todo", title="Atlas task", search_text="Rust")
        session.add(entity)
        await session.flush()
        await session.refresh(entity)
        item = EvidenceItem(
            evidence_id=f"entity:{entity_id}", source_type="entity", source_id=str(entity_id),
            title="Atlas task", excerpt="Rust", updated_at=entity.updated_at.isoformat(),
            retrieval_reason="synthetic",
        )
        first = await capture_snapshot(session, item)
        second = await capture_snapshot(session, item)
        assert revalidate_snapshots((first,), (second,)) == "success"
        entity.title = "Changed task"
        await session.flush()
        third = await capture_snapshot(session, item)
        assert revalidate_snapshots((first,), (third,)) == "stale"
        await session.rollback()
    async with SessionLocal() as session:
        with pytest.raises(SnapshotUnavailable):
            await capture_snapshot(session, item)


async def test_event_snapshot_detects_missing_or_changed_identity():
    async with SessionLocal() as session:
        event = Event(verb="atlas.created", payload={"value": "synthetic"}, occurred_at=datetime.now(UTC))
        session.add(event)
        await session.flush()
        item = EvidenceItem(
            evidence_id=f"event:{event.id}", source_type="event", source_id=str(event.id),
            title="atlas.created", excerpt="synthetic", occurred_at=event.occurred_at.isoformat(),
            retrieval_reason="synthetic",
        )
        first = await capture_snapshot(session, item)
        assert revalidate_snapshots((first,), (await capture_snapshot(session, item),)) == "success"
        changed = item.model_copy(update={"occurred_at": "2020-01-01T00:00:00+00:00"})
        with pytest.raises(SnapshotUnavailable):
            await capture_snapshot(session, changed)
        missing = item.model_copy(update={"source_id": str(event.id + 999999)})
        with pytest.raises(SnapshotUnavailable):
            await capture_snapshot(session, missing)
        await session.rollback()


async def test_vault_snapshot_detects_bytes_and_missing_file(tmp_path, monkeypatch):
    vault = tmp_path / "Vault"
    vault.mkdir()
    note = vault / "Atlas.md"
    note.write_text("# Atlas\nRust", encoding="utf-8")
    monkeypatch.setattr(settings, "obsidian_vault_path", str(vault))
    item = EvidenceItem(
        evidence_id="vault:Atlas.md#root", source_type="vault", source_id="Atlas.md",
        title="Atlas", excerpt="Rust", retrieval_reason="synthetic",
        locator=EvidenceLocator(relative_path="Atlas.md"),
    )
    async with SessionLocal() as session:
        first = await capture_snapshot(session, item)
        assert revalidate_snapshots((first,), (await capture_snapshot(session, item),)) == "success"
        note.write_text("# Atlas\nPython", encoding="utf-8")
        second = await capture_snapshot(session, item)
        assert revalidate_snapshots((first,), (second,)) == "stale"
        note.unlink()
        with pytest.raises(SnapshotUnavailable):
            await capture_snapshot(session, item)


async def test_event_projection_binds_mutable_related_entity_title():
    async with SessionLocal() as session:
        entity = await create_entity(session, type="todo", title="Atlas Rust", search_text="Atlas Rust")
        entity_id = entity.id
        session.add(Event(
            entity_id=entity_id, entity_type="todo", verb="todo.created",
            payload={"synthetic": True}, occurred_at=datetime.now(UTC),
        ))
        await session.commit()

    async with SessionLocal() as session:
        bundle = await retrieve_evidence(
            session, query="Atlas Rust", entity_id=str(entity_id), scope="operational",
        )
        item = next(item for item in bundle.evidence if item.source_type == "event")
        first = await capture_snapshot(session, item)
        assert first.source_revision == item._source_revision

    async with SessionLocal() as session:
        await touch_entity(session, entity_id, title="Atlas Python")
        await session.commit()

    async with SessionLocal() as session:
        second = await capture_snapshot(session, item)
    assert second.source_revision != item._source_revision
