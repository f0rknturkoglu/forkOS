"""H7 yürütme — onaylı TAM revizyonun sınırlı, H1 üzerinden yürütülmesi.

Kurallar:

```text
1. Claim DB-desteklidir: `approved → executing` yalnızca koşullu UPDATE ile.
2. Sıra deterministiktir (ordinal).
3. Her adım öncesi freshness yeniden doğrulanır; stale ise DURULUR.
4. İlk hatada DURULUR (best-effort devam YOK).
5. Otomatik rollback/compensation YOKTUR: sonuç PARTIAL olabilir ve dürüstçe
   raporlanır.
6. Adım başına TEK durable makbuz vardır; tamamlanmış adım restart sonrası
   YENİDEN yürütülmez. Makbuz ile mutasyon arasında çökme olursa adım
   "mutabakat gerekli" sayılır ve körlemesine tekrarlanmaz.
```

Model çağrısı YOKTUR: plan hazır ve onaylıysa yürütme deterministiktir (§59).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity
from app.integrations.agent.write_registry import BY_NAME, run_action
from app.modules.execution.models import (
    MAX_RECEIPT_DETAIL,
    ExecutionDecision,
    ExecutionPlan,
    ExecutionReceipt,
)

log = logging.getLogger("execution")

#: Yürütücü kimliği: süreç başına rastgele jeton (crash sonrası sahiplik izi).
EXECUTOR_TOKEN = uuid.uuid4().hex[:16]


class ExecutionError(Exception):
    """Sınırlı, model-okunur yürütme hatası."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass
class StepOutcome:
    step_id: str
    ordinal: int
    status: str
    action: str
    target: str | None = None
    error_code: str | None = None
    result_ref: str | None = None


@dataclass
class ExecutionOutcome:
    final_status: str
    steps: list[StepOutcome]
    failure_code: str | None = None


async def claim_plan(session: AsyncSession, plan_row: ExecutionPlan, *, now: datetime) -> bool:
    """`approved → executing` geçişini ATOMİK sahiplenir (§22).

    İkinci eşzamanlı çağrı burada kaybeder ve `False` alır: aynı revizyon iki
    kez yürütülemez. Process-local kilit yeterli değildir.
    """
    from sqlalchemy import update

    result = await session.execute(
        update(ExecutionPlan)
        .where(ExecutionPlan.id == plan_row.id, ExecutionPlan.state == "approved")
        .values(
            state="executing",
            execution_started_at=now,
            executor_token=EXECUTOR_TOKEN,
            updated_at=now,
        )
        .returning(ExecutionPlan.id)
    )
    return result.scalar_one_or_none() is not None


async def _decision(
    session: AsyncSession,
    *,
    plan: ExecutionPlan,
    kind: str,
    detail: dict[str, Any] | None = None,
    now: datetime,
) -> None:
    session.add(
        ExecutionDecision(
            plan_id=plan.plan_id,
            plan_row_id=plan.id,
            kind=kind,
            revision=plan.revision,
            detail=detail or {},
            actor="h7",
            at=now,
        )
    )


def _receipt_detail(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text[:MAX_RECEIPT_DETAIL]


async def _fresh_target_stamp(
    session: AsyncSession, step_arguments: dict[str, Any], expected: str | None
) -> tuple[bool, str | None]:
    """Hedefin GÜNCEL `updated_at` damgasını döner; adım bayatlarsa False.

    Onay anındaki damga ile şimdiki damga farklıysa adım stale'dir: kullanıcı
    gördüğü planı onayladı, ama canonical durum değişti.
    """
    spec_target = None
    for spec in BY_NAME.values():
        if spec.target_field and spec.target_field in step_arguments:
            spec_target = step_arguments[spec.target_field]
            break
    if spec_target is None:
        return True, None
    try:
        entity_id = uuid.UUID(str(spec_target))
    except (ValueError, AttributeError):
        return True, None
    row = (await session.execute(select(Entity.id, Entity.updated_at).where(Entity.id == entity_id))).first()
    if row is None:
        return False, None
    current = row.updated_at.isoformat()
    if expected is not None and current != expected:
        return False, current
    return True, current


async def execute_plan(
    session: AsyncSession,
    plan_row: ExecutionPlan,
    *,
    now: datetime | None = None,
) -> ExecutionOutcome:
    """Onaylı planı adım adım yürütür. H1 dışında HİÇBİR yazma yapmaz."""
    moment = now or datetime.now(UTC)
    steps = list(plan_row.steps or [])
    existing = {
        receipt.step_id: receipt
        for receipt in (
            await session.execute(
                select(ExecutionReceipt).where(ExecutionReceipt.plan_row_id == plan_row.id)
            )
        ).scalars()
    }

    outcomes: list[StepOutcome] = []
    failed = False
    blocked = False

    for index, raw_step in enumerate(steps):
        step_id = str(raw_step.get("step_id") or f"s{index + 1}")
        action = str(raw_step.get("action") or "")
        arguments = dict(raw_step.get("arguments") or {})
        expected = raw_step.get("expected_updated_at")
        spec = BY_NAME.get(action)
        target = None
        if spec and spec.target_field:
            target = arguments.get(spec.target_field)
        target_text = str(target) if target is not None else None

        prior = existing.get(step_id)
        if prior is not None and prior.status == "completed":
            # Tamamlanmış adım restart sonrası TEKRAR YÜRÜTÜLMEZ (§20).
            outcomes.append(
                StepOutcome(step_id, index, "completed", action, target_text, None, prior.result_ref)
            )
            continue
        if prior is not None and prior.status == "failed":
            failed = True
            outcomes.append(
                StepOutcome(step_id, index, "failed", action, target_text, prior.error_code)
            )
            continue
        if prior is not None and prior.status == "not_attempted":
            # Makbuz yazıldı ama sonuç bilinmiyor: MUTABAKAT GEREKLİ (§21).
            # Körlemesine tekrar denemek duplicate mutation riski taşır.
            blocked = True
            outcomes.append(
                StepOutcome(
                    step_id,
                    index,
                    "not_attempted",
                    action,
                    target_text,
                    "RECONCILIATION_REQUIRED",
                )
            )
            continue

        if failed or blocked:
            # İlk hatadan sonraki adımlar DENENMEZ (§16).
            session.add(
                ExecutionReceipt(
                    plan_row_id=plan_row.id,
                    step_id=step_id,
                    ordinal=index,
                    action=action,
                    target=target_text,
                    idempotency_key=f"{plan_row.revision}:{step_id}",
                    status="not_attempted",
                    started_at=moment,
                )
            )
            outcomes.append(StepOutcome(step_id, index, "not_attempted", action, target_text))
            continue

        if spec is None:
            session.add(
                ExecutionReceipt(
                    plan_row_id=plan_row.id,
                    step_id=step_id,
                    ordinal=index,
                    action=action,
                    target=target_text,
                    idempotency_key=f"{plan_row.revision}:{step_id}",
                    status="failed",
                    error_code="UNKNOWN_ACTION",
                    started_at=moment,
                    completed_at=moment,
                )
            )
            outcomes.append(StepOutcome(step_id, index, "failed", action, target_text, "UNKNOWN_ACTION"))
            failed = True
            continue

        fresh, _current = await _fresh_target_stamp(session, arguments, expected)
        if not fresh:
            session.add(
                ExecutionReceipt(
                    plan_row_id=plan_row.id,
                    step_id=step_id,
                    ordinal=index,
                    action=action,
                    target=target_text,
                    idempotency_key=f"{plan_row.revision}:{step_id}",
                    status="failed",
                    error_code="STEP_STALE",
                    started_at=moment,
                    completed_at=moment,
                )
            )
            outcomes.append(StepOutcome(step_id, index, "failed", action, target_text, "STEP_STALE"))
            failed = True
            continue

        receipt = ExecutionReceipt(
            plan_row_id=plan_row.id,
            step_id=step_id,
            ordinal=index,
            action=action,
            target=target_text,
            idempotency_key=f"{plan_row.revision}:{step_id}",
            status="not_attempted",
            started_at=moment,
            claimed_by=EXECUTOR_TOKEN,
        )
        session.add(receipt)
        await session.flush()

        try:
            data = spec.model(**arguments)
            result = await run_action(session, spec, data)
        except Exception as exc:  # noqa: BLE001 — H1 hataları sınırlı koda çevrilir
            log.warning("H7 adimi basarisiz: %s (%s)", action, type(exc).__name__)
            receipt.status = "failed"
            receipt.error_code = _error_code(exc)
            receipt.detail = _receipt_detail(str(exc))
            receipt.completed_at = datetime.now(UTC)
            outcomes.append(
                StepOutcome(step_id, index, "failed", action, target_text, receipt.error_code)
            )
            failed = True
            continue

        entity_id = getattr(result, "entity_id", None) or getattr(result, "id", None)
        receipt.status = "completed"
        receipt.result_ref = str(entity_id) if entity_id else None
        receipt.detail = _receipt_detail(getattr(result, "message", None))
        receipt.completed_at = datetime.now(UTC)
        outcomes.append(
            StepOutcome(step_id, index, "completed", action, target_text, None, receipt.result_ref)
        )

    completed = [item for item in outcomes if item.status == "completed"]
    if blocked:
        final = "partial" if completed else "failed"
        failure = "RECONCILIATION_REQUIRED"
    elif failed:
        final = "partial" if completed else "failed"
        failure = next(
            (item.error_code for item in outcomes if item.status == "failed"), "STEP_FAILED"
        )
    else:
        final = "completed"
        failure = None

    return ExecutionOutcome(
        final_status=final,
        steps=outcomes,
        failure_code=failure if (failed or blocked) else None,
    )


def _error_code(exc: Exception) -> str:
    """H1 hataları sınırlı koda indirilir; yığın izi dışarı sızmaz."""
    text = str(exc)
    for code in (
        "INVALID_INPUT",
        "NOT_FOUND",
        "STALE",
        "EXPIRED",
        "CONFLICT",
        "ACTION_ERROR",
        "FORBIDDEN",
    ):
        if code in text.upper():
            return code
    name = type(exc).__name__
    return "ACTION_FAILED" if name not in {"ActionError", "ValueError"} else "INVALID_INPUT"
