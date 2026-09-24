"""Read-only A4 source projections used for A5.2 provenance binding."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity, Event
from app.integrations.agent.evidence_revision import projection_digest
from app.modules.agent_episode.models import (
    AgentSessionEpisode,
    AgentSessionEpisodeItem,
    AgentSessionEpisodeTurn,
)


@dataclass(frozen=True)
class MemorySource:
    ref: str
    text: str
    revision: str
    role: str | None
    evidence_digest: str | None


async def read_memory_source(session: AsyncSession, ref: str) -> MemorySource | None:
    """Only A4's current episode-item/event refs; never arbitrary retrieval."""
    family, sep, value = ref.partition(":")
    if not sep or not value.isdecimal():
        return None
    source_id = int(value)
    if family == "episode_item":
        item = await session.get(AgentSessionEpisodeItem, source_id, populate_existing=True)
        if item is None or item.episode_turn_id is None:
            return None
        turn = await session.get(AgentSessionEpisodeTurn, item.episode_turn_id, populate_existing=True)
        episode = await session.get(AgentSessionEpisode, item.episode_id, populate_existing=True)
        if (
            turn is None
            or episode is None
            or not turn.semantic_memory_eligible
            or episode.status not in ("sealed", "sealed_degraded")
            or "SCOPE_AMBIGUOUS" in (episode.degraded_reasons or [])
        ):
            return None
        text = f"{item.kind}: {item.text}"
        revision = projection_digest(
            (
                item.id,
                item.episode_id,
                item.episode_turn_id,
                item.kind,
                item.text,
                item.evidence_class,
                item.support_refs,
                item.source_role,
                item.evidence_digest,
                turn.semantic_memory_eligible,
                episode.status,
                episode.scope_project,
                episode.degraded_reasons,
            )
        )
        return MemorySource(ref, text, revision, item.source_role, item.evidence_digest)
    if family == "event":
        event = await session.get(Event, source_id, populate_existing=True)
        if event is None:
            return None
        entity = (
            await session.get(Entity, event.entity_id, populate_existing=True)
            if event.entity_id
            else None
        )
        if event.entity_id and (entity is None or entity.archived_at is not None):
            return None
        title = str((entity.title if entity else None) or (event.payload or {}).get("title") or "").strip()
        if not title:
            return None
        text = f"{event.verb}: {title}"
        revision = projection_digest(
            (
                event.id,
                event.entity_id,
                event.entity_type,
                event.verb,
                event.payload,
                event.occurred_at,
                entity.title if entity else None,
                entity.archived_at if entity else None,
                text,
            )
        )
        return MemorySource(ref, text, revision, "canonical", None)
    return None
