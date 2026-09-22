"""A3.1 Epistemic evidence-class DB invariants test (§12 / A3.1).

Verifies the storage-level epistemic matrix on `agent_session_episode_item`:
- `canonical_supported` MUST have `jsonb_array_length(support_refs) > 0` and `episode_turn_id is not null`
- `turn_derived` MUST have `jsonb_array_length(support_refs) = 0` and `episode_turn_id is not null`
- `observed_during_session` MUST have `jsonb_array_length(support_refs) > 0` and `episode_turn_id is null`
"""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.db import SessionLocal
from app.modules.agent_episode.models import (
    AgentSessionEpisode,
    AgentSessionEpisodeItem,
    AgentSessionEpisodeTurn,
)
from tests.a3_fixtures import start_session


async def _setup_turn(session, raw_session_id: str):
    sess_row = await start_session(session, raw_session_id, turn_id="t1")
    started = sess_row.start_seen_at or sess_row.first_seen_at
    episode = AgentSessionEpisode(
        session_id=sess_row.id,
        schema_version=1,
        status="draft",
        started_at=started,
        expires_at=started,
    )
    session.add(episode)
    await session.flush()

    turn = AgentSessionEpisodeTurn(
        episode_id=episode.id,
        turn_key="k1",
        status="pending",
        delivered_at=started,
    )
    session.add(turn)
    await session.flush()
    return episode, turn


async def test_db_rejects_canonical_supported_with_empty_refs(h4_ready: None) -> None:
    """Test F: canonical_supported + [] -> DB reject."""
    async with SessionLocal() as session:
        episode, turn = await _setup_turn(session, "db-inv-canon-empty")
        bad_item = AgentSessionEpisodeItem(
            episode_id=episode.id,
            episode_turn_id=turn.id,
            ordinal=0,
            kind="outcome",
            text="Kanonik iddia ama kanıtı boş",
            evidence_class="canonical_supported",
            support_refs=[],
        )
        session.add(bad_item)
        with pytest.raises(IntegrityError) as exc_info:
            await session.commit()
        assert "ck_agent_session_episode_item_canonical_evidence" in str(exc_info.value)


async def test_db_rejects_turn_derived_with_non_empty_refs(h4_ready: None) -> None:
    """Test G: turn_derived + refs -> DB reject."""
    async with SessionLocal() as session:
        episode, turn = await _setup_turn(session, "db-inv-turn-refs")
        bad_item = AgentSessionEpisodeItem(
            episode_id=episode.id,
            episode_turn_id=turn.id,
            ordinal=0,
            kind="topic",
            text="Tur türevi iddia ama kanonik ref verilmiş",
            evidence_class="turn_derived",
            support_refs=[{"source_id": "entity:123", "source_type": "project"}],
        )
        session.add(bad_item)
        with pytest.raises(IntegrityError) as exc_info:
            await session.commit()
        assert "ck_agent_session_episode_item_turn_derived_evidence" in str(exc_info.value)


async def test_db_accepts_all_three_valid_evidence_classes(h4_ready: None) -> None:
    """Valid matrix: canonical_supported+refs, turn_derived+no refs, observed_during_session+refs."""
    async with SessionLocal() as session:
        episode, turn = await _setup_turn(session, "db-inv-valid")
        item1 = AgentSessionEpisodeItem(
            episode_id=episode.id,
            episode_turn_id=turn.id,
            ordinal=0,
            kind="outcome",
            text="Kanonik destekli geçerli madde",
            evidence_class="canonical_supported",
            support_refs=[{"source_id": "entity:123", "source_type": "project"}],
        )
        item2 = AgentSessionEpisodeItem(
            episode_id=episode.id,
            episode_turn_id=turn.id,
            ordinal=1,
            kind="topic",
            text="Tur türevi geçerli madde",
            evidence_class="turn_derived",
            support_refs=[],
        )
        item3 = AgentSessionEpisodeItem(
            episode_id=episode.id,
            episode_turn_id=None,
            ordinal=2,
            kind="open_thread",
            text="Oturum gözlemi geçerli madde",
            evidence_class="observed_during_session",
            support_refs=[{"source_id": "entity:456", "source_type": "todo"}],
        )
        session.add_all([item1, item2, item3])
        await session.commit()
