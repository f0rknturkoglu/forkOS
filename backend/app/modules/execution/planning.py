"""User-intent → existing H7 preparation; no new execution path."""

from datetime import date
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select, text

from app.core.models import Entity
from app.core.time import local_today
from app.modules.execution import service
from app.modules.execution.models import ExecutionPlan
from app.modules.todo.models import PlanSlot, Todo


class PlanningIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client_uuid: UUID
    todo_ids: list[UUID] = Field(min_length=1, max_length=10)
    day: date

    @model_validator(mode="after")
    def unique(self):
        if len(set(self.todo_ids)) != len(self.todo_ids):
            raise ValueError("Görevler tekrarlanamaz")
        return self


async def prepare_planning(db, body):
    await db.execute(
        text("SELECT pg_advisory_xact_lock(:key)"),
        {
            "key": int.from_bytes(body.client_uuid.bytes[:8], "big", signed=True),
        },
    )
    existing = await db.scalar(
        select(ExecutionPlan).where(ExecutionPlan.plan_id == body.client_uuid)
    )
    if existing:
        ids = {step["arguments"].get("todo_id") for step in existing.steps}
        days = {step["arguments"].get("day") for step in existing.steps}
        if ids != {str(i) for i in body.todo_ids} or days != {body.day.isoformat()}:
            raise HTTPException(409, "Plan kimliği farklı seçimle kullanılmış")
        return await service.get_plan(db, existing.id)
    if body.day < local_today():
        raise HTTPException(422, "Yeni plan geçmiş bir güne hazırlanamaz")
    steps = []
    for identity in sorted(body.todo_ids):
        entity = await db.get(Entity, identity)
        todo = await db.get(Todo, identity)
        if not entity or entity.archived_at or not todo or todo.status not in {"open", "doing"}:
            raise HTTPException(
                422, "Seçili görev yok, arşivlenmiş veya tamamlanmış; seçimi yenile"
            )
        slots = list(
            await db.scalars(
                select(PlanSlot)
                .where(
                    PlanSlot.entity_id == identity,
                    PlanSlot.day >= local_today(),
                )
                .order_by(PlanSlot.day, PlanSlot.id)
            )
        )
        if len(slots) > 1:
            raise HTTPException(
                422,
                "Görevin birden fazla gelecek planı var; önce normal planlayıcıdan hangi kaydı taşıyacağını seç",
            )
        slot = slots[0] if slots else None
        time_label = (
            f"{slot.start_min // 60:02d}:{slot.start_min % 60:02d}"
            if slot and slot.start_min is not None
            else "saat belirtilmemiş"
        )
        duration_label = (
            f"{slot.duration_min} dk"
            if slot and slot.duration_min is not None
            else "süre belirtilmemiş"
        )
        before = f"{slot.day} · {time_label} · {duration_label}" if slot else "Planlanmamış"
        steps.append(
            {
                "action": "todo_plan",
                "arguments": {
                    "todo_id": str(identity),
                    "day": body.day.isoformat(),
                    # H7 normalizes optional fields: explicitly preserve the existing time/duration.
                    "start_min": slot.start_min if slot else None,
                    "duration_min": slot.duration_min if slot else None,
                },
                "description": f"{entity.title[:180]} · Önce: {before} → Sonra: {body.day}; saat ve süre korunur. Son tarih değişmez.",
            }
        )
    plan = await service.prepare(
        db,
        title=f"Seçili görevleri {body.day} gününe planla",
        steps=steps,
        summary="Yalnız seçili mevcut görevlerin plan günü değişir. Son tarih ve tamamlanma durumu değişmez.",
        reason="Kullanıcının bağlam içinden yaptığı açık görev ve gün seçimi.",
        source_refs=["entity:" + str(i) for i in sorted(body.todo_ids)],
        plan_id=body.client_uuid,
        actor="forkos_ui",
    )
    return await service.get_plan(db, plan.id)
