"""C8 service smoke test against an isolated *_test PostgreSQL database."""

from pathlib import Path

import pytest

from app.db import SessionLocal
from app.integrations.obsidian import hot_memory as hot_storage
from app.integrations.obsidian import semantic_memory as semantic_storage
from app.modules.opportunity import candidate_context, career_strategy


async def test_empty_strategy_is_read_only_and_truthful(monkeypatch: pytest.MonkeyPatch):
    # Never inspect the user's personal Vault during an isolated DB test.
    monkeypatch.setattr(career_strategy.hot_storage, "readable_root", lambda: None)

    async def empty_candidate(_session):
        return candidate_context.CandidateCareerContext(revision="isolated-test")

    monkeypatch.setattr(candidate_context, "build_candidate_career_context", empty_candidate)
    async with SessionLocal() as session:
        result = await career_strategy.strategy_snapshot(session)
    assert result.population == 0
    assert result.primary_action is None
    assert result.existing_goals == []
    assert result.goal_progress == []
    assert result.signals == []


async def test_strategy_reads_h2_intent_not_a4_model_goal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    explicit = hot_storage.create_memory(
        tmp_path,
        kind="goal",
        title="Açık hedef",
        text="Backend yönü",
        importance=3,
        source_mode="explicit_user",
    )
    approved = hot_storage.create_memory(
        tmp_path,
        kind="goal",
        title="Onaylı hedef",
        text="Avrupa yönü",
        importance=2,
        source_mode="approved_candidate",
    )
    hot_storage.create_memory(
        tmp_path,
        kind="goal",
        title="Süresi geçmiş",
        text="Eski yön",
        importance=1,
        source_mode="explicit_user",
        expires_at="2000-01-01T00:00:00+00:00",
    )
    retired = hot_storage.create_memory(
        tmp_path,
        kind="goal",
        title="Emekli hedef",
        text="Eski yön",
        importance=1,
        source_mode="explicit_user",
    )
    hot_storage.rewrite_memory(
        tmp_path, retired, expected_revision=retired.revision, status="retired"
    )
    a4_card = semantic_storage.create_semantic_card(
        tmp_path,
        kind="goal",
        title="Model önerisi",
        statement="Model-derived direction",
        evidence_class="model_derived",
        evidence_refs=["episode:synthetic"],
    )
    monkeypatch.setattr(career_strategy.hot_storage, "readable_root", lambda: tmp_path)

    async def empty_candidate(_session):
        return candidate_context.CandidateCareerContext(revision="isolated-test")

    monkeypatch.setattr(candidate_context, "build_candidate_career_context", empty_candidate)
    async with SessionLocal() as session:
        result = await career_strategy.strategy_snapshot(session)
    assert {row.evidence_refs[0] for row in result.existing_goals} == {
        f"hot_memory:{explicit.memory_id}",
        f"hot_memory:{approved.memory_id}",
    }
    assert {row.evidence_type for row in result.existing_goals} == {
        "user_statement",
        "approved_memory",
    }
    assert all(a4_card.card_id not in row.evidence_refs[0] for row in result.existing_goals)
