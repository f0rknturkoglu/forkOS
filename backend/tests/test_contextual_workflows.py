"""Disposable database vertical checks for context, planning and existing ownership."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import func, select

from app.core.entity import create_entity
from app.core.events import log_event
from app.core.links import link
from app.core.models import Event
from app.core.time import local_today
from app.db import SessionLocal
from app.integrations.contextual import MAX_CONTEXT_BYTES, build_summary, inference_context
from app.integrations.contextual_schemas import AssistanceContext, ProjectContext, ReviewContext
from app.main import app
from app.modules.execution import service as execution
from app.modules.execution.planning import PlanningIn, prepare_planning
from app.modules.goal import studio
from app.modules.goal.studio_schemas import StudioSessionIn
from app.modules.project import service as projects
from app.modules.project.schemas import ProjectIn
from app.modules.review import service as reviews
from app.modules.review.schemas import ReviewIn
from app.modules.todo import service as todos
from app.modules.todo.models import PlanSlot
from app.modules.todo.schemas import PlanSlotIn, PlanSlotUpdate, TodoIn


async def task(db, title="Aynı mevcut görev", project_id=None):
    result = await todos.create(db, TodoIn(title=title, project_id=project_id))
    return result.id


async def test_planning_requires_exact_approval_preserves_time_and_replays_identity():
    async with SessionLocal() as db:
        identity = await task(db)
        before_day = local_today() + timedelta(days=1)
        next_day = before_day + timedelta(days=7)
        slot = await todos.schedule(
            db, PlanSlotIn(entity_id=identity, day=before_day, start_min=600, duration_min=45)
        )
        body = PlanningIn(client_uuid=uuid4(), todo_ids=[identity], day=next_day)
        prepared = await prepare_planning(db, body)
        replay = await prepare_planning(db, body)
        assert replay["plan_row_id"] == prepared["plan_row_id"]
        canonical = await db.get(PlanSlot, slot.id)
        assert canonical.day == before_day
        assert "Önce:" in prepared["steps"][0]["description"]
        with pytest.raises(execution.ExecutionPlanError, match="onaylanmamis"):
            await execution.execute(
                db, plan_row_id=prepared["plan_row_id"], revision=prepared["revision"]
            )
        with pytest.raises(execution.ExecutionPlanError):
            await execution.approve(db, plan_row_id=prepared["plan_row_id"], revision="wrong")
        await execution.approve(
            db, plan_row_id=prepared["plan_row_id"], revision=prepared["revision"]
        )
        finished, outcome = await execution.execute(
            db, plan_row_id=prepared["plan_row_id"], revision=prepared["revision"]
        )
        assert finished.state == outcome.final_status == "completed"
        await db.refresh(canonical)
        assert (canonical.day, canonical.start_min, canonical.duration_min) == (next_day, 600, 45)
        assert await db.scalar(select(func.count()).select_from(PlanSlot)) == 1
        with pytest.raises(HTTPException) as conflict:
            await prepare_planning(
                db, body.model_copy(update={"day": next_day + timedelta(days=1)})
            )
        assert conflict.value.status_code == 409


async def test_planning_change_after_preview_requires_revalidation():
    async with SessionLocal() as db:
        identity = await task(db)
        day = local_today() + timedelta(days=1)
        slot = await todos.schedule(db, PlanSlotIn(entity_id=identity, day=day, duration_min=30))
        prepared = await prepare_planning(
            db, PlanningIn(client_uuid=uuid4(), todo_ids=[identity], day=day + timedelta(days=1))
        )
        await todos.update_slot(db, slot.id, PlanSlotUpdate(duration_min=75))
        with pytest.raises(execution.ExecutionPlanError) as stale:
            await execution.approve(
                db, plan_row_id=prepared["plan_row_id"], revision=prepared["revision"]
            )
        assert stale.value.code == "PLAN_NEEDS_REVALIDATION"
        await db.refresh(await db.get(PlanSlot, slot.id))
        assert (await db.get(PlanSlot, slot.id)).day == day


async def test_planning_rejects_ambiguous_slots_and_browser_origin():
    async with SessionLocal() as db:
        identity = await task(db)
        day = local_today() + timedelta(days=1)
        for offset in (0, 1):
            await todos.schedule(
                db, PlanSlotIn(entity_id=identity, day=day + timedelta(days=offset))
            )
        body = PlanningIn(client_uuid=uuid4(), todo_ids=[identity], day=day)
        with pytest.raises(HTTPException) as ambiguous:
            await prepare_planning(db, body)
        assert ambiguous.value.status_code == 422
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as client:
        response = await client.post(
            "/api/execution/planning",
            json=body.model_dump(mode="json"),
            headers={"Origin": "https://example.invalid", "X-ForkOS-Goal-Studio": "1"},
        )
        assert response.status_code == 403


async def test_project_summary_is_scoped_read_only_without_inference(monkeypatch):
    from app.modules.goal import studio_transport

    async def forbidden(*args, **kwargs):
        raise AssertionError("No model request in deterministic summary")

    monkeypatch.setattr(studio_transport, "request", forbidden)
    async with SessionLocal() as db:
        chosen = await projects.create(
            db, ProjectIn(title="Seçili proje", next_action="Kayıtlı sonraki adım")
        )
        other = await projects.create(db, ProjectIn(title="DIŞARIDA_GİZLİ"))
        selected_id = UUID(chosen["id"]) if isinstance(chosen["id"], str) else chosen["id"]
        linked = await task(db, "Seçili projenin görevi", project_id=selected_id)
        await link(db, selected_id, linked, "contains")
        await log_event(
            db,
            verb="project.updated",
            entity_id=selected_id,
            entity_type="project",
            payload={"next_action": "Kayıtlı sonraki adım"},
        )
        await db.commit()
        count = await db.scalar(select(func.count()).select_from(Event))
        out = await build_summary(db, ProjectContext(kind="project", entity_id=selected_id))
        assert "DIŞARIDA_GİZLİ" not in out.model_dump_json()
        assert any(item.id == linked and item.schedulable for item in out.links)
        assert any("Kayıtlı sonraki adım" in item.text for item in out.facts)
        assert len(out.model_dump_json().encode()) <= MAX_CONTEXT_BYTES
        assert await db.scalar(select(func.count()).select_from(Event)) == count
        assert "memory_candidates" not in inference_context(out)
        assert str(other["id"]) not in out.model_dump_json()


async def test_saved_review_never_recomputed_and_live_period_has_task_links(monkeypatch):
    async with SessionLocal() as db:
        await task(db)
        start = local_today() - timedelta(days=local_today().weekday())
        live = await build_summary(
            db, ReviewContext(kind="review", period_kind="weekly", period_start=start)
        )
        assert any(item.schedulable for item in live.links)
        assert live.coverage.partial
        assert any("Tamamlanan görev:" in item.text for item in live.facts)
        saved = await reviews.create(
            db, ReviewIn(kind="weekly", period_start=start, note="O günkü beyan")
        )

        async def forbidden(*args, **kwargs):
            raise AssertionError("Historical snapshot must not be recomputed")

        monkeypatch.setattr(reviews, "preview", forbidden)
        historical = await build_summary(
            db,
            ReviewContext(
                kind="review", period_kind="weekly", period_start=start, review_id=saved.id
            ),
        )
        assert any(
            item.text == "O günkü beyan" and item.status == "candidate" for item in historical.facts
        )
        assert not any(item.schedulable for item in historical.links)
        assert any("yeniden hesaplanmadı" in warning for warning in historical.warnings)


async def test_typed_context_refuses_arbitrary_state_and_contextual_goal_mutation():
    with pytest.raises(ValidationError):
        TypeAdapter(AssistanceContext).validate_python(
            {"kind": "project", "entity_id": str(uuid4()), "tools": ["terminal"]}
        )
    with pytest.raises(ValidationError):
        StudioSessionIn(
            client_uuid=uuid4(),
            goal_id=uuid4(),
            context=ProjectContext(kind="project", entity_id=uuid4()),
        )
    async with SessionLocal() as db:
        project = await projects.create(db, ProjectIn(title="Bağlam"))
        row = await studio.start(
            db,
            StudioSessionIn(
                client_uuid=uuid4(), context=ProjectContext(kind="project", entity_id=project["id"])
            ),
        )
        assert row.context.entity_id == project["id"]
        row = await studio.get_session(db, row.id)
        with pytest.raises(HTTPException) as rejection:
            await studio.revise(db, row, None)
        assert rejection.value.status_code == 422


async def test_context_memory_filters_stale_sensitive_and_unsupported_sources():
    from app.integrations.judgment.memory_sources import read_memory_source
    from app.modules.semantic_memory.models import AgentSemanticCandidate
    from app.modules.semantic_memory.service import contextual_candidates

    async with SessionLocal() as db:
        entity = await create_entity(db, type="project", title="Kaynak")
        event = await log_event(
            db,
            verb="project.updated",
            entity_id=entity.id,
            entity_type="project",
            payload={"next_action": "Kısa sabah planı"},
        )
        await db.flush()
        source = await read_memory_source(db, "event:" + str(event.id))
        now = datetime.now(UTC)
        ids = []
        for sensitivity, revision, evidence_class in (
            ("normal", source.revision, "canonical_source"),
            ("private", source.revision, "canonical_source"),
            ("normal", "stale", "canonical_source"),
            ("normal", source.revision, "model_derived"),
        ):
            identity = uuid4()
            ids.append(identity)
            db.add(
                AgentSemanticCandidate(
                    id=identity,
                    candidate_key=identity.hex,
                    kind="preference",
                    statement="Sabah kısa bir plan tercih ederim",
                    scope="global",
                    primary_evidence_class=evidence_class,
                    suggested_destination="hot_memory",
                    evidence_refs=[{"ref": source.ref, "source_revision": revision}],
                    sensitivity=sensitivity,
                    observed_at=now,
                    first_seen_at=now,
                    last_seen_at=now,
                    revision="r",
                    status="needs_review",
                )
            )
        await db.commit()
        result = await contextual_candidates(
            db, entity_id="", refs={source.ref}, allow_global=False
        )
        assert [item.id for item in result] == [ids[0]]
        assert (await db.get(AgentSemanticCandidate, ids[0])).status == "needs_review"


async def test_goal_learning_career_contexts_keep_missing_measurements_and_canonical_links():
    from app.integrations.contextual_schemas import CareerContext, GoalContext, LearningContext
    from app.modules.goal import service as goals
    from app.modules.goal import strategy
    from app.modules.goal.schemas import GoalIn
    from app.modules.goal.strategy_schemas import KeyResultIn
    from app.modules.learning import service as learning
    from app.modules.learning.schemas import AreaIn, TopicIn
    from app.modules.opportunity import service as opportunities
    from app.modules.opportunity.schemas import OpportunityIn

    async with SessionLocal() as db:
        goal = await goals.create_goal(db, GoalIn(title="Ölçümü eksik hedef"))
        empty = await build_summary(db, GoalContext(kind="goal", entity_id=goal.id))
        assert any("bilinmiyor" in fact.text for fact in empty.facts)
        assert any("Ölçülebilir sonuç" in warning for warning in empty.warnings)
        kr = await strategy.save_kr(db, goal.id, KeyResultIn(title="YDS puanı", target_value=80))
        measured = await build_summary(db, GoalContext(kind="goal", entity_id=goal.id))
        assert any("YDS puanı: ölçüm bilinmiyor" in fact.text for fact in measured.facts)
        assert any(item.id == kr.id for item in measured.links)
        area = await learning.create_area(db, AreaIn(title="Yazılım"))
        topic = await learning.create_topic(db, TopicIn(title="Python", area_id=area["id"]))
        opportunity = await opportunities.create(db, OpportunityIn(title="Deneme ilanı"))
        await link(db, opportunity.id, UUID(str(topic["id"])), "supports")
        study = await build_summary(db, LearningContext(kind="learning", entity_id=topic["id"]))
        career = await build_summary(db, CareerContext(kind="career", entity_id=opportunity.id))
        assert any("ustalığı" in fact.text for fact in study.facts)
        assert any("başvuru kaydı yok" in fact.text for fact in career.facts)
        assert any(item.id == UUID(str(topic["id"])) for item in career.links)


async def test_memory_promotion_rechecks_source_revision_before_persistence():
    from app.integrations.judgment.memory_sources import read_memory_source
    from app.modules.semantic_memory.models import AgentSemanticCandidate
    from app.modules.semantic_memory.service import _check_promotion_sources

    async with SessionLocal() as db:
        entity = await create_entity(db, type="project", title="Kaynak")
        event = await log_event(
            db,
            verb="project.updated",
            entity_id=entity.id,
            entity_type="project",
            payload={"next_action": "Kısa plan"},
        )
        await db.commit()
        source = await read_memory_source(db, f"event:{event.id}")
        now = datetime.now(UTC)
        row = AgentSemanticCandidate(
            id=uuid4(),
            candidate_key=uuid4().hex,
            kind="preference",
            statement="Kısa plan",
            scope="global",
            primary_evidence_class="canonical_source",
            suggested_destination="hot_memory",
            sensitivity="normal",
            status="ready",
            observed_at=now,
            first_seen_at=now,
            last_seen_at=now,
            revision="r",
            evidence_refs=[{"ref": source.ref, "source_revision": "outdated-revision"}],
        )
        db.add(row)
        await db.commit()
        with pytest.raises(HTTPException) as stale:
            await _check_promotion_sources(db, row)
        assert stale.value.status_code == 409
        assert row.status == "stale"


async def test_contextual_model_turn_reuses_transport_and_cannot_create_proposal(monkeypatch):
    import json

    from app.modules.goal import studio_transport
    from app.modules.goal.models import Goal
    from app.modules.goal.studio_schemas import StudioTurnIn

    async def ready():
        pass

    calls = []

    async def request(method, path, **kwargs):
        calls.append((method, path, kwargs))
        if method == "POST":
            return {"run_id": "fixture_context_run"}
        return {
            "status": "completed",
            "output": json.dumps(
                {
                    "discussion": "Kaynak eksik; sonuç bilinmiyor.",
                    "proposal": {"operations": [{"type": "goal.create"}]},
                }
            ),
        }

    monkeypatch.setattr(studio_transport, "require_ready", ready)
    monkeypatch.setattr(
        studio_transport, "verified_profile", lambda: {"model": {"default": "fixture"}}
    )
    monkeypatch.setattr(studio_transport, "request", request)
    async with SessionLocal() as db:
        project = await projects.create(
            db, ProjectIn(title="Seçili proje", next_action="Kayıtlı adım")
        )
        session = await studio.start(
            db,
            StudioSessionIn(
                client_uuid=uuid4(), context=ProjectContext(kind="project", entity_id=project["id"])
            ),
        )
        message = StudioTurnIn(client_uuid=uuid4(), message="Sonraki adım ne?")
        await studio.turn(db, await studio.get_session(db, session.id), message)
        result = await studio.turn(db, await studio.get_session(db, session.id), message)
        assert result.state == "drafting" and result.revision is None
        assert await db.scalar(select(func.count()).select_from(Goal)) == 0
        posts = [call for call in calls if call[1] == "/v1/runs"]
        assert len(posts) == 1
        body = posts[0][2]["body"]
        assert body["provider"] == "custom"
        assert "No tools" in body["instructions"]
        assert "Kayıtlı adım" in body["input"]
        assert "memory_candidates" not in body["input"]
        assert result.context.entity_id == project["id"]
