"""H1 semantik yazma adaptörleri (Hermes "kontrollü eller").

Bu modül MCP ile gelen HER mutasyonun tek geçididir. Kural: burada domain
mantığı YOKTUR. Her fonksiyon şu sırayı izler:

    MCP girdisini doğrula (write_models)
    → hedefi/mevcut durumu çöz
    → H1'e özgü güvenlik önkoşulunu uygula (tazelik / belirsizlik)
    → canonical domain servisini çağır
    → sınırlı ActionReceipt döndür

Tasarım sınırları (H1 sözleşmesi):

  - Genel amaçlı mutasyon YOK: `call_api`, `execute_sql`, `write_file`,
    `update_entity` benzeri bir yüzey açılmaz. Her fonksiyon insan anlamlı
    TEK bir eylemdir.
  - Silme YOK. H1'de yıkıcı hiçbir yetenek bulunmaz.
  - Ağ erişimi YOK. Yalnızca yerel state yazılır; hiçbir adım dış servise
    istek atmaz (bookmark capture sayfa getirmez, fırsat zenginleştirmez).
  - Legacy Notlar'a YAZMA YOK. Bilgi yazmaları doğrudan Obsidian Vault'a
    gider (`integrations/obsidian/service.py`); bu dosya `Path.write_text`
    çağırmaz.
  - Hata "sessizce yutulmaz": her başarısızlık `ActionError` ile
    model-okunur bir kod taşır (§67/§68).

Tazelik: onay ile yürütme arasında durum değişebilir (§16). Güncellemeler
`expected_updated_at`, yaşam döngüsü geçişleri `expected_status`, Vault
yazmaları `expected_mtime` ile fail-closed davranır.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity
from app.core.time import local_today
from app.integrations.agent.write_models import (
    ActionReceipt,
    ApplicationTransitionIn,
    BookmarkCaptureIn,
    BookmarkUpdateIn,
    BrainCaptureIn,
    BrainSaveToEntityIn,
    OpportunityTransitionIn,
    ProjectUpdateIn,
    TodoCreateIn,
    TodoPlanIn,
    TodoUpdateIn,
)
from app.integrations.obsidian import service as obsidian_service
from app.modules.bookmark import service as bookmark_service
from app.modules.bookmark.models import Bookmark
from app.modules.bookmark.schemas import BookmarkUpdate, CaptureIn
from app.modules.opportunity import application as opportunity_application
from app.modules.opportunity.models import Application, Opportunity
from app.modules.opportunity.schemas import ApplyIn
from app.modules.project import service as project_service
from app.modules.project.models import Project
from app.modules.project.schemas import ProjectPatch
from app.modules.todo import service as todo_service
from app.modules.todo.models import PlanSlot, Todo
from app.modules.todo.schemas import PlanSlotIn, PlanSlotUpdate, TodoIn, TodoUpdate

#: Agent kaynaklı yer imi kaydı. Canonical `SOURCES` sözlüğünde "agent" yoktur;
#: "manual" insan onaylı el ile kaydın doğru karşılığıdır (§65).
_AGENT_BOOKMARK_SOURCE = "manual"


class ActionError(ValueError):
    """Model-okunur H1 eylem hatası.

    `ValueError` alt sınıfıdır: çağıranlar `except ValueError` ile de
    yakalayabilir, ama MCP katmanı `code` alanını kullanarak temiz bir
    ToolError üretir. Mesaj her zaman `KOD: açıklama` biçimindedir.
    """

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


# ---------------------------------------------------------------------------
# Ortak yardımcılar
# ---------------------------------------------------------------------------


def _parse_dt(value: str | None) -> datetime | None:
    if value is None:
        return None
    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value is not None else None


def _as_uuid(value: str | uuid.UUID) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value).strip())
    except (ValueError, AttributeError, TypeError) as exc:
        raise ActionError("TARGET_NOT_FOUND", f"geçersiz kimlik: {value!r}") from exc


def _assert_fresh(entity: Entity, expected_updated_at: str | None) -> None:
    """İyimser önkoşul: onaylanan sürüm hâlâ geçerli mi (§17)."""
    if expected_updated_at is None:
        return
    expected = _parse_dt(expected_updated_at)
    if expected is None:
        return
    actual = entity.updated_at
    if actual.tzinfo is None:
        actual = actual.replace(tzinfo=UTC)
    if actual.astimezone(UTC) != expected.astimezone(UTC):
        raise ActionError(
            "STALE_ACTION",
            f"kayıt beklenen sürümden sonra değişmiş "
            f"(beklenen updated_at={expected.isoformat()}, güncel={actual.isoformat()})",
        )


async def _require_entity(session: AsyncSession, item_id: uuid.UUID, label: str) -> Entity:
    entity = await session.get(Entity, item_id)
    if entity is None:
        raise ActionError("TARGET_NOT_FOUND", f"{label} bulunamadı: {item_id}")
    return entity


def _todo_state(
    source: Todo | Any, *, title: str, tags: list[str]
) -> dict[str, Any]:
    """Görevin sınırlı, insan-okunur durumu.

    `title` Entity'de yaşadığı için (Todo modelinde kolon yoktur) dışarıdan
    verilir; etiketler de entity_tag üzerinden geldiği için çağıran getirir.
    """
    return {
        "title": title,
        "status": source.status,
        "priority": source.priority,
        "description": source.description,
        "due_at": source.due_at.isoformat() if source.due_at else None,
        "reminder_at": source.reminder_at.isoformat() if source.reminder_at else None,
        "recur": source.recur,
        "tags": sorted(tags),
    }


def _changed_fields(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    return sorted(key for key in after if before.get(key) != after.get(key))


def _same_value(current: Any, requested: Any) -> bool:
    """İstenen değer zaten geçerli mi? (idempotent araçlar boşa yazmaz.)"""
    if isinstance(current, datetime) and isinstance(requested, datetime):
        left = current if current.tzinfo else current.replace(tzinfo=UTC)
        right = requested if requested.tzinfo else requested.replace(tzinfo=UTC)
        return left.astimezone(UTC) == right.astimezone(UTC)
    if isinstance(current, list) and isinstance(requested, list):
        return sorted(current) == sorted(requested)
    return current == requested


async def _entity_tags(session: AsyncSession, entity_id: uuid.UUID) -> list[str]:
    """Etiketler `entity_tag` üzerinden yaşar; canonical yardımcıdan okunur."""
    from app.core import tags as tag_svc

    return list((await tag_svc.tags_for(session, [entity_id])).get(entity_id, []))


# ---------------------------------------------------------------------------
# Todo
# ---------------------------------------------------------------------------


async def create_todo(
    session: AsyncSession,
    data: TodoCreateIn,
    *,
    request_id: str | None = None,
) -> ActionReceipt:
    """Tek görev oluşturur (canonical `todo.service.create`).

    `project_id`/`milestone_id`/`parent_id` ilişkileri canonical servis
    tarafından `belongs_to` yönünde yazılır; burada elle bağ kurulmaz (§22).
    `plan_day` verildiyse canonical servis aynı transaction'da plan slotunu da
    yazar -- bu onaylanan eylemin parçasıdır (§23).
    """
    todo_in = TodoIn(
        title=data.title,
        description=data.description,
        priority=data.priority,
        status="open",
        due_at=_parse_dt(data.due_at),
        reminder_at=_parse_dt(data.reminder_at),
        parent_id=_as_uuid(data.parent_id) if data.parent_id else None,
        project_id=_as_uuid(data.project_id) if data.project_id else None,
        milestone_id=_as_uuid(data.milestone_id) if data.milestone_id else None,
        tags=list(data.tags),
        recur=data.recur,
        plan_day=_parse_date(data.plan_day),
    )
    out = await todo_service.create(session, todo_in)

    after: dict[str, Any] = {
        "title": out.title,
        "status": out.status,
        "priority": out.priority,
        "due_at": out.due_at.isoformat() if out.due_at else None,
        "reminder_at": out.reminder_at.isoformat() if out.reminder_at else None,
        "project_id": str(out.project_id) if out.project_id else None,
        "project_title": out.project_title,
        "recur": out.recur,
        "tags": sorted(out.tags or []),
    }
    warnings: list[str] = []

    # Plan slotunun gerçekten yazıldığını DOĞRULA (§64: makbuz kanıttır).
    if data.plan_day:
        planned = _parse_date(data.plan_day)
        slot = (
            await session.execute(
                select(PlanSlot).where(
                    PlanSlot.entity_id == out.id, PlanSlot.day == planned
                )
            )
        ).scalar_one_or_none()
        if slot is None:
            warnings.append(
                "plan_day istendi ama plan slotu bulunamadı; planlama ayrıca doğrulanmalı."
            )
        else:
            after["planned_day"] = planned.isoformat() if planned else None
            after["planned_start_min"] = slot.start_min
            after["planned_duration_min"] = slot.duration_min

    summary = f'Created todo "{out.title}"'
    if after.get("planned_day"):
        summary += f' (planned {after["planned_day"]})'
    if out.project_title:
        summary += f" → project {out.project_title}"

    return ActionReceipt(
        request_id=request_id,
        tool="forkos_todo_create",
        status="executed",
        target_type="todo",
        target_id=str(out.id),
        summary=summary,
        changed_fields=sorted(after),
        before={},
        after=after,
        warnings=warnings,
    )


async def update_todo(
    session: AsyncSession,
    data: TodoUpdateIn,
    *,
    request_id: str | None = None,
) -> ActionReceipt:
    """Mevcut görevin metadata'sını günceller (canonical `todo.service.update`).

    Kapsam bilinçli olarak dar (§24): durum, silme, ebeveyn/ilişki yeniden
    düzenleme bu araçta YOKTUR. Tamamlama kendi aracına aittir.
    """
    todo_id = _as_uuid(data.todo_id)
    todo = await session.get(Todo, todo_id)
    entity = await _require_entity(session, todo_id, "görev")
    if todo is None:
        raise ActionError("TARGET_NOT_FOUND", f"görev bulunamadı: {todo_id}")

    _assert_fresh(entity, data.expected_updated_at)

    # Yalnızca ÇAĞIRANIN verdiği alanlar gönderilir. Aksi halde `exclude_unset`
    # semantiği None'ları "temizle" olarak yorumlar ve veri kaybı olur.
    provided = data.model_fields_set
    payload: dict[str, Any] = {}
    if "title" in provided:
        payload["title"] = data.title
    if "description" in provided:
        payload["description"] = data.description
    if "priority" in provided:
        payload["priority"] = data.priority
    if "due_at" in provided:
        payload["due_at"] = _parse_dt(data.due_at)
    if "reminder_at" in provided:
        payload["reminder_at"] = _parse_dt(data.reminder_at)
    if "tags" in provided:
        payload["tags"] = data.tags
    if "recur" in provided:
        payload["recur"] = data.recur

    tags_before = await _entity_tags(session, todo_id)
    before = _todo_state(todo, title=entity.title, tags=tags_before)

    current_map: dict[str, Any] = {
        "title": entity.title,
        "description": todo.description,
        "priority": todo.priority,
        "due_at": todo.due_at,
        "reminder_at": todo.reminder_at,
        "recur": todo.recur,
        "tags": tags_before,
    }
    # İdempotans: istenen değerler zaten geçerliyse canonical servis HİÇ
    # çağrılmaz -- gereksiz event/touch üretilmez (§122).
    if not payload or all(
        _same_value(current_map[key], value) for key, value in payload.items()
    ):
        return ActionReceipt(
            request_id=request_id,
            tool="forkos_todo_update",
            status="noop",
            target_type="todo",
            target_id=str(todo_id),
            summary=f'No change for todo "{entity.title}"',
            before=before,
            after=before,
        )

    out = await todo_service.update(session, todo_id, TodoUpdate(**payload))
    if out is None:
        raise ActionError("TARGET_NOT_FOUND", f"görev bulunamadı: {todo_id}")

    after = _todo_state(out, title=out.title, tags=list(out.tags or []))
    changed = _changed_fields(before, after)
    return ActionReceipt(
        request_id=request_id,
        tool="forkos_todo_update",
        status="executed" if changed else "noop",
        target_type="todo",
        target_id=str(todo_id),
        summary=(
            f'Updated todo "{out.title}": {", ".join(changed)}'
            if changed
            else f'No change for todo "{out.title}"'
        ),
        changed_fields=changed,
        before=before,
        after=after,
    )


async def complete_todo(
    session: AsyncSession,
    todo_id: str,
    *,
    request_id: str | None = None,
) -> ActionReceipt:
    """Görevi canonical kurallarla tamamlar (`todo.service.complete`).

    Tamamlama gerçek domain semantiği taşır: `completed_at`, entity touch,
    `todo.completed` olayı ve rutin görevlerde BİR SONRAKİ oluşum. Rutin
    davranışı taklit edilmez, canonical servis çalıştırılır (§26/§27).
    """
    tid = _as_uuid(todo_id)
    todo = await session.get(Todo, tid)
    await _require_entity(session, tid, "görev")
    if todo is None:
        raise ActionError("TARGET_NOT_FOUND", f"görev bulunamadı: {tid}")

    if todo.status == "done":
        # Makbuz KANITTIR: gerçek kalıcı zaman damgasını bildirir, None uydurmaz.
        completed_at = todo.completed_at.isoformat() if todo.completed_at else None
        return ActionReceipt(
            request_id=request_id,
            tool="forkos_todo_complete",
            status="noop",
            target_type="todo",
            target_id=str(tid),
            summary="Todo already completed",
            before={"status": "done", "completed_at": completed_at},
            after={"status": "done", "completed_at": completed_at},
        )

    was_recurring = bool(todo.recur)
    origin = todo.recur_origin_id or todo.id
    before = {"status": todo.status, "recur": todo.recur}

    out = await todo_service.complete(session, tid)
    if out is None:
        raise ActionError("TARGET_NOT_FOUND", f"görev bulunamadı: {tid}")

    after: dict[str, Any] = {
        "status": out.status,
        "completed_at": out.completed_at.isoformat() if out.completed_at else None,
    }
    warnings: list[str] = []

    if was_recurring:
        # Rutin görev tamamlanınca canonical servis yeni bir oluşum yaratmış
        # olabilir; makbuz bunu KANITLA bildirir (§27/§93).
        spawned = (
            await session.execute(
                select(Todo.id, Todo.due_at)
                .where(
                    Todo.recur_origin_id == origin,
                    Todo.status.in_(("open", "doing")),
                    Todo.id != tid,
                )
                .order_by(Todo.due_at.asc().nullslast())
                .limit(1)
            )
        ).first()
        if spawned is not None:
            after["next_occurrence_id"] = str(spawned.id)
            after["next_occurrence_due_at"] = (
                spawned.due_at.isoformat() if spawned.due_at else None
            )
            warnings.append(
                "Rutin görev: forkOS tekrar kurallarına göre bir sonraki oluşum oluşturuldu."
            )

    return ActionReceipt(
        request_id=request_id,
        tool="forkos_todo_complete",
        status="executed",
        target_type="todo",
        target_id=str(tid),
        summary=f'Completed: {out.title}',
        changed_fields=_changed_fields(before, after),
        before=before,
        after=after,
        warnings=warnings,
    )


async def plan_todo(
    session: AsyncSession,
    data: TodoPlanIn,
    *,
    request_id: str | None = None,
) -> ActionReceipt:
    """Görevi canonical PlanSlot servisleriyle planlar.

    Belirsizlik kuralı (§29): gelecekte TEK uygun slot varsa güncellenir,
    hiç yoksa oluşturulur, BİRDEN FAZLA varsa hangisinin kastedildiği
    belirsizdir ve eylem `AMBIGUOUS_PLAN` ile durur -- sessizce biri seçilmez.
    """
    tid = _as_uuid(data.todo_id)
    entity = await _require_entity(session, tid, "görev")
    todo = await session.get(Todo, tid)
    if todo is None:
        raise ActionError("TARGET_NOT_FOUND", f"görev bulunamadı: {tid}")

    target_day = _parse_date(data.day)
    if target_day is None:
        raise ActionError("INVALID_DATE", "day zorunludur (YYYY-MM-DD)")

    today = local_today()
    future_slots = list(
        (
            await session.execute(
                select(PlanSlot)
                .where(PlanSlot.entity_id == tid, PlanSlot.day >= today)
                .order_by(PlanSlot.day, PlanSlot.id)
            )
        ).scalars()
    )

    if len(future_slots) > 1:
        candidates = [slot.day.isoformat() for slot in future_slots][:10]
        raise ActionError(
            "AMBIGUOUS_PLAN",
            f"bu görev için birden fazla gelecek plan kaydı var: {candidates}. "
            "Hangi kaydın taşınacağı belirsiz; önce tek kayda indir.",
        )

    provided = data.model_fields_set
    warnings: list[str] = []

    if not future_slots:
        out = await todo_service.schedule(
            session,
            PlanSlotIn(
                entity_id=tid,
                day=target_day,
                start_min=data.start_min,
                duration_min=data.duration_min,
            ),
        )
        created = True
    else:
        slot = future_slots[0]
        # Verilmeyen alan MEVCUT değeri korur; sonuç aynıysa canonical servis
        # HİÇ çağrılmaz: olay/timestamp gürültüsü üretilmez (§26).
        next_start = data.start_min if "start_min" in provided else slot.start_min
        next_duration = data.duration_min if "duration_min" in provided else slot.duration_min
        current_slot = {
            "slot_id": str(slot.id),
            "day": slot.day.isoformat(),
            "start_min": slot.start_min,
            "duration_min": slot.duration_min,
        }
        if (
            slot.day == target_day
            and slot.start_min == next_start
            and slot.duration_min == next_duration
        ):
            return ActionReceipt(
                request_id=request_id,
                tool="forkos_todo_plan",
                status="noop",
                target_type="todo",
                target_id=str(tid),
                summary=f'Plan already {current_slot["day"]} {current_slot["start_min"]}',
                before=current_slot,
                after=current_slot,
            )
        payload: dict[str, Any] = {"day": target_day}
        if "start_min" in provided:
            payload["start_min"] = data.start_min
        if "duration_min" in provided:
            payload["duration_min"] = data.duration_min
        out = await todo_service.update_slot(session, slot.id, PlanSlotUpdate(**payload))
        if out is None:
            raise ActionError("TARGET_NOT_FOUND", "plan kaydı bulunamadı")
        created = False

    after = {
        "slot_id": str(out.id),
        "day": out.day.isoformat(),
        "start_min": out.start_min,
        "duration_min": out.duration_min,
    }
    # Görev içeriği bu eylemde DEĞİŞMEZ (§77); makbuz bunu açıkça söyler.
    summary = f'Planned todo "{entity.title}" → {after["day"]}'
    if created:
        warnings.append("Gelecek plan kaydı yoktu; yeni bir plan slotu oluşturuldu.")

    return ActionReceipt(
        request_id=request_id,
        tool="forkos_todo_plan",
        status="executed",
        target_type="todo",
        target_id=str(tid),
        summary=summary,
        changed_fields=["plan_slot"],
        before={},
        after=after,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------


async def update_project(
    session: AsyncSession,
    data: ProjectUpdateIn,
    *,
    request_id: str | None = None,
) -> ActionReceipt:
    """Projenin operasyonel alanını günceller (canonical `project.service.patch`).

    Kapsam KASITLI olarak yalnızca `next_action`'dır (§32): başlık yeniden
    adlandırma, repo/url/stack/konum ve silme H1'de yoktur. Operasyonel state
    operasyonel kalır -- bu eylem Vault'taki proje Markdown'ına DOKUNMAZ (§78).
    """
    pid = _as_uuid(data.project_id)
    project = await session.get(Project, pid)
    entity = await _require_entity(session, pid, "proje")
    if project is None:
        raise ActionError("TARGET_NOT_FOUND", f"proje bulunamadı: {pid}")

    _assert_fresh(entity, data.expected_updated_at)
    before = {"title": entity.title, "next_action": project.next_action}

    # İdempotans: aynı değer yeniden istenirse canonical servis çağrılmaz,
    # böylece tekrar denemeler olay/touch gürültüsü üretmez (§122).
    if (
        "next_action" not in data.model_fields_set
        or data.next_action == project.next_action
    ):
        return ActionReceipt(
            request_id=request_id,
            tool="forkos_project_update",
            status="noop",
            target_type="project",
            target_id=str(pid),
            summary=f'No change for project "{entity.title}"',
            before=before,
            after=before,
        )

    out = await project_service.patch(session, pid, ProjectPatch(next_action=data.next_action))
    if out is None:
        raise ActionError("TARGET_NOT_FOUND", f"proje bulunamadı: {pid}")

    after = {"title": out["title"], "next_action": out["next_action"]}
    changed = _changed_fields(before, after)
    return ActionReceipt(
        request_id=request_id,
        tool="forkos_project_update",
        status="executed" if changed else "noop",
        target_type="project",
        target_id=str(pid),
        summary=(
            f'Updated project "{out["title"]}" next action'
            if changed
            else f'No change for project "{out["title"]}"'
        ),
        changed_fields=changed,
        before=before,
        after=after,
    )


# ---------------------------------------------------------------------------
# Opportunity / Application
# ---------------------------------------------------------------------------


async def transition_opportunity(
    session: AsyncSession,
    data: OpportunityTransitionIn,
    *,
    request_id: str | None = None,
) -> ActionReceipt:
    """Keşif/duyuru yaşam döngüsü geçişi (canonical lifecycle doğrulaması ile).

    Başvuru hattından AYRIDIR (§36): burada fırsatın keşif durumu değişir.
    Geçiş matrisi canonical `opportunity.lifecycle` içinde yaşar; burada
    kopyalanmaz.
    """
    oid = _as_uuid(data.opportunity_id)
    item = await session.get(Opportunity, oid)
    await _require_entity(session, oid, "fırsat")
    if item is None:
        raise ActionError("TARGET_NOT_FOUND", f"fırsat bulunamadı: {oid}")

    if item.status != data.expected_status:
        raise ActionError(
            "STALE_ACTION",
            f"beklenen durum '{data.expected_status}' ama güncel durum '{item.status}'",
        )

    before = {"status": item.status, "kind": item.kind}
    try:
        out = await opportunity_application.transition_status(
            session, oid, to=data.to_status, note=data.note
        )
    except ValueError as exc:
        raise ActionError("INVALID_TRANSITION", str(exc)) from exc
    if out is None:
        raise ActionError("TARGET_NOT_FOUND", f"fırsat bulunamadı: {oid}")

    after = {"status": out.status}
    return ActionReceipt(
        request_id=request_id,
        tool="forkos_opportunity_transition",
        status="executed",
        target_type="opportunity",
        target_id=str(oid),
        summary=f'Opportunity "{out.title}": {before["status"]} → {out.status}',
        changed_fields=["status"],
        before=before,
        after=after,
    )


async def transition_application(
    session: AsyncSession,
    data: ApplicationTransitionIn,
    *,
    request_id: str | None = None,
) -> ActionReceipt:
    """Başvuru CRM hattı geçişi (canonical `transition_application`/`apply`).

    Uygulama kaydı yoksa YALNIZCA `applied` hedefi için canonical `apply`
    çağrılır (§37); başka hedefler `APPLICATION_NOT_FOUND` ile durur. Alanlar
    elle atanmaz, geçiş canonical doğrulamadan geçer.
    """
    oid = _as_uuid(data.opportunity_id)
    item = await session.get(Opportunity, oid)
    entity = await _require_entity(session, oid, "fırsat")
    if item is None:
        raise ActionError("TARGET_NOT_FOUND", f"fırsat bulunamadı: {oid}")

    app = await session.get(Application, oid)

    if app is None:
        if data.to_status != "applied":
            raise ActionError(
                "APPLICATION_NOT_FOUND",
                f"başvuru kaydı yok; '{data.to_status}' hedefine geçilemez "
                "(yalnızca 'applied' kaydı oluşturabilir)",
            )
        before: dict[str, Any] = {"status": None}
        try:
            out = await opportunity_application.apply(
                session, oid, ApplyIn(note=data.note)
            )
        except ValueError as exc:
            raise ActionError("INVALID_TRANSITION", str(exc)) from exc
        if out is None:
            raise ActionError("TARGET_NOT_FOUND", f"fırsat bulunamadı: {oid}")
        created = await session.get(Application, oid)
        status = created.status if created is not None else "applied"
        return ActionReceipt(
            request_id=request_id,
            tool="forkos_application_transition",
            status="executed",
            target_type="application",
            target_id=str(oid),
            summary=f'Application "{out.title}" created: applied',
            changed_fields=["status"],
            before=before,
            after={"status": status},
        )

    if data.expected_status is None:
        # Mevcut bir başvuruda tazelik önkoşulu İSTEĞE BAĞLI OLAMAZ: aksi halde
        # onay ile yürütme arasındaki değişim sessizce ezilir (§18).
        raise ActionError(
            "EXPECTED_STATUS_REQUIRED",
            f"mevcut başvuru durumu '{app.status}'; geçiş için expected_status zorunludur",
        )
    if app.status != data.expected_status:
        raise ActionError(
            "STALE_ACTION",
            f"beklenen başvuru durumu '{data.expected_status}' ama güncel durum '{app.status}'",
        )

    if app.status == data.to_status:
        # Hedef zaten geçerli: canonical servis çağrılmaz, ek geçmiş/olay yazılmaz.
        return ActionReceipt(
            request_id=request_id,
            tool="forkos_application_transition",
            status="noop",
            target_type="application",
            target_id=str(oid),
            summary=f"Application already {app.status}",
            before={"status": app.status},
            after={"status": app.status},
        )

    before = {"status": app.status}
    try:
        updated = await opportunity_application.transition_application(
            session,
            oid,
            to=data.to_status,
            note=data.note,
            rejection_reason=data.rejection_reason,
        )
    except ValueError as exc:
        raise ActionError("INVALID_TRANSITION", str(exc)) from exc
    if updated is None:
        raise ActionError("APPLICATION_NOT_FOUND", f"başvuru kaydı yok: {oid}")

    after = {"status": updated.status}
    if updated.status == before["status"]:
        return ActionReceipt(
            request_id=request_id,
            tool="forkos_application_transition",
            status="noop",
            target_type="application",
            target_id=str(oid),
            summary=f"Application already {updated.status}",
            before=before,
            after=after,
        )

    return ActionReceipt(
        request_id=request_id,
        tool="forkos_application_transition",
        status="executed",
        target_type="application",
        target_id=str(oid),
        summary=f'Application "{entity.title}": {before["status"]} → {updated.status}',
        changed_fields=["status"],
        before=before,
        after=after,
    )


# ---------------------------------------------------------------------------
# Bookmark
# ---------------------------------------------------------------------------


async def capture_bookmark(
    session: AsyncSession,
    data: BookmarkCaptureIn,
    *,
    request_id: str | None = None,
) -> ActionReceipt:
    """Yer imini YEREL olarak kaydeder (canonical `bookmark.service.capture`).

    Sayfa getirilmez, metadata kazınmaz, zenginleştirme yapılmaz (§40).
    Aynı URL zaten kayıtlıysa YENİ KAYIT AÇILMAZ; makbuz mevcut kaydı
    işaret eder (§41).
    """
    existing = await bookmark_service.find_by_url(session, data.url)
    if existing is not None:
        entity = await session.get(Entity, existing.id)
        return ActionReceipt(
            request_id=request_id,
            tool="forkos_bookmark_capture",
            status="noop",
            target_type="bookmark",
            target_id=str(existing.id),
            summary=f'Duplicate URL already saved: "{entity.title if entity else data.url}"',
            before={},
            after={
                "url": existing.url,
                "title": entity.title if entity else None,
                "collection": existing.collection,
                "read_status": existing.read_status,
            },
            warnings=[
                "Duplicate URL: bu adres zaten kayıtlı; yeni kayıt oluşturulmadı."
            ],
        )

    bookmark, replayed, prior = await bookmark_service.capture(
        session,
        CaptureIn(
            url=data.url,
            title=data.title or "",
            collection=data.collection,
            source=_AGENT_BOOKMARK_SOURCE,
            tags=list(data.tags),
            note=data.note,
        ),
    )
    entity = await session.get(Entity, bookmark.id)
    warnings: list[str] = []
    if replayed or prior is not None:
        warnings.append("Duplicate URL: mevcut kayıt yeniden kullanıldı.")

    return ActionReceipt(
        request_id=request_id,
        tool="forkos_bookmark_capture",
        status="executed" if not (replayed or prior is not None) else "noop",
        target_type="bookmark",
        target_id=str(bookmark.id),
        summary=f'Saved bookmark "{entity.title if entity else data.url}"',
        changed_fields=["url", "title", "collection"],
        before={},
        after={
            "url": bookmark.url,
            "title": entity.title if entity else None,
            "collection": bookmark.collection,
            "read_status": bookmark.read_status,
        },
        warnings=warnings,
    )


async def update_bookmark(
    session: AsyncSession,
    data: BookmarkUpdateIn,
    *,
    request_id: str | None = None,
) -> ActionReceipt:
    """Yer iminin düşük riskli alanlarını günceller (§43).

    İzin verilenler: koleksiyon, favori, okuma durumu ve (canonical destekliyorsa)
    etiketler. Silme, toplu işlem, ilerleme simülasyonu, vurgu silme ve
    zenginleştirme H1'de YOKTUR.
    """
    bid = _as_uuid(data.bookmark_id)
    bookmark = await session.get(Bookmark, bid)
    entity = await _require_entity(session, bid, "yer imi")
    if bookmark is None:
        raise ActionError("TARGET_NOT_FOUND", f"yer imi bulunamadı: {bid}")

    _assert_fresh(entity, data.expected_updated_at)
    before = {
        "collection": bookmark.collection,
        "read_status": bookmark.read_status,
        "favorite": bookmark.favorite,
    }

    provided = data.model_fields_set
    payload: dict[str, Any] = {}
    if "collection" in provided:
        payload["collection"] = data.collection
    if "favorite" in provided:
        payload["favorite"] = data.favorite
    if "read_status" in provided:
        payload["read_status"] = data.read_status
    if "tags" in provided:
        payload["tags"] = data.tags

    tags_before = await _entity_tags(session, bid)
    before["tags"] = sorted(tags_before)
    current_map: dict[str, Any] = {
        "collection": bookmark.collection,
        "read_status": bookmark.read_status,
        "favorite": bookmark.favorite,
        "tags": tags_before,
    }
    # Bilinmeyen alan sessizce "değişmedi" sayılmaz: fail-closed.
    unknown = set(payload) - set(current_map)
    if unknown:
        raise ActionError("ACTION_NOT_ALLOWED", f"desteklenmeyen alanlar: {sorted(unknown)}")
    if not payload or all(
        _same_value(current_map[key], value) for key, value in payload.items()
    ):
        return ActionReceipt(
            request_id=request_id,
            tool="forkos_bookmark_update",
            status="noop",
            target_type="bookmark",
            target_id=str(bid),
            summary=f'No change for bookmark "{entity.title}"',
            before=before,
            after=before,
        )

    out = await bookmark_service.update(session, bid, BookmarkUpdate(**payload))
    if out is None:
        raise ActionError("TARGET_NOT_FOUND", f"yer imi bulunamadı: {bid}")

    after = {
        "collection": out.collection,
        "read_status": out.read_status,
        "favorite": out.favorite,
        "tags": sorted(await _entity_tags(session, bid)),
    }
    changed = _changed_fields(before, after)
    return ActionReceipt(
        request_id=request_id,
        tool="forkos_bookmark_update",
        status="executed" if changed else "noop",
        target_type="bookmark",
        target_id=str(bid),
        summary=(
            f'Updated bookmark "{entity.title}": {", ".join(changed)}'
            if changed
            else f'No change for bookmark "{entity.title}"'
        ),
        changed_fields=changed,
        before=before,
        after=after,
    )


# ---------------------------------------------------------------------------
# Durable knowledge (Obsidian Vault)
# ---------------------------------------------------------------------------


def _append_under_heading(body: str, heading: str, text: str) -> str:
    """Metni TAM eşleşen tek başlığın altına ekler.

    §53: 0 eşleşme veya >1 eşleşme varsa TAHMİN EDİLMEZ; hata verilir.
    Kullanıcı Markdown'ı yeniden biçimlendirilmez (§52).
    """
    pattern = re.compile(r"^#{1,6}\s+" + re.escape(heading) + r"\s*$", re.MULTILINE)
    matches = list(pattern.finditer(body))
    if not matches:
        raise ActionError("HEADING_NOT_FOUND", f"başlık bulunamadı: '{heading}'")
    if len(matches) > 1:
        raise ActionError(
            "AMBIGUOUS_HEADING", f"başlık birden fazla kez geçiyor: '{heading}'"
        )
    head_end = matches[0].end()
    return f"{body[:head_end]}\n\n{text.strip()}\n{body[head_end:]}"


async def capture_brain_note(
    session: AsyncSession,
    data: BrainCaptureIn,
    *,
    request_id: str | None = None,
) -> ActionReceipt:
    """`00 Inbox/` altında yeni bir Vault bilgi notu oluşturur.

    Kimliği canonical Obsidian servisi üretir. forkOS veritabanında
    `entity`/`note`/`link` satırı OLUŞMAZ; bilgi tek sahipli olarak Vault'ta
    yaşar (§46).
    """
    try:
        item = await obsidian_service.capture_knowledge_note(
            session,
            body=data.body,
            title=data.title,
            relate_to=_as_uuid(data.relate_to) if data.relate_to else None,
            tags=list(data.tags) if data.tags else None,
        )
    except obsidian_service.VaultConflictError as exc:
        raise ActionError("VAULT_CONFLICT", str(exc)) from exc
    except (PermissionError, RuntimeError) as exc:
        # Vault yapılandırılmamış/erişilemez: legacy Notlar'a DÜŞÜLMEZ (§54/§68).
        raise ActionError("VAULT_UNAVAILABLE", str(exc)) from exc
    except obsidian_service.VaultWriteError as exc:
        raise ActionError("VAULT_WRITE_FAILED", str(exc)) from exc
    except ValueError as exc:
        raise ActionError("INVALID_TARGET", str(exc)) from exc

    return ActionReceipt(
        request_id=request_id,
        tool="brain_capture",
        status="executed",
        target_type="vault_note",
        target_id=item.forkos_id,
        summary=f'Captured knowledge note "{item.title}"',
        changed_fields=["vault_note"],
        before={},
        # §129: gövde makbuza KOPYALANMAZ; yalnızca sınırlı künye döner.
        after={
            "forkos_id": item.forkos_id,
            "relative_path": item.relative_path,
            "title": item.title,
            "note_kind": item.note_kind,
            "relation_count": item.relation_count,
        },
    )


async def save_to_entity_brain(
    session: AsyncSession,
    data: BrainSaveToEntityIn,
    *,
    request_id: str | None = None,
) -> ActionReceipt:
    """Yönetilen bilgi notuna METİN EKLER (tam gövde değiştirmez).

    Hedef yalnızca kararlı yönetilen kimliktir (`forkos_id`); `relative_path`
    şemada YOKTUR, böylece kullanıcının kendi Obsidian notları yazılamaz
    (§49/§55). Not yoksa canonical `ensure` ile oluşturulur (§50).
    """
    fid = _as_uuid(data.forkos_id)

    # §13: yaratıcı birincil çağrıdan ÖNCE doğrula. Aksi halde "not yok +
    # geçersiz başlık" isteği yetim bir yönetilen dosya bırakırdı.
    try:
        existing = obsidian_service.resolve_managed_item(fid)
    except obsidian_service.VaultConflictError as exc:
        raise ActionError("VAULT_CONFLICT", str(exc)) from exc
    except (PermissionError, RuntimeError) as exc:
        raise ActionError("VAULT_UNAVAILABLE", str(exc)) from exc
    if existing is None and data.heading:
        raise ActionError(
            "HEADING_NOT_FOUND",
            f"yönetilen bilgi notu yok; '{data.heading}' başlığı aranamaz",
        )

    try:
        item = await obsidian_service.ensure_entity_knowledge_note(session, fid)
    except obsidian_service.VaultConflictError as exc:
        raise ActionError("VAULT_CONFLICT", str(exc)) from exc
    except (PermissionError, RuntimeError) as exc:
        raise ActionError("VAULT_UNAVAILABLE", str(exc)) from exc
    except obsidian_service.VaultWriteError as exc:
        raise ActionError("VAULT_WRITE_FAILED", str(exc)) from exc
    except ValueError as exc:
        raise ActionError("INVALID_TARGET", str(exc)) from exc

    read = obsidian_service.read_managed_note_body(fid)
    if read is None:
        raise ActionError(
            "KNOWLEDGE_NOT_FOUND", f"yönetilen bilgi notu okunamadı: {fid}"
        )
    current_item, body = read

    if data.heading:
        new_body = _append_under_heading(body, data.heading, data.text)
    else:
        new_body = f"{body.rstrip()}\n\n{data.text.strip()}\n"

    try:
        updated = obsidian_service.update_managed_note_body(
            fid, new_body, expected_mtime=current_item.mtime
        )
    except obsidian_service.VaultStaleWriteError as exc:
        raise ActionError("VAULT_STALE", str(exc)) from exc
    except obsidian_service.VaultConflictError as exc:
        raise ActionError("VAULT_CONFLICT", str(exc)) from exc
    except (PermissionError, RuntimeError) as exc:
        raise ActionError("VAULT_UNAVAILABLE", str(exc)) from exc
    except ValueError as exc:
        raise ActionError("KNOWLEDGE_NOT_FOUND", str(exc)) from exc

    return ActionReceipt(
        request_id=request_id,
        tool="brain_save_to_entity",
        status="executed",
        target_type="vault_note",
        target_id=item.forkos_id,
        summary=(
            f'Appended to knowledge note "{updated.title}"'
            + (f" under heading '{data.heading}'" if data.heading else "")
        ),
        changed_fields=["body"],
        before={"title": item.title, "relative_path": item.relative_path},
        after={
            "forkos_id": updated.forkos_id,
            "relative_path": updated.relative_path,
            "title": updated.title,
            "appended_chars": len(data.text.strip()),
            "heading": data.heading,
        },
    )
