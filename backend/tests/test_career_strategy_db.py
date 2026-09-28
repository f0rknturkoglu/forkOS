"""C8 service smoke test against an isolated *_test PostgreSQL database."""

import pytest

from app.db import SessionLocal
from app.modules.opportunity import candidate_context, career_strategy


async def test_empty_strategy_is_read_only_and_truthful(monkeypatch: pytest.MonkeyPatch):
    # Never inspect the user's personal Vault during an isolated DB test.
    monkeypatch.setattr(career_strategy.semantic_storage, "readable_root", lambda: None)

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
