"""Synthetic PostgreSQL acceptance tests
fixture authoring is labelled, not live inference."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from app.core.links import link
from app.db import SessionLocal
from app.modules.calendar import service as calendar
from app.modules.goal import roadmap, studio
from app.modules.goal.context_snapshot import build
from app.modules.goal.models import Goal, GoalMilestone
from app.modules.goal.package_authoring import compile_draft
from app.modules.goal.roadmap_models import GoalRoadmapNode
from app.modules.goal.studio_models import GoalStudioSession
from app.modules.goal.studio_schemas import StudioDecisionIn, StudioSessionIn
from app.modules.learning.models import StudyArea, StudyTopic
from app.modules.todo import service as todos
from app.modules.todo.models import PlanSlot, Todo
from app.modules.todo.schemas import TodoUpdate


def draft():
    return {
        "kind": "package",
        "title": "YDS 55+",
        "description": "Günde iki saat hazırlık",
        "learning_area": "YDS Hazırlık",
        "planning": {"daily_capacity_min": 120, "capacity_confirmed": True},
        "outcome": {"title": "YDS puanı", "target_value": 55, "unit": "puan"},
        "missing_information": ["Sınav tarihi ve mevcut puan bilinmiyor"],
        "phases": [
            {
                "title": "Temeller",
                "milestone": "Temelleri öğren",
                "topics": [{"title": "Kelime", "resource_needs": ["Kelime alıştırmaları"]}],
                "tasks": [{"title": "İlk denemeyi çöz", "duration_min": 60}],
            },
            {
                "title": "Uygulama",
                "milestone": "Düzenli pratik",
                "depends_on": [0],
                "topics": [{"title": "Okuma"}],
                "tasks": [{"title": "Okuma alıştırması yap", "duration_min": 60, "topic_index": 0}],
            },
            {
                "title": "Sonuç",
                "milestone": "Sınav sonucunu doğrula",
                "completion_gate": True,
                "depends_on": [1],
            },
        ],
    }


async def preview(db, value=None, goal_id=None):
    body = StudioSessionIn(client_uuid=uuid4(), mode="living", goal_id=goal_id)
    started = await studio.start(db, body)
    row = await db.get(GoalStudioSession, started.id)
    proposal = await compile_draft(db, value or draft(), goal_id=goal_id)
    return await studio.revise(db, row, proposal)


async def approve(db, state):
    row = await studio.get_session(db, state.id)
    return await studio.decide(
        db,
        row,
        StudioDecisionIn(
            revision_id=state.revision.id,
            fingerprint=state.revision.fingerprint,
            decision="approve",
        ),
    )


async def test_package_materializes_real_modules_atomically_and_progress_is_separate():
    async with SessionLocal() as db:
        state = await preview(db)
        assert state.revision.proposal.schema_version == 2
        assert len(state.revision.proposal.operations) > 20
        assert await db.scalar(select(func.count()).select_from(Todo)) == 0
        applied = await approve(db, state)
        assert applied.state == "applied"
        gid = applied.revision.results["goal"].id
        assert (await db.get(Goal, gid)).target_at is None
        assert await db.scalar(select(func.count()).select_from(StudyArea)) == 1
        assert await db.scalar(select(func.count()).select_from(StudyTopic)) == 2
        assert await db.scalar(select(func.count()).select_from(Todo)) == 2
        assert await db.scalar(select(func.count()).select_from(PlanSlot)) == 2
        events = await calendar.events(
            db, datetime.now(UTC) - timedelta(days=1), datetime.now(UTC) + timedelta(days=14)
        )
        assert len(events) == 2 and all(e["all_day"] for e in events)
        first = await roadmap.read(db, gid)
        assert first.percent == 0 and len(first.nodes) > 3
        task = applied.revision.results["task_0_0"].id
        await todos.update(db, task, TodoUpdate(status="done"))
        assert (
            await roadmap.read(db, gid)
        ).percent == 17  # first phase: 1 of 2 requirements, equal 3 phases
        await todos.update(db, task, TodoUpdate(status="open"))
        assert (await db.get(Todo, task)).completed_at is None
        assert (await roadmap.read(db, gid)).percent == 0
        ctx = await build(db, gid)
        assert ctx["outcome"]["percent"] is None
        assert len(ctx["planned_slots"]) == 2 and ctx["todos"][0]["status"] in {"open", "done"}
        again = await approve(db, state)
        assert again.revision.results == applied.revision.results
        assert await db.scalar(select(func.count()).select_from(Todo)) == 2


async def test_two_concurrent_approvals_return_one_durable_result():
    async with SessionLocal() as db:
        state = await preview(db)

    async def run():
        async with SessionLocal() as db:
            return await approve(db, state)

    a, b = await asyncio.gather(run(), run())
    assert a.state == b.state == "applied" and a.revision.results == b.revision.results
    async with SessionLocal() as db:
        assert await db.scalar(select(func.count()).select_from(Goal)) == 1


async def test_full_apply_failure_after_slot_rolls_back_all_operational_records(monkeypatch):
    async with SessionLocal() as db:
        state = await preview(db)
        original = todos.schedule

        async def broken(*args, **kwargs):
            await original(*args, **kwargs)
            raise RuntimeError("Synthetic failure after plan insertion")

        monkeypatch.setattr(todos, "schedule", broken)
        result = await approve(db, state)
        assert result.state == "failed"
        for model in (Goal, GoalMilestone, GoalRoadmapNode, Todo, StudyArea, StudyTopic, PlanSlot):
            assert await db.scalar(select(func.count()).select_from(model)) == 0


async def test_stale_planning_rejects_without_partial_writes():
    async with SessionLocal() as db:
        state = await preview(db)
        from app.modules.todo.schemas import PlanSlotIn, TodoIn

        external = await todos.create(db, TodoIn(title="Mevcut çalışma"))
        block = next(op for op in state.revision.proposal.operations if op.type == "plan.schedule")
        await todos.schedule(
            db, PlanSlotIn(entity_id=external.id, day=block.data.day, duration_min=120)
        )
        result = await approve(db, state)
        assert result.state == "stale"
        assert await db.scalar(select(func.count()).select_from(Goal)) == 0
        assert await db.scalar(select(func.count()).select_from(Todo)) == 1


async def test_reused_task_is_not_duplicated_and_canonical_change_is_stale():
    async with SessionLocal() as db:
        from app.modules.todo.schemas import TodoIn

        task = await todos.create(db, TodoIn(title="İlk denemeyi çöz"))
        value = draft()
        value["phases"][0]["tasks"][0]["reuse"] = "candidate_0"
        proposal = await compile_draft(
            db,
            value,
            candidates=[
                {"token": "candidate_0", "id": str(task.id), "type": "todo", "title": task.title}
            ],
        )
        started = await studio.start(db, StudioSessionIn(client_uuid=uuid4(), mode="living"))
        state = await studio.revise(db, await studio.get_session(db, started.id), proposal)
        await todos.update(db, task.id, TodoUpdate(status="done"))
        result = await approve(db, state)
        assert (
            result.state == "stale" and await db.scalar(select(func.count()).select_from(Goal)) == 0
        )


async def test_five_year_scope_does_not_finish_with_first_fortnight_tasks():
    async with SessionLocal() as db:
        value = {
            "kind": "package",
            "title": "Beş yıllık gelişim",
            "long_term": True,
            "children": [
                {
                    "title": "Temel yetkinlikler",
                    "period": "1. yıl",
                    "phases": [
                        {
                            "title": "Başlangıç",
                            "milestone": "İlk yetkinlik",
                            "tasks": [{"title": "İlk çalışmayı tamamla"}],
                        }
                    ],
                },
                {
                    "title": "Araştırma üretimi",
                    "period": "2–5. yıllar",
                    "phases": [{"title": "Araştırma", "milestone": "Araştırma üretimini tamamla"}],
                },
            ],
        }
        result = await approve(db, await preview(db, value))
        gid = result.revision.results["goal"].id
        tid = result.revision.results["c0_task_0_0"].id
        await todos.update(db, tid, TodoUpdate(status="done"))
        assert (await roadmap.read(db, gid)).percent == 50
        assert (await roadmap.read(db, result.revision.results["child_0"].id)).percent == 100
        assert await db.scalar(select(func.count()).select_from(PlanSlot)) == 1


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d["phases"][0].update(depends_on=[1]),
        lambda d: d.update(approved=True),
        lambda d: d["phases"][0]["tasks"][0].update(id=str(uuid4())),
        lambda d: d["phases"][0]["tasks"].append({"title": "İlk denemeyi çöz"}),
    ],
)
async def test_authoring_rejects_cycles_ids_unknown_fields_and_duplicates(mutate):
    async with SessionLocal() as db:
        value = draft()
        mutate(value)
        with pytest.raises((ValueError, ValidationError)):
            await compile_draft(db, value)


async def test_missing_candidate_cannot_be_hallucinated():
    async with SessionLocal() as db:
        value = draft()
        value["phases"][0]["topics"][0]["resources"] = ["candidate_99"]
        with pytest.raises(ValueError, match="doğrulanamıyor"):
            await compile_draft(db, value)


async def test_duplicate_paths_and_archived_target_do_not_create_phantom_progress():
    from app.core.entity import archive_entity
    from app.modules.goal.package_schemas import NodeData

    async with SessionLocal() as db:
        result = await approve(db, await preview(db))
        gid = result.revision.results["goal"].id
        tid = result.revision.results["task_0_0"].id
        await roadmap.save_node(db, gid, NodeData(title="Aynı görev", kind="record"), target_id=tid)
        await link(db, tid, gid, "advances_goal")
        await db.commit()
        graph = await roadmap.read(db, gid)
        assert graph.total_requirements == 4  # task/topic phase 1, topic phase 2, final gate
        await archive_entity(db, tid)
        await db.commit()
        graph = await roadmap.read(db, gid)
        assert graph.percent is None and any(n.missing for n in graph.nodes)


async def test_agent_additions_are_previewed_then_applied_once_with_existing_measurements_intact():
    from app.modules.goal import strategy
    from app.modules.goal.models import KeyResult
    from app.modules.goal.strategy_schemas import KeyResultIn

    async with SessionLocal() as db:
        first = await approve(db, await preview(db))
        gid = first.revision.results["goal"].id
        kid = first.revision.results["outcome"].id
        await strategy.save_kr(
            db,
            gid,
            KeyResultIn(
                title="YDS puanı", baseline_value=0, target_value=55, unit="puan", manual_value=32
            ),
            kid,
        )
        value = {
            "kind": "package",
            "title": "YDS 55+",
            "phases": [
                {
                    "title": "Ek deneme",
                    "milestone": "Ek pratik",
                    "tasks": [{"title": "Birinci ek deneme"}, {"title": "İkinci ek deneme"}],
                }
            ],
        }
        state = await preview(db, value, goal_id=gid)
        assert await db.scalar(select(func.count()).select_from(Todo)) == 2
        assert (await db.get(KeyResult, kid)).manual_value == 32
        approved = await approve(db, state)
        assert approved.state == "applied"
        assert await db.scalar(select(func.count()).select_from(Todo)) == 4
        assert await db.scalar(select(func.count()).select_from(PlanSlot)) == 4
        assert (await db.get(KeyResult, kid)).manual_value == 32
        assert (await approve(db, state)).revision.results == approved.revision.results


async def test_project_task_topic_multiple_paths_count_one_requirement():
    from app.core.progress import project_progress
    from app.modules.learning import service as learning
    from app.modules.learning.schemas import TopicPatch
    from app.modules.project import service as projects
    from app.modules.project.schemas import ProjectIn

    async with SessionLocal() as db:
        project = await projects.create(db, ProjectIn(title="YDS Projesi"))
        pid = project["id"]
        value = {
            "kind": "package",
            "title": "YDS hazırlık",
            "projects": ["candidate_0"],
            "phases": [
                {
                    "title": "Okuma",
                    "milestone": "Oku",
                    "topics": [{"title": "Okuma bilgisi"}],
                    "tasks": [{"title": "Okuma yap", "topic_index": 0}],
                }
            ],
        }
        from app.modules.goal import service
        from app.modules.goal.schemas import GoalIn

        existing_goal = await service.create_goal(db, GoalIn(title="YDS hazırlık"))
        started = await studio.start(
            db, StudioSessionIn(client_uuid=uuid4(), mode="living", goal_id=existing_goal.id)
        )
        proposal = await compile_draft(
            db,
            value,
            goal_id=existing_goal.id,
            candidates=[
                {"id": str(pid), "type": "project", "title": "YDS Projesi", "token": "candidate_0"}
            ],
        )
        state = await studio.revise(db, await studio.get_session(db, started.id), proposal)
        result = await approve(db, state)
        gid = existing_goal.id
        tid = result.revision.results["task_0_0"].id
        topic = result.revision.results["topic_0_0"].id
        graph = await roadmap.read(db, gid)
        assert graph.total_requirements == 1
        await todos.update(db, tid, TodoUpdate(status="done"))
        assert (await project_progress(db, [pid]))[pid]["percent"] == 100
        assert (
            await roadmap.read(db, gid)
        ).percent == 50  # one requirement with practice and learning evidence
        await learning.patch_topic(db, topic, TopicPatch(status="done"))
        assert (await roadmap.read(db, gid)).percent == 100
        await todos.update(db, tid, TodoUpdate(status="open"))
        assert (await project_progress(db, [pid]))[pid]["percent"] == 0


async def test_schedule_revision_moves_one_slot_and_preserves_deadline():
    from app.core.time import local_today

    async with SessionLocal() as db:
        result = await approve(db, await preview(db))
        gid = result.revision.results["goal"].id
        tid = result.revision.results["task_0_0"].id
        prior = await db.scalar(select(PlanSlot).where(PlanSlot.entity_id == tid))
        newday = local_today() + timedelta(days=3)
        value = {
            "kind": "package",
            "title": "YDS 55+",
            "schedule_changes": [
                {
                    "task": "candidate_0",
                    "day": newday.isoformat(),
                    "from_day": prior.day.isoformat(),
                    "duration_min": 60,
                }
            ],
            "planning": {"daily_capacity_min": 120, "capacity_confirmed": True},
        }
        proposal = await compile_draft(
            db,
            value,
            goal_id=gid,
            candidates=[
                {
                    "id": str(tid),
                    "type": "todo",
                    "title": "İlk denemeyi çöz",
                    "token": "candidate_0",
                }
            ],
            confirmed_capacity=120,
        )
        started = await studio.start(
            db, StudioSessionIn(client_uuid=uuid4(), mode="living", goal_id=gid)
        )
        state = await studio.revise(db, await studio.get_session(db, started.id), proposal)
        result = await approve(db, state)
        assert result.state == "applied"
        assert await db.scalar(select(func.count()).select_from(PlanSlot)) == 2
        assert (await db.scalar(select(PlanSlot).where(PlanSlot.entity_id == tid))).day == newday
        assert (await db.get(Todo, tid)).due_at is None


async def test_goal_graph_cycle_and_detachment_are_safe():
    from app.modules.goal import service
    from app.modules.goal.package_schemas import NodeData
    from app.modules.goal.schemas import GoalIn

    async with SessionLocal() as db:
        a = await service.create_goal(db, GoalIn(title="Bir"))
        b = await service.create_goal(db, GoalIn(title="İki"))
        n = await roadmap.save_node(
            db, a.id, NodeData(title="İki", kind="child_goal"), target_id=b.id
        )
        node_id = n.id
        await db.commit()
        with pytest.raises(ValueError, match="döngü"):
            await roadmap.save_node(
                db, b.id, NodeData(title="Bir", kind="child_goal"), target_id=a.id
            )
        await db.rollback()
        await roadmap.save_node(
            db, a.id, NodeData(title="İki", kind="child_goal"), node_id=node_id, detached=True
        )
        await db.commit()
        graph = await roadmap.read(db, a.id)
        assert not graph.legacy and graph.nodes == [] and graph.percent is None


async def test_public_workspace_contract_and_user_capacity_are_verified():
    from app.modules.goal.context_schemas import GoalContextSnapshot
    from app.modules.goal.package_authoring import user_capacity

    assert (
        user_capacity({"messages": [{"role": "user", "text": "Günde iki saat çalışabilirim."}]})
        == 120
    )
    assert (
        user_capacity({"messages": [{"role": "assistant", "text": "Günde iki saat varsayıyorum."}]})
        is None
    )
    async with SessionLocal() as db:
        result = await approve(db, await preview(db))
        data = GoalContextSnapshot.model_validate(
            await build(db, result.revision.results["goal"].id)
        )
        assert data.schema_version == 2 and data.outcome.percent is None


async def test_shared_task_is_counted_once_across_child_goals_and_reads_are_stable():
    from app.core.models import Event
    from app.modules.goal import service
    from app.modules.goal.package_schemas import NodeData
    from app.modules.goal.schemas import GoalIn
    from app.modules.todo.schemas import TodoIn

    async with SessionLocal() as db:
        parent = await service.create_goal(db, GoalIn(title="Ana hedef"))
        a = await service.create_goal(db, GoalIn(title="Birinci dönem", parent_goal_id=parent.id))
        b = await service.create_goal(db, GoalIn(title="İkinci dönem", parent_goal_id=parent.id))
        task = await todos.create(db, TodoIn(title="Ortak çalışma"))
        other = await todos.create(db, TodoIn(title="Bağımsız çalışma"))
        for gid, tid in ((a.id, task.id), (b.id, task.id), (b.id, other.id)):
            await roadmap.save_node(
                db, gid, NodeData(title="Çalışma", kind="record"), target_id=tid
            )
        await db.commit()
        await todos.update(db, task.id, TodoUpdate(status="done"))
        event_count = await db.scalar(select(func.count()).select_from(Event))
        first = await roadmap.read(db, parent.id)
        assert first.percent == 50 and first.total_requirements == 2
        assert first.scope_count == 2 and first.completed_scope_count == 1
        assert (await roadmap.read(db, parent.id)).model_dump() == first.model_dump()
        assert await db.scalar(select(func.count()).select_from(Event)) == event_count


async def test_missing_target_and_recurring_template_are_unknown_occurrence_is_evidence():
    from app.modules.goal import service
    from app.modules.goal.package_schemas import NodeData
    from app.modules.goal.schemas import GoalIn
    from app.modules.todo.schemas import TodoIn

    async with SessionLocal() as db:
        goal = await service.create_goal(db, GoalIn(title="Rutin kapsamı"))
        template = await todos.create(db, TodoIn(title="Günlük çalışma", recur="daily"))
        node = await roadmap.save_node(
            db, goal.id, NodeData(title="Rutin", kind="record"), target_id=template.id
        )
        await db.commit()
        assert (await roadmap.read(db, goal.id)).percent is None
        occurrence = await todos.create(db, TodoIn(title="Bugünkü çalışma"))
        (await db.get(Todo, occurrence.id)).recur_origin_id = template.id
        occurrence_goal = await service.create_goal(db, GoalIn(title="Bugünkü kapsam"))
        node = await roadmap.save_node(
            db,
            occurrence_goal.id,
            NodeData(title="Bugünkü çalışma", kind="record"),
            target_id=occurrence.id,
        )
        await db.commit()
        await todos.update(db, occurrence.id, TodoUpdate(status="done"))
        assert (await roadmap.read(db, occurrence_goal.id)).percent == 100
        node.target_id = None  # mirrors FK SET NULL after canonical deletion
        await db.commit()
        graph = await roadmap.read(db, occurrence_goal.id)
        assert graph.percent is None and graph.nodes[0].missing


async def test_task_edit_is_reviewed_scoped_and_preserves_completion_and_measurements():
    from app.core.models import Entity

    async with SessionLocal() as db:
        initial = await approve(db, await preview(db))
        gid = initial.revision.results["goal"].id
        tid = initial.revision.results["task_0_0"].id
        entity = await db.get(Entity, tid)
        candidates = [
            {
                "token": "candidate_0",
                "id": str(tid),
                "title": entity.title,
                "type": "todo",
                "updated_at": entity.updated_at.isoformat(),
            }
        ]
        package = {
            "kind": "package",
            "title": "YDS 55+",
            "task_changes": [
                {
                    "task": "candidate_0",
                    "title": "Eksikleri kaydet",
                    "priority": 1,
                    "due_date": None,
                }
            ],
        }
        proposal = await compile_draft(
            db, package, goal_id=gid, candidates=candidates, task_snapshot=[{"id": str(tid)}]
        )
        started = await studio.start(
            db, StudioSessionIn(client_uuid=uuid4(), mode="living", goal_id=gid)
        )
        state = await studio.revise(db, await db.get(GoalStudioSession, started.id), proposal)
        assert (await db.get(Entity, tid)).title != "Eksikleri kaydet"
        done = await approve(db, state)
        assert done.state == "applied" and (await db.get(Entity, tid)).title == "Eksikleri kaydet"
        assert (await db.get(Todo, tid)).status == "open"
        current_stamp = (await db.get(Entity, tid, populate_existing=True)).updated_at.isoformat()
        with pytest.raises(ValueError, match="yalnız bu hedef"):
            await compile_draft(
                db,
                package,
                goal_id=gid,
                candidates=[
                    {
                        **candidates[0],
                        "title": "Eksikleri kaydet",
                        "updated_at": current_stamp,
                    }
                ],
                task_snapshot=[],
            )


async def test_attach_existing_phase_and_node_edits_do_not_recreate_stage():
    from app.core.models import Entity

    async with SessionLocal() as db:
        initial = await approve(db, await preview(db))
        gid = initial.revision.results["goal"].id
        ctx = await build(db, gid)
        phase = next(n for n in ctx["roadmap"]["nodes"] if n["kind"] == "phase")
        package = {
            "kind": "package",
            "title": "YDS 55+",
            "phases": [
                {
                    "title": phase["title"],
                    "attach_node_index": phase["index"],
                    "milestone": "Yeni deneme",
                    "tasks": [{"title": "İkinci denemeyi çöz"}],
                }
            ],
            "node_changes": [{"node_index": phase["index"], "title": "Güncel temel aşama"}],
        }
        proposal = await compile_draft(
            db, package, goal_id=gid, roadmap_snapshot=ctx["roadmap"]["nodes"]
        )
        assert not any(
            op.type == "roadmap.create" and op.data.kind == "phase" for op in proposal.operations
        )
        started = await studio.start(
            db, StudioSessionIn(client_uuid=uuid4(), mode="living", goal_id=gid)
        )
        state = await studio.revise(db, await db.get(GoalStudioSession, started.id), proposal)
        assert await db.scalar(select(func.count()).select_from(Todo)) == 2
        assert (await approve(db, state)).state == "applied"
        assert await db.scalar(select(func.count()).select_from(Todo)) == 3
        assert (await db.get(Entity, phase["id"])).title == "Güncel temel aşama"
        assert (
            await db.scalar(
                select(func.count())
                .select_from(GoalRoadmapNode)
                .where(GoalRoadmapNode.kind == "phase")
            )
            == 3
        )


async def test_planning_splits_full_duration_and_preserves_latest_confirmed_capacity():
    from app.modules.goal.package_planning import propose
    from app.modules.goal.package_schemas import PlanningConstraints

    async with SessionLocal() as db:
        slots, _ = await propose(
            db,
            [("work", 180)],
            PlanningConstraints(daily_capacity_min=120, capacity_confirmed=True),
        )
        assert [s["data"]["duration_min"] for s in slots] == [120, 60]
        assert all(s["data"].get("start_min") is None for s in slots)
        proposal = await compile_draft(
            db,
            draft(),
            planning_default={"daily_capacity_min": 90, "capacity_confirmed": True},
            confirmed_capacity=60,
        )
        assert proposal.planning.daily_capacity_min == 60 and proposal.planning.capacity_confirmed
        proposal = await compile_draft(
            db, draft(), planning_default={"daily_capacity_min": 90, "capacity_confirmed": True}
        )
        assert proposal.planning.daily_capacity_min == 90


@pytest.mark.no_database
def test_only_user_dates_establish_deadlines_and_task_patch_cannot_complete_work():
    from datetime import date

    from app.modules.goal.package_constraints import dates
    from app.modules.goal.package_schemas import TaskPatch

    allowed = dates(
        {
            "turns": {
                "a": {
                    "message": "15 Ekim 2026 ve 2026-11-01. Önümüzdeki beş yıl.",
                    "at": "2026-10-13T10:00:00+03:00",
                }
            },
            "messages": [{"role": "assistant", "text": "2026-12-01"}],
        }
    )
    assert allowed == {date(2026, 10, 15), date(2026, 11, 1), date(2031, 10, 13)}
    for invalid in ({}, {"priority": None}, {"title": None}, {"status": "done"}):
        with pytest.raises(ValidationError):
            TaskPatch.model_validate(invalid)
    assert TaskPatch.model_validate({"due_at": None}).model_dump() == {"due_at": None}


@pytest.mark.no_database
def test_explicit_availability_does_not_accept_assistant_or_unavailable_hours():
    from app.modules.goal.package_constraints import availability

    assert availability(
        {"messages": [{"role": "user", "text": "Sadece hafta içi 18:00-20:00 çalışabilirim."}]}
    ) == {"weekdays": [0, 1, 2, 3, 4], "available_start_min": 1080, "available_end_min": 1200}
    assert (
        availability({"messages": [{"role": "assistant", "text": "18:00-20:00 uygunsun."}]}) == {}
    )
    assert (
        availability({"messages": [{"role": "user", "text": "18:00-20:00 müsait değilim."}]}) == {}
    )
    assert availability({"messages": [{"role": "user", "text": "Hafta sonları çalışamam."}]}) == {
        "weekdays": [0, 1, 2, 3, 4]
    }


async def test_existing_phase_cannot_be_recreated_by_revision_and_scoped_area_is_candidate():
    from app.modules.goal.package_discovery import include_scope

    async with SessionLocal() as db:
        applied = await approve(db, await preview(db))
        gid = applied.revision.results["goal"].id
        ctx = await build(db, gid)
        scoped = await include_scope(db, [], ctx)
        assert any(c["type"] == "study_area" for c in scoped)
        assert len(scoped) <= 30 and len({c["id"] for c in scoped}) == len(scoped)
        with pytest.raises(ValueError, match="Mevcut aşama yeniden oluşturulamaz"):
            await compile_draft(
                db,
                draft(),
                goal_id=gid,
                roadmap_snapshot=ctx["roadmap"]["nodes"],
                candidates=scoped,
            )
        assert await db.scalar(select(func.count()).select_from(Todo)) == 2


async def test_parent_task_is_container_for_shared_goal_and_project_evidence():
    from app.core.progress import project_progress
    from app.modules.goal import service
    from app.modules.goal.package_schemas import NodeData
    from app.modules.goal.schemas import GoalIn
    from app.modules.project import service as projects
    from app.modules.project.schemas import ProjectIn
    from app.modules.todo.schemas import TodoIn

    async with SessionLocal() as db:
        goal = await service.create_goal(db, GoalIn(title="Alt işler"))
        project = await projects.create(db, ProjectIn(title="Ortak iş"))
        parent = await todos.create(db, TodoIn(title="Kapsayıcı", project_id=project["id"]))
        child = await todos.create(
            db, TodoIn(title="Asıl iş", parent_id=parent.id, project_id=project["id"])
        )
        for task in (parent, child):
            await roadmap.save_node(
                db, goal.id, NodeData(title=task.title, kind="record"), target_id=task.id
            )
        await db.commit()
        await todos.update(db, child.id, TodoUpdate(status="done"))
        graph = await roadmap.read(db, goal.id)
        assert graph.percent == 100 and graph.total_requirements == 1
        progress = await project_progress(db, [project["id"]])
        assert progress[project["id"]]["percent"] == 100 and progress[project["id"]]["total"] == 1


async def test_goal_cycle_cannot_hide_in_generic_record_node():
    from app.modules.goal import service
    from app.modules.goal.package_schemas import NodeData
    from app.modules.goal.schemas import GoalIn

    async with SessionLocal() as db:
        a = await service.create_goal(db, GoalIn(title="Bir"))
        b = await service.create_goal(db, GoalIn(title="İki"))
        with pytest.raises(ValueError, match="child_goal"):
            await roadmap.save_node(db, a.id, NodeData(title="İki", kind="record"), target_id=b.id)


async def test_confirmed_hours_plan_around_actual_local_calendar_and_preserve_full_duration():
    from app.core.entity import create_entity
    from app.core.time import local_datetime, local_today
    from app.modules.calendar.models import ExternalEvent
    from app.modules.goal.package_planning import propose, snapshot, validate
    from app.modules.goal.package_schemas import PlanningConstraints
    from app.modules.goal.studio_schemas import StudioProposal
    from app.modules.todo.schemas import TodoIn

    async with SessionLocal() as db:
        task = await todos.create(db, TodoIn(title="Uzun çalışma"))
        day = local_today()
        entity = await create_entity(db, type="external_event", title="Sentetik yerel etkinlik")
        db.add(
            ExternalEvent(
                id=entity.id,
                provider="google",
                external_id="test-event",
                starts_at=local_datetime(day, 18 * 60),
                ends_at=local_datetime(day, 19 * 60),
                all_day=False,
                synced_at=datetime.now(UTC),
            )
        )
        await db.commit()
        constraints = PlanningConstraints(
            daily_capacity_min=120,
            capacity_confirmed=True,
            available_start_min=1080,
            available_end_min=1200,
        )
        slots, warnings = await propose(db, [(str(task.id), 180)], constraints)
        assert [(s["data"]["duration_min"], s["data"]["start_min"]) for s in slots] == [
            (60, 1140),
            (120, 1080),
        ]
        assert not warnings
        proposal = StudioProposal(
            schema_version=2, rationale="Çalışma", planning=constraints, operations=slots
        )
        evidence = await snapshot(db, proposal)
        validate(proposal, evidence)
        proposal.operations[0].data.start_min = 1080
        with pytest.raises(ValueError, match="etkinlikle çakışıyor"):
            validate(proposal, evidence)


@pytest.mark.no_database
def test_authoring_examples_are_closed_regular_and_long_term_packages():
    import json

    from app.modules.goal.package_authoring import PackageDraft, instructions

    for long_term in (False, True):
        example, _ = json.JSONDecoder().raw_decode(
            instructions(long_term=long_term).split("Example: ")[1]
        )
        value = PackageDraft.model_validate(example["proposal"])
        assert value.long_term == long_term
        assert len(value.children) == (3 if long_term else 0)


@pytest.mark.no_database
def test_bare_semantic_package_is_living_only_and_still_requires_closed_validation():
    import json

    from app.modules.goal.package_authoring import PackageDraft

    value = draft()
    with pytest.raises(ValueError, match="discussion/proposal"):
        studio.public_reply(json.dumps(value))
    parsed = studio.public_reply(json.dumps(value), allow_package=True)
    assert PackageDraft.model_validate(parsed["proposal"]).title == "YDS 55+"
    with pytest.raises(ValidationError):
        PackageDraft.model_validate(
            studio.public_reply(
                json.dumps({**value, "operations": [{"sql": "ignored"}]}), allow_package=True
            )["proposal"]
        )


async def test_partial_detachment_does_not_reappear_through_legacy_links_or_agent_context():
    from app.core.models import Entity
    from app.modules.goal.package_schemas import NodeData

    async with SessionLocal() as db:
        initial = await approve(db, await preview(db))
        gid = initial.revision.results["goal"].id
        tid = initial.revision.results["task_0_0"].id
        node_id = initial.revision.results["taskn_0_0"].id
        node = await db.get(GoalRoadmapNode, node_id)
        entity = await db.get(Entity, node_id)
        body = NodeData(title=entity.title, kind=node.kind, position=node.position)
        await roadmap.save_node(
            db, gid, body, node_id=node_id, parent_id=node.parent_id, detached=True
        )
        await db.commit()
        graph = await roadmap.read(db, gid)
        assert tid not in {n.target_id for n in graph.nodes}
        ctx = await build(db, gid)
        assert str(tid) not in {t["id"] for t in ctx["todos"]}
        assert await db.get(Todo, tid) is not None


@pytest.mark.no_database
def test_requested_task_count_is_user_authored_and_new_creation_is_near_term_only():
    from app.modules.goal.package_constraints import requested_tasks

    assert (
        requested_tasks({"messages": [{"role": "user", "text": "İki yeni pratik görev ekle."}]})
        == 2
    )
    assert (
        requested_tasks(
            {"messages": [{"role": "assistant", "text": "İki yeni pratik görev ekle."}]}
        )
        is None
    )


async def test_revision_cannot_clone_owned_task_or_ignore_requested_task_count():
    async with SessionLocal() as db:
        initial = await approve(db, await preview(db))
        gid = initial.revision.results["goal"].id
        ctx = await build(db, gid)
        phase = next(n for n in ctx["roadmap"]["nodes"] if n["kind"] == "phase")
        value = {
            "kind": "package",
            "title": "YDS 55+",
            "phases": [
                {
                    "title": phase["title"],
                    "attach_node_index": phase["index"],
                    "milestone": "Yeni pratikler",
                    "tasks": [{"title": "Yeni pratik"}],
                }
            ],
        }
        with pytest.raises(ValueError, match="tam 2 yeni görev"):
            await compile_draft(
                db,
                value,
                goal_id=str(gid),
                roadmap_snapshot=ctx["roadmap"]["nodes"],
                task_snapshot=ctx["todos"],
                expected_new_tasks=2,
            )
        value["phases"][0]["tasks"][0]["title"] = ctx["todos"][0]["title"]
        with pytest.raises(ValueError, match="Mevcut görev yeniden oluşturulamaz"):
            await compile_draft(
                db,
                value,
                goal_id=str(gid),
                roadmap_snapshot=ctx["roadmap"]["nodes"],
                task_snapshot=ctx["todos"],
            )
        assert await db.scalar(select(func.count()).select_from(Todo)) == 2


@pytest.mark.no_database
def test_duplicate_json_fields_cannot_silently_drop_operations():
    output = '{"discussion":"Yeni işler","proposal":{"kind":"package","phases":[{"tasks":[{"title":"İş"}]}],"phases":[]}}'
    with pytest.raises(studio.DuplicateJSONField, match="phases"):
        studio.public_reply(output, allow_package=True)


async def test_project_milestone_weighting_and_archived_criteria_are_shared():
    from app.core.entity import archive_entity
    from app.core.progress import project_progress
    from app.modules.goal import service
    from app.modules.goal.package_schemas import NodeData
    from app.modules.goal.schemas import GoalIn
    from app.modules.project import service as projects
    from app.modules.project.schemas import MilestoneIn, ProjectIn
    from app.modules.todo.schemas import TodoIn

    async with SessionLocal() as db:
        project = await projects.create(db, ProjectIn(title="İki aşamalı proje"))
        pid = project["id"]
        a = await projects.add_milestone(db, pid, MilestoneIn(title="İlk aşama"))
        aid = a.id
        b = await projects.add_milestone(db, pid, MilestoneIn(title="İkinci aşama"))
        bid = b.id
        first = await todos.create(db, TodoIn(title="İlk iş", project_id=pid, milestone_id=aid))
        for i in range(3):
            await todos.create(
                db, TodoIn(title=f"İkinci aşama işi {i}", project_id=pid, milestone_id=bid)
            )
        goal = await service.create_goal(db, GoalIn(title="Projenin hedefi"))
        await roadmap.save_node(db, goal.id, NodeData(title="Proje", kind="record"), target_id=pid)
        await db.commit()
        await todos.update(db, first.id, TodoUpdate(status="done"))
        assert (await project_progress(db, [pid]))[pid]["percent"] == 50
        graph = await roadmap.read(db, goal.id)
        assert graph.percent == 50 and graph.nodes[0].canonical_percent == 50
        await archive_entity(db, aid)
        await db.commit()
        assert (await project_progress(db, [pid]))[pid]["percent"] is None
        assert (await roadmap.read(db, goal.id)).percent is None


async def test_nested_goal_context_contains_canonical_descendant_work_without_reintroducing_detached_work():
    from app.modules.goal import service
    from app.modules.goal.package_schemas import NodeData
    from app.modules.goal.schemas import GoalIn
    from app.modules.todo.schemas import TodoIn

    async with SessionLocal() as db:
        root = await service.create_goal(db, GoalIn(title="Ana hedef"))
        mid = await service.create_goal(db, GoalIn(title="Dönem", parent_goal_id=root.id))
        leaf = await service.create_goal(db, GoalIn(title="Alt kapsam", parent_goal_id=mid.id))
        task = await todos.create(db, TodoIn(title="Derindeki iş"))
        node = await roadmap.save_node(
            db, leaf.id, NodeData(title="İş", kind="record"), target_id=task.id
        )
        nid = node.id
        await db.commit()
        assert str(task.id) in {t["id"] for t in (await build(db, root.id))["todos"]}
        await roadmap.save_node(
            db, leaf.id, NodeData(title="İş", kind="record"), node_id=nid, detached=True
        )
        await db.commit()
        assert str(task.id) not in {t["id"] for t in (await build(db, root.id))["todos"]}


async def test_schedule_move_preserves_existing_user_clock_duration_and_note():
    from app.core.models import Entity
    from app.core.time import local_today
    from app.modules.goal import service
    from app.modules.goal.schemas import GoalIn
    from app.modules.todo.schemas import PlanSlotIn, TodoIn

    async with SessionLocal() as db:
        goal = await service.create_goal(db, GoalIn(title="Planı taşınacak hedef"))
        task = await todos.create(db, TodoIn(title="Planlı çalışma"))
        slot = await todos.schedule(
            db,
            PlanSlotIn(
                entity_id=task.id,
                day=local_today(),
                start_min=540,
                duration_min=60,
                note="Kullanıcının çalışma notu",
            ),
        )
        entity = await db.get(Entity, task.id)
        candidates = [
            {"token": "candidate_0", "id": str(task.id), "type": "todo", "title": entity.title}
        ]
        value = {
            "kind": "package",
            "title": "Hedef",
            "schedule_changes": [
                {"task": "candidate_0", "day": (local_today() + timedelta(days=1)).isoformat()}
            ],
        }
        proposal = await compile_draft(
            db, value, goal_id=goal.id, candidates=candidates, confirmed_capacity=120
        )
        operation = next(o for o in proposal.operations if o.type == "plan.schedule")
        assert operation.replace_slot_id == slot.id
        assert (
            operation.data.start_min == 540
            and operation.data.duration_min == 60
            and operation.data.note == "Kullanıcının çalışma notu"
        )
        from app.modules.goal.package_planning import snapshot, validate

        validate(proposal, await snapshot(db, proposal))
