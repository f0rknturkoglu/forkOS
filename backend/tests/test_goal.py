"""Canonical Goal is measurable state, not an H2 semantic-memory clone."""

from types import SimpleNamespace

import pytest

from app.db import SessionLocal
from app.modules.goal import service
from app.modules.goal.models import Goal
from app.modules.goal.schemas import GoalIn, GoalMilestoneIn, GoalMilestonePatch, GoalPatch


def test_progress_has_an_explicit_denominator():
    assert service.progress(0, 0) is None
    assert service.progress(1, 3) == 33
    assert service.progress(3, 3) == 100
    assert service.progress(4, 3) == 100


async def test_goal_crud_and_milestone_progress():
    async with SessionLocal() as session:
        created = await service.create_goal(
            session, GoalIn(title="EU backend role", horizon="long_term")
        )
        assert created.status == "active"
        assert created.progress_percent is None
        assert (await service.get_goal(session, created.id)).id == created.id
        assert len(await service.list_goals(session)) == 1
        patched = await service.update_goal(
            session, created.id, GoalPatch(status="paused", description="Measurable target")
        )
        assert patched.status == "paused"
        assert patched.description == "Measurable target"
        first = await service.add_goal_milestone(
            session, created.id, GoalMilestoneIn(title="Ship one deployment")
        )
        await service.add_goal_milestone(session, created.id, GoalMilestoneIn(title="Story bank"))
        await service.add_goal_milestone(
            session, created.id, GoalMilestoneIn(title="Interview prep")
        )
        assert (await service.get_goal(session, created.id)).progress_percent == 0
        await service.update_goal_milestone(session, first.id, GoalMilestonePatch(completed=True))
        assert (await service.get_goal(session, created.id)).progress_percent == 33
        current = await service.get_goal(session, created.id)
        for milestone in current.milestones:
            await service.update_goal_milestone(
                session, milestone.id, GoalMilestonePatch(completed=True)
            )
        assert (await service.get_goal(session, created.id)).progress_percent == 100
        assert await session.get(Goal, created.id)


async def test_semantic_link_is_provenance_only(monkeypatch: pytest.MonkeyPatch):
    card = SimpleNamespace(card_id="memory-1", kind="goal", effective_status="active")
    monkeypatch.setattr(service.semantic_storage, "readable_root", lambda: "isolated")
    monkeypatch.setattr(service.semantic_storage, "scan_semantic_cards", lambda root: [card])
    async with SessionLocal() as session:
        # An H2 card alone has no operational Goal row.
        assert await service.list_goals(session) == []
        created = await service.create_goal(
            session, GoalIn(title="Operational EU target", source_memory_id="memory-1")
        )
        await service.update_goal(session, created.id, GoalPatch(status="completed"))
        assert card.kind == "goal"
        assert card.card_id == "memory-1"
        assert (await service.get_goal(session, created.id)).source_memory_id == "memory-1"
