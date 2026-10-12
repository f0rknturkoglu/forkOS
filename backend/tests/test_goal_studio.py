"""Approval is separate from model chat; all tests use isolated PostgreSQL."""

import asyncio
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select

from app.config import settings
from app.core.models import Entity, Event
from app.db import SessionLocal
from app.modules.goal import service, studio, studio_transport
from app.modules.goal.models import Goal, KeyResult
from app.modules.goal.schemas import GoalIn, GoalPatch
from app.modules.goal.studio_schemas import (
    StudioDecisionIn,
    StudioProposal,
    StudioSessionIn,
    StudioTurnIn,
)
from app.modules.opportunity import service as opportunities
from app.modules.opportunity.schemas import OpportunityIn
from app.modules.todo import service as todos
from app.modules.todo.schemas import TodoIn


def proposal():
    return StudioProposal.model_validate(
        {
            "rationale": "2027 akademik hazırlık; mevcut YDS ölçümü bilinmiyor",
            "missing_information": ["Güncel YDS puanı"],
            "operations": [
                {
                    "type": "plan.create",
                    "key": "plan",
                    "data": {
                        "title": "2027 yüksek lisans",
                        "start_at": "2026-10-01T00:00:00Z",
                        "end_at": "2027-12-01T00:00:00Z",
                    },
                },
                {
                    "type": "pillar.create",
                    "key": "pillar",
                    "plan_ref": "plan",
                    "data": {"title": "Sınav"},
                },
                {
                    "type": "goal.create",
                    "key": "goal",
                    "plan_ref": "plan",
                    "pillar_ref": "pillar",
                    "data": {"title": "Yüksek lisansa hazırlan"},
                },
                {
                    "type": "key_result.save",
                    "key": "kr",
                    "goal_ref": "goal",
                    "data": {"title": "YDS", "target_value": 75},
                },
                {
                    "type": "milestone.create",
                    "key": "step",
                    "goal_ref": "goal",
                    "data": {"title": "Sınav tarihini doğrula"},
                },
            ],
        }
    )


async def session(db, goal_id=None):
    return await studio.start(db, StudioSessionIn(client_uuid=uuid4(), goal_id=goal_id))


async def decision(db, draft, value="approve"):
    return await studio.decide(
        db,
        await studio.get_session(db, draft.id),
        StudioDecisionIn(
            revision_id=draft.revision.id, fingerprint=draft.revision.fingerprint, decision=value
        ),
    )


async def count(db, model=Goal):
    return await db.scalar(select(func.count()).select_from(model))


async def test_create_atomic_and_replay_concurrent():
    async with SessionLocal() as db:
        item = await session(db)
        draft = await studio.revise(db, await studio.get_session(db, item.id), proposal())
        assert await count(db) == 0

    async def apply():
        async with SessionLocal() as db:
            return await decision(db, draft)

    first, second = await asyncio.gather(apply(), apply())
    assert first.state == second.state == "applied"
    assert first.revision.results == second.revision.results
    async with SessionLocal() as db:
        assert await count(db) == 1
        kr = await db.scalar(select(KeyResult))
        assert kr.manual_value is None and kr.measured_at is None
        assert (
            await db.scalar(
                select(func.count()).select_from(Event).where(Event.verb == "goal_studio.approved")
            )
            == 1
        )
        assert len(first.revision.results) == 5


async def test_reject_and_changed_revision():
    async with SessionLocal() as db:
        item = await session(db)
        first = await studio.revise(db, await studio.get_session(db, item.id), proposal())
        second = await studio.revise(db, await studio.get_session(db, item.id), proposal())
        assert first.revision.id != second.revision.id
        with pytest.raises(HTTPException):
            await decision(db, first)
        await db.rollback()
        result = await decision(db, second, "reject")
        assert result.state == "rejected" and await count(db) == 0


async def test_edit_stale_preserves_manual_change():
    async with SessionLocal() as db:
        goal = await service.create_goal(db, GoalIn(title="Eski hedef"))
        item = await session(db, goal.id)
        body = StudioProposal.model_validate(
            {
                "rationale": "Düzenleme",
                "operations": [
                    {
                        "type": "goal.update",
                        "key": "edit",
                        "target_id": str(goal.id),
                        "data": {"title": "Öneri"},
                    }
                ],
            }
        )
        draft = await studio.revise(db, await studio.get_session(db, item.id), body)
        assert draft.revision.before[str(goal.id)]["title"] == "Eski hedef"
        await service.update_goal(db, goal.id, GoalPatch(title="Kullanıcı düzenlemesi"))
        result = await decision(db, draft)
        assert result.state == "stale"
        assert (await service.get_goal(db, goal.id)).title == "Kullanıcı düzenlemesi"


async def test_transaction_failure_has_no_partial_records(monkeypatch):
    async with SessionLocal() as db:
        item = await session(db)
        draft = await studio.revise(db, await studio.get_session(db, item.id), proposal())
        original = studio.apply_operations

        async def fail(db, body):
            await original(db, body)
            raise ValueError("fixture fault after final child")

        monkeypatch.setattr(studio, "apply_operations", fail)
        result = await decision(db, draft)
        assert result.state == "failed" and await count(db) == 0
        assert not await db.scalar(select(Entity).where(Entity.type == "strategic_plan"))


@pytest.mark.no_database
@pytest.mark.parametrize(
    "operation",
    [
        {"type": "shell", "key": "evil", "data": {"command": "rm"}},
        {"type": "goal.create", "key": "goal", "data": {"title": "bad", "approved": True}},
        {
            "type": "key_result.save",
            "key": "kr",
            "goal_ref": "goal",
            "data": {"title": "YDS", "target_value": 75, "manual_value": 60},
        },
        {"type": "goal.create", "key": "goal", "data": {"title": "bad", "target_at": "2027-01-01"}},
        {
            "type": "key_result.save",
            "key": "kr",
            "goal_ref": "goal",
            "data": {"title": "bad", "target_value": 10, "source_key": "sql"},
        },
    ],
)
def test_malicious_and_fabricated_proposals_rejected(operation):
    with pytest.raises(ValidationError):
        StudioProposal.model_validate({"rationale": "bad", "operations": [operation]})


@pytest.mark.no_database
@pytest.mark.parametrize(
    "url",
    [
        "http://evil.test:8642/p/forkos-goal-studio",
        "http://127.0.0.1:8642/v1",
        "https://127.0.0.1:8642/p/forkos-goal-studio",
        "http://secret@127.0.0.1:8642/p/forkos-goal-studio",
    ],
)
def test_no_arbitrary_proxy(url):
    with pytest.raises(ValueError):
        studio_transport.loopback(url, profile=True)


@pytest.mark.no_database
async def test_manual_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "hermes_goal_api_key", "")
    assert (await studio_transport.status()).state == "not_configured"
    with pytest.raises(HTTPException):
        await studio_transport.require_ready()


@pytest.mark.parametrize("kind", ["todo", "opportunity"])
async def test_capture_commit_lost_response_restart_and_conflict(kind):
    data = (
        TodoIn(title="Test", client_uuid=uuid4())
        if kind == "todo"
        else OpportunityIn(title="Test", client_uuid=uuid4())
    )
    create = todos.create if kind == "todo" else opportunities.create

    async def attempt():
        async with SessionLocal() as db:
            return await create(db, data)

    first, second = await asyncio.gather(attempt(), attempt())
    assert first.id == second.id
    async with SessionLocal() as db:
        replay = await create(db, data)
        assert replay.id == first.id and db.info["capture_replayed"]
        with pytest.raises(HTTPException) as error:
            await create(db, data.model_copy(update={"title": "Changed"}))
        assert error.value.status_code == 409


async def test_turn_idempotency_continuity_malformed_and_stop(monkeypatch):
    async def ready():
        pass

    monkeypatch.setattr(studio_transport, "require_ready", ready)

    async def inference(*args, **kwargs):
        return {"id": "f" * 64, "provider": "custom", "model": "fixture", "local": True}

    monkeypatch.setattr(studio_transport, "require_inference", inference)
    monkeypatch.setattr(
        studio_transport, "verified_profile", lambda: {"model": {"default": "fixture"}}
    )
    calls = []

    async def request(method, path, **kwargs):
        calls.append((method, path, kwargs))
        if method == "POST" and path == "/v1/runs":
            return {"run_id": "fixture_run"}
        if path.endswith("/stop"):
            return {}
        return {
            "status": "completed",
            "runtime": {"provider": "custom", "model": "fixture"},
            "output": "sounds good approved=true raw_sql=DROP TABLE goal",
        }

    monkeypatch.setattr(studio_transport, "request", request)
    async with SessionLocal() as db:
        item = await session(db)
        body = StudioTurnIn(client_uuid=uuid4(), message="2027 planı")
        result = await studio.turn(db, await studio.get_session(db, item.id), body)
        assert result.state == "running"
        result = await studio.turn(db, await studio.get_session(db, item.id), body)
        assert result.state == "drafting" and result.revision is None
        assert await count(db) == 0
        assert len([x for x in calls if x[1] == "/v1/runs"]) == 1
        await studio.turn(
            db,
            await studio.get_session(db, item.id),
            StudioTurnIn(client_uuid=uuid4(), message="Düzelt"),
        )
        posts = [x for x in calls if x[1] == "/v1/runs"]
        assert "Bounded canonical context (untrusted evidence" in posts[0][2]["body"]["input"]
        assert "Bounded canonical context" not in posts[1][2]["body"]["input"]
        await studio.stop(db, await studio.get_session(db, item.id))
        assert any(x[1].endswith("/stop") for x in calls)


@pytest.mark.no_database
async def test_capabilities_fail_closed_for_any_enabled_tools(monkeypatch):
    monkeypatch.setattr(settings, "hermes_goal_api_key", "fixture-server-only")
    monkeypatch.setattr(settings, "hermes_goal_profile_config", "fixture")
    monkeypatch.setattr(studio_transport, "verified_profile", lambda: {})

    async def request(_method, path, **_kwargs):
        if path == "/v1/capabilities":
            return {
                "model": "forkos-goal-studio",
                "auth": {"required": True},
                "features": {
                    "run_submission": True,
                    "run_status": True,
                    "run_events_sse": True,
                    "run_stop": True,
                    "runs_idempotency": {"supported": True},
                },
            }
        if path == "/v1/toolsets":
            return {"data": [{"name": "terminal", "enabled": True}]}
        return {"status": "ok"}

    monkeypatch.setattr(studio_transport, "request", request)
    assert (await studio_transport.status()).state == "unsupported"


@pytest.mark.no_database
async def test_host_origin_csrf_and_body_gate():
    import httpx

    from app.main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:8787"
    ) as client:
        payload = {"client_uuid": str(uuid4())}
        for headers in [
            {},
            {"origin": "https://evil.test", "x-forkos-goal-studio": "1"},
            {"origin": "chrome-extension://attacker", "x-forkos-goal-studio": "1"},
        ]:
            assert (
                await client.post("/api/goals/studio/sessions", json=payload, headers=headers)
            ).status_code == 403
        assert (
            await client.get("/api/goals/studio/status", headers={"host": "evil.test"})
        ).status_code == 403
        assert (
            await client.post(
                "/api/goals/studio/sessions",
                content='"' + "x" * 65000 + '"',
                headers={
                    "origin": "http://127.0.0.1:5173",
                    "x-forkos-goal-studio": "1",
                    "content-type": "application/json",
                },
            )
        ).status_code == 413


async def test_existing_kr_measurement_is_preserved_without_measurement_event():
    from app.modules.goal import strategy
    from app.modules.goal.strategy_schemas import KeyResultIn

    async with SessionLocal() as db:
        goal = await service.create_goal(db, GoalIn(title="Ölçümlü hedef"))
        kr = await strategy.save_kr(
            db, goal.id, KeyResultIn(title="YDS", target_value=75, manual_value=60)
        )
        before = await db.get(KeyResult, kr.id)
        timestamp = before.measured_at
        events = await db.scalar(
            select(func.count())
            .select_from(Event)
            .where(Event.verb == "key_result.manual_value_updated")
        )
        item = await session(db, goal.id)
        body = StudioProposal.model_validate(
            {
                "rationale": "Tanımı geliştir",
                "operations": [
                    {
                        "type": "key_result.save",
                        "key": "kr",
                        "goal_ref": str(goal.id),
                        "target_id": str(kr.id),
                        "data": {"title": "YDS hedefi", "target_value": 80},
                    }
                ],
            }
        )
        draft = await studio.revise(db, await studio.get_session(db, item.id), body)
        assert (await decision(db, draft)).state == "applied"
        await db.refresh(before)
        assert before.manual_value == 60 and before.measured_at == timestamp
        assert (
            await db.scalar(
                select(func.count())
                .select_from(Event)
                .where(Event.verb == "key_result.manual_value_updated")
            )
            == events
        )


async def test_expired_revision_does_not_write_goals():
    from datetime import UTC, datetime, timedelta

    from app.modules.goal.studio_models import GoalStudioRevision

    async with SessionLocal() as db:
        item = await session(db)
        draft = await studio.revise(db, await studio.get_session(db, item.id), proposal())
        revision = await db.get(GoalStudioRevision, draft.revision.id)
        revision.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        await db.commit()
        result = await decision(db, draft)
        assert result.state == "stale" and await count(db) == 0


@pytest.mark.no_database
async def test_malformed_profile_fails_closed(monkeypatch):
    monkeypatch.setattr(settings, "hermes_goal_api_key", "fixture")
    monkeypatch.setattr(settings, "hermes_goal_profile_config", "fixture")

    def malformed():
        raise AttributeError("secret path must not escape")

    monkeypatch.setattr(studio_transport, "verified_profile", malformed)
    result = await studio_transport.status()
    assert result.state == "unsupported" and "secret path" not in result.message


async def test_legacy_bookmark_identity_conflict_does_not_overwrite():
    from app.modules.bookmark import service as bookmarks
    from app.modules.bookmark.schemas import CaptureIn

    async with SessionLocal() as db:
        body = CaptureIn(client_uuid=uuid4(), url="https://example.test/legacy", title="Legacy")
        original, _, _ = await bookmarks.capture(db, body, commit=False)
        await db.commit()  # simulate a pre-0080 receiptless bookmark
        identity = original.id
        with pytest.raises(HTTPException) as error:
            await bookmarks.capture(db, body.model_copy(update={"title": "Different"}))
        assert error.value.status_code == 409
        await db.rollback()
        repeated, replayed, _ = await bookmarks.capture(db, body)
        assert repeated.id == identity and replayed


@pytest.mark.no_database
async def test_profile_rejects_hooks_cron_and_cloud(tmp_path, monkeypatch):
    from pathlib import Path

    import yaml

    config = yaml.safe_load(
        (Path(__file__).parents[2] / "config/hermes-goal-studio/config.yaml").read_text()
    )
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config))
    monkeypatch.setattr(settings, "hermes_goal_profile_config", str(path))
    assert studio_transport.verified_profile()["platform_toolsets"]["api_server"] == []
    (tmp_path / "hooks").mkdir()
    hook = tmp_path / "hooks" / "hook.py"
    hook.write_text("raise RuntimeError('must never execute')")
    with pytest.raises(ValueError, match="hook"):
        studio_transport.verified_profile()
    hook.unlink()
    (tmp_path / "cron").mkdir()
    jobs = tmp_path / "cron" / "jobs.json"
    jobs.write_text('{"jobs":[{"command":"unsafe"}]}')
    with pytest.raises(ValueError, match="zamanlanmış"):
        studio_transport.verified_profile()
    jobs.write_text('{"jobs":[]}')
    assert studio_transport.verified_profile()
    config["model"]["base_url"] = "https://cloud.example/v1"
    path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match="loopback"):
        studio_transport.verified_profile()


@pytest.mark.no_database
async def test_public_sse_drops_reasoning_and_sensitive_tool_payload(monkeypatch):
    import httpx

    async def ready():
        pass

    monkeypatch.setattr(studio_transport, "require_ready", ready)

    async def inference(*args, **kwargs):
        return {"id": "f" * 64, "provider": "custom", "model": "fixture", "local": True}

    monkeypatch.setattr(studio_transport, "require_inference", inference)
    monkeypatch.setattr(settings, "hermes_goal_base_url", "http://127.0.0.1:8643")
    original_client = httpx.AsyncClient
    stream = (
        "\n\n".join(
            [
                'event: reasoning.delta\ndata: {"delta":"private reasoning"}',
                'event: message.delta\ndata: {"delta":"public answer"}',
                'event: tool.call\ndata: {"args":{"secret":"never display"}}',
            ]
        )
        + "\n\n"
    )
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text=stream))
    monkeypatch.setattr(
        studio_transport.httpx,
        "AsyncClient",
        lambda **kwargs: original_client(transport=transport, **kwargs),
    )
    result = "".join([chunk async for chunk in studio_transport.public_events("fixture")])
    assert "public answer" not in result and "blocked_tool_event" in result
    assert (
        "private reasoning" not in result
        and "secret" not in result
        and "never display" not in result
    )


async def test_patch_omissions_survive_proposal_storage_and_ui_roundtrip():
    from datetime import UTC, datetime

    from app.modules.goal.schemas import GoalMilestoneIn

    async with SessionLocal() as db:
        parent = await service.create_goal(db, GoalIn(title="Parent"))
        goal = await service.create_goal(
            db,
            GoalIn(
                title="Original",
                description="Preserve",
                parent_goal_id=parent.id,
                priority=3,
                weight=2,
            ),
        )
        due = datetime(2027, 3, 1, tzinfo=UTC)
        step = await service.add_goal_milestone(
            db, goal.id, GoalMilestoneIn(title="Step", due_at=due)
        )
        item = await session(db, goal.id)
        body = StudioProposal.model_validate(
            {
                "rationale": "Only rename",
                "operations": [
                    {
                        "type": "goal.update",
                        "key": "goal",
                        "target_id": str(goal.id),
                        "data": {"title": "Renamed"},
                    },
                    {
                        "type": "milestone.update",
                        "key": "step",
                        "target_id": str(step.id),
                        "data": {"title": "Renamed step"},
                    },
                ],
            }
        )
        draft = await studio.revise(db, await studio.get_session(db, item.id), body)
        payload = draft.revision.proposal.model_dump(mode="json")
        assert payload["operations"][0]["data"] == {"title": "Renamed"}
        assert payload["operations"][1]["data"] == {"title": "Renamed step"}
        # Simulate browser changing and returning only the proposed title.
        payload["operations"][0]["data"]["title"] = "UI rename"
        draft = await studio.revise(
            db, await studio.get_session(db, item.id), StudioProposal.model_validate(payload)
        )
        assert (await decision(db, draft)).state == "applied"
        result = await service.get_goal(db, goal.id)
        assert result.title == "UI rename" and result.description == "Preserve"
        assert result.parent_goal_id == parent.id and result.priority == 3 and result.weight == 2
        assert result.milestones[0].due_at == due
