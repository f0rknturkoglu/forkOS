"""H7 son sertleştirme: adım NİYETİ yan etkiden ÖNCE dayanıklı olmalı.

Yarış: A makbuzu yalnızca `flush()` edip uzun H1 aksiyonuna girerse, bayat
lease'i devralan B bağımsız oturumdan makbuzu GÖREMEZ, adımı "hiç talep
edilmedi" sanıp yürütür → A da bitirirse AYNI adım iki kez mutasyon üretir.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, update
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

NOW = datetime.now(UTC)
STALE = NOW + timedelta(seconds=EXECUTOR_STALE_AFTER_SECONDS + 5)


@pytest.fixture(autouse=True)
def refresh_test_clock() -> None:
    """Keep lease fixtures current even when this module runs late in the full suite."""
    global NOW, STALE
    NOW = datetime.now(UTC)
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


async def _receipts(session: AsyncSession, plan_row_id: int) -> list[ExecutionReceipt]:
    return list(
        (
            await session.execute(
                select(ExecutionReceipt)
                .where(ExecutionReceipt.plan_row_id == plan_row_id)
                .order_by(ExecutionReceipt.ordinal)
            )
        ).scalars()
    )


async def _age_lease(session: AsyncSession, plan_row_id: int) -> None:
    """Lease'i bayatlat (gerçek bekleme yok)."""
    await session.execute(
        update(ExecutionPlan)
        .where(ExecutionPlan.id == plan_row_id)
        .values(execution_heartbeat_at=STALE - timedelta(seconds=EXECUTOR_STALE_AFTER_SECONDS * 2))
    )
    await session.commit()


# ---------------------------------------------------------------------------
# D1/D2/D11 — ana kabul kanıtı (§31)
# ---------------------------------------------------------------------------


async def test_claimed_step_is_visible_and_not_replayed_while_h1_is_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A'nın H1 aksiyonu SÜRERKEN B kurtarır: tekrar YOK, tek mutasyon."""
    async with SessionLocal() as setup:
        plan = await _approved(setup, _steps("Uzun aksiyon"))
        plan_row_id = plan.id

    enter = asyncio.Event()
    release = asyncio.Event()
    real_run = execution_mod.run_action
    invoked: list[str] = []

    async def blocking_run(session, spec, data):  # type: ignore[no-untyped-def]
        invoked.append(spec.name)
        if len(invoked) == 1:
            enter.set()
            await release.wait()  # H1 aksiyonu burada BLOKE
        return await real_run(session, spec, data)

    monkeypatch.setattr(execution_mod, "run_action", blocking_run)

    async def executor_a() -> str:
        async with SessionLocal() as session:
            try:
                await service.execute(session, plan_row_id=plan_row_id, now=NOW)
                return "completed"
            except service.ExecutionPlanError as exc:
                return exc.code

    task_a = asyncio.create_task(executor_a())
    await asyncio.wait_for(enter.wait(), timeout=10)

    # --- D2: BAĞIMSIZ oturumdan adım niyeti GÖRÜNÜR olmalı -----------------
    async with SessionLocal() as session_b:
        receipts = await _receipts(session_b, plan_row_id)
        assert receipts, "adım niyeti yan etkiden ÖNCE dayanıklı olmalı"
        assert receipts[0].status == "not_attempted"
        assert receipts[0].claimed_by, "talep sahibi yazılmalı"

        # Lease bayatlar → B kurtarır.
        await _age_lease(session_b, plan_row_id)
        # Niyet commit edildigi icin adim satiri KILITLI DEGILDIR: kurtarma
        # istemi beklemeden tamamlanmalidir (once: kilitte bloke oluyordu).
        _plan_b, outcome_b = await asyncio.wait_for(
            service.recover(session_b, plan_row_id=plan_row_id, now=STALE), timeout=10
        )
        assert outcome_b.failure_code == "RECONCILIATION_REQUIRED"
        assert outcome_b.steps[0].status == "unresolved"
        assert invoked == ["todo_create"], "B aynı H1 aksiyonunu ÇAĞIRMAMALI"

    release.set()
    result_a = await asyncio.wait_for(task_a, timeout=10)

    async with SessionLocal() as check:
        todos = list((await check.execute(select(Todo))).scalars())
        receipts = await _receipts(check, plan_row_id)

    assert len(todos) == 1, "kanonik mutasyon TAM OLARAK BİR olmalı"
    assert result_a == "EXECUTION_OWNERSHIP_LOST", result_a
    assert receipts[0].claimed_by and receipts[0].status in {"unresolved", "completed"}


# ---------------------------------------------------------------------------
# D3/D5 — aksiyondan ÖNCE sahiplik kaybı
# ---------------------------------------------------------------------------


async def test_takeover_during_step_stops_owner_without_duplicate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D3/D5: adım sınırında devralma → eski yürütücü DURUR, kurtarıcı TEKRARLAMAZ.

    Niyet dayanıklı olduğu için kurtarıcı bu adımı "talep edilmiş" görür ve
    mutabakat ister; eski yürütücü ise sahipliği kaybettiğini görüp finalize
    EDEMEZ. Sonuç: tek kanonik mutasyon, sahte muvaffakiyet yok.
    """
    async with SessionLocal() as setup:
        plan = await _approved(setup, _steps("Çalışmayacak"))
        plan_row_id = plan.id

    real_run = execution_mod.run_action
    calls: list[str] = []

    async def takeover_then_run(session, spec, data):  # type: ignore[no-untyped-def]
        # Süreç, aksiyona girmeden HEMEN önce ölür; yerine sahiplik devralınır.
        async with SessionLocal() as other:
            await other.execute(
                update(ExecutionPlan)
                .where(ExecutionPlan.id == plan_row_id)
                .values(executor_token="token-b", execution_heartbeat_at=STALE)
            )
            await other.commit()
        calls.append(spec.name)
        return await real_run(session, spec, data)

    monkeypatch.setattr(execution_mod, "run_action", takeover_then_run)

    async with SessionLocal() as session:
        with pytest.raises(service.ExecutionPlanError, match="EXECUTION_OWNERSHIP_LOST"):
            await service.execute(session, plan_row_id=plan_row_id, now=NOW)

    # Sahiplik yeniden doğrulaması ile H1 çağrısı arasındaki pencere kapatılamaz;
    # kapanması gereken şey SONUÇTUR: eski yürütücü devam edemez, finalize edemez.
    assert calls == ["todo_create"], "adım en fazla BİR kez çağrılır"
    async with SessionLocal() as check:
        receipts = await _receipts(check, plan_row_id)
        todos = list((await check.execute(select(Todo))).scalars())
        refreshed = await check.get(ExecutionPlan, plan_row_id)
    assert len(todos) == 1, "kanonik mutasyon TEK olmalı (mükerrer YOK)"
    assert receipts and receipts[0].claimed_by, "talep sahipliği tarihsel olarak kalır"
    # Plan, devralan yürütücünün sorumluluğundadır; eski yürütücü finalize EDEMEDİ.
    assert refreshed is not None and refreshed.state == "executing"
    assert refreshed.final_status is None


# ---------------------------------------------------------------------------
# D9/D10 — sahipsiz makbuz güvenle devam eder
# ---------------------------------------------------------------------------


async def test_unclaimed_receipt_is_resumable_and_durably_claimed(
    db_session: AsyncSession,
) -> None:
    """D9/D10: `claimed_by=NULL` adım kurtarmada SAHİPLENİLİR ve bir kez yürür."""
    plan = await _approved(db_session, _steps("Sahipsiz"))
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
            claimed_by=None,
        )
    )
    await db_session.commit()

    await _age_lease(db_session, plan.id)
    _recovered, outcome = await service.recover(db_session, plan_row_id=plan.id, now=STALE)

    assert outcome.final_status == "completed"
    async with SessionLocal() as check:
        todos = list((await check.execute(select(Todo))).scalars())
        receipts = await _receipts(check, plan.id)
    assert len(todos) == 1
    assert receipts[0].claimed_by is not None
    assert receipts[0].claimed_by != "None"


# ---------------------------------------------------------------------------
# D8/D12 — tarihsel sahiplik ve Vault semantiği korunur
# ---------------------------------------------------------------------------


async def test_recovered_executor_does_not_overwrite_claimed_by(
    db_session: AsyncSession,
) -> None:
    plan = await _approved(db_session, _steps("Tarihsel"))
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
    await _age_lease(db_session, plan.id)

    _plan_b, outcome = await service.recover(db_session, plan_row_id=plan.id, now=STALE)

    assert outcome.steps[0].status == "unresolved"
    async with SessionLocal() as check:
        receipts = await _receipts(check, plan.id)
    assert receipts[0].claimed_by == "token-a", "tarihsel sahiplik YENİDEN YAZILMAZ"


async def test_vault_step_keeps_conservative_semantics(db_session: AsyncSession) -> None:
    """D12: Vault adımı hâlâ mutabakat gerektirir; körlemesine tekrar YOK."""
    from app.integrations.agent.write_registry import BY_NAME

    spec = BY_NAME["brain_capture"]
    assert spec.side_effect_domain == "vault"
    assert spec.replay_safety == "ambiguous"
