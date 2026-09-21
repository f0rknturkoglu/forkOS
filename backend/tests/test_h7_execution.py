"""H7 yürütme: H1 delegasyonu, makbuz, durma, kısmi, resume, eşzamanlılık."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity
from app.db import SessionLocal
from app.modules.execution import execution as execution_mod
from app.modules.execution import service
from app.modules.execution.models import ExecutionPlan, ExecutionReceipt
from app.modules.project.models import Project
from app.modules.todo.models import Todo
from tests.h5_fixtures import make_project

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def make_todo_for_deletion(session: AsyncSession) -> Entity:
    from tests.h5_fixtures import make_todo

    entity = await make_todo(session, title="Silinecek görev")
    await session.commit()
    return entity


async def _approved_plan(session: AsyncSession, steps: list[dict], **kwargs: object) -> ExecutionPlan:
    plan = await service.prepare(
        session, title="Plan", steps=steps, now=NOW, **kwargs  # type: ignore[arg-type]
    )
    return await service.approve(session, plan_row_id=plan.id, now=NOW)


async def test_execute_runs_steps_through_h1(db_session: AsyncSession) -> None:
    """§41/A: iki adımlı plan H1 üzerinden yürür ve makbuz üretir."""
    project = await make_project(db_session, title="forkjob", next_action="")
    await db_session.commit()

    plan = await _approved_plan(
        db_session,
        [
            {
                "step_id": "s1",
                "action": "todo_create",
                "arguments": {"title": "ALES başvurusunu tamamla", "priority": 3},
            },
            {
                "step_id": "s2",
                "action": "project_update",
                "arguments": {"project_id": str(project.id), "next_action": "Başvuruyu bitir"},
            },
        ],
    )

    finished, outcome = await service.execute(db_session, plan_row_id=plan.id, now=NOW)

    assert outcome.final_status == "completed"
    assert finished.state == "completed"
    assert [step.status for step in outcome.steps] == ["completed", "completed"]

    # Canonical etki GERÇEKTEN oluştu (H1 üzerinden).
    todos = list((await db_session.execute(select(Todo))).scalars())
    assert any(row.status == "open" for row in todos)
    refreshed_project = await db_session.get(Project, project.id)
    assert refreshed_project is not None
    assert refreshed_project.next_action == "Başvuruyu bitir"

    receipts = list(
        (
            await db_session.execute(
                select(ExecutionReceipt)
                .where(ExecutionReceipt.plan_row_id == plan.id)
                .order_by(ExecutionReceipt.ordinal)
            )
        ).scalars()
    )
    assert [item.status for item in receipts] == ["completed", "completed"]
    assert all(item.completed_at is not None for item in receipts)
    assert all(item.idempotency_key.startswith(plan.revision) for item in receipts)


async def test_stale_target_stops_execution_and_marks_partial(db_session: AsyncSession) -> None:
    """§16/§75-B: ilk adım stale olursa sonraki adımlar DENENMEZ."""
    project = await make_project(db_session, title="forkjob", next_action="")
    await db_session.commit()

    plan = await _approved_plan(
        db_session,
        [
            {
                "step_id": "s1",
                "action": "todo_create",
                "arguments": {"title": "İlk görev"},
            },
            {
                "step_id": "s2",
                "action": "project_update",
                "arguments": {"project_id": str(project.id), "next_action": "İkinci"},
            },
            {
                "step_id": "s3",
                "action": "todo_create",
                "arguments": {"title": "Üçüncü görev"},
            },
        ],
    )

    # Onaydan SONRA hedef değişir: s2 stale olmalı.
    from sqlalchemy import update

    await db_session.execute(
        update(Project)
        .where(Project.id == project.id)
        .values(next_action="Kullanıcı değiştirdi")
    )
    await db_session.execute(
        update(Entity).where(Entity.id == project.id).values(updated_at=NOW + timedelta(minutes=1))
    )
    await db_session.commit()

    finished, outcome = await service.execute(db_session, plan_row_id=plan.id, now=NOW)

    assert outcome.final_status == "partial"
    assert [step.status for step in outcome.steps] == ["completed", "failed", "not_attempted"]
    assert outcome.steps[1].error_code == "STEP_STALE"
    # s3 DENENMEDİ: yeni görev oluşmadı.
    todos = list((await db_session.execute(select(Todo))).scalars())
    assert len(todos) == 1


async def test_failed_step_stops_and_later_steps_are_not_attempted(
    db_session: AsyncSession,
) -> None:
    """İlk hatada DURULUR; sonraki adımlar not_attempted makbuzu alır."""
    victim = await make_todo_for_deletion(db_session)
    plan = await _approved_plan(
        db_session,
        [
            {
                "step_id": "s1",
                "action": "todo_create",
                "arguments": {"title": "Geçerli"},
            },
            {
                "step_id": "s2",
                "action": "todo_complete",
                "arguments": {"todo_id": str(victim.id)},
            },
            {
                "step_id": "s3",
                "action": "todo_create",
                "arguments": {"title": "Asla"},
            },
        ],
    )

    # Onaydan SONRA hedef silinir: validation bunu göremezdi, yürütme DURMALI.
    await db_session.execute(delete(Todo).where(Todo.id == victim.id))
    await db_session.execute(delete(Entity).where(Entity.id == victim.id))
    await db_session.commit()

    finished, outcome = await service.execute(db_session, plan_row_id=plan.id, now=NOW)

    assert outcome.final_status == "partial"
    assert [step.status for step in outcome.steps] == ["completed", "failed", "not_attempted"]
    receipts = list(
        (
            await db_session.execute(
                select(ExecutionReceipt)
                .where(ExecutionReceipt.plan_row_id == plan.id)
                .order_by(ExecutionReceipt.ordinal)
            )
        ).scalars()
    )
    assert [item.status for item in receipts] == ["completed", "failed", "not_attempted"]


async def test_completed_steps_are_not_repeated_on_resume(db_session: AsyncSession) -> None:
    """§20/§65: tamamlanmış adım restart sonrası TEKRAR yürütülmez."""
    plan = await _approved_plan(
        db_session,
        [
            {"step_id": "s1", "action": "todo_create", "arguments": {"title": "Bir kez"}},
        ],
    )
    finished, outcome = await service.execute(db_session, plan_row_id=plan.id, now=NOW)
    assert outcome.final_status == "completed"
    before = len(list((await db_session.execute(select(Todo))).scalars()))

    # Yeniden yürütme denemesi: terminal plan reddedilir.
    with pytest.raises(service.ExecutionPlanError, match="PLAN_TERMINAL"):
        await service.execute(db_session, plan_row_id=plan.id, now=NOW)

    # Aynı adımı "yarım kalmış executor" gibi yeniden çalıştır: makbuz korur.
    plan_row = await db_session.get(ExecutionPlan, plan.id)
    assert plan_row is not None
    plan_row.state = "executing"
    await db_session.commit()
    resumed = await execution_mod.execute_plan(db_session, plan_row, now=NOW + timedelta(minutes=1))
    assert resumed.final_status == "completed"
    assert len(list((await db_session.execute(select(Todo))).scalars())) == before


async def test_mutation_without_receipt_requires_reconciliation(
    db_session: AsyncSession,
) -> None:
    """§21: makbuz yazılmadan çökme → körlemesine tekrar DENENMEZ."""
    plan = await _approved_plan(
        db_session,
        [{"step_id": "s1", "action": "todo_create", "arguments": {"title": "Yarım"}}],
    )
    plan_row = await db_session.get(ExecutionPlan, plan.id)
    assert plan_row is not None
    plan_row.state = "executing"
    db_session.add(
        ExecutionReceipt(
            plan_row_id=plan.id,
            step_id="s1",
            ordinal=0,
            action="todo_create",
            idempotency_key=f"{plan_row.revision}:s1",
            status="not_attempted",
            started_at=NOW,
            claimed_by="dead-executor",
        )
    )
    await db_session.commit()

    outcome = await execution_mod.execute_plan(db_session, plan_row, now=NOW + timedelta(minutes=1))

    assert outcome.final_status == "failed"
    assert outcome.failure_code == "RECONCILIATION_REQUIRED"
    assert outcome.steps[0].status == "not_attempted"
    # Mutasyon TEKRARLANMADI.
    assert list((await db_session.execute(select(Todo))).scalars()) == []


async def test_concurrent_execute_has_single_owner(db_session: AsyncSession) -> None:
    """§22/§76-D: iki eşzamanlı execute → tek sahiplik, tek mutasyon."""
    plan = await _approved_plan(
        db_session,
        [{"step_id": "s1", "action": "todo_create", "arguments": {"title": "Tek"}}],
    )
    plan_row_id = plan.id

    async def run() -> str:
        async with SessionLocal() as session:
            try:
                await service.execute(session, plan_row_id=plan_row_id, now=NOW)
                return "ok"
            except service.ExecutionPlanError as exc:
                return exc.code

    results = await asyncio.gather(run(), run())

    async with SessionLocal() as session:
        todos = list((await session.execute(select(Todo))).scalars())
        refreshed = await session.get(ExecutionPlan, plan_row_id)
    assert sorted(results).count("ok") == 1, results
    assert any(code in {"PLAN_ALREADY_EXECUTING", "PLAN_TERMINAL"} for code in results)
    assert len(todos) == 1, "eşzamanlı yürütme MÜKERRER mutasyon üretmemeli"
    assert refreshed is not None
    assert refreshed.state in {"completed", "failed", "partial"}


async def test_execution_requires_no_model(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    """§59: onaylı plan yürütmesi modele BAĞLI DEĞİLDİR."""
    from app.integrations.local_cognition import service as lc_svc

    async def explode(*args: object, **kwargs: object) -> object:
        raise AssertionError("yürütme model çağırmamalı")

    monkeypatch.setattr(lc_svc, "run_local_cognition", explode)

    plan = await _approved_plan(
        db_session,
        [{"step_id": "s1", "action": "todo_create", "arguments": {"title": "Modelsiz"}}],
    )
    _, outcome = await service.execute(db_session, plan_row_id=plan.id, now=NOW)
    assert outcome.final_status == "completed"
