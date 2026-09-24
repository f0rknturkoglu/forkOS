"""Read-only current source revisions for H3 items; never invent a version."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity, Event
from app.integrations.agent.evidence import _entity_candidate
from app.integrations.agent.evidence_models import EvidenceItem
from app.integrations.obsidian.evidence import MAX_VAULT_FILE_BYTES
from app.integrations.obsidian.security import is_evidence_path, resolve_safe_vault_path
from app.integrations.obsidian.vault import vault_context

from .models import SourceSnapshot


class SnapshotUnavailable(Exception):
    """A source cannot be safely bound to a current revision."""


def _digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


async def capture_snapshot(session: AsyncSession, item: EvidenceItem) -> SourceSnapshot:
    captured_at = datetime.now(UTC)
    try:
        if item.source_type == "entity":
            entity = await session.get(Entity, uuid.UUID(item.source_id), populate_existing=True)
            if entity is None:
                raise SnapshotUnavailable
            current = await _entity_candidate(
                session, entity, tier=0, rank=0, reason="snapshot", relation_path=[]
            )
            version = entity.updated_at.isoformat() if entity.updated_at else None
            if version != item.updated_at:
                raise SnapshotUnavailable
            return SourceSnapshot(
                source_id=item.source_id, source_type="entity", source_version=version,
                source_revision=_digest(current.lines), captured_at=captured_at,
            )
        if item.source_type == "event":
            event = await session.get(Event, int(item.source_id), populate_existing=True)
            if event is None or event.occurred_at.isoformat() != item.occurred_at:
                raise SnapshotUnavailable
            return SourceSnapshot(
                source_id=item.source_id, source_type="event",
                source_revision=_digest((event.id, event.entity_id, event.entity_type, event.verb, event.payload, event.occurred_at)),
                captured_at=captured_at,
            )
        if item.source_type == "vault":
            rel_path = item.locator.relative_path
            root, _ = vault_context()
            if root is None or not rel_path or not is_evidence_path(rel_path):
                raise SnapshotUnavailable
            path = resolve_safe_vault_path(root, rel_path)
            if not path.is_file():
                raise SnapshotUnavailable
            with path.open("rb") as handle:
                raw = handle.read(MAX_VAULT_FILE_BYTES + 1)
            if len(raw) > MAX_VAULT_FILE_BYTES:
                raise SnapshotUnavailable
            return SourceSnapshot(
                source_id=item.source_id, source_type="vault",
                source_revision=hashlib.sha256(raw).hexdigest(), captured_at=captured_at,
            )
    except (OSError, ValueError, TypeError, PermissionError) as exc:
        raise SnapshotUnavailable from exc
    raise SnapshotUnavailable


async def capture_snapshots(session: AsyncSession, items: list[EvidenceItem]) -> tuple[SourceSnapshot, ...]:
    return tuple([await capture_snapshot(session, item) for item in items])
