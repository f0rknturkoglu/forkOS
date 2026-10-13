import asyncio
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app.core.links import link
from app.core.models import Event
from app.db import SessionLocal
from app.modules.goal import service, strategy
from app.modules.goal.schemas import GoalIn, GoalMilestoneIn, GoalMilestonePatch
from app.modules.goal.work import GoalActionIn, create_action, load_work
from app.modules.learning import service as learning
from app.modules.learning.models import StudyArea, StudyTopic
from app.modules.learning.schemas import TopicPatch
from app.modules.todo import service as todos
from app.modules.todo.models import Todo
from app.modules.todo.schemas import TodoIn, TodoUpdate


async def fixture(db):
    goal = await service.create_goal(db, GoalIn(title="YDS 60+"))
    first = await service.add_goal_milestone(db, goal.id, GoalMilestoneIn(title="İlk deneme"))
    second = await service.add_goal_milestone(db, goal.id, GoalMilestoneIn(title="Eksik konuları çalış"))
    return goal.id, first.id, second.id


async def work(db, goal_id):
    return (await load_work(db, [await service.get_goal(db, goal_id)]))[goal_id]


async def test_completed_tasks_and_topics_drive_steps_without_changing_outcome():
    async with SessionLocal() as db:
        gid, first, second = await fixture(db)
        assert (await work(db, gid)).progress_percent == 0
        request = GoalActionIn(client_uuid=uuid4(), kind="todo", milestone_id=first)
        task = await create_action(db, gid, request)
        assert await create_action(db, gid, request) == task
        duplicate = await create_action(db, gid, request.model_copy(update={"client_uuid":uuid4()}))
        assert duplicate.id == task.id
        assert await db.scalar(select(func.count()).select_from(Todo)) == 1
        await link(db, task.id, gid, "advances_goal")
        await db.commit()
        assert (await work(db, gid)).total_count == 2
        await todos.update(db, task.id, TodoUpdate(status="done"))
        assert (await work(db, gid)).progress_percent == 50
        topic = await create_action(db, gid, GoalActionIn(client_uuid=uuid4(), kind="study_topic", milestone_id=second, new_area_title="İngilizce"))
        await learning.patch_topic(db, topic.id, TopicPatch(status="done"))
        state = await work(db, gid)
        assert state.progress_percent == 100 and state.completed_count == 2
        assert all(step.completed for step in state.milestones)
        await todos.update(db, task.id, TodoUpdate(status="open"))
        assert (await work(db, gid)).progress_percent == 50
        objective = (await strategy.overview(db)).objectives[0]
        assert objective.strategic_progress_percent is None
        assert objective.work.progress_percent == 50
        assert await db.scalar(select(func.count()).select_from(StudyArea)) == 1
        assert await db.scalar(select(func.count()).select_from(Event).where(Event.verb == "link.created")) == 2


async def test_manual_steps_and_direct_work_are_visible_and_reproducible():
    async with SessionLocal() as db:
        gid, first, _ = await fixture(db)
        await service.update_goal_milestone(db, first, GoalMilestonePatch(completed=True))
        task = await todos.create(db, TodoIn(title="Ek çalışma"))
        await link(db, task.id, gid, "advances_goal")
        await db.commit()
        state = await work(db, gid)
        assert state.total_count == 3 and state.completed_count == 1 and state.progress_percent == 33
        await todos.update(db, task.id, TodoUpdate(status="done"))
        assert (await work(db, gid)).progress_percent == 67


async def test_conversion_rejects_foreign_milestone_and_invalid_area_without_partial_records():
    async with SessionLocal() as db:
        gid, first, _ = await fixture(db)
        other = await service.create_goal(db, GoalIn(title="Başka hedef"))
        with pytest.raises(HTTPException) as denied:
            await create_action(db, other.id, GoalActionIn(client_uuid=uuid4(), kind="todo", milestone_id=first))
        assert denied.value.status_code == 404
        await db.rollback()
        with pytest.raises(HTTPException) as invalid:
            await create_action(db, gid, GoalActionIn(client_uuid=uuid4(), kind="study_topic", milestone_id=first, area_id=uuid4()))
        assert invalid.value.status_code == 422
        await db.rollback()
        assert await db.scalar(select(func.count()).select_from(Todo)) == 0
        assert await db.scalar(select(func.count()).select_from(StudyTopic)) == 0


async def test_concurrent_conversion_uses_one_canonical_task():
    async with SessionLocal() as db:
        gid, first, _ = await fixture(db)
    async def convert():
        async with SessionLocal() as db:
            return await create_action(db, gid, GoalActionIn(client_uuid=uuid4(), kind="todo", milestone_id=first))
    a, b = await asyncio.gather(convert(), convert())
    assert a.id == b.id
    async with SessionLocal() as db:
        assert await db.scalar(select(func.count()).select_from(Todo)) == 1


async def test_partial_step_work_counts_once_and_new_steps_append_in_order():
    async with SessionLocal() as db:
        gid, first, second = await fixture(db)
        goal = await service.get_goal(db, gid)
        assert [m.id for m in goal.milestones] == [first, second]
        task = await create_action(db, gid, GoalActionIn(client_uuid=uuid4(), kind="todo", milestone_id=first))
        await create_action(db, gid, GoalActionIn(client_uuid=uuid4(), kind="study_topic", milestone_id=first, new_area_title="İngilizce"))
        await todos.update(db, task.id, TodoUpdate(status="done"))
        state = await work(db, gid)
        assert state.total_count == 2 and state.completed_count == 0 and state.progress_percent == 25
        assert state.milestones[0].progress_percent == 50
