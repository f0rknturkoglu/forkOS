"""C8 approval is the only boundary that can materialize canonical records."""

from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.core.models import Link
from app.db import SessionLocal
from app.integrations.obsidian import hot_memory as hot_storage
from app.modules.goal import service as goal_service
from app.modules.goal.models import Goal, GoalMilestone
from app.modules.goal.schemas import GoalMilestonePatch
from app.modules.learning import service as learning_service
from app.modules.learning.models import StudyTopic
from app.modules.learning.schemas import AreaIn
from app.modules.opportunity import career_strategy_proposals as proposals
from app.modules.opportunity.career_strategy import build_strategy
from app.modules.project import service as project_service
from app.modules.project.schemas import ProjectIn
from app.modules.todo.models import Todo
from tests.test_career_strategy import NOW, analytics


@pytest.fixture
def strategy_fixture(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    state = {"missing": 4}
    memory = hot_storage.create_memory(
        tmp_path,
        kind="goal",
        title="EU backend role",
        text="EU backend role",
        importance=3,
        source_mode="explicit_user",
    )
    state["memory_id"] = memory.memory_id
    state["root"] = tmp_path
    monkeypatch.setattr(hot_storage, "readable_root", lambda: tmp_path)

    async def strategy(session, **_kwargs):
        canonical = [row.model_dump(mode="json") for row in await goal_service.list_goals(session)]
        current = hot_storage.find_memory(hot_storage.scan_memories(tmp_path), memory.memory_id)
        goals = (
            [
                {
                    "memory_id": current.memory_id,
                    "kind": current.kind,
                    "title": current.title,
                    "text": current.text,
                    "source_mode": current.source_mode,
                    "importance": current.importance,
                    "revision": current.revision,
                    "effective_status": current.effective_status(),
                    "related_forkos_ids": current.related_forkos_ids,
                }
            ]
            if current
            else []
        )
        return build_strategy(
            analytics(state["missing"]),
            projects=[],
            milestones=[],
            topics=[],
            todos=[],
            now=NOW,
            goals=goals,
            canonical_goals=canonical,
        )

    monkeypatch.setattr(proposals, "strategy_snapshot", strategy)
    return state


async def _count(session, model):
    return await session.scalar(select(func.count()).select_from(model))


async def _has_link(session, from_id, to_id, relation):
    return (
        await session.scalar(
            select(Link.id).where(
                Link.from_id == from_id, Link.to_id == to_id, Link.relation == relation
            )
        )
        is not None
    )


async def test_duplicate_refresh_reject_and_stale_fail_closed(strategy_fixture):
    async with SessionLocal() as session:
        first = await proposals.refresh_proposals(session)
        goal = next(item for item in first if item.type == "goal")
        learning = next(item for item in first if item.type == "learning")
        assert goal.status == "proposed"
        assert await _count(session, Goal) == 0
        assert await _count(session, StudyTopic) == 0
        second = await proposals.refresh_proposals(session)
        assert {item.id for item in second} == {item.id for item in first}
        rejected = await proposals.reject_proposal(session, learning.id)
        assert rejected.status == "rejected"
        assert await _count(session, StudyTopic) == 0
        strategy_fixture["missing"] = 2
        with pytest.raises(proposals.ProposalError, match="Kanıt"):
            await proposals.approve_proposal(session, goal.id)
        assert await _count(session, Goal) == 0


async def test_h2_revision_change_stales_pending_goal_proposal(strategy_fixture):
    async with SessionLocal() as session:
        goal = next(
            item for item in await proposals.refresh_proposals(session) if item.type == "goal"
        )
        root = strategy_fixture["root"]
        record = hot_storage.find_memory(
            hot_storage.scan_memories(root), strategy_fixture["memory_id"]
        )
        hot_storage.rewrite_memory(
            root, record, expected_revision=record.revision, text="Revised EU backend intent"
        )
        with pytest.raises(proposals.ProposalError, match="Kanıt"):
            await proposals.approve_proposal(session, goal.id)
        assert await _count(session, Goal) == 0


@pytest.mark.no_database
def test_a4_model_goal_cannot_generate_operational_goal_proposal():
    a4_goal_card = {
        "card_id": "a4-model-goal",
        "kind": "goal",
        "statement": "Model-derived direction",
        "evidence_class": "model_derived",
        "revision": "a4-v1",
    }
    snapshot = build_strategy(
        analytics(),
        projects=[],
        milestones=[],
        topics=[],
        todos=[],
        now=NOW,
        goals=[a4_goal_card],
    )
    drafts = proposals._drafts(snapshot, goals=[], goal_milestones=[], projects=[], area_id=None)
    assert snapshot.existing_goals == []
    assert not any(draft.type == "goal" for draft in drafts)


async def test_goal_milestone_todo_learning_and_project_materialization(strategy_fixture):
    async with SessionLocal() as session:
        await learning_service.create_area(session, AreaIn(title="Career"))
        project = await project_service.create(
            session, ProjectIn(title="Kubernetes lab", stack=["kubernetes"])
        )
        first = await proposals.refresh_proposals(session)
        assert await _count(session, Goal) == 0
        assert await _count(session, StudyTopic) == 0
        assert await _count(session, Todo) == 0
        goal_proposal = next(item for item in first if item.type == "goal")
        created = await proposals.approve_proposal(session, goal_proposal.id)
        assert created.status == "materialized"
        assert created.target_type == "goal"
        assert created.target_id is not None
        assert await _count(session, Goal) == 1
        assert await _has_link(session, created.target_id, created.id, "originated_from")
        assert (
            await goal_service.get_goal(session, created.target_id)
        ).source_memory_id == strategy_fixture["memory_id"]
        assert (await goal_service.get_goal(session, created.target_id)).progress_percent is None

        second = await proposals.refresh_proposals(session)
        milestone_proposal = next(
            item for item in second if item.type == "milestone" and item.status == "proposed"
        )
        milestone = await proposals.approve_proposal(session, milestone_proposal.id)
        assert milestone.target_type == "goal_milestone"
        assert await _has_link(session, milestone.target_id, milestone.id, "originated_from")
        assert await _count(session, GoalMilestone) == 1
        assert (await goal_service.get_goal(session, created.target_id)).progress_percent == 0

        third = await proposals.refresh_proposals(session)
        todo_proposal = next(
            item for item in third if item.type == "todo" and item.status == "proposed"
        )
        todo = await proposals.approve_proposal(session, todo_proposal.id)
        assert todo.target_type == "todo"
        assert await _has_link(session, todo.target_id, todo.id, "originated_from")
        assert await _count(session, Todo) == 1

        await goal_service.update_goal_milestone(
            session, milestone.target_id, GoalMilestonePatch(completed=True)
        )
        assert (await goal_service.get_goal(session, created.target_id)).progress_percent == 100

        fourth = await proposals.refresh_proposals(session)
        learning = next(
            item for item in fourth if item.type == "learning" and item.status == "proposed"
        )
        result = await proposals.approve_proposal(session, learning.id)
        assert result.target_type == "study_topic"
        assert await _has_link(session, result.target_id, result.id, "originated_from")
        assert await _count(session, StudyTopic) == 1

        project_proposal = next(
            item for item in fourth if item.type == "project" and item.status == "proposed"
        )
        # Learning creation changes strategy evidence only in production's full snapshot.
        # The isolated reducer fixture intentionally holds its read model fixed here.
        linked = await proposals.approve_proposal(session, project_proposal.id)
        assert linked.target_type == "project"
        assert linked.target_id == project["id"]
        assert await _has_link(session, linked.id, project["id"], "targets")
        assert not await _has_link(session, project["id"], linked.id, "originated_from")


async def test_learning_without_area_reports_unsupported_target(strategy_fixture):
    async with SessionLocal() as session:
        items = await proposals.refresh_proposals(session)
        learning = next(item for item in items if item.type == "learning")
        result = await proposals.approve_proposal(session, learning.id)
        assert result.status == "approved"
        assert result.materialization_status == "unsupported_target"
        assert result.target_id is None
        assert result.warnings
        assert await _count(session, StudyTopic) == 0
