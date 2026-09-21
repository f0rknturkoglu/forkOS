"""H7.1 — input_required → respond → yeni revizyon → onay → yürütme zinciri."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity
from app.db import SessionLocal
from app.modules.execution import service
from app.modules.todo.models import Todo

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


def _steps(title: str = "Başvuruyu tamamla") -> list[dict]:
    return [{"step_id": "s1", "action": "todo_create", "arguments": {"title": title}}]


async def _awaiting_input(session: AsyncSession):
    return await service.prepare(
        session,
        title="Başvuru planı",
        steps=_steps(),
        input_questions=["Hangi CV?"],
        now=NOW,
    )


async def test_i1_respond_then_reprepare_is_not_a_dead_end(db_session: AsyncSession) -> None:
    """I1: cevap sonrası yeniden hazırlama KULLANILABİLİR revizyon üretir."""
    plan = await _awaiting_input(db_session)
    assert plan.state == "input_required"

    answered = await service.respond(
        db_session, plan_row_id=plan.id, answers={"cv": "Backend CV"}, now=NOW
    )
    assert answered.state == "draft"

    reprepared = await service.prepare(
        session=db_session,
        title="Başvuru planı",
        steps=_steps(),
        input_questions=[],
        plan_id=plan.plan_id,
        now=NOW,
    )
    assert reprepared.id != plan.id, "eski draft satırına çökülmemeli"
    assert reprepared.state == "awaiting_approval"
    assert reprepared.revision != plan.revision


async def test_i2_respond_new_revision_approve_execute(db_session: AsyncSession) -> None:
    """I2: cevap → yeni revizyon → onay → yürütme uçtan uca çalışır."""
    plan = await _awaiting_input(db_session)
    await service.respond(db_session, plan_row_id=plan.id, answers={"cv": "Backend CV"}, now=NOW)
    revised = await service.prepare(
        session=db_session,
        title="Başvuru planı",
        steps=_steps(),
        plan_id=plan.plan_id,
        now=NOW,
    )
    await service.approve(db_session, plan_row_id=revised.id, now=NOW)
    finished, outcome = await service.execute(db_session, plan_row_id=revised.id, now=NOW)

    assert outcome.final_status == "completed"
    assert finished.state == "completed"
    todos = list((await db_session.execute(select(Todo))).scalars())
    assert len(todos) == 1


async def test_i3_post_response_revision_requires_new_approval(db_session: AsyncSession) -> None:
    """I3: yeni revizyon yeni onay ister; eski onay transfer olmaz."""
    plan = await _awaiting_input(db_session)
    await service.respond(db_session, plan_row_id=plan.id, answers={"cv": "Backend CV"}, now=NOW)
    revised = await service.prepare(
        session=db_session, title="Başvuru planı", steps=_steps(), plan_id=plan.plan_id, now=NOW
    )
    with pytest.raises(service.ExecutionPlanError, match="APPROVAL_REQUIRED"):
        await service.execute(db_session, plan_row_id=revised.id, now=NOW)


async def test_i4_old_revision_approval_is_stale_after_response(db_session: AsyncSession) -> None:
    """I4: cevap/yeni revizyon sonrası eski revizyonun onayı GEÇERSİZ."""
    plan = await _awaiting_input(db_session)
    await service.respond(db_session, plan_row_id=plan.id, answers={"cv": "Backend CV"}, now=NOW)
    await service.prepare(
        session=db_session, title="Başvuru planı", steps=_steps(), plan_id=plan.plan_id, now=NOW
    )
    with pytest.raises(service.ExecutionPlanError, match="PLAN_NOT_APPROVABLE|APPROVAL_STALE"):
        await service.approve(db_session, plan_row_id=plan.id, now=NOW)


async def test_i5_answer_cannot_execute_an_action(db_session: AsyncSession) -> None:
    """I5: cevap VERİDİR; canonical mutasyon üretmez ve eylem olamaz."""
    plan = await _awaiting_input(db_session)
    await service.respond(
        db_session,
        plan_row_id=plan.id,
        answers={"cv": "todo_create: {'title': 'Kaçak görev'}"},
        now=NOW,
    )
    todos = list((await db_session.execute(select(Todo))).scalars())
    assert todos == [], "cevap metni yürütülemez"
    entities = list((await db_session.execute(select(Entity))).scalars())
    assert entities == []


async def test_i6_repeated_identical_response_is_bounded(db_session: AsyncSession) -> None:
    """I6: aynı cevap + aynı içerik revizyon spam'i üretmez (deterministik)."""
    plan = await _awaiting_input(db_session)
    await service.respond(db_session, plan_row_id=plan.id, answers={"cv": "Backend CV"}, now=NOW)

    first = await service.prepare(
        session=db_session, title="Başvuru planı", steps=_steps(), plan_id=plan.plan_id, now=NOW
    )
    second = await service.prepare(
        session=db_session, title="Başvuru planı", steps=_steps(), plan_id=plan.plan_id, now=NOW
    )
    assert first.id == second.id
    assert first.revision == second.revision

    from app.modules.execution.models import ExecutionPlan

    rows = list(
        (
            await db_session.execute(
                select(ExecutionPlan).where(ExecutionPlan.plan_id == plan.plan_id)
            )
        ).scalars()
    )
    assert len(rows) == 2, "yalnızca ilk revizyon + cevaplı revizyon"


async def test_i7_answer_is_bounded(db_session: AsyncSession) -> None:
    plan = await _awaiting_input(db_session)
    answered = await service.respond(
        db_session, plan_row_id=plan.id, answers={"cv": "x" * 5000}, now=NOW
    )
    assert len(answered.input_answers["cv"]) <= 1000
