"""Canonical Goal is measurable state, not an H2 semantic-memory clone."""

import shutil
import uuid
from pathlib import Path

import pytest

from app.db import SessionLocal
from app.integrations.obsidian import hot_memory as hot_storage
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


def _memory(
    root: Path,
    *,
    kind: str = "goal",
    source_mode: str = "explicit_user",
    expires_at: str | None = None,
):
    return hot_storage.create_memory(
        root,
        kind=kind,
        title="EU backend",
        text="EU backend career direction",
        importance=3,
        source_mode=source_mode,
        expires_at=expires_at,
    )


async def test_h2_link_is_provenance_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    record = _memory(tmp_path)
    monkeypatch.setattr(service.hot_storage, "readable_root", lambda: tmp_path)
    async with SessionLocal() as session:
        # H2 intent alone has no operational Goal row.
        assert await service.list_goals(session) == []
        created = await service.create_goal(
            session, GoalIn(title="Operational EU target", source_memory_id=record.memory_id)
        )
        await service.update_goal(session, created.id, GoalPatch(status="completed"))
        assert (await service.get_goal(session, created.id)).source_memory_id == record.memory_id
        # Operational changes never rewrite the H2 intent file.
        assert (
            hot_storage.find_memory(hot_storage.scan_memories(tmp_path), record.memory_id).revision
            == record.revision
        )


@pytest.mark.no_database
def test_h2_source_validation_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(service.hot_storage, "readable_root", lambda: tmp_path)
    active = _memory(tmp_path)
    service._check_memory(active.memory_id)
    with pytest.raises(ValueError, match="bulunamadı"):
        service._check_memory(str(uuid.uuid4()))
    wrong_kind = _memory(tmp_path, kind="preference")
    with pytest.raises(ValueError, match="bulunamadı"):
        service._check_memory(wrong_kind.memory_id)
    expired = _memory(tmp_path, expires_at="2000-01-01T00:00:00+00:00")
    with pytest.raises(ValueError, match="bulunamadı"):
        service._check_memory(expired.memory_id)
    retired = hot_storage.rewrite_memory(
        tmp_path, active, expected_revision=active.revision, status="retired"
    )
    with pytest.raises(ValueError, match="bulunamadı"):
        service._check_memory(retired.memory_id)
    approved = _memory(tmp_path, source_mode="approved_candidate")
    service._check_memory(approved.memory_id)
    duplicate = tmp_path / hot_storage.MEMORY_ROOT / "duplicate.md"
    shutil.copyfile(tmp_path / approved.relative_path, duplicate)
    with pytest.raises(ValueError, match="çakışmalı"):
        service._check_memory(approved.memory_id)
    monkeypatch.setattr(service.hot_storage, "readable_root", lambda: None)
    with pytest.raises(ValueError, match="erişilemiyor"):
        service._check_memory(approved.memory_id)
