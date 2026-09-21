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

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity
from app.integrations.agent.write_registry import BY_NAME, run_action
from app.modules.execution.models import (
    EXECUTOR_STALE_AFTER_SECONDS,
    MAX_RECEIPT_DETAIL,
    ExecutionPlan,
    ExecutionReceipt,
)

log = logging.getLogger("execution")

def new_executor_token() -> str:
    """Her YÜRÜTME DENEMESİ için yeni sahiplik jetonu (fencing nonce).

    Süreç-global bir jeton YETKİ KAYNAĞI DEĞİLDİR: devralınan bir plan eski
    süreci değil, o sürecin DENEMESİNİ geçersiz kılar. Jeton sır değildir;
    yalnızca "hangi deneme sahip" sorusunu yanıtlar.
    """
    return uuid.uuid4().hex[:16]


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


async def claim_plan(
    session: AsyncSession, plan_row: ExecutionPlan, *, now: datetime
) -> str | None:
    """`approved → executing` geçişini ATOMİK sahiplenir ve DENEME jetonunu döner.

    İkinci eşzamanlı çağrı burada kaybeder ve `None` alır: aynı revizyon iki
    kez yürütülemez. Process-local kilit yeterli değildir.
    """
    token = new_executor_token()
    from sqlalchemy import update

    result = await session.execute(
        update(ExecutionPlan)
        .where(ExecutionPlan.id == plan_row.id, ExecutionPlan.state == "approved")
        .values(
            state="executing",
            execution_started_at=now,
            execution_heartbeat_at=now,
            executor_token=token,
            updated_at=now,
        )
        .returning(ExecutionPlan.id)
    )
    return token if result.scalar_one_or_none() is not None else None


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


def lease_is_stale(plan_row: ExecutionPlan, *, now: datetime) -> bool:
    """Yürütücü lease'i bayat mı? Canlı bir süreç KORUNUR.

    Kalp atışı adım sınırlarında yazılır; eşik tek bir adımın makul üst
    sınırından büyük seçildi. Böylece "yavaş ama canlı" yürütücü sahiplikten
    edilmez, çökmüş yürütücü ise SONSUZA DEK `executing` kalmaz.
    """
    heartbeat = plan_row.execution_heartbeat_at or plan_row.execution_started_at
    if heartbeat is None:
        return True
    if heartbeat.tzinfo is None:
        heartbeat = heartbeat.replace(tzinfo=UTC)
    return (now - heartbeat).total_seconds() > EXECUTOR_STALE_AFTER_SECONDS


def lease_age_seconds(plan_row: ExecutionPlan, *, now: datetime) -> float | None:
    heartbeat = plan_row.execution_heartbeat_at or plan_row.execution_started_at
    if heartbeat is None:
        return None
    if heartbeat.tzinfo is None:
        heartbeat = heartbeat.replace(tzinfo=UTC)
    return max((now - heartbeat).total_seconds(), 0.0)


async def touch_heartbeat(
    session: AsyncSession, plan_row_id: int, *, token: str, now: datetime
) -> bool:
    """Adım sınırlarında yürütücünün canlı olduğunu yazar (ayrı zamanlayıcı YOK).

    Güncelleme JETONA bağlıdır: sahipliği kaybetmiş (devralınmış) bir yürütücü
    yeni sahibin lease'ini TAZELEYEMEZ. `False` → EXECUTION_OWNERSHIP_LOST.
    """
    result = await session.execute(
        update(ExecutionPlan)
        .where(
            ExecutionPlan.id == plan_row_id,
            ExecutionPlan.state == "executing",
            ExecutionPlan.executor_token == token,
        )
        .values(execution_heartbeat_at=now, updated_at=now)
        .returning(ExecutionPlan.id)
    )
    updated = result.scalar_one_or_none() is not None
    await session.flush()
    return updated


async def assert_execution_owner(
    session: AsyncSession, plan_row_id: int, *, token: str
) -> bool:
    """Sahiplik hâlâ bende mi? (her adımdan ÖNCE ve uzun adımdan SONRA)."""
    owner = (
        await session.execute(
            select(ExecutionPlan.executor_token, ExecutionPlan.state).where(
                ExecutionPlan.id == plan_row_id
            )
        )
    ).first()
    if owner is None:
        return False
    return owner.state == "executing" and owner.executor_token == token


async def finalize_if_owner(
    session: AsyncSession,
    plan_row_id: int,
    *,
    token: str,
    final_status: str,
    failure_code: str | None,
    now: datetime,
) -> bool:
    """Plan sonucu YALNIZCA güncel sahip tarafından yazılır (§7).

    Yarışı kaybeden eski yürütücü kazananın nihai durumunu EZEMEZ.
    """
    result = await session.execute(
        update(ExecutionPlan)
        .where(
            ExecutionPlan.id == plan_row_id,
            ExecutionPlan.state == "executing",
            ExecutionPlan.executor_token == token,
        )
        .values(
            state=final_status,
            final_status=final_status,
            failure_code=failure_code,
            execution_finished_at=now,
            updated_at=now,
        )
        .returning(ExecutionPlan.id)
    )
    updated = result.scalar_one_or_none() is not None
    await session.flush()
    return updated


async def execute_plan(
    session: AsyncSession,
    plan_row: ExecutionPlan,
    *,
    token: str,
    now: datetime | None = None,
) -> ExecutionOutcome:
    """`token` sahibi yürütücü tarafından çağrılır; sahiplik kaybedilirse DURUR."""
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
    ownership_lost = False
    if not await assert_execution_owner(session, plan_row.id, token=token):
        # Sahiplik zaten devralınmış: HİÇBİR adım başlatılmaz, hiçbir şey yazılmaz.
        return ExecutionOutcome(
            final_status="failed", steps=[], failure_code="EXECUTION_OWNERSHIP_LOST"
        )

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
        if prior is not None and prior.status == "not_attempted" and prior.claimed_by is None:
            # Hiç DENENMEDİ (önceki adım düştü ya da yürütücü adıma sıra
            # gelmeden öldü): GÜVENLE sürdürülür. Talep satırı yeniden
            # açılmaz; var olan makbuz sahiplenilir (UNIQUE korunur).
            claimed = prior
        elif prior is not None and prior.status in {"not_attempted", "unresolved"}:
            # Makbuz ALINDI ama sonuç bilinmiyor: mutasyon olmuş OLABİLİR.
            # Körlemesine tekrar denemek duplicate mutation riski taşır; bu
            # yüzden adım AYRI bir durumla işaretlenir (H7.1: "hiç denenmedi"
            # ile "sonucu bilinmiyor" aynı değerde birleştirilmez).
            prior.status = "unresolved"
            prior.error_code = "RECONCILIATION_REQUIRED"
            prior.claimed_by = prior.claimed_by
            blocked = True
            outcomes.append(
                StepOutcome(
                    step_id,
                    index,
                    "unresolved",
                    action,
                    target_text,
                    "RECONCILIATION_REQUIRED",
                )
            )
            continue
        else:
            claimed = None

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

        # Uzun adımlarda (özellikle Vault yazmaları) lease tazelenir. Kalp
        # atışı JETONA bağlıdır: sahiplik devralındıysa bu adım BAŞLAMAZ.
        if not await touch_heartbeat(session, plan_row.id, token=token, now=datetime.now(UTC)):
            ownership_lost = True
            outcomes.append(
                StepOutcome(step_id, index, "not_attempted", action, target_text, "EXECUTION_OWNERSHIP_LOST")
            )
            break

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

        if claimed is not None:
            receipt = claimed
            receipt.claimed_by = token
            receipt.started_at = moment
            receipt.status = "not_attempted"
        else:
            receipt = ExecutionReceipt(
                plan_row_id=plan_row.id,
                step_id=step_id,
                ordinal=index,
                action=action,
                target=target_text,
                idempotency_key=f"{plan_row.revision}:{step_id}",
                # "SAHIPLENILDI" izi: bu satir varsa mutasyon olmus OLABILIR.
                status="not_attempted",
                started_at=moment,
                claimed_by=token,
            )
            session.add(receipt)
        await session.flush()

        # --- ADIM NIYETI: yan etkiden ONCE DAYANIKLI olmali (final gate) ----
        #
        # Neden TUM aksiyonlarda: `flush()` baska bir transaction'a GORUNMEZ.
        # Niyet commit edilmezse, bayat lease'i devralan kurtarici adimi "hic
        # talep edilmedi" sanabilir. Ayrica bu commit adim satirindaki kilidi
        # BIRAKIR: aksi halde uzun bir aksiyon surerken `recover()` cagrisi
        # kilitte bekler ve kurtarma pratikte yapilamaz hale gelir.
        #
        # Guvenlik tercihi: niyet yazildiktan SONRA cokme, hic mutasyon
        # olmamis olsa bile "mutabakat gerekli" uretir. Bu KABUL EDILIR:
        # belirsizken durmak, belirsizken tekrar denemekten her zaman iyidir.
        await session.commit()
        await session.refresh(receipt)

        # Commit siniri transaction'i degistirdi: H1'e GIRMEDEN once sahipligi
        # YENIDEN dogrula (devralma tam bu arada olabilir).
        if not await assert_execution_owner(session, plan_row.id, token=token):
            ownership_lost = True
            outcomes.append(
                StepOutcome(
                    step_id,
                    index,
                    # Niyet duruyor ama aksiyon HIC cagrilmadi: tarihsel
                    # sahiplik korunur, durum "kurtarilabilir" kalir.
                    "not_attempted",
                    action,
                    target_text,
                    "EXECUTION_OWNERSHIP_LOST",
                )
            )
            await session.commit()
            break

        try:
            data = spec.model(**arguments)
            result = await run_action(session, spec, data)
        except Exception as exc:  # noqa: BLE001 — H1 hataları sınırlı koda çevrilir
            log.warning("H7 adimi basarisiz: %s (%s)", action, type(exc).__name__)
            # Vault (dosya sistemi) adımları DB işlemiyle AYNI atomik
            # transaction'da DEĞİLDİR: yazma başarılı olup süreç ölürse sonuç
            # belirsizdir. Bu yüzden yan etki alanı `vault` olan adımlar
            # "mutabakat gerekli" işaretlenir, "failed" DENMEZ (§11-13).
            if spec.side_effect_domain == "vault":
                receipt.status = "unresolved"
                receipt.error_code = "SIDE_EFFECT_UNCERTAIN"
            else:
                receipt.status = "failed"
                receipt.error_code = _error_code(exc)
            receipt.detail = _receipt_detail(str(exc))
            receipt.completed_at = datetime.now(UTC)
            outcomes.append(
                StepOutcome(step_id, index, receipt.status, action, target_text, receipt.error_code)
            )
            if receipt.status == "unresolved":
                blocked = True
            else:
                failed = True
            continue

        if not await assert_execution_owner(session, plan_row.id, token=token):
            # H1 mutasyonu ÇALIŞIRKEN sahiplik devralındı. Geri alma YOK;
            # makbuz dürüstçe işaretlenir ve DURULUR (sonraki adım başlamaz).
            receipt.status = "unresolved"
            receipt.error_code = "EXECUTION_OWNERSHIP_LOST"
            receipt.completed_at = datetime.now(UTC)
            outcomes.append(
                StepOutcome(step_id, index, "unresolved", action, target_text, receipt.error_code)
            )
            ownership_lost = True
            break

        entity_id = getattr(result, "entity_id", None) or getattr(result, "id", None)
        receipt.status = "completed"
        receipt.result_ref = str(entity_id) if entity_id else None
        receipt.detail = _receipt_detail(getattr(result, "message", None))
        receipt.completed_at = datetime.now(UTC)
        outcomes.append(
            StepOutcome(step_id, index, "completed", action, target_text, None, receipt.result_ref)
        )

    if ownership_lost:
        completed_now = [item for item in outcomes if item.status == "completed"]
        return ExecutionOutcome(
            final_status="partial" if completed_now else "failed",
            steps=outcomes,
            failure_code="EXECUTION_OWNERSHIP_LOST",
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
