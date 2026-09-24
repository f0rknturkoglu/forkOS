"""Read-only current source revisions for H3 items; never invent a version."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity, Event
from app.integrations.agent.evidence import _entity_candidate
from app.integrations.agent.evidence_models import EvidenceItem
from app.integrations.agent.evidence_revision import event_source_revision, projection_digest
from app.integrations.obsidian.evidence import read_note_lines
from app.integrations.obsidian.frontmatter import extract_title, parse_frontmatter
from app.integrations.obsidian.security import is_evidence_path
from app.integrations.obsidian.vault import vault_context

from .models import SourceSnapshot


class SnapshotUnavailable(Exception):
    """A source cannot be safely bound to a current revision."""


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
                source_revision=projection_digest(current.lines), captured_at=captured_at,
            )
        if item.source_type == "event":
            event = await session.get(Event, int(item.source_id), populate_existing=True)
            if event is None or event.occurred_at.isoformat() != item.occurred_at:
                raise SnapshotUnavailable
            related = await session.get(Entity, event.entity_id, populate_existing=True) if event.entity_id else None
            return SourceSnapshot(
                source_id=item.source_id, source_type="event",
                source_revision=event_source_revision(event, related.title if related else ""),
                captured_at=captured_at,
            )
        if item.source_type == "vault":
            rel_path = item.locator.relative_path
            root, _ = vault_context()
            if root is None or not rel_path or not is_evidence_path(rel_path):
                raise SnapshotUnavailable
            lines = read_note_lines(root, rel_path)
            if lines is None:
                raise SnapshotUnavailable
            title = Path(rel_path).stem
            if item._vault_title_from_index:
                frontmatter, body = parse_frontmatter("\n".join(lines))
                title = extract_title(
                    frontmatter if isinstance(frontmatter, dict) else {},
                    body, fallback=title,
                )
            return SourceSnapshot(
                source_id=item.source_id, source_type="vault",
                source_revision=projection_digest((lines, title)), captured_at=captured_at,
            )
    except (OSError, ValueError, TypeError, PermissionError) as exc:
        raise SnapshotUnavailable from exc
    raise SnapshotUnavailable


async def capture_snapshots(session: AsyncSession, items: list[EvidenceItem]) -> tuple[SourceSnapshot, ...]:
    # H3 may have loaded ORM rows into this session's identity map. Re-read all
    # mutable projections under READ COMMITTED instead of trusting stale objects.
    session.expire_all()
    return tuple([await capture_snapshot(session, item) for item in items])


def bind_evidence_to_snapshots(items: list[EvidenceItem], snapshots: tuple[SourceSnapshot, ...]) -> bool:
    """Only H3-produced items with the exact captured projection may be judged."""
    return len(items) == len(snapshots) and all(
        item._source_revision is not None
        and item._source_revision == snapshot.source_revision
        and item.source_id == snapshot.source_id
        and item.source_type == snapshot.source_type
        for item, snapshot in zip(items, snapshots, strict=True)
    )
