"""Day-level conservative planning. Clock times only come from confirmed availability."""

from datetime import timedelta

from sqlalchemy import or_, select, text

from app.core.models import Entity
from app.core.time import local_datetime, local_today
from app.modules.calendar.models import ExternalEvent
from app.modules.goal.package_schemas import ScheduleTask
from app.modules.todo.models import PlanSlot


async def snapshot(db, proposal, *, lock=False):
    days = sorted({op.data.day for op in proposal.operations if isinstance(op, ScheduleTask)})
    if not days:
        return None
    if lock:
        await db.execute(text("SELECT pg_advisory_xact_lock(8010081)"))
    replaced_ids = [
        op.replace_slot_id
        for op in proposal.operations
        if isinstance(op, ScheduleTask) and op.replace_slot_id
    ]
    stmt = (
        select(PlanSlot)
        .where(or_(PlanSlot.day.in_(days), PlanSlot.id.in_(replaced_ids)))
        .order_by(PlanSlot.day, PlanSlot.id)
        .limit(2001)
    )
    if lock:
        stmt = stmt.with_for_update()
    rows = (await db.scalars(stmt)).all()
    if len(rows) > 2000:
        raise ValueError("Plan kayıtları sınırı aşıldı")
    output = [
        {
            "kind": "slot",
            "id": str(s.id),
            "entity_id": str(s.entity_id),
            "day": s.day.isoformat(),
            "start": s.start_min,
            "duration": s.duration_min,
            "note": s.note,
            "google": s.google_event_id,
        }
        for s in rows
    ]
    events = (
        await db.scalars(
            select(ExternalEvent)
            .join(Entity, Entity.id == ExternalEvent.id)
            .where(
                Entity.archived_at.is_(None),
                ExternalEvent.starts_at < local_datetime(days[-1] + timedelta(days=1), 0),
                ExternalEvent.ends_at > local_datetime(days[0], 0),
            )
            .order_by(ExternalEvent.id)
            .limit(501)
        )
    ).all()
    if len(events) > 500:
        raise ValueError("Takvim uygunluk kapsamı aşıldı")
    output.extend(
        {
            "kind": "event",
            "id": str(e.id),
            "starts_at": e.starts_at.isoformat(),
            "ends_at": e.ends_at.isoformat(),
            "all_day": e.all_day,
        }
        for e in events
    )
    return output


def validate(proposal, slots):
    ops = [op for op in proposal.operations if isinstance(op, ScheduleTask)]
    if not ops:
        return
    constraints = proposal.planning
    if not constraints:
        raise ValueError("Takvim planı çalışma kapasitesi içermeli")
    if len(ops) > 28:
        raise ValueError("İlk plan en fazla 28 çalışma bloğu içerebilir")
    replaced = {str(op.replace_slot_id) for op in ops if op.replace_slot_id}
    existing = [s for s in slots if s.get("kind", "slot") == "slot" and s["id"] not in replaced]
    load, intervals = {}, {}
    unknown_duration = set()
    for s in existing:
        day = s["day"]
        if s["duration"] is None:
            unknown_duration.add(day)
        load[day] = load.get(day, 0) + (s["duration"] or 0)
        if s["start"] is not None:
            intervals.setdefault(day, []).append((s["start"], s["start"] + (s["duration"] or 30)))
    for op in ops:
        block = op.data
        if not local_today() <= block.day < local_today() + timedelta(days=14):
            raise ValueError("Başlangıç planı bugünden başlayan 14 gün içinde olmalı")
        day = block.day.isoformat()
        if (
            block.day in constraints.unavailable_days
            or block.day.weekday() not in constraints.weekdays
        ):
            raise ValueError("Plan uygun olmayan bir güne yerleştirilemez")
        if day in unknown_duration:
            raise ValueError("Mevcut çalışma süresi belirsiz; önce o günün plan süresini belirt")
        load[day] = load.get(day, 0) + block.duration_min
        if load[day] > constraints.daily_capacity_min:
            raise ValueError("Günlük çalışma kapasitesi aşılıyor; planı dağıt")
        if block.start_min is not None:
            old = next(
                (
                    s
                    for s in slots
                    if s.get("kind", "slot") == "slot" and s["id"] == str(op.replace_slot_id)
                ),
                None,
            )
            preserving = old is not None and old["start"] == block.start_min
            if not preserving and (
                constraints.available_start_min is None or not constraints.capacity_confirmed
            ):
                raise ValueError(
                    "Kesin saat için kullanıcı tarafından doğrulanmış çalışma aralığı gerekli"
                )
            from datetime import datetime

            start_at = local_datetime(block.day, block.start_min)
            end_at = start_at + timedelta(minutes=block.duration_min)
            if any(
                start_at < datetime.fromisoformat(e["ends_at"])
                and end_at > datetime.fromisoformat(e["starts_at"])
                for e in slots
                if e.get("kind") == "event" and not e["all_day"]
            ):
                raise ValueError("Çalışma saati yerel takvimdeki etkinlikle çakışıyor")
            end = block.start_min + block.duration_min
            if constraints.available_start_min is not None and (
                block.start_min < constraints.available_start_min
                or end > constraints.available_end_min
            ):
                raise ValueError("Plan uygun çalışma saatleri dışında")
            if any(block.start_min < b and end > a for a, b in intervals.get(day, [])):
                raise ValueError("Plan saati mevcut çalışmayla çakışıyor")
            intervals.setdefault(day, []).append((block.start_min, end))


async def propose(db, tasks, constraints):
    """Tasks: (operation ref, duration). Skip blocked days; never overwrite commitments."""
    today = local_today()
    slots = (
        await db.scalars(
            select(PlanSlot)
            .where(PlanSlot.day >= today, PlanSlot.day < today + timedelta(days=14))
            .limit(2001)
        )
    ).all()
    if len(slots) > 2000:
        return [], ["Mevcut takvim çok büyük; görevler planlanmadan önerildi"]
    loads, unknown = {}, set()
    for s in slots:
        loads[s.day] = loads.get(s.day, 0) + (s.duration_min or 0)
        if s.duration_min is None:
            unknown.add(s.day)
    output, warnings = [], []
    events = (
        await db.scalars(
            select(ExternalEvent)
            .join(Entity, Entity.id == ExternalEvent.id)
            .where(
                Entity.archived_at.is_(None),
                ExternalEvent.starts_at < local_datetime(today + timedelta(days=14), 0),
                ExternalEvent.ends_at > local_datetime(today, 0),
            )
            .limit(501)
        )
    ).all()
    if len(events) > 500:
        return [], ["Takvim uygunluk kapsamı çok büyük; önce mevcut planı gözden geçir"]
    precise = constraints.capacity_confirmed and constraints.available_start_min is not None
    busy = {}
    for slot in slots:
        if slot.start_min is not None:
            busy.setdefault(slot.day, []).append(
                (slot.start_min, slot.start_min + (slot.duration_min or 30))
            )
    for offset in range(14):
        day = today + timedelta(days=offset)
        start = local_datetime(day, 0)
        end = start + timedelta(days=1)
        for event in events:
            if event.starts_at < end and event.ends_at > start:
                if event.all_day:
                    busy.setdefault(day, []).append((0, 1440))
                else:
                    busy.setdefault(day, []).append(
                        (
                            max(0, int((event.starts_at - start).total_seconds() / 60)),
                            min(1440, int((event.ends_at - start).total_seconds() / 60)),
                        )
                    )
    if events and not precise:
        warnings.append(
            "Yerel takvimde etkinlikler var. Çalışmalar gün düzeyinde önerildi; kesin saat seçerken etkinlikler tekrar kontrol edilir."
        )
    cursor = 0
    for ref, duration in tasks:
        remaining = duration
        for offset in range(cursor, 14):
            if not remaining or len(output) >= 28:
                break
            day = today + timedelta(days=offset)
            if (
                day in unknown
                or day in constraints.unavailable_days
                or day.weekday() not in constraints.weekdays
            ):
                continue
            available = constraints.daily_capacity_min - loads.get(day, 0)
            if available <= 0:
                continue
            block_duration = min(remaining, available)
            clock = None
            if precise:
                clock = constraints.available_start_min
                best = None
                for a, b in sorted([*busy.get(day, []), (constraints.available_end_min, 1440)]):
                    if a > clock:
                        gap = min(a, constraints.available_end_min) - clock
                        if gap > 0 and (best is None or gap > best[1]):
                            best = (clock, gap)
                    clock = max(clock, b)
                    if clock >= constraints.available_end_min:
                        break
                if not best:
                    continue
                clock, space = best
                block_duration = min(block_duration, space)
                busy.setdefault(day, []).append((clock, clock + block_duration))
            output.append(
                {
                    "type": "plan.schedule",
                    "key": f"slot_{len(output)}",
                    "task_ref": ref,
                    "data": {
                        "day": day.isoformat(),
                        "duration_min": block_duration,
                        **({"start_min": clock} if clock is not None else {}),
                    },
                }
            )
            loads[day] = loads.get(day, 0) + block_duration
            remaining -= block_duration
            cursor = offset
        if remaining:
            warnings.append(
                f"{ref}: {remaining} dakikalık devam çalışması başlangıç penceresine sığmadı; sonraki planlamada yerleştirilmeli."
            )
    return output, warnings[:12]
