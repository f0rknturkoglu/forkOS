"""H7.1 — genel yüzeyden kurtarma: lease, devralma, makbuz güvenliği."""

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
    ExecutionPlan,
    ExecutionReceipt,
)
from app.modules.todo.models import Todo

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


def _steps(*titles: str) -> list[dict]:
    return [
        {
            "step_id": f"s{index + 1}",
            "action": "todo_create",
            "arguments": {"title": title},
        }
        for index, title in enumerate(titles or ("Görev",))
    ]


async def _plan(session: AsyncSession, steps: list[dict]) -> ExecutionPlan:
    plan = await service.prepare(session, title="Plan", steps=steps, now=NOW)
    return await service.approve(session, plan_row_id=plan.id, now=NOW)


async def _claim_only(session: AsyncSession, plan: ExecutionPlan) -> None:
    """Süreç, sahipliği aldıktan HEMEN sonra ölmüş gibi davran."""
    assert await execution_mod.claim_plan(session, plan, now=NOW) is not None
    await session.commit()


async def test_r1_crash_after_claim_is_recoverable_from_public_surface(
    db_session: AsyncSession,
) -> None:
    """R1: claim commit edip ölen plan, canlı yürütücü yokken kurtarılabilir."""
    plan = await _plan(db_session, _steps("Kurtarılacak"))
    await _claim_only(db_session, plan)

    # Lease hâlâ taze: sahiplik DEVRALINMAZ (taze okuma için ayrı oturum).
    async with SessionLocal() as other:
        with pytest.raises(service.ExecutionPlanError, match="PLAN_ACTIVE_EXECUTOR"):
            await service.recover(other, plan_row_id=plan.id, now=NOW + timedelta(seconds=5))

    # Eşik geçti: genel yüzeyden kurtarma çalışır ve TEK mutasyon üretir.
    later = NOW + timedelta(seconds=EXECUTOR_STALE_AFTER_SECONDS + 5)
    recovered, outcome = await service.recover(db_session, plan_row_id=plan.id, now=later)

    assert outcome.final_status == "completed"
    assert recovered.state == "completed"
    todos = list((await db_session.execute(select(Todo))).scalars())
    assert len(todos) == 1


async def test_r2_active_executor_cannot_be_stolen(db_session: AsyncSession) -> None:
    """R2: kalp atışı taze olan yürütücü sahiplikten EDİLMEZ."""
    plan = await _plan(db_session, _steps("Canlı"))
    await _claim_only(db_session, plan)

    async with SessionLocal() as other:
        row = await other.get(ExecutionPlan, plan.id)
        assert row is not None
        with pytest.raises(service.ExecutionPlanError, match="PLAN_ACTIVE_EXECUTOR"):
            await service.recover(other, plan_row_id=plan.id, now=NOW + timedelta(seconds=30))


async def test_r3_stale_recovery_has_a_single_owner(db_session: AsyncSession) -> None:
    """R3: iki kurtarıcıdan yalnız BİRİ sahip olur."""
    plan = await _plan(db_session, _steps("Yarış"))
    await _claim_only(db_session, plan)
    later = NOW + timedelta(seconds=EXECUTOR_STALE_AFTER_SECONDS + 5)

    async def recover() -> str:
        async with SessionLocal() as session:
            try:
                await service.recover(session, plan_row_id=plan.id, now=later)
                return "ok"
            except service.ExecutionPlanError as exc:
                return exc.code

    results = await asyncio.gather(recover(), recover())

    async with SessionLocal() as session:
        todos = list((await session.execute(select(Todo))).scalars())
        refreshed = await session.get(ExecutionPlan, plan.id)
    assert sorted(results).count("ok") == 1, results
    assert len(todos) == 1, "kurtarma MÜKERRER mutasyon üretmemeli"
    assert refreshed is not None
    assert refreshed.state in {"completed", "failed", "partial"}


async def test_r4_completed_step_is_not_replayed_after_restart(
    db_session: AsyncSession,
) -> None:
    """R4: tamamlanan adım kurtarmada TEKRAR yürütülmez."""
    plan = await _plan(db_session, _steps("Birinci", "İkinci"))
    await _claim_only(db_session, plan)

    # İlk adım tamamlanmış, ikinci hiç denenmemiş gibi kayıt bırak.
    db_session.add(
        ExecutionReceipt(
            plan_row_id=plan.id,
            step_id="s1",
            ordinal=0,
            action="todo_create",
            idempotency_key=f"{plan.revision}:s1",
            status="completed",
            started_at=NOW,
            completed_at=NOW,
            claimed_by="token-a",
        )
    )
    db_session.add(
        ExecutionReceipt(
            plan_row_id=plan.id,
            step_id="s2",
            ordinal=1,
            action="todo_create",
            idempotency_key=f"{plan.revision}:s2",
            status="not_attempted",
            started_at=NOW,
        )
    )
    await db_session.commit()

    later = NOW + timedelta(seconds=EXECUTOR_STALE_AFTER_SECONDS + 5)
    _recovered, outcome = await service.recover(db_session, plan_row_id=plan.id, now=later)

    statuses = {step.step_id: step.status for step in outcome.steps}
    assert statuses == {"s1": "completed", "s2": "completed"}
    # s1 TEKRAR yürütülmedi: yalnız s2'nin görevi oluştu.
    todos = list((await db_session.execute(select(Todo))).scalars())
    assert len(todos) == 1


async def test_r5_ambiguous_step_requires_reconciliation(db_session: AsyncSession) -> None:
    """R5: sahiplenilmiş ama sonucu bilinmeyen adım körlemesine tekrarlanmaz."""
    plan = await _plan(db_session, _steps("Belirsiz"))
    await _claim_only(db_session, plan)
    db_session.add(
        ExecutionReceipt(
            plan_row_id=plan.id,
            step_id="s1",
            ordinal=0,
            action="todo_create",
            idempotency_key=f"{plan.revision}:s1",
            status="not_attempted",
            started_at=NOW,
            claimed_by="dead-executor",  # talep edildi, sonuç yok
        )
    )
    await db_session.commit()

    later = NOW + timedelta(seconds=EXECUTOR_STALE_AFTER_SECONDS + 5)
    _recovered, outcome = await service.recover(db_session, plan_row_id=plan.id, now=later)

    assert outcome.failure_code == "RECONCILIATION_REQUIRED"
    assert outcome.steps[0].status == "unresolved"
    assert list((await db_session.execute(select(Todo))).scalars()) == []


async def test_r6_recovery_continues_only_untouched_steps(db_session: AsyncSession) -> None:
    """R6: yalnız GÜVENLE sürdürülebilir adımlar devam eder."""
    plan = await _plan(db_session, _steps("A", "B", "C"))
    await _claim_only(db_session, plan)
    db_session.add(
        ExecutionReceipt(
            plan_row_id=plan.id,
            step_id="s1",
            ordinal=0,
            action="todo_create",
            idempotency_key=f"{plan.revision}:s1",
            status="completed",
            started_at=NOW,
            completed_at=NOW,
            claimed_by="token-a",
        )
    )
    await db_session.commit()

    later = NOW + timedelta(seconds=EXECUTOR_STALE_AFTER_SECONDS + 5)
    _recovered, outcome = await service.recover(db_session, plan_row_id=plan.id, now=later)

    assert [step.status for step in outcome.steps] == ["completed", "completed", "completed"]
    todos = list((await db_session.execute(select(Todo))).scalars())
    assert len(todos) == 2  # s1 atlandı, s2+s3 oluştu


async def test_r7_terminal_plan_cannot_resume(db_session: AsyncSession) -> None:
    """R7: terminal plan deterministik olarak reddedilir."""
    plan = await _plan(db_session, _steps("Terminal"))
    await service.execute(db_session, plan_row_id=plan.id, now=NOW)

    with pytest.raises(service.ExecutionPlanError, match="PLAN_NOT_RECOVERABLE"):
        await service.recover(
            db_session, plan_row_id=plan.id, now=NOW + timedelta(seconds=EXECUTOR_STALE_AFTER_SECONDS + 5)
        )


async def test_recovery_does_not_require_new_approval(db_session: AsyncSession) -> None:
    """§28: restart yeni onay gerektirmez; tam revizyon ve onay kaydı aynıdır."""
    plan = await _plan(db_session, _steps("Onay korunur"))
    await _claim_only(db_session, plan)
    approved_at = plan.approved_at
    revision = plan.revision

    later = NOW + timedelta(seconds=EXECUTOR_STALE_AFTER_SECONDS + 5)
    recovered, outcome = await service.recover(db_session, plan_row_id=plan.id, now=later)

    assert outcome.final_status == "completed"
    assert recovered.revision == revision
    assert recovered.approved_at == approved_at
    assert recovered.approved_revision == revision


async def test_recovery_records_takeover_in_the_ledger(db_session: AsyncSession) -> None:
    from app.modules.execution.models import ExecutionDecision

    plan = await _plan(db_session, _steps("Denetim"))
    await _claim_only(db_session, plan)
    later = NOW + timedelta(seconds=EXECUTOR_STALE_AFTER_SECONDS + 5)
    await service.recover(db_session, plan_row_id=plan.id, now=later)

    kinds = [
        row.kind
        for row in (
            await db_session.execute(
                select(ExecutionDecision).where(ExecutionDecision.plan_row_id == plan.id)
            )
        ).scalars()
    ]
    assert "execution_recovered" in kinds
