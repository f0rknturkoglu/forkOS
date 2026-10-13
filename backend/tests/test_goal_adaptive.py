"""Adaptive closure regressions: only synthetic disposable PostgreSQL records."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.entity import create_entity
from app.core.time import local_datetime, local_today
from app.db import SessionLocal
from app.modules.calendar.models import ExternalEvent
from app.modules.goal import roadmap, service, strategy, studio
from app.modules.goal.context_snapshot import build
from app.modules.goal.models import Goal, KeyResult
from app.modules.goal.package_authoring import compile_draft
from app.modules.goal.package_planning import propose, snapshot, validate
from app.modules.goal.package_schemas import NodeData, PlanningConstraints
from app.modules.goal.schemas import GoalIn
from app.modules.goal.semantic_pipeline import input_payload
from app.modules.goal.studio_schemas import StudioDecisionIn, StudioProposal, StudioSessionIn
from app.modules.learning.models import StudyArea, StudyTopic
from app.modules.todo import service as todos
from app.modules.todo.models import PlanSlot, Todo
from app.modules.todo.schemas import TodoIn, TodoUpdate

CASES = json.loads((Path(__file__).parent / "fixtures/goals_adaptive.json").read_text())


async def review_and_apply(db, package):
    started = await studio.start(db, StudioSessionIn(client_uuid=uuid4(), mode="living"))
    row = await studio.get_session(db, started.id)
    review = await studio.revise(db, row, package)
    assert review.state == "approval_pending"
    assert await db.scalar(select(func.count()).select_from(Goal)) == 0
    applied = await studio.decide(
        db,
        row,
        StudioDecisionIn(
            decision="approve",
            revision_id=review.revision.id,
            fingerprint=review.revision.fingerprint,
        ),
    )
    assert applied.state == "applied"
    again = await studio.decide(
        db,
        row,
        StudioDecisionIn(
            decision="approve",
            revision_id=review.revision.id,
            fingerprint=review.revision.fingerprint,
        ),
    )
    assert again.revision.results == applied.revision.results
    return applied


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
async def test_adaptive_evaluation_materializes_canonical_work_without_padding(case):
    from app.modules.goal.package_authoring import user_capacity
    from app.modules.goal.package_constraints import availability, deadline, numeric_target

    async with SessionLocal() as db:
        authored = {
            "messages": [{"role": "user", "text": case["request"]}],
            "turns": {"fixture": {"at": datetime.now(UTC).isoformat(), "message": case["request"]}},
        }
        package = await compile_draft(
            db,
            case["package"],
            target_date=deadline(authored),
            confirmed_capacity=user_capacity(authored),
            confirmed_availability=availability(authored),
            expected_outcome_target=numeric_target(authored),
        )
        topics = sum(len(p.get("topics", [])) for p in case["package"].get("phases", []))
        result = await review_and_apply(db, package)
        gid = result.revision.results["goal"].id
        assert await db.scalar(select(func.count()).select_from(StudyArea)) == bool(topics)
        assert await db.scalar(select(func.count()).select_from(StudyTopic)) == topics
        assert await db.scalar(select(func.count()).select_from(KeyResult)) == bool(
            case["package"].get("outcome")
        )
        tasks = (await db.scalars(select(Todo))).all()
        expected_tasks = sum(len(p.get("tasks", [])) for p in case["package"].get("phases", []))
        expected_tasks += sum(
            len(p.get("tasks", []))
            for c in case["package"].get("children", [])
            for p in c.get("phases", [])
        )
        assert len(tasks) == expected_tasks
        slots = (await db.scalars(select(PlanSlot))).all()
        assert expected_tasks <= len(slots) <= 28
        assert len({slot.entity_id for slot in slots}) == expected_tasks
        assert (await build(db, gid))["outcome"]["percent"] is None
        if case["id"] == "minimal":
            assert local_today((await db.get(Goal, gid)).target_at) == local_today() + timedelta(
                days=1
            )
        if case["id"] == "academic":
            assert package.planning.daily_capacity_min == 120
            kr = await db.scalar(select(KeyResult))
            assert kr.target_value == 55 and kr.manual_value is None
        for task in tasks:
            await todos.update(db, task.id, TodoUpdate(status="done"))
        progress = (await roadmap.read(db, gid)).percent
        if case["id"] in {"long", "passport", "delivery", "academic", "move"}:
            assert progress != 100
        else:
            assert progress == 100
        print(
            json.dumps(
                {
                    "fixture_eval": case["id"],
                    "operations": len(package.operations),
                    "tasks": len(tasks),
                    "topics": topics,
                    "slots": len(slots),
                    "progress_after_tasks": progress,
                    "violations": [],
                    "apply": result.state,
                },
                ensure_ascii=False,
            )
        )


async def busy_event(db, *, start=None, end=None, all_day=True):
    entity = await create_entity(db, type="external_event", title="Sentetik takvim engeli")
    event = ExternalEvent(
        id=entity.id,
        provider="local",
        external_id=str(entity.id),
        starts_at=start or local_datetime(local_today(), 0),
        ends_at=end,
        all_day=all_day,
        synced_at=datetime.now(UTC),
    )
    db.add(event)
    await db.flush()
    return event


async def test_one_phase_without_learning_or_milestone_is_valid():
    async with SessionLocal() as db:
        package = await compile_draft(
            db,
            {
                "kind": "package",
                "title": "Pasaport başvurusunu tamamla",
                "phases": [{"title": "Başvuru", "tasks": [{"title": "Başvuruyu teslim et"}]}],
            },
        )
        types = [op.type for op in package.operations]
        assert "todo.create" in types
        assert not {"learning.area", "learning.topic", "milestone.create", "key_result.save"} & set(
            types
        )


async def test_all_day_blocks_automatic_day_level_plan_and_validation():
    async with SessionLocal() as db:
        await busy_event(db, end=local_datetime(local_today() + timedelta(days=1), 0))
        constraints = PlanningConstraints(daily_capacity_min=60, capacity_confirmed=True)
        blocks, _ = await propose(db, [("task", 60)], constraints)
        assert blocks[0]["data"]["day"] == (local_today() + timedelta(days=1)).isoformat()
        proposal = StudioProposal.model_validate(
            {
                "schema_version": 2,
                "rationale": "Sentetik",
                "planning": constraints.model_dump(),
                "operations": [
                    {"key": "task", "type": "todo.create", "data": {"title": "İş"}},
                    {
                        "key": "slot",
                        "type": "plan.schedule",
                        "task_ref": "task",
                        "data": {"day": local_today(), "duration_min": 30},
                    },
                ],
            }
        )
        with pytest.raises(ValueError, match="takvim|etkinlik"):
            validate(proposal, await snapshot(db, proposal))


async def test_detached_roadmap_work_stops_current_strategic_contribution():
    async with SessionLocal() as db:
        goal = await service.create_goal(db, GoalIn(title="Sentetik hedef"))
        task = await todos.create(db, TodoIn(title="Bağlı iş"))
        body = NodeData(title="İş", kind="record")
        node = await roadmap.save_node(db, goal.id, body, target_id=task.id)
        nid, gid, tid = node.id, goal.id, task.id
        await db.commit()
        goals = await service.list_goals(db)
        _, supports, _ = await strategy.alignment(db, goals, [], days=30, now=datetime.now(UTC))
        assert tid in supports[gid]
        await roadmap.save_node(db, gid, body, node_id=nid, detached=True)
        await db.commit()
        _, supports, _ = await strategy.alignment(db, goals, [], days=30, now=datetime.now(UTC))
        assert tid not in supports[gid]


@pytest.mark.parametrize(
    "mode", ["timed", "multi_day", "overnight", "unknown_end", "archived", "adjacent"]
)
async def test_calendar_availability_boundaries_are_shared(mode):
    from app.core.entity import archive_entity

    today = local_today()
    async with SessionLocal() as db:
        start, end, all_day = (
            local_datetime(today, 0),
            local_datetime(today + timedelta(days=1), 0),
            True,
        )
        if mode == "multi_day":
            end = local_datetime(today + timedelta(days=3), 0)
        if mode == "overnight":
            start, end, all_day = (
                local_datetime(today - timedelta(days=1), 23 * 60),
                local_datetime(today, 10 * 60),
                False,
            )
        if mode == "unknown_end":
            end, all_day = None, False
        if mode == "adjacent":
            end, all_day = local_datetime(today, 9 * 60), False
        event = await busy_event(db, start=start, end=end, all_day=all_day)
        if mode == "archived":
            await archive_entity(db, event.id)
        constraints = PlanningConstraints(
            daily_capacity_min=60,
            capacity_confirmed=True,
            **(
                {"available_start_min": 540, "available_end_min": 600}
                if mode in {"timed", "overnight", "adjacent"}
                else {}
            ),
        )
        blocks, warnings = await propose(db, [("task", 60)], constraints)
        offset = 3 if mode == "multi_day" else (0 if mode in {"archived", "adjacent"} else 1)
        assert blocks[0]["data"]["day"] == (today + timedelta(days=offset)).isoformat()
        proposal = StudioProposal.model_validate(
            {
                "schema_version": 2,
                "rationale": "Fixture",
                "planning": constraints.model_dump(),
                "operations": [
                    {"type": "todo.create", "key": "task", "data": {"title": "İş"}},
                    *blocks,
                ],
            }
        )
        validate(proposal, await snapshot(db, proposal))
        if mode == "unknown_end":
            assert any("Bitişi bilinmeyen" in warning for warning in warnings)


async def test_user_override_requires_explicit_preview_and_calendar_stale_rolls_back():
    from app.modules.goal.studio_models import GoalStudioSession

    async with SessionLocal() as db:
        await busy_event(db, end=local_datetime(local_today() + timedelta(days=1), 0))
        package = await compile_draft(db, CASES[2]["package"])
        slot = next(op for op in package.operations if op.type == "plan.schedule")
        slot.data.day = local_today()
        started = await studio.start(db, StudioSessionIn(client_uuid=uuid4(), mode="living"))
        row = await db.get(GoalStudioSession, started.id)
        with pytest.raises(ValueError, match="takvim"):
            await studio.revise(db, row, package)
        assert await db.scalar(select(func.count()).select_from(Todo)) == 0
        slot.data.calendar_override = True
        review = await studio.revise(db, row, package)
        assert any("kullanıcı tarafından" in w for w in review.revision.proposal.warnings)
        await busy_event(db, start=local_datetime(local_today(), 540), end=None, all_day=False)
        await db.commit()
        result = await studio.decide(
            db,
            row,
            StudioDecisionIn(
                decision="approve",
                revision_id=review.revision.id,
                fingerprint=review.revision.fingerprint,
            ),
        )
        assert result.state == "stale"
        assert await db.scalar(select(func.count()).select_from(Todo)) == 0


async def test_infeasible_calendar_preserves_duration_as_explicit_remaining_work():
    async with SessionLocal() as db:
        await busy_event(db, end=local_datetime(local_today() + timedelta(days=14), 0))
        blocks, warnings = await propose(db, [("task", 120)], PlanningConstraints())
        assert blocks == [] and any("120 dakikalık" in warning for warning in warnings)


async def test_existing_project_learning_work_and_resource_reuse_has_verified_provenance():
    from app.core.models import Entity
    from app.modules.learning import service as learning
    from app.modules.learning.schemas import AreaIn, ResourceIn, TopicIn
    from app.modules.project import service as projects
    from app.modules.project.schemas import ProjectIn

    async with SessionLocal() as db:
        area = await learning.create_area(db, AreaIn(title="Gelişim"))
        topic = await learning.create_topic(
            db, TopicIn(title="Sürüm doğrulama", area_id=area["id"])
        )
        resource = await learning.create_resource(
            db, topic["id"], ResourceIn(title="Yerel kontrol listesi", kind="doc")
        )
        project = await projects.create(db, ProjectIn(title="forkOS"))
        task = await todos.create(db, TodoIn(title="Kabul testleri", project_id=project["id"]))
        tid = task.id
        await todos.update(db, tid, TodoUpdate(status="done"))
        records = [area["id"], topic["id"], tid, project["id"], resource["id"]]
        candidates = []
        for index, identity in enumerate(records):
            e = await db.get(Entity, identity, populate_existing=True)
            candidates.append(
                {
                    "token": f"candidate_{index}",
                    "id": str(identity),
                    "title": e.title,
                    "type": e.type,
                    "updated_at": e.updated_at.isoformat(),
                }
            )
        value = {
            "kind": "package",
            "title": "Teslim hedefi",
            "reuse_area": "candidate_0",
            "projects": ["candidate_3"],
            "phases": [
                {
                    "title": "Doğrulama",
                    "topics": [
                        {
                            "title": "Sürüm doğrulama",
                            "reuse": "candidate_1",
                            "resources": ["candidate_4"],
                        }
                    ],
                    "tasks": [
                        {"title": "Kabul testleri", "reuse": "candidate_2", "topic_index": 0}
                    ],
                }
            ],
        }
        package = await compile_draft(db, value, candidates=candidates)
        assert not {"todo.create", "learning.area", "learning.topic", "learning.resource"} & {
            op.type for op in package.operations
        }
        result = await review_and_apply(db, package)
        assert await db.scalar(select(func.count()).select_from(Todo)) == 1
        assert await db.scalar(select(func.count()).select_from(StudyArea)) == 1
        assert (await db.get(Todo, tid)).status == "done"
        assert (await roadmap.read(db, result.revision.results["goal"].id)).percent is not None
        from app.modules.goal.context_schemas import GoalContextSnapshot

        gid = result.revision.results["goal"].id
        snapshot = GoalContextSnapshot.model_validate(await build(db, gid))
        assert snapshot.projects[0].id == project["id"]
        assert snapshot.projects[0].percent == 100
        from httpx import ASGITransport, AsyncClient

        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/goals/{gid}/workspace")
        assert response.status_code == 200
        assert "groups" not in response.json()["projects"][0]
        print(
            json.dumps(
                {
                    "fixture_eval": "reuse",
                    "operations": len(package.operations),
                    "new_tasks": 0,
                    "new_topics": 0,
                    "canonical_project_progress": 100,
                    "violations": [],
                    "apply": result.state,
                }
            )
        )


@pytest.mark.no_database
def test_explicit_relative_dates_and_targets_are_anchored_without_model_facts():
    from app.modules.goal.package_authoring import PackageDraft
    from app.modules.goal.package_constraints import deadline, numeric_target, requested_learning

    at = "2026-01-31T20:59:00+00:00"
    data = {"turns": {"x": {"at": at, "message": "Üç ay içinde evimi taşımak istiyorum."}}}
    assert deadline(data).isoformat() == "2026-04-30"
    data["turns"]["x"]["message"] = "Yarın belgeyi teslim edeceğim."
    assert deadline(data).isoformat() == "2026-02-01"
    data["turns"]["x"]["message"] = "Önümüzdeki beş yılda kariyerimi geliştir."
    assert deadline(data).isoformat() == "2031-01-31"
    assert requested_learning(
        {"messages": [{"role": "user", "text": "Öğrenme ve deneme çalışmaları olsun"}]}
    )
    assert not requested_learning(
        {"messages": [{"role": "user", "text": "Öğrenme programı gerekmiyor"}]}
    )
    assert not requested_learning(
        {"messages": [{"role": "assistant", "text": "Öğrenme planı ekle"}]}
    )
    assert (
        numeric_target(
            {
                "messages": [
                    {"role": "assistant", "text": "60 puan"},
                    {"role": "user", "text": "En az 55 puan almak istiyorum"},
                ]
            }
        )
        == 55
    )
    with pytest.raises(ValueError, match="başlangıç puanı"):
        PackageDraft.model_validate(
            {
                "kind": "package",
                "title": "Hedef",
                "outcome": {"title": "Puan", "target_value": 55, "baseline_value": 40},
            }
        )


async def test_empty_duplicate_and_mismatched_numeric_target_are_rejected():
    async with SessionLocal() as db:
        with pytest.raises(ValueError, match="öğrenme çalışması"):
            await compile_draft(db, CASES[-1]["package"], expected_learning=True)
        for value in (
            {"kind": "package", "title": "Boş", "phases": []},
            {"kind": "package", "title": "Boş", "phases": [{"title": "A"}, {"title": "A"}]},
        ):
            with pytest.raises(ValueError):
                await compile_draft(db, value)
        value = CASES[0]["package"]
        with pytest.raises(ValueError, match="sayısal hedef"):
            await compile_draft(db, value, expected_outcome_target=60)
        assert await db.scalar(select(func.count()).select_from(Goal)) == 0


@pytest.mark.parametrize("change", ["canonical", "structure"])
async def test_detach_approval_is_stale_after_relevant_target_or_structure_change(change):
    async with SessionLocal() as db:
        goal = await service.create_goal(db, GoalIn(title="A"))
        task = await todos.create(db, TodoIn(title="İş"))
        gid, tid = goal.id, task.id
        body = NodeData(title="İş", kind="record")
        node = await roadmap.save_node(db, gid, body, target_id=tid)
        nid = node.id
        await db.commit()
        proposal = StudioProposal.model_validate(
            {
                "schema_version": 2,
                "rationale": "Ayırma",
                "operations": [
                    {
                        "type": "roadmap.update",
                        "key": "detach",
                        "target_id": nid,
                        "detached": True,
                        "data": body.model_dump(),
                    }
                ],
            }
        )
        session = await studio.start(
            db, StudioSessionIn(client_uuid=uuid4(), mode="living", goal_id=gid)
        )
        row = await studio.get_session(db, session.id)
        review = await studio.revise(db, row, proposal)
        if change == "canonical":
            await todos.update(db, tid, TodoUpdate(status="done"))
        else:
            await roadmap.save_node(db, gid, NodeData(title="Yeni aşama", kind="phase"))
            await db.commit()
        result = await studio.decide(
            db,
            row,
            StudioDecisionIn(
                decision="approve",
                revision_id=review.revision.id,
                fingerprint=review.revision.fingerprint,
            ),
        )
        assert result.state == "stale"
        from app.modules.goal.roadmap_models import GoalRoadmapNode

        assert (await db.get(GoalRoadmapNode, nid, populate_existing=True)).detached is False


@pytest.mark.parametrize(
    "mode", ["manual", "manual_after", "same_goal", "other_goal", "subtree", "reattach"]
)
async def test_detachment_retains_independent_links_shared_work_and_history(mode):
    from app.core.events import log_event
    from app.core.links import link
    from app.core.models import Event, Link

    async with SessionLocal() as db:
        goal = await service.create_goal(db, GoalIn(title="A"))
        other = await service.create_goal(db, GoalIn(title="B"))
        task = await todos.create(db, TodoIn(title="Paylaşılan iş"))
        gid, bid, tid = goal.id, other.id, task.id
        if mode == "manual":
            await link(db, tid, gid, "advances_goal")
            await log_event(
                db,
                verb="link.created",
                entity_id=tid,
                payload={"to_id": str(gid), "relation": "advances_goal"},
            )
            await db.commit()
        parent = await roadmap.save_node(db, gid, NodeData(title="Aşama", kind="phase"))
        pid = parent.id
        body = NodeData(title="İş", kind="record")
        node = await roadmap.save_node(db, gid, body, parent_id=pid, target_id=tid)
        nid = node.id
        if mode == "manual_after":
            await log_event(
                db,
                verb="link.created",
                entity_id=tid,
                payload={"to_id": str(gid), "relation": "advances_goal"},
            )
        if mode == "same_goal":
            await roadmap.save_node(db, gid, body, target_id=tid)
        if mode == "other_goal":
            await roadmap.save_node(db, bid, body, target_id=tid)
        await db.commit()
        await todos.update(db, tid, TodoUpdate(status="done"))
        historical = await db.scalar(select(func.count()).select_from(Event))
        from app.modules.review.models import Review

        review_entity = await create_entity(
            db, type="review", title="Kabul edilmiş tarihsel review"
        )
        saved_stats = {"goal_id": str(gid), "historical_percent": 100}
        review_record = Review(
            id=review_entity.id,
            kind="weekly",
            period_start=local_today(),
            period_end=local_today(),
            stats=saved_stats,
        )
        db.add(review_record)
        await db.commit()
        review_id = review_record.id
        if mode == "subtree":
            await roadmap.save_node(
                db, gid, NodeData(title="Aşama", kind="phase"), node_id=pid, detached=True
            )
        else:
            await roadmap.save_node(db, gid, body, node_id=nid, parent_id=pid, detached=True)
        await db.commit()
        graph = await roadmap.read(db, gid)
        context = await build(db, gid)
        goals = await service.list_goals(db)
        _, supports, _ = await strategy.alignment(db, goals, [], days=30, now=datetime.now(UTC))
        retained = mode in {"manual", "manual_after", "same_goal"}
        assert (tid in supports[gid]) == retained
        assert (str(tid) in {t["id"] for t in context["todos"]}) == retained
        assert any(n.target_id == tid for n in graph.nodes) == retained
        if mode == "other_goal":
            assert tid in supports[bid] and (await roadmap.read(db, bid)).percent == 100
        if mode == "reattach":
            await roadmap.save_node(db, gid, body, node_id=nid, parent_id=pid, detached=False)
            await db.commit()
            assert (await roadmap.read(db, gid)).percent == 100
        assert (await db.get(Todo, tid)).status == "done"
        assert (await db.get(Review, review_id, populate_existing=True)).stats == saved_stats
        assert (
            await db.scalar(
                select(func.count())
                .select_from(Link)
                .where(Link.from_id == tid, Link.to_id == gid, Link.relation == "advances_goal")
            )
            == 1
        )
        assert await db.scalar(select(func.count()).select_from(Event)) >= historical


async def test_project_detach_preserves_canonical_progress_and_public_context():
    from app.core.progress import project_progress
    from app.modules.goal.context_schemas import GoalContextSnapshot
    from app.modules.project import service as projects
    from app.modules.project.schemas import ProjectIn

    async with SessionLocal() as db:
        project = await projects.create(db, ProjectIn(title="Kanonik proje"))
        task = await todos.create(db, TodoIn(title="Proje işi", project_id=project["id"]))
        await todos.update(db, task.id, TodoUpdate(status="done"))
        goal = await service.create_goal(db, GoalIn(title="Teslim"))
        gid, pid = goal.id, project["id"]
        body = NodeData(title="Proje", kind="record")
        node = await roadmap.save_node(db, gid, body, target_id=pid)
        nid = node.id
        await db.commit()
        before = await project_progress(db, [pid])
        assert GoalContextSnapshot.model_validate(await build(db, gid)).projects[0].percent == 100
        await roadmap.save_node(db, gid, body, node_id=nid, detached=True)
        await db.commit()
        assert GoalContextSnapshot.model_validate(await build(db, gid)).projects == []
        assert (await roadmap.read(db, gid)).percent is None
        _, supports, _ = await strategy.alignment(
            db, await service.list_goals(db), [], days=30, now=datetime.now(UTC)
        )
        assert supports[gid] == set()
        assert await project_progress(db, [pid]) == before


@pytest.mark.parametrize("semantic", [False, True])
async def test_adaptive_user_deadline_is_sent_to_model_and_retry_payload_is_stable(
    monkeypatch, semantic
):
    from app.config import settings

    monkeypatch.setattr(settings, "goal_studio_semantic_enabled", semantic)
    from app.modules.goal import studio_transport as transport
    from app.modules.goal.studio_schemas import StudioTurnIn

    calls = []

    async def ready(db, **kwargs):
        return {"id": "fixture-policy", "provider": "custom", "model": "fixture-model"}

    async def connected():
        return None

    async def request(method, path, **kwargs):
        if path == "/v1/runs":
            calls.append(kwargs["body"])
            return {"run_id": "run_fixture"}
        return {"status": "running"}

    monkeypatch.setattr(transport, "require_inference", ready)
    monkeypatch.setattr(transport, "require_ready", connected)
    monkeypatch.setattr(transport, "request", request)
    async with SessionLocal() as db:
        session = await studio.start(db, StudioSessionIn(mode="living", client_uuid=uuid4()))
        row = await studio.get_session(db, session.id)
        body = StudioTurnIn(
            client_uuid=uuid4(), message="Altı hafta içinde sürümü teslim et. Hedef oluştur."
        )
        await studio.turn(db, row, body)
        expected = (local_today() + timedelta(weeks=6)).isoformat()
        constraints = (
            input_payload(calls[0]["input"])["explicit_constraints"]
            if semantic
            else json.JSONDecoder().raw_decode(calls[0]["input"].split("USER CONSTRAINTS: ", 1)[1])[
                0
            ]
        )
        assert constraints["target_date"] == expected
        assert "allowed_dates" in calls[0]["input"]
        assert json.dumps([expected]) in calls[0]["input"]
        await studio.turn(db, await studio.get_session(db, session.id), body)
        assert len(calls) == 1
