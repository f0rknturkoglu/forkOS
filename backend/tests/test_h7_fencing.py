"""H7 fencing: devralınan yürütme eski yürütücüyü KESİN olarak durdurur."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.modules.execution import execution as execution_mod
from app.modules.execution import service
from app.modules.execution.models import (
    EXECUTOR_STALE_AFTER_SECONDS,
    ExecutionDecision,
    ExecutionPlan,
    ExecutionReceipt,
)
from app.modules.todo.models import Todo

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)
STALE = NOW + timedelta(seconds=EXECUTOR_STALE_AFTER_SECONDS + 5)


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


def _steps(*titles: str) -> list[dict]:
    return [
        {"step_id": f"s{i + 1}", "action": "todo_create", "arguments": {"title": t}}
        for i, t in enumerate(titles or ("Görev",))
    ]


async def _approved(session: AsyncSession, steps: list[dict]) -> ExecutionPlan:
    plan = await service.prepare(session, title="Plan", steps=steps, now=NOW)
    return await service.approve(session, plan_row_id=plan.id, now=NOW)


async def _zombie_setup(session: AsyncSession, steps: list[dict]) -> tuple[ExecutionPlan, str]:
    """A sahiplenir, B bayat lease'i devralır; A'nın jetonu döner (zombi)."""
    plan = await _approved(session, steps)
    token_a = await execution_mod.claim_plan(session, plan, now=NOW)
    assert token_a is not None
    await session.commit()

    async with SessionLocal() as other:
        _plan_b, _outcome = await service.recover(other, plan_row_id=plan.id, now=STALE)
    return plan, token_a


# ---------------------------------------------------------------------------
# F1-F3 — jeton üretimi
# ---------------------------------------------------------------------------


async def test_f1_normal_execution_receives_a_unique_attempt_token(
    db_session: AsyncSession,
) -> None:
    plan = await _approved(db_session, _steps("Tek"))
    token = await execution_mod.claim_plan(db_session, plan, now=NOW)
    await db_session.commit()
    assert token
    await db_session.refresh(plan)
    assert plan.executor_token == token


async def test_f2_separate_plans_receive_different_tokens(db_session: AsyncSession) -> None:
    first = await _approved(db_session, _steps("Bir"))
    second = await _approved(db_session, _steps("İki"))
    token_one = await execution_mod.claim_plan(db_session, first, now=NOW)
    await db_session.commit()
    token_two = await execution_mod.claim_plan(db_session, second, now=NOW)
    await db_session.commit()
    assert token_one and token_two and token_one != token_two


async def test_f3_recovery_receives_a_new_token(db_session: AsyncSession) -> None:
    plan, token_a = await _zombie_setup(db_session, _steps("Kurtarma"))
    await db_session.refresh(plan)
    assert plan.executor_token and plan.executor_token != token_a


# ---------------------------------------------------------------------------
# F4-F8 — zombi yürütücü DURDURULUR
# ---------------------------------------------------------------------------


async def test_f4_heartbeat_requires_matching_token(db_session: AsyncSession) -> None:
    plan = await _approved(db_session, _steps("Kalp"))
    token = await execution_mod.claim_plan(db_session, plan, now=NOW)
    await db_session.commit()
    assert await execution_mod.touch_heartbeat(db_session, plan.id, token=token, now=NOW) is True
    assert (
        await execution_mod.touch_heartbeat(db_session, plan.id, token="yanlis", now=NOW) is False
    )


async def test_f5_f6_f7_f8_zombie_executor_is_fenced(db_session: AsyncSession) -> None:
    """F5-F8: devralma sonrası eski yürütücü hiçbir şey YAPAMAZ."""
    plan, token_a = await _zombie_setup(db_session, _steps("Zombi bir", "Zombi iki", "Zombi üç"))
    await db_session.refresh(plan)
    token_b = plan.executor_token
    assert token_b and token_b != token_a
    heartbeat_after_recovery = plan.execution_heartbeat_at

    # F5: eski yürütücü kalp atışı YAZAMAZ ve yeni sahibin lease'ini bozamaz.
    assert await execution_mod.touch_heartbeat(db_session, plan.id, token=token_a, now=STALE) is False
    await db_session.commit()
    await db_session.refresh(plan)
    assert plan.execution_heartbeat_at == heartbeat_after_recovery
    assert plan.executor_token == token_b

    # Kazanan (B) kendi adımlarını yürütmüş olabilir; zombi EK mutasyon
    # üretmemelidir: sayı önce/sonra AYNI kalmalı.
    todos_after_b = len(list((await db_session.execute(select(Todo))).scalars()))

    # F6/F8: eski yürütücü ADIM BAŞLATAMAZ.
    outcome = await execution_mod.execute_plan(
        db_session, plan, token=token_a, now=STALE + timedelta(seconds=1)
    )
    assert outcome.failure_code == "EXECUTION_OWNERSHIP_LOST"
    assert outcome.steps == []
    await db_session.commit()
    assert len(list((await db_session.execute(select(Todo))).scalars())) == todos_after_b

    # F7: eski yürütücü planı FINALIZE EDEMEZ.
    finalized = await execution_mod.finalize_if_owner(
        db_session,
        plan.id,
        token=token_a,
        final_status="completed",
        failure_code=None,
        now=STALE,
    )
    assert finalized is False
    await db_session.commit()
    await db_session.refresh(plan)
    assert plan.final_status != "completed" or plan.executor_token == token_b

    # Kazanan (B) kendi akışında finalize etmiştir: plan terminal durumdadır ve
    # zombi bu durumu EZEMEDİ.
    assert plan.state in {"completed", "partial", "failed"}
    assert plan.final_status in {"completed", "partial", "failed"}


async def test_f13_long_running_action_takeover_stops_before_next_step(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F13/F14: adım sürerken devralma olursa SONRAKİ adım başlamaz."""
    plan = await _approved(db_session, _steps("Uzun bir", "Uzun iki"))
    token_a = await execution_mod.claim_plan(db_session, plan, now=NOW)
    await db_session.commit()
    await db_session.refresh(plan)

    real_run = execution_mod.run_action
    calls: list[str] = []

    async def slow_run(session, spec, data):  # type: ignore[no-untyped-def]
        calls.append(spec.name)
        result = await real_run(session, spec, data)
        # H1 aksiyonu ÇALIŞIRKEN başka bir yürütücü sahipliği devralır.
        if len(calls) == 1:
            async with SessionLocal() as other:
                row = await other.get(ExecutionPlan, plan.id)
                assert row is not None
                row.executor_token = "token-b"
                row.execution_heartbeat_at = STALE
                await other.commit()
        return result

    monkeypatch.setattr(execution_mod, "run_action", slow_run)

    outcome = await execution_mod.execute_plan(
        db_session, plan, token=token_a or "", now=NOW
    )

    assert calls == ["todo_create"], "devralma sonrası İKİNCİ adım başlamamalı"
    assert outcome.failure_code == "EXECUTION_OWNERSHIP_LOST"
    assert outcome.steps[0].status in {"unresolved", "completed"}
    todos = list((await db_session.execute(select(Todo))).scalars())
    assert len(todos) == 1, "kanonik etki TEKRARLANMAMALI"


# ---------------------------------------------------------------------------
# F9-F10 — kurtarma yarışı ve canlı sahip
# ---------------------------------------------------------------------------


async def test_f9_concurrent_recovery_has_exactly_one_owner(db_session: AsyncSession) -> None:
    plan = await _approved(db_session, _steps("Yarış"))
    await execution_mod.claim_plan(db_session, plan, now=NOW)
    await db_session.commit()

    async def recover() -> str:
        async with SessionLocal() as session:
            try:
                await service.recover(session, plan_row_id=plan.id, now=STALE)
                return "ok"
            except service.ExecutionPlanError as exc:
                return exc.code

    results = await asyncio.gather(recover(), recover())
    async with SessionLocal() as session:
        refreshed = await session.get(ExecutionPlan, plan.id)
        todos = list((await session.execute(select(Todo))).scalars())
    assert sorted(results).count("ok") == 1, results
    assert len(todos) == 1
    assert refreshed is not None and refreshed.state == "completed"


async def test_f10_active_executor_cannot_be_stolen_and_state_unchanged(
    db_session: AsyncSession,
) -> None:
    plan = await _approved(db_session, _steps("Canlı"))
    token = await execution_mod.claim_plan(db_session, plan, now=NOW)
    await db_session.commit()
    await db_session.refresh(plan)
    before = (plan.executor_token, plan.execution_heartbeat_at)

    async with SessionLocal() as other:
        with pytest.raises(service.ExecutionPlanError, match="PLAN_ACTIVE_EXECUTOR"):
            await service.recover(other, plan_row_id=plan.id, now=NOW + timedelta(seconds=10))

    await db_session.refresh(plan)
    assert (plan.executor_token, plan.execution_heartbeat_at) == before
    assert plan.executor_token == token


# ---------------------------------------------------------------------------
# F11-F12 — makbuz sahipliği
# ---------------------------------------------------------------------------


async def test_f11_claimed_receipt_from_old_owner_is_unresolved(
    db_session: AsyncSession,
) -> None:
    """A'nın talep ettiği adım: B MUTABAKAT ister, körlemesine tekrarlamaz."""
    plan = await _approved(db_session, _steps("A talep etti"))
    await execution_mod.claim_plan(db_session, plan, now=NOW)
    db_session.add(
        ExecutionReceipt(
            plan_row_id=plan.id,
            step_id="s1",
            ordinal=0,
            action="todo_create",
            idempotency_key=f"{plan.revision}:s1",
            status="not_attempted",
            started_at=NOW,
            claimed_by="token-a",
        )
    )
    await db_session.commit()

    _plan_b, outcome = await service.recover(db_session, plan_row_id=plan.id, now=STALE)

    assert outcome.steps[0].status == "unresolved"
    assert outcome.failure_code == "RECONCILIATION_REQUIRED"
    assert list((await db_session.execute(select(Todo))).scalars()) == []
    # Tarihsel `claimed_by` YENİDEN YAZILMAZ: A o adımı talep etmişti.
    receipt = (
        await db_session.execute(
            select(ExecutionReceipt).where(ExecutionReceipt.plan_row_id == plan.id)
        )
    ).scalar_one()
    assert receipt.claimed_by == "token-a"


async def test_f12_unclaimed_not_attempted_receipt_remains_resumable(
    db_session: AsyncSession,
) -> None:
    plan = await _approved(db_session, _steps("Talep edilmedi"))
    await execution_mod.claim_plan(db_session, plan, now=NOW)
    db_session.add(
        ExecutionReceipt(
            plan_row_id=plan.id,
            step_id="s1",
            ordinal=0,
            action="todo_create",
            idempotency_key=f"{plan.revision}:s1",
            status="not_attempted",
            started_at=NOW,
            claimed_by=None,  # hiç talep edilmedi
        )
    )
    await db_session.commit()

    _plan_b, outcome = await service.recover(db_session, plan_row_id=plan.id, now=STALE)

    assert outcome.final_status == "completed"
    assert len(list((await db_session.execute(select(Todo))).scalars())) == 1


# ---------------------------------------------------------------------------
# F15-F16 — sözleşme ve denetim dürüstlüğü
# ---------------------------------------------------------------------------


async def test_f15_mcp_description_and_schema_include_recover() -> None:
    from app.integrations.agent.mcp import mcp_server

    tools = {tool.name: tool for tool in await mcp_server.list_tools()}
    tool = tools["forkos_execution"]
    assert "recover" in tool.input_schema["properties"]["operation"]["enum"]
    assert "recover" in (tool.description or "")


async def test_f16_not_attempted_is_not_recorded_as_failed(db_session: AsyncSession) -> None:
    """H7.1 §20: hiç denenmeyen adım sahte HATA geçmişi üretmez."""
    from app.core.models import Entity
    from tests.h5_fixtures import make_todo

    victim = await make_todo(db_session, title="Silinecek hedef")
    await db_session.commit()
    plan = await _approved(
        db_session,
        [
            {"step_id": "s1", "action": "todo_create", "arguments": {"title": "A"}},
            {
                "step_id": "s2",
                "action": "todo_complete",
                "arguments": {"todo_id": str(victim.id)},
            },
            {"step_id": "s3", "action": "todo_create", "arguments": {"title": "Asla"}},
        ],
    )
    # Hedef onaydan SONRA silinir: s2 yürütme anında düşer, s3 DENENMEZ.
    from sqlalchemy import delete

    await db_session.execute(delete(Todo).where(Todo.id == victim.id))
    await db_session.execute(delete(Entity).where(Entity.id == victim.id))
    await db_session.commit()
    await service.execute(db_session, plan_row_id=plan.id, now=NOW)

    kinds = [
        row.kind
        for row in (
            await db_session.execute(
                select(ExecutionDecision).where(ExecutionDecision.plan_row_id == plan.id)
            )
        ).scalars()
    ]
    # s3 HİÇ DENENMEDİ: denetim izinde "başarısız" olarak GEÇMEZ.
    assert "step_not_attempted" in kinds
    assert kinds.count("step_failed") == 1, kinds
