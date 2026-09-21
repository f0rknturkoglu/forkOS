"""H7 orkestrasyon: plan hazırlama, karar, sınırlı yürütme.

Ownership:

```text
Hermes   → öneri (adımlar)
H7       → plan sözleşmesi, doğrulama, kalıcı karar, yürütme, makbuz
H1       → gerçek canonical mutasyon
```

Onay SUNUCU TARAFI bir kayıttır ve HER ZAMAN bir revizyona bağlanır. Model
`"approved": true` üretse bile bu kayıt yoksa yürütme `APPROVAL_REQUIRED`
döner. Plan hazırlamak canonical mutasyon DEĞİLDİR (§44): yalnızca bu modülün
operasyonel tablolarına yazılır.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.execution import execution as execution_mod
from app.modules.execution import revision as revision_mod
from app.modules.execution import validation as validation_mod
from app.modules.execution.models import (
    DECISION_KINDS,
    DEFAULT_PLAN_TTL_HOURS,
    MAX_INPUT_ANSWER,
    MAX_LIST_LIMIT,
    MAX_PLAN_MUTATIONS,
    MAX_VALIDATION_ERRORS,
    ExecutionDecision,
    ExecutionPlan,
    ExecutionReceipt,
)
from app.modules.execution.state import TransitionError, ensure_transition
from app.modules.execution.steps import step_payload

log = logging.getLogger("execution.service")


class ExecutionPlanError(Exception):
    """Sınırlı, model-okunur H7 hatası."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


async def _audit(
    session: AsyncSession,
    *,
    plan: ExecutionPlan | None,
    plan_id: uuid.UUID,
    kind: str,
    detail: dict[str, Any],
    actor: str,
    now: datetime,
    revision: str | None = None,
) -> None:
    if kind not in DECISION_KINDS:
        raise ExecutionPlanError("UNKNOWN_DECISION_KIND", f"bilinmeyen karar turu: {kind}")
    session.add(
        ExecutionDecision(
            plan_id=plan_id,
            plan_row_id=plan.id if plan else None,
            kind=kind,
            revision=revision or (plan.revision if plan else None),
            detail=detail,
            actor=actor,
            at=now,
        )
    )


def _bounded_answer(value: Any) -> str:
    return str(value or "").strip()[:MAX_INPUT_ANSWER]


async def _load_plan(session: AsyncSession, plan_row_id: int) -> ExecutionPlan:
    plan = await session.get(ExecutionPlan, plan_row_id)
    if plan is None:
        raise ExecutionPlanError("PLAN_NOT_FOUND", "plan bulunamadi")
    return plan


async def _pending_decision_context(
    session: AsyncSession, plan_id: uuid.UUID
) -> dict[str, str]:
    """Soy ağacındaki en yeni `draft`/`input_required` cevabını toplar (sınırlı)."""
    row = (
        await session.execute(
            select(ExecutionPlan.input_answers)
            .where(
                ExecutionPlan.plan_id == plan_id,
                ExecutionPlan.state.in_(("draft", "input_required")),
            )
            .order_by(ExecutionPlan.created_at.desc(), ExecutionPlan.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not row or not isinstance(row, dict):
        return {}
    return {str(key): str(value) for key, value in row.items()}


async def _latest_revision(session: AsyncSession, plan_id: uuid.UUID) -> str | None:
    return (
        await session.execute(
            select(ExecutionPlan.revision)
            .where(ExecutionPlan.plan_id == plan_id)
            .order_by(ExecutionPlan.created_at.desc(), ExecutionPlan.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def expire_due_plans(session: AsyncSession, *, now: datetime) -> int:
    """Süresi geçen karar bekleyen planları `expired` yapar (sınırlı iş)."""
    plan = await session.execute(
        select(ExecutionPlan).where(
            ExecutionPlan.state.in_(("awaiting_approval", "input_required", "approved")),
            ExecutionPlan.expires_at.is_not(None),
            ExecutionPlan.expires_at <= now,
        )
    )
    count = 0
    for row in plan.scalars():
        row.state = "expired"
        count += 1
        await _audit(
            session,
            plan=row,
            plan_id=row.plan_id,
            kind="expired",
            detail={"reason": "TTL"},
            actor="system",
            now=now,
        )
    return count


# ---------------------------------------------------------------------------
# Hazırlama
# ---------------------------------------------------------------------------


async def prepare(
    session: AsyncSession,
    *,
    title: str,
    steps: Any,
    summary: str | None = None,
    reason: str | None = None,
    source_refs: list[str] | None = None,
    evidence_refs: list[str] | None = None,
    input_questions: list[str] | None = None,
    plan_id: uuid.UUID | None = None,
    ttl_hours: int | None = None,
    actor: str = "hermes",
    now: datetime | None = None,
) -> ExecutionPlan:
    """Öneriyi doğrular ve KALICI plan revizyonu olarak kaydeder.

    Aynı içerik aynı revizyonu üretir: `(plan_id, revision)` UNIQUE olduğu için
    tekrar hazırlama YENİ satır açmaz (idempotent).
    """
    moment = now or datetime.now(UTC)
    lineage = plan_id or uuid.uuid4()

    # Kullanıcı cevabı bekleyen bir revizyon varsa, o cevap YENİ revizyonun
    # parçası olur: aynı içerikle tekrar hazırlama artık eski `draft` satırına
    # dönmez, `awaiting_approval` bir revizyon üretir (H7.1/B).
    decision_context = await _pending_decision_context(session, lineage)

    result = await validation_mod.validate_plan(
        session,
        title=title,
        summary=summary,
        reason=reason,
        steps=steps,
        source_refs=source_refs,
        evidence_refs=evidence_refs,
        input_questions=input_questions,
    )
    if result.status == "invalid":
        # Onaya hazır olmayan plan KAYDEDİLMEZ: kullanıcıya gosterilmez (§9).
        # Yine de SINIRLI bir denetim kaydı bırakılır (plan satırı OLMAYARAK):
        # "bu öneri neden reddedildi" sorusu cevaplanabilir kalır.
        await _audit(
            session,
            plan=None,
            plan_id=lineage,
            kind="validation_failed",
            detail={"codes": [item["code"] for item in result.errors[:MAX_VALIDATION_ERRORS]]},
            actor=actor,
            now=moment,
        )
        await session.commit()
        raise ExecutionPlanError(
            "PLAN_VALIDATION_FAILED",
            "; ".join(item["code"] for item in result.errors[:3]) or "gecersiz plan",
        )

    step_payloads = [step_payload(step) for step in result.steps]
    normalized = revision_mod.normalized_plan(
        title=title,
        summary=summary,
        reason=reason,
        steps=step_payloads,
        source_refs=source_refs,
        evidence_refs=evidence_refs,
        decision_context=decision_context,
    )
    revision = revision_mod.revision_of(normalized)

    existing = (
        await session.execute(
            select(ExecutionPlan).where(
                ExecutionPlan.plan_id == lineage, ExecutionPlan.revision == revision
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    previous = await _latest_revision(session, lineage)
    state = "input_required" if result.status == "input_required" else "awaiting_approval"
    plan = ExecutionPlan(
        plan_id=lineage,
        revision=revision,
        supersedes_revision=previous,
        state=state,
        title=str(title)[: validation_mod.MAX_PLAN_TITLE],
        summary=summary,
        reason=reason,
        steps=step_payloads,
        step_count=len(step_payloads),
        mutation_count=len(step_payloads),
        budget={
            "max_steps": validation_mod.MAX_PLAN_STEPS,
            "max_mutations": MAX_PLAN_MUTATIONS,
            "steps": len(step_payloads),
        },
        source_refs=normalized["source_refs"],
        evidence_refs=normalized["evidence_refs"],
        # Dogrulama ciktisi planla birlikte kalir: arayuz "dogrulanmis" ile
        # "cozulemedi" ayrimini SONRADAN da gosterebilsin.
        verified_refs=result.verified_refs,
        unresolved_refs=result.unresolved_refs,
        validation_status="valid" if result.status == "valid" else "input_required",
        input_questions=result.questions,
        expires_at=moment + timedelta(hours=ttl_hours or DEFAULT_PLAN_TTL_HOURS),
    )
    session.add(plan)
    await session.flush()

    await _audit(
        session,
        plan=plan,
        plan_id=lineage,
        kind="created",
        detail={"steps": len(step_payloads), "mutations": len(step_payloads)},
        actor=actor,
        now=moment,
    )
    if previous is not None:
        await _audit(
            session,
            plan=plan,
            plan_id=lineage,
            kind="revision_created",
            detail={"supersedes": previous},
            actor=actor,
            now=moment,
        )
    if result.status == "input_required":
        await _audit(
            session,
            plan=plan,
            plan_id=lineage,
            kind="input_requested",
            detail={"questions": len(result.questions)},
            actor=actor,
            now=moment,
        )
    else:
        await _audit(
            session,
            plan=plan,
            plan_id=lineage,
            kind="validated",
            detail={"steps": len(step_payloads)},
            actor=actor,
            now=moment,
        )
    await session.commit()
    return plan


# ---------------------------------------------------------------------------
# Karar
# ---------------------------------------------------------------------------


async def approve(
    session: AsyncSession,
    *,
    plan_row_id: int,
    revision: str | None = None,
    actor: str = "forkos_ui",
    now: datetime | None = None,
) -> ExecutionPlan:
    """Kullanıcı onayı — SUNUCU TARAFI kayıt. Model bunu üretemez (§6/§38)."""
    moment = now or datetime.now(UTC)
    plan = await _load_plan(session, plan_row_id)
    if plan.state == "expired" or (plan.expires_at is not None and plan.expires_at <= moment):
        raise ExecutionPlanError("PLAN_EXPIRED", "plan suresi doldu; yeni revizyon hazirlanmali")
    if plan.state == "rejected":
        raise ExecutionPlanError("PLAN_REJECTED", "plan reddedilmis")
    if plan.state not in {"awaiting_approval"}:
        raise ExecutionPlanError("PLAN_NOT_APPROVABLE", f"durum: {plan.state}")
    if revision is not None and revision != plan.revision:
        # Onay ESKI revizyona baglanamaz (§39).
        raise ExecutionPlanError("APPROVAL_STALE", "onay guncel revizyona ait degil")
    latest = await _latest_revision(session, plan.plan_id)
    if latest != plan.revision:
        raise ExecutionPlanError("APPROVAL_STALE", "daha yeni bir revizyon var")

    # Kaynak tazeligi: onay, hazirlik anindaki duruma korlemesine uygulanmaz (§35).
    fresh = await _verify_freshness(session, plan)
    if not fresh:
        raise ExecutionPlanError(
            "PLAN_NEEDS_REVALIDATION", "hedef durum degisti; plan yeniden hazirlanmali"
        )

    plan.approved_at = moment
    plan.approved_revision = plan.revision
    plan.decided_by = actor
    ensure_transition(plan.state, "approved")
    plan.state = "approved"
    await _audit(
        session,
        plan=plan,
        plan_id=plan.plan_id,
        kind="approved",
        detail={"revision": plan.revision},
        actor=actor,
        now=moment,
    )
    await session.commit()
    return plan


async def reject(
    session: AsyncSession, *, plan_row_id: int, actor: str = "forkos_ui", now: datetime | None = None
) -> ExecutionPlan:
    moment = now or datetime.now(UTC)
    plan = await _load_plan(session, plan_row_id)
    ensure_transition(plan.state, "rejected")
    plan.state = "rejected"
    plan.rejected_at = moment
    plan.decided_by = actor
    await _audit(
        session, plan=plan, plan_id=plan.plan_id, kind="rejected", detail={}, actor=actor, now=moment
    )
    await session.commit()
    return plan


async def respond(
    session: AsyncSession,
    *,
    plan_row_id: int,
    answers: dict[str, Any],
    actor: str = "forkos_ui",
    now: datetime | None = None,
) -> ExecutionPlan:
    """`input_required` planına kullanıcı cevabı.

    Cevap MUTASYON ÜRETMEZ: plan `draft`'a döner ve yeniden hazırlanır
    (yeni revizyon → yeni onay). Cevap metni yeni bir eylem olamaz (§40).
    """
    moment = now or datetime.now(UTC)
    plan = await _load_plan(session, plan_row_id)
    if plan.state != "input_required":
        raise ExecutionPlanError("PLAN_NOT_AWAITING_INPUT", f"durum: {plan.state}")
    cleaned = {str(key)[:64]: _bounded_answer(value) for key, value in (answers or {}).items()}
    if not cleaned:
        raise ExecutionPlanError("INVALID_INPUT_RESPONSE", "cevap bos olamaz")
    plan.input_answers = {**(plan.input_answers or {}), **cleaned}
    ensure_transition(plan.state, "draft")
    plan.state = "draft"
    await _audit(
        session,
        plan=plan,
        plan_id=plan.plan_id,
        kind="input_supplied",
        detail={"keys": sorted(cleaned)},
        actor=actor,
        now=moment,
    )
    await session.commit()
    return plan


async def cancel(
    session: AsyncSession, *, plan_row_id: int, actor: str = "forkos_ui", now: datetime | None = None
) -> ExecutionPlan:
    moment = now or datetime.now(UTC)
    plan = await _load_plan(session, plan_row_id)
    ensure_transition(plan.state, "cancelled")
    plan.state = "cancelled"
    plan.cancelled_at = moment
    await _audit(
        session, plan=plan, plan_id=plan.plan_id, kind="cancelled", detail={}, actor=actor, now=moment
    )
    await session.commit()
    return plan


async def _verify_freshness(session: AsyncSession, plan: ExecutionPlan) -> bool:
    """Onaylı revizyondaki freshness damgaları hâlâ geçerli mi?"""
    for raw_step in plan.steps or []:
        arguments = dict(raw_step.get("arguments") or {})
        ok, _current = await execution_mod._fresh_target_stamp(
            session, arguments, raw_step.get("expected_updated_at")
        )
        if not ok:
            return False
    return True


# ---------------------------------------------------------------------------
# Yürütme
# ---------------------------------------------------------------------------


async def execute(
    session: AsyncSession,
    *,
    plan_row_id: int,
    revision: str | None = None,
    actor: str = "forkos_ui",
    now: datetime | None = None,
) -> tuple[ExecutionPlan, execution_mod.ExecutionOutcome]:
    """Onaylı TAM revizyonu H1 üzerinden yürütür."""
    moment = now or datetime.now(UTC)
    plan = await _load_plan(session, plan_row_id)

    if plan.approved_at is None or plan.approved_revision is None:
        raise ExecutionPlanError("APPROVAL_REQUIRED", "plan onaylanmamis")
    if revision is not None and revision != plan.revision:
        raise ExecutionPlanError("APPROVAL_STALE", "istenen revizyon onaylanan revizyon degil")
    if plan.approved_revision != plan.revision:
        raise ExecutionPlanError("APPROVAL_STALE", "onay baska bir revizyona ait")
    if plan.expires_at is not None and plan.expires_at <= moment:
        plan.state = "expired"
        await session.commit()
        raise ExecutionPlanError("PLAN_EXPIRED", "plan suresi doldu")
    if plan.state == "executing":
        raise ExecutionPlanError("PLAN_ALREADY_EXECUTING", "plan zaten yurutuluyor")
    if plan.state in {"completed", "partial", "failed", "rejected", "cancelled", "expired"}:
        raise ExecutionPlanError("PLAN_TERMINAL", f"plan terminal durumda: {plan.state}")
    latest = await _latest_revision(session, plan.plan_id)
    if latest != plan.revision:
        raise ExecutionPlanError("APPROVAL_STALE", "daha yeni bir revizyon var")

    token = await execution_mod.claim_plan(session, plan, now=moment)
    if token is None:
        await session.rollback()
        raise ExecutionPlanError("PLAN_ALREADY_EXECUTING", "yurutme sahipligi baska cagrida")
    await session.commit()
    plan = await _load_plan(session, plan_row_id)

    await _audit(
        session,
        plan=plan,
        plan_id=plan.plan_id,
        kind="execution_started",
        detail={"steps": plan.step_count},
        actor=actor,
        now=moment,
    )
    await session.commit()

    outcome = await execution_mod.execute_plan(session, plan, token=token, now=moment)

    # Finalizasyon JETONA bağlıdır: devralınmış bir yürütücü kazananın nihai
    # durumunu EZEMEZ (§7).
    finalized = await execution_mod.finalize_if_owner(
        session,
        plan_row_id,
        token=token,
        final_status=outcome.final_status,
        failure_code=outcome.failure_code,
        now=datetime.now(UTC),
    )
    plan = await _load_plan(session, plan_row_id)
    if finalized:
        await _finish_audit(session, plan=plan, outcome=outcome, actor=actor)
    await session.commit()
    if not finalized:
        raise ExecutionPlanError(
            "EXECUTION_OWNERSHIP_LOST", "sahiplik devralindi; sonuc yazilmadi"
        )
    # Kosullu UPDATE ORM kimlik haritasini tazelemez: yanit taze degerle doner.
    await session.refresh(plan)
    return plan, outcome


async def recover(
    session: AsyncSession,
    *,
    plan_row_id: int,
    actor: str = "forkos_ui",
    now: datetime | None = None,
) -> tuple[ExecutionPlan, execution_mod.ExecutionOutcome]:
    """ÇÖKMÜŞ bir yürütmeyi desteklenen yüzeyden kurtarır (H7.1).

    Kurallar:

    ```text
    1. Yalnızca `executing` plan kurtarılabilir.
    2. Lease TAZE ise sahiplik DEVRALINMAZ (canlı yürütücü korunur).
    3. Devralma ATOMİKTİR: iki kurtarıcıdan yalnız biri sahip olur.
    4. Devir denetim izine yazılır (execution_recovered + gerekçe).
    5. Adım makbuzları önce incelenir: tamamlanan adım TEKRAR YÜRÜTÜLMEZ,
       sonucu belirsiz adım MUTABAKAT GEREKTİRİR, hiç denenmemiş adım
       güvenle sürdürülebilir.
    6. Yeni onay İSTENMEZ: tam revizyon ve onay kaydı değişmemiştir (§28).
       Adım bazlı tazelik kontrolü yine çalışır.
    """
    moment = now or datetime.now(UTC)
    plan = await _load_plan(session, plan_row_id)
    # Lease karari TAZE degerle verilir: oturumun kimlik haritasindaki bayat
    # nesne "canli yurutucuyu" yanlislikla devralinabilir gosterirdi.
    await session.refresh(plan)
    if plan.state != "executing":
        raise ExecutionPlanError(
            "PLAN_NOT_RECOVERABLE", f"plan su anda kurtarilabilir degil: {plan.state}"
        )
    age = execution_mod.lease_age_seconds(plan, now=moment)
    if not execution_mod.lease_is_stale(plan, now=moment):
        raise ExecutionPlanError(
            "PLAN_ACTIVE_EXECUTOR",
            f"yurutucu lease'i hala canli ({int(age or 0)} sn); sahiplik devralinmaz",
        )

    from sqlalchemy import update

    cutoff = moment - timedelta(seconds=execution_mod.EXECUTOR_STALE_AFTER_SECONDS)
    recovery_token = execution_mod.new_executor_token()
    reclaimed = await session.execute(
        update(ExecutionPlan)
        .where(
            ExecutionPlan.id == plan.id,
            ExecutionPlan.state == "executing",
            ExecutionPlan.updated_at <= moment,
            or_(
                ExecutionPlan.execution_heartbeat_at.is_(None),
                ExecutionPlan.execution_heartbeat_at < cutoff,
            ),
        )
        .values(
            # KURTARMA YENİ BİR DENEME JETONU ÜRETİR: eski yürütücü artık
            # kalp atışı yazamaz, adım başlatamaz, planı finalize edemez.
            executor_token=recovery_token,
            execution_heartbeat_at=moment,
            updated_at=moment,
        )
        .returning(ExecutionPlan.id)
    )
    if reclaimed.scalar_one_or_none() is None:
        # Başka bir kurtarıcı bizden önce devraldı: sahiplik TEKİLDİR.
        raise ExecutionPlanError("PLAN_ALREADY_RECOVERING", "sahiplik baska kurtariciya gecti")
    await _audit(
        session,
        plan=plan,
        plan_id=plan.plan_id,
        kind="execution_recovered",
        detail={"stale_seconds": int(age or 0), "threshold": execution_mod.EXECUTOR_STALE_AFTER_SECONDS},
        actor=actor,
        now=moment,
    )
    await session.commit()
    plan = await _load_plan(session, plan_row_id)

    outcome = await execution_mod.execute_plan(session, plan, token=recovery_token, now=moment)
    finalized = await execution_mod.finalize_if_owner(
        session,
        plan_row_id,
        token=recovery_token,
        final_status=outcome.final_status,
        failure_code=outcome.failure_code,
        now=datetime.now(UTC),
    )
    plan = await _load_plan(session, plan_row_id)
    if finalized:
        await _finish_audit(session, plan=plan, outcome=outcome, actor=actor)
    await session.commit()
    if not finalized:
        raise ExecutionPlanError(
            "EXECUTION_OWNERSHIP_LOST", "kurtarma sirasinda sahiplik degisti"
        )
    await session.refresh(plan)
    return plan, outcome


async def _finish_audit(
    session: AsyncSession,
    *,
    plan: ExecutionPlan,
    outcome: execution_mod.ExecutionOutcome,
    actor: str,
) -> None:
    for step in outcome.steps:
        if step.status == "unresolved":
            await _audit(
                session,
                plan=plan,
                plan_id=plan.plan_id,
                kind="execution_blocked",
                detail={"step_id": step.step_id, "reason": step.error_code},
                actor=actor,
                now=datetime.now(UTC),
            )
            continue
        if step.status == "not_attempted":
            # Hiç denenmeyen adım BAŞARISIZ değildir: sahte hata geçmişi yazılmaz.
            await _audit(
                session,
                plan=plan,
                plan_id=plan.plan_id,
                kind="step_not_attempted",
                detail={"step_id": step.step_id},
                actor=actor,
                now=datetime.now(UTC),
            )
            continue
        await _audit(
            session,
            plan=plan,
            plan_id=plan.plan_id,
            kind="step_completed" if step.status == "completed" else "step_failed",
            detail={"step_id": step.step_id, "status": step.status, "error": step.error_code},
            actor=actor,
            now=datetime.now(UTC),
        )
    await _audit(
        session,
        plan=plan,
        plan_id=plan.plan_id,
        kind="execution_finished",
        detail={"final_status": outcome.final_status, "failure": outcome.failure_code},
        actor=actor,
        now=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Okuma
# ---------------------------------------------------------------------------


async def get_plan(session: AsyncSession, plan_row_id: int, *, now: datetime | None = None) -> dict:
    moment = now or datetime.now(UTC)
    await expire_due_plans(session, now=moment)
    await session.commit()
    plan = await _load_plan(session, plan_row_id)
    await session.refresh(plan)
    receipts = list(
        (
            await session.execute(
                select(ExecutionReceipt)
                .where(ExecutionReceipt.plan_row_id == plan.id)
                .order_by(ExecutionReceipt.ordinal.asc())
            )
        ).scalars()
    )
    latest = await _latest_revision(session, plan.plan_id)
    return _plan_view(plan, receipts=receipts, is_current=latest == plan.revision)


async def list_plans(
    session: AsyncSession,
    *,
    states: list[str] | None = None,
    limit: int = 20,
    now: datetime | None = None,
) -> list[dict]:
    moment = now or datetime.now(UTC)
    await expire_due_plans(session, now=moment)
    await session.commit()
    bounded = max(1, min(int(limit), MAX_LIST_LIMIT))
    statement = select(ExecutionPlan).order_by(
        ExecutionPlan.updated_at.desc(), ExecutionPlan.id.desc()
    )
    if states:
        statement = statement.where(ExecutionPlan.state.in_(states))
    statement = statement.limit(bounded)
    rows = list((await session.execute(statement)).scalars())
    for row in rows:
        await session.refresh(row)
    latest_cache: dict[uuid.UUID, str | None] = {}
    views: list[dict] = []
    for row in rows:
        if row.plan_id not in latest_cache:
            latest_cache[row.plan_id] = await _latest_revision(session, row.plan_id)
        views.append(_plan_view(row, receipts=[], is_current=latest_cache[row.plan_id] == row.revision))
    return views


def _plan_view(plan: ExecutionPlan, *, receipts: list[ExecutionReceipt], is_current: bool) -> dict:
    """Hermes ve arayüz AYNI canonical plan durumunu okur (§28)."""
    return {
        "plan_row_id": plan.id,
        "plan_id": str(plan.plan_id),
        "revision": plan.revision,
        "is_current_revision": is_current,
        "state": plan.state,
        "title": plan.title,
        "summary": plan.summary,
        "reason": plan.reason,
        "steps": plan.steps,
        "step_count": plan.step_count,
        "mutation_count": plan.mutation_count,
        "budget": plan.budget,
        "source_refs": plan.source_refs,
        "evidence_refs": plan.evidence_refs,
        # Kanit durumu: yalnizca `entity:` referanslari GERCEKTEN dogrulanir.
        "verified_refs": plan.verified_refs or [],
        "unresolved_refs": plan.unresolved_refs or [],
        "validation_status": plan.validation_status,
        "validation_errors": plan.validation_errors,
        "input_questions": plan.input_questions,
        "input_answers": plan.input_answers,
        "approved_revision": plan.approved_revision,
        "approved_at": plan.approved_at.isoformat() if plan.approved_at else None,
        "expires_at": plan.expires_at.isoformat() if plan.expires_at else None,
        "decision_required": plan.state in {"awaiting_approval", "input_required"},
        # Çökmüş yürütme: kullanıcı/ajan desteklenen kurtarma yolunu görebilsin.
        "needs_recovery": plan.state == "executing"
        and execution_mod.lease_is_stale(plan, now=datetime.now(UTC)),
        "lease_age_seconds": int(execution_mod.lease_age_seconds(plan, now=datetime.now(UTC)) or 0)
        if plan.state == "executing"
        else None,
        "final_status": plan.final_status,
        "failure_code": plan.failure_code,
        "receipts": [
            {
                "step_id": item.step_id,
                "ordinal": item.ordinal,
                "action": item.action,
                "target": item.target,
                "status": item.status,
                "error_code": item.error_code,
                "result_ref": item.result_ref,
                "completed_at": item.completed_at.isoformat() if item.completed_at else None,
            }
            for item in receipts
        ],
        "created_at": plan.created_at.isoformat(),
        "updated_at": plan.updated_at.isoformat(),
    }


__all__ = [
    "ExecutionPlanError",
    "TransitionError",
    "approve",
    "cancel",
    "execute",
    "expire_due_plans",
    "get_plan",
    "list_plans",
    "prepare",
    "recover",
    "reject",
    "respond",
]
