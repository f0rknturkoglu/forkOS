"""H7 onay ve karar sözleşmesi — sunucu tarafı yetki, replay koruması."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity
from app.db import SessionLocal
from app.modules.execution import service
from app.modules.execution.models import ExecutionDecision, ExecutionPlan
from tests.h5_fixtures import make_project

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


def _todo_steps(title: str = "ALES başvurusunu tamamla") -> list[dict]:
    return [{"step_id": "s1", "action": "todo_create", "arguments": {"title": title}}]


async def _prepared(session: AsyncSession, **kwargs: object) -> ExecutionPlan:
    return await service.prepare(
        session, title="ALES planı", steps=_todo_steps(), reason="son tarih 3 gün", now=NOW, **kwargs  # type: ignore[arg-type]
    )


async def test_prepare_does_not_mutate_canonical_state(db_session: AsyncSession) -> None:
    before = (await db_session.execute(select(Entity.id).order_by(Entity.id))).scalars().all()
    plan = await _prepared(db_session)
    after = (await db_session.execute(select(Entity.id).order_by(Entity.id))).scalars().all()

    assert before == after, "plan hazırlamak canonical mutasyon DEĞİLDİR"
    assert plan.state == "awaiting_approval"
    assert plan.validation_status == "valid"


async def test_prepare_rejects_invalid_plan(db_session: AsyncSession) -> None:
    with pytest.raises(service.ExecutionPlanError, match="PLAN_VALIDATION_FAILED"):
        await service.prepare(
            session=db_session,
            title="Kötü plan",
            steps=[{"action": "shell", "arguments": {"cmd": "rm -rf /"}}],
            now=NOW,
        )


async def test_prepare_rejects_missing_target(db_session: AsyncSession) -> None:
    with pytest.raises(service.ExecutionPlanError, match="PLAN_VALIDATION_FAILED"):
        await service.prepare(
            session=db_session,
            title="Hedefsiz",
            steps=[
                {
                    "action": "project_update",
                    "arguments": {"project_id": "00000000-0000-4000-8000-000000000000"},
                }
            ],
            now=NOW,
        )


async def test_prepare_rejects_fabricated_evidence(db_session: AsyncSession) -> None:
    """Uydurma provenance kabul edilmez (§65)."""
    with pytest.raises(service.ExecutionPlanError, match="PLAN_VALIDATION_FAILED"):
        await _prepared(
            db_session,
            evidence_refs=["entity:00000000-0000-4000-8000-000000000000"],
        )
    with pytest.raises(service.ExecutionPlanError, match="PLAN_VALIDATION_FAILED"):
        await _prepared(db_session, source_refs=["made_up:1"])


async def test_prepare_is_idempotent_for_identical_content(db_session: AsyncSession) -> None:
    """Aynı soy ağacı + aynı içerik → AYNI satır (yeni revizyon açılmaz)."""
    first = await _prepared(db_session)
    second = await _prepared(db_session, plan_id=first.plan_id)
    assert first.id == second.id
    assert first.revision == second.revision

    # Farklı soy ağacı ayrı plandır (aynı içerik olsa bile).
    other_lineage = await _prepared(db_session)
    assert other_lineage.id != first.id
    assert other_lineage.plan_id != first.plan_id


async def test_input_required_blocks_approval(db_session: AsyncSession) -> None:
    plan = await _prepared(db_session, input_questions=["Hangi CV?"])
    assert plan.state == "input_required"
    assert plan.validation_status == "input_required"

    with pytest.raises(service.ExecutionPlanError, match="PLAN_NOT_APPROVABLE"):
        await service.approve(db_session, plan_row_id=plan.id, now=NOW)


async def test_respond_returns_plan_to_draft_without_mutation(db_session: AsyncSession) -> None:
    plan = await _prepared(db_session, input_questions=["Hangi CV?"])
    answered = await service.respond(
        db_session, plan_row_id=plan.id, answers={"cv": "Backend CV"}, now=NOW
    )
    assert answered.state == "draft"
    assert answered.input_answers["cv"] == "Backend CV"
    # Cevap yeni bir eylem ÜRETMEZ: canonical mutasyon yok.
    assert answered.step_count == plan.step_count


async def test_approval_requires_server_side_record(db_session: AsyncSession) -> None:
    """Model `approved=true` iddia etse bile onay kaydı yoksa yürütme reddedilir."""
    plan = await _prepared(db_session)
    with pytest.raises(service.ExecutionPlanError, match="APPROVAL_REQUIRED"):
        await service.execute(db_session, plan_row_id=plan.id, now=NOW)


async def test_approve_binds_exact_revision(db_session: AsyncSession) -> None:
    plan = await _prepared(db_session)
    approved = await service.approve(db_session, plan_row_id=plan.id, revision=plan.revision, now=NOW)
    assert approved.state == "approved"
    assert approved.approved_revision == plan.revision
    assert approved.decided_by == "forkos_ui"

    decisions = list(
        (
            await db_session.execute(
                select(ExecutionDecision).where(ExecutionDecision.plan_row_id == plan.id)
            )
        ).scalars()
    )
    assert [item.kind for item in decisions] == ["created", "validated", "approved"]


async def test_approval_with_wrong_revision_is_stale(db_session: AsyncSession) -> None:
    plan = await _prepared(db_session)
    with pytest.raises(service.ExecutionPlanError, match="APPROVAL_STALE"):
        await service.approve(
            db_session, plan_row_id=plan.id, revision="plan-v1:" + "0" * 64, now=NOW
        )


async def test_new_revision_invalidates_previous_approval(db_session: AsyncSession) -> None:
    """§58: plan düzenlenirse eski onay GEÇERSİZ olur."""
    plan = await _prepared(db_session)
    await service.approve(db_session, plan_row_id=plan.id, now=NOW)

    edited = await service.prepare(
        session=db_session,
        title="ALES planı",
        steps=_todo_steps("ALES başvurusunu YARIN tamamla"),
        reason="son tarih 3 gün",
        plan_id=plan.plan_id,
        now=NOW,
    )
    assert edited.revision != plan.revision
    assert edited.supersedes_revision == plan.revision

    with pytest.raises(service.ExecutionPlanError, match="APPROVAL_STALE"):
        await service.execute(db_session, plan_row_id=plan.id, now=NOW)


async def test_rejected_plan_cannot_execute(db_session: AsyncSession) -> None:
    plan = await _prepared(db_session)
    await service.reject(db_session, plan_row_id=plan.id, now=NOW)
    with pytest.raises(service.ExecutionPlanError, match="PLAN_REJECTED"):
        await service.approve(db_session, plan_row_id=plan.id, now=NOW)
    with pytest.raises(service.ExecutionPlanError, match="APPROVAL_REQUIRED"):
        await service.execute(db_session, plan_row_id=plan.id, now=NOW)


async def test_expired_plan_cannot_be_approved(db_session: AsyncSession) -> None:
    plan = await _prepared(db_session, ttl_hours=1)
    later = NOW + timedelta(hours=2)
    with pytest.raises(service.ExecutionPlanError, match="PLAN_EXPIRED"):
        await service.approve(db_session, plan_row_id=plan.id, now=later)


async def test_expiry_is_materialized_on_read(db_session: AsyncSession) -> None:
    plan = await _prepared(db_session, ttl_hours=1)
    view = await service.get_plan(db_session, plan.id, now=NOW + timedelta(hours=3))
    assert view["state"] == "expired"
    assert view["decision_required"] is False


async def test_source_freshness_blocks_stale_approval(db_session: AsyncSession) -> None:
    """§35: kaynak değiştiyse eski plana onay verilemez."""
    project = await make_project(db_session, title="forkjob")
    await db_session.commit()
    plan = await service.prepare(
        session=db_session,
        title="Proje planı",
        steps=[
            {
                "step_id": "s1",
                "action": "project_update",
                "arguments": {"project_id": str(project.id), "next_action": "Dogfooding"},
            }
        ],
        now=NOW,
    )
    assert plan.state == "awaiting_approval"

    project.next_action = "Başka bir şey"
    project.updated_at = NOW + timedelta(minutes=5)
    await db_session.commit()

    with pytest.raises(service.ExecutionPlanError, match="PLAN_NEEDS_REVALIDATION"):
        await service.approve(db_session, plan_row_id=plan.id, now=NOW + timedelta(minutes=6))


async def test_cancel_before_execution_prevents_mutation(db_session: AsyncSession) -> None:
    plan = await _prepared(db_session)
    cancelled = await service.cancel(db_session, plan_row_id=plan.id, now=NOW)
    assert cancelled.state == "cancelled"
    with pytest.raises(service.ExecutionPlanError):
        await service.execute(db_session, plan_row_id=plan.id, now=NOW)


async def test_unknown_plan_is_reported(db_session: AsyncSession) -> None:
    with pytest.raises(service.ExecutionPlanError, match="PLAN_NOT_FOUND"):
        await service.get_plan(db_session, 999_999, now=NOW)
