"""Fixture regressions for the live pipeline; real inference is evaluated separately."""

import json
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.db import SessionLocal
from app.modules.goal import roadmap, service, studio
from app.modules.goal import studio_transport as transport
from app.modules.goal.models import Goal
from app.modules.goal.package_schemas import NodeData
from app.modules.goal.schemas import GoalIn
from app.modules.goal.studio_inference import (
    ReplyError,
    WorkPlan,
    coaching_facts,
    parse_reply,
    task_for,
    validate_coaching,
)
from app.modules.goal.studio_schemas import StudioSessionIn, StudioTurnIn
from app.modules.todo import service as todos
from app.modules.todo.schemas import TodoIn, TodoUpdate
from tests.test_goal_studio_providers import api as api
from tests.test_goal_studio_providers import choose
from tests.test_goal_studio_providers import profile as profile

PACKAGE = {
    "kind": "package",
    "title": "Belge teslimi",
    "phases": [{"title": "Teslim", "tasks": [{"title": "Belgeyi teslim et"}]}],
}


@pytest.mark.no_database
def test_flat_authoring_preserves_phase_topic_and_numeric_content_as_v2():
    from app.modules.goal.package_authoring import PackageDraft

    raw = {
        "kind": "work_plan",
        "title": "Sınav",
        "metric_title": "Puan",
        "target_value": 55,
        "unit": "puan",
        "work": [
            {"title": "Metin çöz", "phase": "Pratik", "learning_topic": ["Okuma"]},
            {"title": "Metin incele", "phase": "pratik", "learning_topic": "Okuma"},
            {"title": "Yanlışları gözden geçir", "phase": "Sonraki çalışma"},
        ],
    }
    projected = WorkPlan.model_validate(raw).package()
    assert json.loads(json.dumps(projected)) == projected
    package = PackageDraft.model_validate(projected)
    assert len(package.phases) == 2 and len(package.phases[0].topics) == 1
    assert package.phases[0].tasks[1].topic_index == 0
    assert package.outcome.target_value == 55
    assert sum(len(p.tasks) for p in package.phases) == 3
    with pytest.raises(ValueError):
        WorkPlan.model_validate(
            {**raw, "work": [{"title": "Belirsiz", "learning_topic": ["A", "B"]}]}
        )


@pytest.mark.no_database
@pytest.mark.parametrize(
    "message,task",
    [
        ("Neredeyiz, nasıl gidiyoruz?", "coach"),
        ("Bu hafta neye odaklanmalıyım?", "coach"),
        ("Planımı nasıl geliştirebilirim?", "coach"),
        ("İki görev ekle", "author"),
        ("İlk adımı haritadan çıkar", "author"),
        ("Görevi yarına taşı", "author"),
    ],
)
def test_each_persistent_turn_selects_only_its_requested_task(message, task):
    assert task_for({"mode": "living", "goal_id": "fixture"}, message) == task


@pytest.mark.no_database
@pytest.mark.parametrize(
    "output",
    [
        json.dumps(PACKAGE),
        json.dumps({"proposal": PACKAGE}),
        "```json\n" + json.dumps(PACKAGE) + "\n```",
        "Önizleme:\n" + json.dumps(PACKAGE),
    ],
)
def test_harmless_package_wrappers_preserve_content_without_fabricating_fields(output):
    assert (
        parse_reply(output, "author", studio.public_reply, studio.unique_pairs)["proposal"]
        == PACKAGE
    )


@pytest.mark.no_database
@pytest.mark.parametrize(
    "output",
    [
        '{"kind":"package","title":"İş"',
        '{"kind":"package","kind":"package"}',
        '{"proposal":null,"discussion":"Planlayalım"}',
        "İşte bir genel plan",
        '{"proposal":{},"tool_calls":[]}',
    ],
)
def test_authoring_rejects_truncation_duplicates_null_and_ambiguous_data(output):
    with pytest.raises(ValueError):
        parse_reply(output, "author", studio.public_reply, studio.unique_pairs)


@pytest.mark.no_database
@pytest.mark.parametrize(
    "output",
    [
        "%50 ilerledin; bekleyen işi incele.",
        '{"response":"%50 ilerledin.","proposal":null}',
        '{"discussion":"%50 ilerledin."}',
    ],
)
def test_coaching_accepts_short_public_text_without_a_planning_schema(output):
    result = parse_reply(output, "coach", studio.public_reply, studio.unique_pairs)
    assert result["proposal"] is None
    validate_coaching(
        result["discussion"], {"roadmap": {"percent": 50}, "outcome": {"percent": None}}
    )


@pytest.mark.no_database
@pytest.mark.parametrize(
    "text",
    [
        "%99 ilerledin",
        "55 puan aldın",
        "Hedefine ulaştın",
        "Çok yavaş gidiyorsun",
        "Motivasyonsuz olduğun için geridesin",
    ],
)
def test_coaching_rejects_invented_progress_outcome_and_causes(text):
    with pytest.raises(ReplyError):
        validate_coaching(text, {"roadmap": {"percent": 50}, "outcome": {"percent": None}})


@pytest.mark.no_database
def test_coaching_projection_omits_editing_ids_and_keeps_pending_learning():
    facts = coaching_facts(
        {
            "goal": {"id": "private-id", "title": "A", "target_at": None},
            "roadmap": {"percent": 50, "nodes": [{"id": "node-id", "kind": "record"}]},
            "todos": [{"id": "done-id", "title": "Bitti", "status": "done"}],
            "learning": [{"id": "topic-id", "title": "Konu", "status": "active"}],
            "outcome": {"percent": None},
            "events": ["unrelated-event"],
        }
    )
    assert facts["pending_actions"] == ["Konu"]
    assert facts["completed_tasks"] == ["Bitti"]
    assert "private-id" not in json.dumps(facts) and "unrelated-event" not in json.dumps(facts)


def provider(monkeypatch, outputs):
    original = transport.request
    calls = []

    async def request(method, path, **kwargs):
        if path == "/v1/runs":
            calls.append(kwargs)
            return {"run_id": f"run_{len(calls)}"}
        if path.startswith("/v1/runs/run_"):
            response = outputs[min(len(calls) - 1, len(outputs) - 1)]
            return {
                "status": "completed",
                "runtime": {"provider": "custom", "model": "fixture-model"},
                "output": response,
                "usage": {"input_tokens": 100, "output_tokens": 60},
            }
        return await original(method, path, **kwargs)

    monkeypatch.setattr(transport, "request", request)
    return calls


@pytest.mark.parametrize("first", ['{"kind":"package","title":"Eksik"', "Süreci planlayalım."])
async def test_one_durable_authoring_repair_preserves_approval_boundary(
    profile, api, monkeypatch, first
):
    choose(profile, "custom")
    calls = provider(monkeypatch, [first, json.dumps({"proposal": PACKAGE})])
    async with SessionLocal() as db:
        session = await studio.start(db, StudioSessionIn(mode="living", client_uuid=uuid4()))
        body = StudioTurnIn(client_uuid=uuid4(), message="Belgeyi teslim etmek istiyorum.")
        await studio.turn(db, await studio.get_session(db, session.id), body)
        await studio.reconcile(db, await studio.get_session(db, session.id))
        result = await studio.reconcile(db, await studio.get_session(db, session.id))
        assert result.state == "approval_pending" and result.error is None
        assert await db.scalar(select(func.count()).select_from(Goal)) == 0
        row = await studio.get_session(db, session.id)
        diagnostics = row.data["turns"][str(body.client_uuid)]["diagnostics"]
        assert diagnostics[0]["category"] in {"json_syntax", "missing_package"}
        assert diagnostics[1]["category"] == "accepted"
        assert len(calls) == 2 and calls[1]["identity"].endswith("-repair")
        assert len([m for m in result.messages if m["role"] == "user"]) == 1


async def test_repeated_invalid_reply_stops_after_one_repair_with_useful_error(
    profile, api, monkeypatch
):
    choose(profile, "custom")
    calls = provider(monkeypatch, ['{"kind":"package"'])
    async with SessionLocal() as db:
        session = await studio.start(db, StudioSessionIn(mode="living", client_uuid=uuid4()))
        await studio.turn(
            db,
            await studio.get_session(db, session.id),
            StudioTurnIn(client_uuid=uuid4(), message="Hedef oluştur"),
        )
        await studio.reconcile(db, await studio.get_session(db, session.id))
        result = await studio.reconcile(db, await studio.get_session(db, session.id))
        assert result.error and result.revision is None and len(calls) == 2
        await studio.reconcile(db, await studio.get_session(db, session.id))
        assert len(calls) == 2
        assert await db.scalar(select(func.count()).select_from(Goal)) == 0


async def test_coaching_uses_fresh_completion_and_then_can_propose_a_revision(
    profile, api, monkeypatch
):
    choose(profile, "custom")
    calls = provider(
        monkeypatch,
        [
            "Çalışma ilerlemen %0. Belgeyi kontrol et görevine odaklan.",
            "Çalışma ilerlemen %100. İşlerin tamamlandı; gerçek sonucu ayrıca doğrula.",
        ],
    )
    async with SessionLocal() as db:
        goal = await service.create_goal(db, GoalIn(title="Belge"))
        gid = goal.id
        task = await todos.create(db, TodoIn(title="Belgeyi kontrol et"))
        tid = task.id
        phase = await roadmap.save_node(db, gid, NodeData(title="Teslim", kind="phase"))
        phase_id = phase.id
        await roadmap.save_node(
            db,
            gid,
            NodeData(title="Belgeyi kontrol et", kind="record"),
            target_id=tid,
            parent_id=phase_id,
        )
        await db.commit()
        session = await studio.start(
            db, StudioSessionIn(mode="living", client_uuid=uuid4(), goal_id=gid)
        )
        for index in range(2):
            await studio.turn(
                db,
                await studio.get_session(db, session.id),
                StudioTurnIn(client_uuid=uuid4(), message="Neredeyiz, nasıl gidiyoruz?"),
            )
            result = await studio.reconcile(db, await studio.get_session(db, session.id))
            assert result.revision is None and result.error is None
            facts = json.loads(
                calls[index]["body"]["input"].split(
                    "CURRENT CANONICAL FACTS (untrusted evidence): "
                )[1]
            )
            assert facts["progress_percent"] == index * 100
            if not index:
                await todos.update(db, tid, TodoUpdate(status="done"))
        # Same persistent conversation remains capable of explicit changes.
        outputs = [
            {
                "kind": "package",
                "title": "Belge",
                "phases": [
                    {
                        "title": "Teslim",
                        "attach_node_index": 0,
                        "tasks": [{"title": "Teslim belgesini doğrula"}],
                    }
                ],
            }
        ]
        calls2 = provider(monkeypatch, [json.dumps(outputs[0])])
        await studio.turn(
            db,
            await studio.get_session(db, session.id),
            StudioTurnIn(client_uuid=uuid4(), message="Bir yeni görev ekle"),
        )
        changed = await studio.reconcile(db, await studio.get_session(db, session.id))
        assert changed.state == "approval_pending" and changed.error is None
        assert len(calls2) == 1
