"""Independent layer and lifecycle regressions; live model evaluation is separate."""

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from app.db import SessionLocal
from app.modules.goal import semantic_pipeline as flow
from app.modules.goal import semantic_planning as meaning
from app.modules.goal import studio
from app.modules.goal import studio_transport as transport
from app.modules.goal.models import Goal
from app.modules.goal.semantic_pipeline import input_payload
from app.modules.goal.studio_inference import ReplyError, task_for
from app.modules.goal.studio_schemas import StudioDecisionIn, StudioSessionIn, StudioTurnIn
from app.modules.todo.models import PlanSlot, Todo
from tests.test_goal_studio_providers import api as api
from tests.test_goal_studio_providers import choose
from tests.test_goal_studio_providers import profile as profile

REQ = {
    "objective": "Beceri edinme",
    "needs": {"learning": "required", "resources": "required"},
    "dimensions": ["uygulama"],
    "unknowns": ["başlangıç seviyesi"],
    "justification": "Beceri ve pratik gerektirir",
}
DRAFT = {
    "kind": "semantic_plan",
    "title": "Beceri edinme",
    "topics": [{"title": "Temel kavram", "resource_needs": ["Uygun giriş alıştırması bul"]}],
    "tasks": [{"title": "İlk örneği uygula", "topic": "Temel kavram", "duration_min": 20}],
}
ACCEPT = {"verdict": "accept", "covered": [0], "issues": []}


def data(message="Becerimi geliştirmek istiyorum.", **extra):
    identity = str(uuid4())
    return {
        "mode": "living",
        "messages": [{"role": "user", "text": message}],
        "turns": {identity: {"message": message, "at": datetime.now(UTC).isoformat()}},
        "active_turn": identity,
        "candidates": [],
        **extra,
    }


@pytest.mark.no_database
@pytest.mark.parametrize(
    "message,expected",
    [
        ("İki görev ekleyebilir miyiz?", "author"),
        ("Bu konuyu da plana alsak?", "author"),
        ("Çalışmaları biraz azaltabilir misin?", "author"),
        ("Yarına taşıyalım.", "author"),
        ("Yeni bir aşama oluşturalım mı?", "author"),
        ("Planı güncellememiz lazım.", "author"),
        ("İlk aşamayı çıkarsak nasıl olur?", "coach"),
        ("Planı değiştirmemiz gerekir mi?", "coach"),
        ("Sence bir görev eklemeli miyim?", "coach"),
        ("Görev ekleme, sadece değerlendir.", "coach"),
        ("Planımı nasıl geliştirebilirim?", "coach"),
        ("Can you add two tasks?", "author"),
        ("Should I add two tasks?", "coach"),
        ("Hangi işleri değiştirmemiz daha iyi?", "coach"),
        ("Planı revize etsek?", "route"),
        ("Neredeyiz?", "coach"),
        ("Bu hafta neye odaklanmalıyım?", "coach"),
        ("Bu işi silmeden nasıl düzenleyebilirim?", "coach"),
    ],
)
def test_natural_requests_advice_negation_and_unknown_routing(message, expected):
    assert task_for({"mode": "living", "goal_id": "selected"}, message) == expected


@pytest.mark.no_database
def test_inferred_learning_cannot_override_explicit_exclusions_capacity_or_numeric_target():
    d = data(
        "En az 55 puan istiyorum. Learning oluşturma. Projeye bağlama. Takvime şimdilik yerleştirme. Günde en fazla 30 dakika."
    )
    constraints = meaning.literal_constraints(d)
    assert set(constraints["excluded"]) == {"learning", "project", "schedule"}
    assert constraints["numeric_target"] == "55" and constraints["capacity_min"] == 30
    req = meaning.accepted_requirements(REQ, constraints)
    assert req.needs.learning == req.needs.project == req.needs.schedule == "not_applicable"
    assert req.needs.outcome == "required" and req.needs.periods == "not_applicable"
    assert req.justification == REQ["justification"]


@pytest.mark.no_database
def test_independent_topic_and_unambiguous_authored_phase_association():
    draft = meaning.SemanticDraft.model_validate(
        {**DRAFT, "tasks": [{**DRAFT["tasks"][0], "phase": "Uygulama"}]}
    )
    projected = draft.package()
    assert projected["phases"][0]["title"] == "Uygulama"
    assert projected["phases"][0]["tasks"][0]["topic_index"] == 0
    assert projected["phases"][0]["topics"][0]["resource_needs"]
    assert not projected["outcome"]
    meaning.quality_gate(
        projected, meaning.Requirements.model_validate(REQ), meaning.literal_constraints(data()), []
    )


@pytest.mark.no_database
@pytest.mark.parametrize(
    "change,code",
    [
        ({"topics": []}, "invalid_candidate_reference"),
        ({"topics": [{"title": "Temel kavram"}]}, "missing_resources"),
        (
            {"outcome": {"title": "Uydurma sayı", "target_value": 7, "unit": "adet"}},
            "unsupported_claim",
        ),
        ({"projects": ["candidate_19"]}, "invalid_candidate_reference"),
        (
            {"topics": [{"title": "Temel kavram", "resource_needs": ["https://fake.invalid"]}]},
            "unsupported_claim",
        ),
        (
            {"topics": [{"title": "Temel kavram", "resource_needs": ["HTTPS://fake.invalid"]}]},
            "unsupported_claim",
        ),
    ],
)
def test_semantic_and_reference_failures_are_explainable(change, code):
    with pytest.raises(ReplyError) as err:
        projected = meaning.SemanticDraft.model_validate({**DRAFT, **change}).package()
        meaning.quality_gate(
            projected,
            meaning.Requirements.model_validate(REQ),
            meaning.literal_constraints(data()),
            [],
        )
    assert err.value.code == code


@pytest.mark.no_database
def test_missing_learning_is_rejected_independently_of_json_or_task_validity():
    package = meaning.SemanticDraft(
        kind="semantic_plan",
        title="Beceri",
        tasks=[meaning.SemanticTask(title="İlk örneği uygula")],
    ).package()
    with pytest.raises(ReplyError, match="öğrenme") as err:
        meaning.quality_gate(
            package,
            meaning.Requirements.model_validate(REQ),
            meaning.literal_constraints(data()),
            [],
        )
    assert err.value.code == "missing_required_learning"


@pytest.mark.no_database
def test_wrong_resource_type_and_explicit_outcome_are_checked_before_compilation():
    d = meaning.SemanticDraft.model_validate(
        {**DRAFT, "topics": [{"title": "Temel kavram", "sources": ["candidate_1"]}]}
    )
    c = meaning.literal_constraints(data("En az 55 puan almak istiyorum."))
    with pytest.raises(ReplyError) as missing:
        meaning.quality_gate(
            d.package(),
            meaning.Requirements.model_validate(REQ),
            c,
            [{"token": "candidate_1", "type": "todo"}],
        )
    assert missing.value.code == "missing_explicit_outcome"
    d.outcome = meaning.Outcome(title="Puan", target_value=55, unit="puan")
    with pytest.raises(ReplyError) as wrong:
        meaning.quality_gate(
            d.package(),
            meaning.Requirements.model_validate(REQ),
            c,
            [{"token": "candidate_1", "type": "todo"}],
        )
    assert wrong.value.code == "invalid_candidate_reference"


@pytest.mark.no_database
def test_long_term_requirements_and_future_task_rejection_use_existing_v2_rules():
    d = data("Beş yılda kariyerimi geliştirmek istiyorum.")
    req = meaning.accepted_requirements(REQ, meaning.literal_constraints(d))
    assert req.needs.periods == "required"
    projected = meaning.SemanticDraft(
        kind="semantic_plan",
        title="Kariyer",
        periods=[
            meaning.Period(
                title="Başlangıç",
                label="İlk dönem",
                tasks=[meaning.SemanticTask(title="Mevcut çalışmaları incele")],
            ),
            meaning.Period(title="İleri kapsam", label="Sonraki dönem"),
        ],
    ).package()
    assert len(projected["children"]) == 2
    assert not projected["children"][1]["phases"]


@pytest.mark.no_database
def test_minimal_explicit_task_skips_understanding_without_inventing_a_task():
    p = flow.start(data("Belgeyi teslim et."), "author")
    assert p["stage"] == "draft" and "package" not in p
    assert p["requirements"]["needs"]["learning"] == "not_applicable"
    assert (
        flow.start(data("Dil becerimi geliştirmek istiyorum."), "author")["stage"] == "requirements"
    )


@pytest.mark.no_database
def test_selected_contract_has_balanced_task_object_and_only_applicable_fields():
    d = data()
    p = flow.start(d, "author")
    p.update(stage="draft", requirements=meaning.Requirements.model_validate(REQ).model_dump())
    instruction, payload = flow.input_for(d, {"message": d["messages"][0]["text"], "pipeline": p})
    example = json.JSONDecoder().raw_decode(instruction.split("Biçim örneği: ")[1])[0]
    meaning.SemanticDraft.model_validate(example).package()
    assert example["tasks"][0]["topic"] == example["topics"][0]["title"]
    assert "periods:[" not in instruction and "projects?:candidate_tokens[]" not in instruction
    assert payload["verified_candidates"]["sources"] == []


@pytest.mark.no_database
@pytest.mark.parametrize(
    "raw",
    [
        '{"objective":"eksik"',
        '{"objective":"A","objective":"B"}',
        '{"raw_sql":"DROP TABLE"}',
        '```json\n{"tool_calls":[]}\n```',
    ],
)
def test_stage_parser_does_not_repair_truncated_duplicate_or_unsafe_content(raw):
    from app.modules.goal.studio import unique_pairs

    with pytest.raises(ValueError):
        flow.accept(data(), {"pipeline": flow.start(data(), "author")}, raw, unique_pairs)


@pytest.mark.no_database
def test_quality_review_must_be_independent_consistent_and_cover_every_dimension():
    d = data()
    p = flow.start(d, "author")
    p.update(
        stage="review",
        requirements=REQ,
        package=meaning.SemanticDraft.model_validate(DRAFT).package(),
    )
    with pytest.raises(ReplyError):
        flow.accept(
            d,
            {"pipeline": p},
            json.dumps({"verdict": "accept", "covered": [], "issues": []}),
            studio.unique_pairs,
        )
    with pytest.raises(ValueError):
        meaning.QualityReview(
            verdict="accept", issues=[meaning.Issue(code="unsupported_claim", detail="Yanlış")]
        )
    with pytest.raises(ReplyError) as err:
        flow.accept(
            d,
            {"pipeline": p},
            json.dumps(
                {
                    "verdict": "reject",
                    "covered": [],
                    "issues": [
                        {
                            "code": "unrelated_administrative_scope",
                            "detail": "İstenen süreçten farklı",
                            "excerpt": "İlk örneği uygula",
                        }
                    ],
                }
            ),
            studio.unique_pairs,
        )
    assert err.value.code == "unrelated_administrative_scope"


CATALOG = [
    {"ref": "node_1", "kind": "node", "title": "Pratik", "node_kind": "phase", "index": 0},
    {
        "ref": "work_1",
        "kind": "work",
        "title": "Açık iş",
        "status": "open",
        "candidate": "candidate_1",
    },
    {"ref": "node_2", "kind": "node", "title": "Açık iş", "node_kind": "record", "index": 1},
    {
        "ref": "topic_1",
        "kind": "topic",
        "title": "Kavram",
        "status": "active",
        "candidate": "candidate_2",
    },
    {
        "ref": "slot_1",
        "kind": "slot",
        "title": "Açık iş",
        "candidate": "candidate_1",
        "day": "2026-10-13",
        "duration_min": 40,
    },
]
SNAPSHOT = {"goal": {"title": "Mevcut hedef"}}


@pytest.mark.no_database
@pytest.mark.parametrize(
    "draft,expected",
    [
        (
            {
                "action": "add_tasks",
                "target": "node_1",
                "tasks": [{"title": "Yeni iş", "topic": "topic_1"}],
            },
            "phases",
        ),
        (
            {
                "action": "add_topics",
                "target": "node_1",
                "topics": [{"title": "Yeni kavram", "resource_needs": ["Alıştırma bul"]}],
            },
            "phases",
        ),
        ({"action": "rename", "changes": [{"ref": "node_1", "title": "Yeni ad"}]}, "node_changes"),
        ({"action": "detach", "changes": [{"ref": "node_2"}]}, "node_changes"),
        ({"action": "attach", "changes": [{"ref": "node_2"}]}, "node_changes"),
        ({"action": "prioritize", "changes": [{"ref": "work_1", "priority": 3}]}, "task_changes"),
        (
            {"action": "move", "changes": [{"ref": "slot_1", "day": "2026-10-14"}]},
            "schedule_changes",
        ),
        (
            {"action": "reduce", "changes": [{"ref": "slot_1", "duration_min": 20}]},
            "schedule_changes",
        ),
    ],
)
def test_typed_revision_resolves_only_actual_scoped_references(draft, expected):
    c = meaning.literal_constraints(data())
    c["schedule_days"] = ["2026-10-14"]
    p = meaning.SemanticRevision.model_validate({"kind": "revision", **draft}).package(
        SNAPSHOT, CATALOG, c
    )
    assert p[expected]
    if draft["action"] == "add_tasks":
        assert p["phases"][0]["tasks"][0]["existing_topic"] == "candidate_2"
        assert p["phases"][0]["topics"] == []
        assert p["phases"][0]["attach_node_index"] == 0
    assert not p.get("outcome") and p["title"] == "Mevcut hedef"


@pytest.mark.no_database
@pytest.mark.parametrize(
    "changes",
    [
        [{"ref": "unknown", "title": "X"}],
        [{"ref": "work_1", "title": "X"}],
        [{"ref": "node_1", "title": "X"}, {"ref": "node_1", "title": "Y"}],
    ],
)
def test_unknown_wrong_type_and_duplicate_revision_targets_are_rejected(changes):
    with pytest.raises(ReplyError):
        meaning.SemanticRevision(kind="revision", action="rename", changes=changes).package(
            SNAPSHOT, CATALOG, meaning.literal_constraints(data())
        )


@pytest.mark.no_database
def test_unambiguous_action_title_is_safe_even_when_roadmap_node_has_same_title():
    assert meaning.CoachingReply(
        advice="Bu inceleme eksikleri bulmana yardımcı olur.", actions=["Açık iş"]
    ).checked(CATALOG).actions == ["Açık iş"]
    with pytest.raises(ReplyError):
        meaning.CoachingReply(advice="Çalış.", actions=["work_1"]).checked(
            [{**CATALOG[1], "status": "done"}]
        )
    with pytest.raises(ReplyError):
        meaning.CoachingReply(advice="Çalış.", actions=["Açık iş"]).checked(
            [CATALOG[1], {**CATALOG[1], "ref": "work_2"}]
        )


def staged_provider(monkeypatch, *, reject_once=False):
    original = transport.request
    calls = []
    replies = {}
    review_count = 0

    async def request(method, path, **kwargs):
        nonlocal review_count
        if path == "/v1/runs":
            calls.append(kwargs)
            body = kwargs["body"]
            payload = input_payload(body["input"])
            if "draft" in payload:
                review_count += 1
                out = (
                    {
                        "verdict": "reject",
                        "covered": [],
                        "issues": [
                            {
                                "code": "insufficient_delivery_coverage",
                                "detail": "İlk taslak kapsamı eksik",
                            }
                        ],
                    }
                    if reject_once and review_count == 1
                    else ACCEPT
                )
            elif "accepted_requirements" in payload:
                out = DRAFT
            else:
                out = REQ
            rid = f"run_semantic_{len(calls)}"
            replies[rid] = json.dumps(out, ensure_ascii=False)
            return {"run_id": rid}
        if path.startswith("/v1/runs/run_semantic_"):
            return {
                "status": "completed",
                "runtime": {"provider": "custom", "model": "fixture-model"},
                "output": replies[path.rsplit("/", 1)[-1]],
                "usage": {"input_tokens": 100, "output_tokens": 50},
            }
        return await original(method, path, **kwargs)

    monkeypatch.setattr(transport, "request", request)
    return calls


@pytest.mark.parametrize("reject_once", [False, True])
async def test_all_stages_preserve_durable_turn_no_writes_and_human_approval(
    profile, api, monkeypatch, reject_once
):
    choose(profile, "custom")
    calls = staged_provider(monkeypatch, reject_once=reject_once)
    async with SessionLocal() as db:
        s = await studio.start(db, StudioSessionIn(mode="living", client_uuid=uuid4()))
        body = StudioTurnIn(client_uuid=uuid4(), message="Becerimi geliştirmek istiyorum.")
        state = await studio.turn(db, await studio.get_session(db, s.id), body)
        from app.config import settings

        monkeypatch.setattr(settings, "goal_studio_semantic_enabled", False)
        while state.state in {"running", "unknown_delivery"}:
            state = await studio.turn(db, await studio.get_session(db, s.id), body)
        assert state.state == "approval_pending" and state.error is None
        assert len(calls) == (5 if reject_once else 3)
        assert await db.scalar(select(func.count()).select_from(Goal)) == 0
        assert await db.scalar(select(func.count()).select_from(Todo)) == 0
        assert len([m for m in state.messages if m["role"] == "user"]) == 1
        assert calls[0]["body"]["session_id"] != calls[-1]["body"]["session_id"]
        assert input_payload(calls[-1]["body"]["input"])["draft"]["tasks"]
        decision = StudioDecisionIn(
            revision_id=state.revision.id,
            fingerprint=state.revision.fingerprint,
            decision="approve",
        )
        applied = await studio.decide(db, await studio.get_session(db, s.id), decision)
        again = await studio.decide(db, await studio.get_session(db, s.id), decision)
        assert applied.state == again.state == "applied"
        assert await db.scalar(select(func.count()).select_from(Goal)) == 1
        assert await db.scalar(select(func.count()).select_from(Todo)) == 1
        assert await db.scalar(select(func.count()).select_from(PlanSlot)) == 1


async def test_wall_budget_stops_late_generation_and_never_accepts_a_late_package(
    profile, api, monkeypatch
):
    from datetime import timedelta

    choose(profile, "custom")
    calls = staged_provider(monkeypatch)
    original = transport.request
    cancelled = []

    async def request(method, path, **kwargs):
        if path.endswith("/stop"):
            cancelled.append(path)
            return {"status": "cancelling"}
        return await original(method, path, **kwargs)

    monkeypatch.setattr(transport, "request", request)
    async with SessionLocal() as db:
        s = await studio.start(db, StudioSessionIn(mode="living", client_uuid=uuid4()))
        body = StudioTurnIn(client_uuid=uuid4(), message="Becerimi geliştirmek istiyorum.")
        await studio.turn(db, await studio.get_session(db, s.id), body)
        row = await studio.get_session(db, s.id)
        identity = str(body.client_uuid)
        turn = {
            **row.data["turns"][identity],
            "at": (datetime.now(UTC) - timedelta(minutes=4)).isoformat(),
        }
        row.data = {**row.data, "turns": {identity: turn}}
        await db.commit()
        result = await studio.reconcile(db, await studio.get_session(db, s.id))
        assert result.state == "failed" and result.revision is None and cancelled
        assert "süresi doldu" in result.error
        again = await studio.reconcile(db, await studio.get_session(db, s.id))
        assert again.revision is None and len(calls) == 1
        assert await db.scalar(select(func.count()).select_from(Goal)) == 0


async def test_existing_topic_binding_and_area_reuse_are_canonical_and_approval_only(
    profile, api, monkeypatch
):
    from app.modules.goal import roadmap, service
    from app.modules.goal.context_snapshot import build
    from app.modules.goal.package_schemas import NodeData
    from app.modules.goal.schemas import GoalIn
    from app.modules.learning import service as learning
    from app.modules.learning.models import StudyArea, StudyTopic
    from app.modules.learning.schemas import AreaIn, TopicIn

    choose(profile, "custom")
    original = transport.request
    replies = {}
    calls = []

    async def request(method, path, **kwargs):
        if path == "/v1/runs":
            calls.append(kwargs["body"])
            payload = input_payload(calls[-1]["input"])
            if "revision" in payload:
                value = {"ok": True, "reason": ""}
            else:
                phase = next(i for i in payload["catalog"] if i.get("node_kind") == "phase")
                topic = next(i for i in payload["catalog"] if i["kind"] == "topic")
                value = {
                    "kind": "revision",
                    "action": "add_tasks",
                    "target": phase["ref"],
                    "tasks": [{"title": "Yeni pratik", "topic": topic["ref"], "duration_min": 20}],
                }
            rid = "run_binding_" + str(len(calls))
            replies[rid] = value
            return {"run_id": rid}
        if path.startswith("/v1/runs/run_binding_"):
            return {
                "status": "completed",
                "runtime": {"provider": "custom", "model": "fixture-model"},
                "output": json.dumps(replies[path.rsplit("/", 1)[-1]]),
            }
        return await original(method, path, **kwargs)

    monkeypatch.setattr(transport, "request", request)
    async with SessionLocal() as db:
        goal = await service.create_goal(db, GoalIn(title="Sentetik dil"))
        gid = goal.id
        area = await learning.create_area(db, AreaIn(title="Mevcut öğrenme"))
        topic = await learning.create_topic(db, TopicIn(area_id=area["id"], title="Gramer"))
        phase = await roadmap.save_node(db, gid, NodeData(title="Pratik", kind="phase"))
        pid = phase.id
        await roadmap.save_node(
            db, gid, NodeData(title="Gramer", kind="record"), target_id=topic["id"], parent_id=pid
        )
        await db.commit()
        s = await studio.start(db, StudioSessionIn(mode="living", goal_id=gid, client_uuid=uuid4()))
        result = await studio.turn(
            db,
            await studio.get_session(db, s.id),
            StudioTurnIn(client_uuid=uuid4(), message="Bir yeni görev ekle."),
        )
        while result.state == "running":
            result = await studio.reconcile(db, await studio.get_session(db, s.id))
        assert result.state == "approval_pending" and result.error is None
        assert await db.scalar(select(func.count()).select_from(Todo)) == 0
        decision = StudioDecisionIn(
            revision_id=result.revision.id,
            fingerprint=result.revision.fingerprint,
            decision="approve",
        )
        result = await studio.decide(db, await studio.get_session(db, s.id), decision)
        assert result.state == "applied"
        assert await db.scalar(select(func.count()).select_from(StudyArea)) == 1
        assert await db.scalar(select(func.count()).select_from(StudyTopic)) == 1
        assert await db.scalar(select(func.count()).select_from(Todo)) == 1
        snap = await build(db, gid)
        assert (
            len([n for n in snap["roadmap"]["nodes"] if n.get("target_id") == str(topic["id"])])
            == 1
        )


async def test_independent_topic_supports_tasks_across_phases_without_duplicate_records():
    from app.core.models import Link
    from app.modules.goal.package_authoring import compile_draft
    from app.modules.learning.models import StudyTopic

    semantic = meaning.SemanticDraft.model_validate(
        {
            "kind": "semantic_plan",
            "title": "Sentetik dil pratiği",
            "topics": [
                {"title": "Kelime", "phase": "Kaynaklar", "resource_needs": ["Alıştırma seç"]}
            ],
            "tasks": [
                {"title": "Metni oku", "phase": "Okuma", "topic": "Kelime", "duration_min": 10},
                {
                    "title": "Yanlışları incele",
                    "phase": "Değerlendirme",
                    "topic": "Kelime",
                    "duration_min": 10,
                },
            ],
        }
    )
    package = semantic.package()
    assert any(t.get("new_topic_title") == "Kelime" for p in package["phases"] for t in p["tasks"])
    async with SessionLocal() as db:
        s = await studio.start(db, StudioSessionIn(mode="living", client_uuid=uuid4()))
        proposal = await compile_draft(db, package)
        topics = [op for op in proposal.operations if op.type == "learning.topic"]
        tasks = [op for op in proposal.operations if op.type == "todo.create"]
        assert len(topics) == 1 and len(tasks) == 2
        assert {t.topic_ref for t in tasks} == {topics[0].key}
        state = await studio.revise(db, await studio.get_session(db, s.id), proposal)
        applied = await studio.decide(
            db,
            await studio.get_session(db, s.id),
            StudioDecisionIn(
                revision_id=state.revision.id,
                fingerprint=state.revision.fingerprint,
                decision="approve",
            ),
        )
        assert applied.state == "applied"
        assert await db.scalar(select(func.count()).select_from(StudyTopic)) == 1
        assert await db.scalar(select(func.count()).select_from(Todo)) == 2
        assert (
            await db.scalar(
                select(func.count()).select_from(Link).where(Link.relation == "prepares_for")
            )
            == 2
        )


async def test_approved_resource_and_record_attachment_reuse_canonical_learning_and_shared_work():
    from app.modules.goal import roadmap, service
    from app.modules.goal.context_snapshot import build
    from app.modules.goal.package_authoring import compile_draft
    from app.modules.goal.package_schemas import NodeData
    from app.modules.goal.schemas import GoalIn, GoalPatch
    from app.modules.learning import service as learning
    from app.modules.learning.models import LearningResource, StudyTopic
    from app.modules.learning.schemas import AreaIn, TopicIn
    from app.modules.todo import service as todos
    from app.modules.todo.schemas import TodoIn

    async with SessionLocal() as db:
        goal = await service.create_goal(db, GoalIn(title="Kaynak çalışması"))
        gid = goal.id
        area = await learning.create_area(db, AreaIn(title="Ortak çalışma"))
        topic = await learning.create_topic(db, TopicIn(area_id=area["id"], title="Kavram"))
        await roadmap.save_node(
            db, gid, NodeData(title="Kavram", kind="record"), target_id=topic["id"]
        )
        task = await todos.create(db, TodoIn(title="Paylaşılan çalışma"))
        tid = task.id
        await db.commit()
        candidates = [
            {
                "token": "candidate_0",
                "id": str(topic["id"]),
                "type": "study_topic",
                "title": "Kavram",
            },
            {"token": "candidate_1", "id": str(tid), "type": "todo", "title": "Paylaşılan çalışma"},
        ]
        snap = await build(db, gid)
        catalog = meaning.scope_catalog(snap, candidates)
        target = next(i["ref"] for i in catalog if i["kind"] == "topic")
        resource = meaning.SemanticRevision(
            kind="revision",
            action="add_resources",
            target=target,
            resource_needs=["HTTP için uygun uygulama kaynağı seç"],
        ).package(snap, catalog, {})
        attach = meaning.SemanticRevision(
            kind="revision", action="attach_record", record="candidate_1"
        ).package(snap, catalog, {})
        await service.update_goal(db, gid, GoalPatch(title="Güncel hedef adı"))
        for package in (resource, attach):
            snap = await build(db, gid)
            proposal = await compile_draft(
                db,
                package,
                goal_id=gid,
                candidates=candidates,
                roadmap_snapshot=snap["roadmap"]["nodes"],
            )
            assert not any(
                op.type in {"goal.update", "learning.topic", "learning.area", "todo.create"}
                for op in proposal.operations
            )
            s = await studio.start(
                db, StudioSessionIn(mode="living", goal_id=gid, client_uuid=uuid4())
            )
            state = await studio.revise(db, await studio.get_session(db, s.id), proposal)
            assert await db.scalar(select(func.count()).select_from(LearningResource)) == (
                0 if package is resource else 1
            )
            result = await studio.decide(
                db,
                await studio.get_session(db, s.id),
                StudioDecisionIn(
                    revision_id=state.revision.id,
                    fingerprint=state.revision.fingerprint,
                    decision="approve",
                ),
            )
            assert result.state == "applied"
        from app.core.models import Entity

        assert await db.scalar(select(Entity.title).where(Entity.id == gid)) == "Güncel hedef adı"
        assert await db.scalar(select(func.count()).select_from(StudyTopic)) == 1
        assert await db.scalar(select(func.count()).select_from(Todo)) == 1
        assert await db.scalar(select(func.count()).select_from(LearningResource)) == 1
        snap = await build(db, gid)
        with pytest.raises(ValueError, match="zaten"):
            await compile_draft(
                db,
                attach,
                goal_id=gid,
                candidates=candidates,
                roadmap_snapshot=snap["roadmap"]["nodes"],
            )

        # Scope may change between model context and compilation; stale scope cannot become a preview.
        stale = await build(db, gid)
        topic_node = next(
            n for n in stale["roadmap"]["nodes"] if n.get("target_id") == str(topic["id"])
        )
        await roadmap.save_node(
            db,
            gid,
            NodeData(title="Kavram", kind="record"),
            node_id=UUID(topic_node["id"]),
            detached=True,
        )
        await db.commit()
        with pytest.raises(ValueError, match="bağlantısı değişmiş"):
            await compile_draft(
                db,
                resource,
                goal_id=gid,
                candidates=candidates,
                roadmap_snapshot=stale["roadmap"]["nodes"],
            )
        extra = await todos.create(db, TodoIn(title="Başka kontrol"))
        extra_id = extra.id
        phase = await roadmap.save_node(db, gid, NodeData(title="Eski aşama", kind="phase"))
        phase_id = phase.id
        await db.commit()
        stale = await build(db, gid)
        phase_node = next(n for n in stale["roadmap"]["nodes"] if n["id"] == str(phase_id))
        candidates.append(
            {"token": "candidate_2", "id": str(extra_id), "type": "todo", "title": "Başka kontrol"}
        )
        await roadmap.save_node(
            db, gid, NodeData(title="Yeni aşama", kind="phase"), node_id=phase_id
        )
        await db.commit()
        with pytest.raises(ValueError, match="aşama değişmiş"):
            await compile_draft(
                db,
                {
                    "kind": "package",
                    "title": "Kaynak çalışması",
                    "record_attachments": [
                        {"record": "candidate_2", "parent_index": phase_node["index"]}
                    ],
                },
                goal_id=gid,
                candidates=candidates,
                roadmap_snapshot=stale["roadmap"]["nodes"],
            )


@pytest.mark.no_database
def test_existing_topic_addition_and_unknown_slot_duration_require_user_resolution():
    catalog = [{"kind": "topic", "ref": "topic_1", "title": "Kavram", "candidate": "candidate_0"}]
    with pytest.raises(ReplyError, match="zaten"):
        meaning.SemanticRevision(
            kind="revision", action="add_topics", topics=[meaning.SemanticTopic(title="Kavram")]
        ).package({"goal": {"title": "Hedef"}}, catalog, {"requested_tasks": None})
    catalog = [
        {
            "kind": "slot",
            "ref": "slot_1",
            "title": "Çalışma",
            "candidate": "candidate_0",
            "duration_min": None,
            "day": "2026-10-14",
        }
    ]
    with pytest.raises(ReplyError, match="süresini"):
        meaning.SemanticRevision(
            kind="revision",
            action="reduce",
            changes=[meaning.RevisionChange(ref="slot_1", duration_min=10)],
        ).package({"goal": {"title": "Hedef"}}, catalog, {})


async def test_same_conversation_coaching_reloads_real_completion_reopen_new_work_and_outcome(
    profile, api, monkeypatch
):
    from app.modules.goal import roadmap, service, strategy
    from app.modules.goal.context_snapshot import build
    from app.modules.goal.package_schemas import NodeData
    from app.modules.goal.schemas import GoalIn
    from app.modules.goal.strategy_schemas import KeyResultIn
    from app.modules.todo import service as todos
    from app.modules.todo.schemas import TodoIn, TodoUpdate

    choose(profile, "custom")
    original = transport.request
    replies = {}

    async def request(method, path, **kwargs):
        if path == "/v1/runs":
            payload = input_payload(kwargs["body"]["input"])
            rid = f"run_fresh_{len(replies)}"
            reply = (
                {"ok": True, "reason": ""}
                if "interpretation" in payload
                else {"advice": "Kayıtlı işleri sırayla ele alabilirsin.", "actions": []}
            )
            replies[rid] = json.dumps(reply)
            return {"run_id": rid}
        if path.startswith("/v1/runs/run_fresh_"):
            return {
                "status": "completed",
                "runtime": {"provider": "custom", "model": "fixture-model"},
                "output": replies[path.rsplit("/", 1)[-1]],
            }
        return await original(method, path, **kwargs)

    monkeypatch.setattr(transport, "request", request)
    async with SessionLocal() as db:
        goal = await service.create_goal(db, GoalIn(title="Güncel durum"))
        gid = goal.id
        ids = []
        for title in ("Birinci iş", "İkinci iş"):
            task = await todos.create(db, TodoIn(title=title))
            ids.append(task.id)
            await roadmap.save_node(
                db, gid, NodeData(title=title, kind="record"), target_id=task.id
            )
        await db.commit()
        s = await studio.start(db, StudioSessionIn(mode="living", goal_id=gid, client_uuid=uuid4()))
        observed = []

        async def coach():
            state = await studio.turn(
                db,
                await studio.get_session(db, s.id),
                StudioTurnIn(client_uuid=uuid4(), message="Neredeyiz?"),
            )
            while state.state == "running":
                state = await studio.reconcile(db, await studio.get_session(db, s.id))
            assert state.error is None and state.revision is None
            facts = state.messages[-1]["facts"]
            observed.append(facts["percent"])
            assert facts["percent"] == (await build(db, gid))["roadmap"]["percent"]
            return facts

        assert (await coach())["completed"] == 0
        await todos.update(db, ids[0], TodoUpdate(status="done"))
        assert (await coach())["completed"] == 1
        await todos.update(db, ids[1], TodoUpdate(status="done"))
        assert (await coach())["outcome_percent"] is None
        task = await todos.create(db, TodoIn(title="Yeni iş"))
        ids.append(task.id)
        await roadmap.save_node(
            db, gid, NodeData(title="Yeni iş", kind="record"), target_id=task.id
        )
        await db.commit()
        assert (await coach())["remaining"] == ["Yeni iş"]
        await todos.update(db, ids[2], TodoUpdate(status="done"))
        await coach()
        await todos.update(db, ids[0], TodoUpdate(status="open"))
        assert "Birinci iş" in (await coach())["remaining"]
        assert observed == [0, 50, 100, 67, 100, 67]
        await strategy.save_kr(
            db,
            gid,
            KeyResultIn(title="Gerçek ölçüm", target_value=55, manual_value=55, unit="puan"),
        )
        assert (await coach())["outcome_percent"] == 100
        state = await studio.out(db, await studio.get_session(db, s.id))
        # Historical message remains a snapshot; new answer is fresh, no rewriting past facts.
        assert next(m["facts"]["percent"] for m in state.messages if m.get("facts")) == 0


@pytest.mark.parametrize("message", ["Neredeyiz?", "Planı revize etsek?"])
async def test_default_policy_preserves_single_call_coaching_with_canonical_facts(
    profile, api, monkeypatch, message
):
    from app.config import settings
    from app.modules.goal import service
    from app.modules.goal.schemas import GoalIn

    choose(profile, "custom")
    monkeypatch.setattr(settings, "goal_studio_semantic_enabled", False)
    original = transport.request
    calls = []

    async def request(method, path, **kwargs):
        if path == "/v1/runs":
            calls.append(kwargs["body"])
            return {"run_id": "run_default_coach"}
        if path == "/v1/runs/run_default_coach":
            return {
                "status": "completed",
                "runtime": {"provider": "custom", "model": "fixture-model"},
                "output": "Sıradaki açık işini seçip başlayabilirsin.",
            }
        return await original(method, path, **kwargs)

    monkeypatch.setattr(transport, "request", request)
    async with SessionLocal() as db:
        goal = await service.create_goal(db, GoalIn(title="Varsayılan koçluk"))
        gid = goal.id
        s = await studio.start(db, StudioSessionIn(mode="living", goal_id=gid, client_uuid=uuid4()))
        state = await studio.turn(
            db,
            await studio.get_session(db, s.id),
            StudioTurnIn(client_uuid=uuid4(), message=message),
        )
        while state.state == "running":
            state = await studio.reconcile(db, await studio.get_session(db, s.id))
        assert state.error is None and state.revision is None and len(calls) == 1
        assert state.messages[-1]["facts"]["percent"] is None
        row = await studio.get_session(db, s.id)
        assert "pipeline" not in row.data["turns"][row.data["active_turn"]]


async def test_default_author_respects_explicit_exclusions_and_never_calls_scheduler(
    profile, api, monkeypatch
):
    from app.config import settings
    from app.modules.goal import package_authoring
    from app.modules.learning.models import StudyTopic

    choose(profile, "custom")
    monkeypatch.setattr(settings, "goal_studio_semantic_enabled", False)
    original = transport.request
    calls = []

    async def unavailable_planner(*args, **kwargs):
        raise AssertionError("No-schedule request must not query or invoke the planner")

    monkeypatch.setattr(package_authoring, "propose", unavailable_planner)

    async def request(method, path, **kwargs):
        if path == "/v1/runs":
            calls.append(kwargs["body"])
            return {"run_id": "run_literal_default"}
        if path == "/v1/runs/run_literal_default":
            return {
                "status": "completed",
                "runtime": {"provider": "custom", "model": "fixture-model"},
                "output": json.dumps(
                    {
                        "kind": "work_plan",
                        "title": "Belge inceleme",
                        "work": [{"title": "Belgeyi incele", "duration_min": 20}],
                    }
                ),
            }
        return await original(method, path, **kwargs)

    monkeypatch.setattr(transport, "request", request)
    async with SessionLocal() as db:
        s = await studio.start(db, StudioSessionIn(mode="living", client_uuid=uuid4()))
        state = await studio.turn(
            db,
            await studio.get_session(db, s.id),
            StudioTurnIn(
                client_uuid=uuid4(),
                message="Belgeyi incele. Learning oluşturma. Projeye bağlama. Takvime şimdilik yerleştirme. Günde en fazla 30 dakika.",
            ),
        )
        while state.state == "running":
            state = await studio.reconcile(db, await studio.get_session(db, s.id))
        assert state.error is None and state.state == "approval_pending" and len(calls) == 1
        assert state.revision.proposal.planning.daily_capacity_min == 30
        assert state.revision.proposal.planning.capacity_confirmed
        assert not any(
            op.type in {"learning.area", "learning.topic", "plan.schedule"}
            for op in state.revision.proposal.operations
        )
        assert await db.scalar(select(func.count()).select_from(Goal)) == 0
        applied = await studio.decide(
            db,
            await studio.get_session(db, s.id),
            StudioDecisionIn(
                revision_id=state.revision.id,
                fingerprint=state.revision.fingerprint,
                decision="approve",
            ),
        )
        assert applied.state == "applied"
        assert await db.scalar(select(func.count()).select_from(Todo)) == 1
        assert await db.scalar(select(func.count()).select_from(StudyTopic)) == 0
        assert await db.scalar(select(func.count()).select_from(PlanSlot)) == 0


@pytest.mark.no_database
def test_ambiguous_learning_area_and_record_rename_cannot_change_canonical_ownership():
    catalog = [
        {"kind": "area", "ref": "area_1", "title": "Dil", "candidate": "candidate_0"},
        {"kind": "area", "ref": "area_2", "title": "Yazılım", "candidate": "candidate_1"},
        {"kind": "node", "ref": "node_1", "title": "İş", "index": 0, "node_kind": "record"},
    ]
    revision = meaning.SemanticRevision(
        kind="revision", action="add_topics", topics=[meaning.SemanticTopic(title="Yeni kavram")]
    )
    with pytest.raises(ReplyError, match="öğrenme alanını"):
        revision.package({"goal": {"title": "Hedef"}}, catalog, {"requested_tasks": None})
    revision.area = "area_2"
    assert (
        revision.package({"goal": {"title": "Hedef"}}, catalog, {"requested_tasks": None})[
            "reuse_area"
        ]
        == "candidate_1"
    )
    with pytest.raises(ReplyError, match="aşama"):
        meaning.SemanticRevision(
            kind="revision",
            action="rename",
            changes=[meaning.RevisionChange(ref="node_1", title="Yeni")],
        ).package({"goal": {"title": "Hedef"}}, catalog, {})
    with pytest.raises(ReplyError, match="bağlantı"):
        meaning.SemanticRevision(
            kind="revision",
            action="add_topics",
            topics=[
                meaning.SemanticTopic(title="Konu", resource_needs=["https://unverified.invalid"])
            ],
        ).package({"goal": {"title": "Hedef"}}, catalog, {"requested_tasks": None})


@pytest.mark.no_database
def test_coaching_resolves_display_names_without_exposing_or_inventing_record_refs():
    catalog = [{"kind": "work", "ref": "work_1", "title": "Metni incele", "status": "open"}]
    reply = meaning.CoachingReply(
        advice="work_1 üzerine odaklanabilirsin.", actions=["work_1"]
    ).checked(catalog)
    assert reply.advice == "Metni incele üzerine odaklanabilirsin."
    with pytest.raises(ReplyError, match="bilinmeyen"):
        meaning.CoachingReply(advice="work_99 üzerine odaklan.").checked(catalog)


@pytest.mark.parametrize(
    "message", ["Neredeyiz?", "Sıradaki çalışma olarak hangisine zaman ayırmam daha mantıklı?"]
)
async def test_canonical_facts_are_available_before_inference_and_after_malformed_coaching(
    profile, api, monkeypatch, message
):
    from app.modules.goal import roadmap, service
    from app.modules.goal.package_schemas import NodeData
    from app.modules.goal.schemas import GoalIn
    from app.modules.todo import service as todos
    from app.modules.todo.schemas import TodoIn

    choose(profile, "custom")
    original = transport.request
    count = 0

    async def request(method, path, **kwargs):
        nonlocal count
        if path == "/v1/runs":
            count += 1
            return {"run_id": f"run_bad_facts_{count}"}
        if path.startswith("/v1/runs/run_bad_facts_"):
            return {
                "status": "completed",
                "runtime": {"provider": "custom", "model": "fixture-model"},
                "output": "{invalid",
            }
        return await original(method, path, **kwargs)

    monkeypatch.setattr(transport, "request", request)
    async with SessionLocal() as db:
        goal = await service.create_goal(db, GoalIn(title="Yanıt hatası"))
        gid = goal.id
        task = await todos.create(db, TodoIn(title="Açık iş"))
        await roadmap.save_node(
            db, gid, NodeData(title="Açık iş", kind="record"), target_id=task.id
        )
        await db.commit()
        s = await studio.start(db, StudioSessionIn(mode="living", goal_id=gid, client_uuid=uuid4()))
        state = await studio.turn(
            db,
            await studio.get_session(db, s.id),
            StudioTurnIn(client_uuid=uuid4(), message=message),
        )
        assert state.current_facts.percent == 0 and state.current_facts.remaining == ["Açık iş"]
        while state.state in {"running", "unknown_delivery"}:
            state = await studio.reconcile(db, await studio.get_session(db, s.id))
        assert state.error and count == 2
        assert state.current_facts.percent == 0 and state.current_facts.outcome_percent is None
        assert state.messages[-1]["role"] == "user" and state.revision is None
        assert await db.scalar(select(func.count()).select_from(Todo)) == 1


@pytest.mark.parametrize(
    "message, field, count",
    [
        ("Gramer bölümüne bir konu ekle.", "requested_topics", 1),
        ("İki yeni öğrenme konusu oluştur.", "requested_topics", 2),
        ("Zamanlar için bir alıştırma kaynağı ihtiyacı ekle.", "requested_resources", 1),
        ("Üç yeni kaynak ekle.", "requested_resources", 3),
    ],
)
def test_explicit_topic_and_resource_quantities_are_literal_constraints(message, field, count):
    constraints = meaning.literal_constraints({"messages": [{"role": "user", "text": message}]})
    assert constraints[field] == count


def test_one_topic_request_cannot_accept_two_topics_or_two_resource_needs():
    constraints = {"requested_tasks": None, "requested_topics": 1, "requested_resources": 1}
    snapshot = {"goal": {"title": "Hedef"}}
    with pytest.raises(ReplyError, match="konu sayısını"):
        meaning.SemanticRevision.model_validate(
            {
                "kind": "revision",
                "action": "add_topics",
                "topics": [{"title": "Bir"}, {"title": "İki"}],
            }
        ).package(snapshot, [], constraints)
    with pytest.raises(ReplyError, match="kaynak sayısını"):
        meaning.SemanticRevision.model_validate(
            {
                "kind": "revision",
                "action": "add_resources",
                "target": "topic_1",
                "resource_needs": ["Birinci alıştırma", "İkinci alıştırma"],
            }
        ).package(
            snapshot,
            [{"kind": "topic", "ref": "topic_1", "title": "Zamanlar", "candidate": "candidate_0"}],
            constraints,
        )
    with pytest.raises(ReplyError, match="konu sayısını"):
        meaning.validate_literal_package(
            {
                "kind": "package",
                "title": "Hedef",
                "phases": [{"title": "Gramer", "topics": [{"title": "Bir"}, {"title": "İki"}]}],
            },
            {"excluded": [], "requested_topics": 1},
        )


@pytest.mark.parametrize(
    "action, change, allowed",
    [
        ("move", {"ref": "slot_1"}, ["2026-10-14", "2026-10-15"]),
        ("move", {"ref": "slot_1", "day": "2026-10-14"}, ["2026-10-14"]),
        ("replan", {"ref": "slot_1", "duration_min": 25}, ["2026-10-14"]),
        ("replan", {"ref": "slot_1", "duration_min": 15}, ["2026-10-19"]),
    ],
)
def test_schedule_revision_rejects_no_change_and_explicit_week_scope_mismatch(
    action, change, allowed
):
    catalog = [
        {
            "kind": "slot",
            "ref": "slot_1",
            "title": "İlk çalışma",
            "candidate": "candidate_0",
            "duration_min": 25,
            "day": "2026-10-14",
        }
    ]
    with pytest.raises(ReplyError):
        meaning.SemanticRevision.model_validate(
            {"kind": "revision", "action": action, "changes": [change]}
        ).package({"goal": {"title": "Hedef"}}, catalog, {"schedule_days": allowed})


async def test_classifier_coaching_keeps_canonical_facts_on_accepted_message(
    profile, api, monkeypatch
):
    from app.modules.goal import roadmap, service
    from app.modules.goal.package_schemas import NodeData
    from app.modules.goal.schemas import GoalIn
    from app.modules.todo import service as todos
    from app.modules.todo.schemas import TodoIn

    choose(profile, "custom")
    original = transport.request
    replies = {}
    outputs = iter(
        [
            {"mode": "coach", "explanation": "Çalışma önceliği yorumu."},
            {"advice": "Açık iş üzerine odaklanabilirsin.", "actions": []},
            {"ok": True, "reason": ""},
        ]
    )

    async def request(method, path, **kwargs):
        if path == "/v1/runs":
            rid = f"run_route_facts_{len(replies)}"
            replies[rid] = json.dumps(next(outputs))
            return {"run_id": rid}
        if path.startswith("/v1/runs/run_route_facts_"):
            return {
                "status": "completed",
                "runtime": {"provider": "custom", "model": "fixture-model"},
                "output": replies[path.rsplit("/", 1)[-1]],
            }
        return await original(method, path, **kwargs)

    monkeypatch.setattr(transport, "request", request)
    async with SessionLocal() as db:
        goal = await service.create_goal(db, GoalIn(title="Öncelik"))
        task = await todos.create(db, TodoIn(title="Açık iş"))
        await roadmap.save_node(
            db, goal.id, NodeData(title="Açık iş", kind="record"), target_id=task.id
        )
        await db.commit()
        s = await studio.start(
            db, StudioSessionIn(mode="living", goal_id=goal.id, client_uuid=uuid4())
        )
        state = await studio.turn(
            db,
            await studio.get_session(db, s.id),
            StudioTurnIn(
                client_uuid=uuid4(),
                message="Sıradaki çalışma olarak hangisine zaman ayırmam daha mantıklı?",
            ),
        )
        assert state.current_facts.percent == 0
        while state.state == "running":
            state = await studio.reconcile(db, await studio.get_session(db, s.id))
        assert state.error is None and state.revision is None and len(replies) == 3
        assert state.messages[-1]["facts"]["remaining"] == ["Açık iş"]
