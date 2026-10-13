"""Provider policy, consent and actual Hermes API shapes; no paid inference or OAuth login."""

import copy
import json
from pathlib import Path
from uuid import uuid4

import pytest
import yaml
from fastapi import HTTPException

from app.config import settings
from app.db import SessionLocal
from app.modules.goal import studio
from app.modules.goal import studio_policy as policy
from app.modules.goal import studio_transport as transport
from app.modules.goal.studio_schemas import StudioConsentIn, StudioSessionIn, StudioTurnIn
from app.modules.system import export, restore
from app.modules.system.models import Setting

REAL_MODEL_READY = transport.local_model_ready


@pytest.fixture
def profile(tmp_path, monkeypatch):
    config = yaml.safe_load(
        (Path(__file__).parents[2] / "config/hermes-goal-studio/config.yaml").read_text()
    )
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config))
    monkeypatch.setattr(settings, "hermes_goal_profile_config", str(path))
    monkeypatch.setattr(settings, "hermes_goal_api_key", "fixture-private-key")
    monkeypatch.setattr(settings, "hermes_goal_base_url", "http://127.0.0.1:8643")
    monkeypatch.setattr(settings, "hermes_goal_topology", "native")
    return config, path


@pytest.fixture
def api(monkeypatch):
    replies = {
        "/health": {"status": "ok", "version": "0.21.6"},
        "/health/detailed": {"status": "ok", "readiness": {"status": "ok"}},
        "/v1/toolsets": [{"name": "terminal", "enabled": False, "tools": ["terminal"]}],
        "/v1/capabilities": {
            "object": "hermes.api_server.capabilities",
            "model": "forkos-goal-studio",
            "auth": {"required": True},
            "features": {
                "run_submission": True,
                "run_status": True,
                "run_events_sse": True,
                "run_stop": True,
                "runs_idempotency": {
                    "supported": True,
                    "durable": True,
                    "retention_seconds": 86400,
                },
                "browser_extension_control": {"enabled": False},
                "cors": False,
            },
            "endpoints": {"runs": {"method": "POST", "path": "/v1/runs"}},
        },
    }

    async def request(method, path, **kwargs):
        return copy.deepcopy(replies[path])

    async def model_ready(config):
        return None

    monkeypatch.setattr(transport, "request", request)
    monkeypatch.setattr(transport, "local_model_ready", model_ready)
    return replies


def choose(profile, provider):
    config, path = profile
    config["model"] = {"provider": provider, "default": "fixture-model"}
    if provider == "custom":
        config["model"]["base_url"] = "http://127.0.0.1:18435/v1"
    path.write_text(yaml.safe_dump(config))
    return policy.binding(config)


@pytest.mark.no_database
@pytest.mark.parametrize("provider", ["custom", "openai-codex", "nous"])
async def test_connection_metadata_is_not_claimed_as_inference(profile, api, provider):
    current = choose(profile, provider)
    result = await transport.status()
    assert result.state == "ready" and result.configured_model == "fixture-model"
    assert result.provider == current["mode"] and result.tools_verified
    assert "fixture-private-key" not in result.model_dump_json()


@pytest.mark.no_database
@pytest.mark.parametrize(
    "change",
    [
        "prefix",
        "host",
        "tools",
        "inherit",
        "provider",
        "routing",
        "version",
        "shape",
        "mcp",
        "browser",
        "auth",
        "durability",
    ],
)
async def test_untrusted_topology_or_capabilities_fail_closed(profile, api, monkeypatch, change):
    config, path = profile
    if change == "prefix":
        monkeypatch.setattr(
            settings, "hermes_goal_base_url", "http://127.0.0.1:8643/p/forkos-goal-studio"
        )
        with pytest.raises(ValueError):
            transport.loopback(settings.hermes_goal_base_url, profile=True)
        return
    if change == "host":
        with pytest.raises(ValueError):
            transport.loopback("http://evil.invalid:8643", profile=True)
        return
    if change == "tools":
        api["/v1/toolsets"][0]["enabled"] = True
    if change == "inherit":
        config["auth"]["adopt_external_logins"] = True
    if change == "provider":
        config["model"]["provider"] = "anthropic"
    if change == "routing":
        config["model"]["api"] = "codex-app-server"
    if change == "version":
        api["/health"]["version"] = "future"
    if change == "shape":
        api["/v1/toolsets"] = {"tools": []}
    if change == "mcp":
        config["mcp_servers"] = {"shell": {"command": "sh"}}
    if change == "browser":
        api["/v1/capabilities"]["features"]["browser_extension_control"]["enabled"] = True
    if change == "auth":
        api["/v1/capabilities"]["auth"]["required"] = False
    if change == "durability":
        api["/v1/capabilities"]["features"]["runs_idempotency"]["durable"] = False
    path.write_text(yaml.safe_dump(config))
    assert (await transport.status()).state == "unsupported"


@pytest.mark.no_database
@pytest.mark.parametrize("provider", ["custom", "openai-codex", "nous"])
async def test_wrong_key_expired_auth_and_provider_unavailable(profile, monkeypatch, provider):
    choose(profile, provider)

    async def rejected(*args, **kwargs):
        raise HTTPException(
            503, "Hermes/profil/model kimlik doğrulaması geçersiz veya süresi dolmuş"
        )

    monkeypatch.setattr(transport, "request", rejected)
    result = await transport.status()
    assert result.state == "unavailable" and "fixture-private-key" not in result.model_dump_json()


@pytest.mark.parametrize("provider", ["openai-codex", "nous"])
async def test_cloud_permission_cas_provider_model_binding_and_revoke(profile, api, provider):
    current = choose(profile, provider)
    async with SessionLocal() as db:
        result = await transport.status(db)
        assert result.state == "consent_required" and not result.consent.allowed
        with pytest.raises(HTTPException) as denied:
            await transport.require_inference(db)
        assert denied.value.status_code == 403
        await db.rollback()
        granted = await policy.update_consent(
            db,
            StudioConsentIn(
                revision=result.consent.revision, policy_id=current["id"], allowed=True
            ),
        )
        assert (await transport.require_inference(db))["id"] == current["id"]
        await db.rollback()
        with pytest.raises(HTTPException) as stale:
            await policy.update_consent(
                db,
                StudioConsentIn(
                    revision=result.consent.revision, policy_id=current["id"], allowed=False
                ),
            )
        assert stale.value.status_code == 409
        await db.rollback()
        choose(profile, "nous" if provider == "openai-codex" else "openai-codex")
        assert (await transport.status(db)).state == "consent_required"
        with pytest.raises(HTTPException) as changed:
            await transport.require_inference(db, expected_policy=current["id"])
        assert changed.value.status_code == 409
        await db.rollback()
        # Broken configuration cannot prevent revocation.
        profile[1].write_text("broken: [")
        revoked = await policy.update_consent(
            db, StudioConsentIn(revision=granted.revision, allowed=False)
        )
        assert not revoked.allowed


@pytest.mark.parametrize("provider", ["custom", "openai-codex", "nous"])
async def test_validated_turn_runtime_replay_and_provider_mismatch(
    profile, api, monkeypatch, provider
):
    current = choose(profile, provider)
    original = transport.request
    calls = []
    actual = {"provider": provider, "model": "fixture-model"}

    async def run_request(method, path, **kwargs):
        if path == "/v1/runs":
            calls.append(kwargs)
            return {"run_id": "run-fixture"}
        if path == "/v1/runs/run-fixture":
            return {
                "status": "completed",
                "runtime": actual,
                "output": json.dumps({"discussion": "Doğrulanmış yanıt", "proposal": None}),
            }
        return await original(method, path, **kwargs)

    monkeypatch.setattr(transport, "request", run_request)
    async with SessionLocal() as db:
        if provider != "custom":
            state = await transport.status(db)
            await policy.update_consent(
                db,
                StudioConsentIn(
                    revision=state.consent.revision, policy_id=current["id"], allowed=True
                ),
            )
        item = await studio.start(db, StudioSessionIn(client_uuid=uuid4()))
        body = StudioTurnIn(client_uuid=uuid4(), message="Hedefimi konuşalım")
        result = await studio.turn(db, await studio.get_session(db, item.id), body)
        assert result.state == "running" and calls[0]["body"]["provider"] == provider
        result = await studio.turn(db, await studio.get_session(db, item.id), body)
        assert len(calls) == 1 and result.runtime.provider == provider
        assert result.messages[-1]["text"] == "Doğrulanmış yanıt"
        with pytest.raises(HTTPException) as conflict:
            await studio.turn(
                db,
                await studio.get_session(db, item.id),
                StudioTurnIn(client_uuid=body.client_uuid, message="Farklı"),
            )
        assert conflict.value.status_code == 409
        await db.rollback()
        second = await studio.turn(
            db,
            await studio.get_session(db, item.id),
            StudioTurnIn(client_uuid=uuid4(), message="İkinci tur"),
        )
        actual["model"] = "unapproved-model"
        failed = await studio.reconcile(db, await studio.get_session(db, second.id))
        assert failed.state == "failed" and len(failed.messages) == len(result.messages) + 1


async def test_backup_cannot_restore_authorization():
    async with SessionLocal() as db:
        db.add(Setting(key=policy.KEY, value={"allowed": True}))
        await db.commit()
        payload = await export.full_json(db)
        assert policy.KEY not in {row["key"] for row in payload["modules"]["setting"]}
        summary = await restore.restore(
            db,
            {
                "entities": [],
                "links": [],
                "events": [],
                "modules": {"setting": [{"key": policy.KEY, "value": {"allowed": True}}]},
            },
        )
        assert summary["setting"]["secret_skipped"] == 1


@pytest.mark.no_database
@pytest.mark.parametrize(
    "runtime",
    [
        None,
        {"provider": "custom", "model": "other"},
        {"provider": "nous", "model": "fixture-model"},
    ],
)
def test_runtime_is_actual_not_gateway_alias(runtime):
    with pytest.raises(HTTPException):
        transport.verified_runtime(
            {"runtime": runtime}, {"provider": "custom", "model": "fixture-model"}
        )


async def test_revoke_between_durable_identity_and_http_blocks_delivery(profile, api, monkeypatch):
    current = choose(profile, "nous")
    original = transport.require_inference
    checks = 0
    async with SessionLocal() as db:
        state = await transport.status(db)
        granted = await policy.update_consent(
            db,
            StudioConsentIn(revision=state.consent.revision, policy_id=current["id"], allowed=True),
        )

        async def revoke_before_post(db, **kwargs):
            nonlocal checks
            checks += 1
            if checks == 2:
                async with SessionLocal() as other:
                    await policy.update_consent(
                        other, StudioConsentIn(revision=granted.revision, allowed=False)
                    )
            return await original(db, **kwargs)

        monkeypatch.setattr(transport, "require_inference", revoke_before_post)
        item = await studio.start(db, StudioSessionIn(client_uuid=uuid4()))
        body = StudioTurnIn(client_uuid=uuid4(), message="Selected bounded context")
        # api fixture has no POST /v1/runs entry: any submission would fail the test.
        result = await studio.turn(db, await studio.get_session(db, item.id), body)
        assert result.state == "delivery_blocked" and result.pending_turn == body
        assert "geri alındı" in result.error
        stopped = await studio.stop(db, await studio.get_session(db, item.id))
        assert stopped.state == "drafting" and stopped.messages == result.messages


@pytest.mark.no_database
@pytest.mark.parametrize("missing", [True, False])
async def test_local_model_absent_or_offline_is_not_ready(profile, api, monkeypatch, missing):
    async def model_json(*args, **kwargs):
        if missing:
            return {"data": []}
        raise HTTPException(503, "Yerel model erişilemiyor")

    monkeypatch.setattr(transport, "_json", model_json)
    monkeypatch.setattr(transport, "local_model_ready", REAL_MODEL_READY)
    assert (await transport.status()).state == "unavailable"


@pytest.mark.no_database
async def test_supported_wrapper_and_unknown_metadata_fail_closed():
    transport.verify_toolsets({"object": "list", "platform": "api_server", "data": []}, "0.21.6")
    with pytest.raises(ValueError):
        transport.verify_toolsets({"object": "list", "platform": "other", "data": []}, "0.21.6")


@pytest.mark.no_database
@pytest.mark.parametrize(
    "value",
    [
        '{"discussion": "partial"',
        '{"discussion":"visible","reasoning_content":"private"}',
        "approved=true raw_sql=DROP TABLE goal",
        "<think>private reasoning</think>answer",
        '{"discussion":"<analysis>private</analysis>","proposal":null}',
        "x" * 6001,
    ],
)
def test_public_final_does_not_render_broken_structured_or_private_payload(value):
    with pytest.raises(ValueError):
        studio.public_reply(value)


async def test_attributed_plain_final_is_only_discussion_no_proposal(profile, api, monkeypatch):
    choose(profile, "custom")
    original = transport.request

    async def response(method, path, **kwargs):
        if path == "/v1/runs":
            return {"run_id": "plain-final"}
        if path == "/v1/runs/plain-final":
            return {
                "status": "completed",
                "runtime": {"provider": "custom", "model": "fixture-model"},
                "output": "Merhaba!",
            }
        return await original(method, path, **kwargs)

    monkeypatch.setattr(transport, "request", response)
    async with SessionLocal() as db:
        item = await studio.start(db, StudioSessionIn(client_uuid=uuid4()))
        await studio.turn(
            db,
            await studio.get_session(db, item.id),
            StudioTurnIn(client_uuid=uuid4(), message="Selam"),
        )
        result = await studio.reconcile(db, await studio.get_session(db, item.id))
        assert result.state == "drafting" and result.error is None and result.revision is None
        assert result.messages[-1] == {"role": "assistant", "text": "Merhaba!"}


@pytest.mark.no_database
async def test_invalid_port_never_echoes_pasted_secret(profile, api, monkeypatch):
    secret = "fixture-secret-not-for-response"
    monkeypatch.setattr(settings, "hermes_goal_base_url", "http://127.0.0.1:" + secret)
    with pytest.raises(ValueError) as invalid:
        transport.loopback(settings.hermes_goal_base_url, profile=True)
    assert secret not in str(invalid.value)


@pytest.mark.parametrize("lost_response", [False, True])
async def test_invalid_draft_gets_one_durable_model_correction(
    profile, api, monkeypatch, lost_response
):
    choose(profile, "custom")
    original = transport.request
    calls = []
    invalid = {
        "kind": "goal",
        "title": "YDS 60+",
        "description": "Günde 4 saat.",
        "manual_value": 60,
    }
    valid = {key: value for key, value in invalid.items() if key != "manual_value"}

    async def request(method, path, **kwargs):
        if path == "/v1/runs":
            calls.append(kwargs)
            if len(calls) == 2 and lost_response:
                raise HTTPException(503, "fixture lost response")
            return {"run_id": "original" if len(calls) == 1 else "correction"}
        if path in {"/v1/runs/original", "/v1/runs/correction"}:
            return {
                "status": "completed",
                "runtime": {"provider": "custom", "model": "fixture-model"},
                "output": json.dumps(
                    {
                        "discussion": "Taslağın hazır.",
                        "proposal": invalid if path.endswith("original") else valid,
                    }
                ),
            }
        return await original(method, path, **kwargs)

    monkeypatch.setattr(transport, "request", request)
    async with SessionLocal() as db:
        item = await studio.start(db, StudioSessionIn(client_uuid=uuid4()))
        body = StudioTurnIn(client_uuid=uuid4(), message="YDS hedefi hazırla")
        await studio.turn(db, await studio.get_session(db, item.id), body)
        result = await studio.reconcile(db, await studio.get_session(db, item.id))
        if lost_response:
            assert result.state == "unknown_delivery"
            result = await studio.turn(db, await studio.get_session(db, item.id), body)
            assert calls[1] == calls[2] and calls[1]["identity"].endswith("-repair")
        result = await studio.reconcile(db, await studio.get_session(db, item.id))
        assert result.state == "approval_pending" and result.error is None
        assert sum(message["role"] == "user" for message in result.messages) == 1
        assert len(calls) == (3 if lost_response else 2)
        from sqlalchemy import func, select

        from app.modules.goal.models import Goal

        assert await db.scalar(select(func.count()).select_from(Goal)) == 0


async def test_correction_is_bounded_if_model_repeats_invalid_fields(profile, api, monkeypatch):
    choose(profile, "custom")
    original = transport.request
    calls = []

    async def request(method, path, **kwargs):
        if path == "/v1/runs":
            calls.append(kwargs)
            return {"run_id": "run-fixture"}
        if path == "/v1/runs/run-fixture":
            return {
                "status": "completed",
                "runtime": {"provider": "custom", "model": "fixture-model"},
                "output": json.dumps(
                    {
                        "discussion": "Draft",
                        "proposal": {
                            "kind": "goal",
                            "title": "YDS",
                            "description": "Study",
                            "approved": True,
                        },
                    }
                ),
            }
        return await original(method, path, **kwargs)

    monkeypatch.setattr(transport, "request", request)
    async with SessionLocal() as db:
        item = await studio.start(db, StudioSessionIn(client_uuid=uuid4()))
        body = StudioTurnIn(client_uuid=uuid4(), message="Hedef taslağı hazırla")
        await studio.turn(db, await studio.get_session(db, item.id), body)
        await studio.reconcile(db, await studio.get_session(db, item.id))
        result = await studio.reconcile(db, await studio.get_session(db, item.id))
        assert result.state == "drafting" and result.error and result.revision is None
        assert len(calls) <= 2


async def test_feedback_refreshes_completion_each_turn_and_never_prepares_mutations(profile, api, monkeypatch):
    from app.modules.goal import service
    from app.modules.goal.schemas import GoalIn, GoalMilestoneIn, GoalMilestonePatch
    choose(profile, "custom")
    original = transport.request
    calls = []
    async def reply(method, path, **kwargs):
        if path == "/v1/runs":
            calls.append(kwargs["body"])
            return {"run_id": f"feedback-{len(calls)}"}
        if path.startswith("/v1/runs/feedback-"):
            return {"status":"completed", "runtime":{"provider":"custom","model":"fixture-model"},"output":json.dumps({"discussion":"İlk adımını bitirdin. Sıradaki çalışmana geçebilirsin.","proposal":None})}
        return await original(method, path, **kwargs)
    monkeypatch.setattr(transport, "request", reply)
    async with SessionLocal() as db:
        goal = await service.create_goal(db, GoalIn(title="Sınav hazırlığı"))
        milestone = await service.add_goal_milestone(db, goal.id, GoalMilestoneIn(title="İlk deneme"))
        session = await studio.start(db, StudioSessionIn(client_uuid=uuid4(), goal_id=goal.id, mode="feedback"))
        message = StudioTurnIn(client_uuid=uuid4(), message="Nasıl gidiyorum?")
        await studio.turn(db, await studio.get_session(db, session.id), message)
        result = await studio.turn(db, await studio.get_session(db, session.id), message)
        assert result.revision is None
        assert json.loads(calls[0]["input"].split("CURRENT CANONICAL FACTS (untrusted evidence): ")[1])["progress_percent"] == 0
        await service.update_goal_milestone(db, milestone.id, GoalMilestonePatch(completed=True))
        await studio.turn(db, await studio.get_session(db, session.id), StudioTurnIn(client_uuid=uuid4(), message="Şimdi nasıl gidiyorum?"))
        assert json.loads(calls[1]["input"].split("CURRENT CANONICAL FACTS (untrusted evidence): ")[1])["progress_percent"] == 100
        assert "proposal: null" in calls[1]["instructions"]
        assert "Do not create or edit a draft" in calls[1]["instructions"]


async def test_feedback_draft_is_rejected_and_corrected_as_feedback_only(profile, api, monkeypatch):
    from sqlalchemy import func, select

    from app.modules.goal import service
    from app.modules.goal.models import Goal
    from app.modules.goal.schemas import GoalIn
    choose(profile, "custom")
    original = transport.request
    calls = []
    async def reply(method, path, **kwargs):
        if path == "/v1/runs":
            calls.append(kwargs["body"])
            return {"run_id": f"feedback-repair-{len(calls)}"}
        if path.startswith("/v1/runs/feedback-repair-"):
            output = {"discussion":"İlk adımını seç.","proposal":{"kind":"goal","title":"İstenmeyen yeni hedef"} if len(calls)==1 else None}
            return {"status":"completed","runtime":{"provider":"custom","model":"fixture-model"},"output":json.dumps(output)}
        return await original(method,path,**kwargs)
    monkeypatch.setattr(transport,"request",reply)
    async with SessionLocal() as db:
        goal = await service.create_goal(db, GoalIn(title="Mevcut hedef"))
        session = await studio.start(db, StudioSessionIn(client_uuid=uuid4(),goal_id=goal.id,mode="feedback"))
        body = StudioTurnIn(client_uuid=uuid4(),message="İlerlemem nasıl?")
        await studio.turn(db,await studio.get_session(db,session.id),body)
        await studio.turn(db,await studio.get_session(db,session.id),body)
        result = await studio.turn(db,await studio.get_session(db,session.id),body)
        assert result.revision is None and result.state == "drafting"
        assert "No proposal, JSON or new work" in calls[1]["input"]
        assert await db.scalar(select(func.count()).select_from(Goal)) == 1
