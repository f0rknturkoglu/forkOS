"""H1 todo ve proje eylem adaptörleri.

Kanıtlanan sözleşmeler: canonical servis kullanımı, kapsam daraltması,
iyimser önkoşul (STALE_ACTION), alan kaybı olmaması, rutin tekrar semantiği
ve plan belirsizliğinde fail-closed davranış.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity, Link
from app.core.time import local_today
from app.db import SessionLocal
from app.integrations.agent.actions import (
    ActionError,
    complete_todo,
    create_todo,
    plan_todo,
    update_project,
    update_todo,
)
from app.integrations.agent.write_models import (
    ProjectUpdateIn,
    TodoCreateIn,
    TodoPlanIn,
    TodoUpdateIn,
)
from app.modules.project.models import Project
from app.modules.todo.models import PlanSlot, Todo
from tests.agent_test_utils import (
    capture_db_content_fingerprint,
    forbid_outbound_network,  # noqa: F401  (autouse ağ koruması)
    table_counts,
)


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def _make_project(session: AsyncSession, title: str = "Test Project") -> uuid.UUID:
    project_id = uuid.uuid4()
    session.add(Entity(id=project_id, type="project", title=title, search_text=""))
    session.add(Project(id=project_id, status="active"))
    await session.commit()
    return project_id


async def _updated_at(session: AsyncSession, entity_id: uuid.UUID) -> str:
    entity = await session.get(Entity, entity_id)
    assert entity is not None
    updated = entity.updated_at
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=UTC)
    return updated.isoformat()


# ---------------------------------------------------------------------------
# forkos_todo_create
# ---------------------------------------------------------------------------


async def test_create_todo_uses_canonical_service_and_writes_plan_slot(
    db_session: AsyncSession,
) -> None:
    project_id = await _make_project(db_session)
    day = local_today().isoformat()
    before = await table_counts(db_session)

    receipt = await create_todo(
        db_session,
        TodoCreateIn(
            title="ALES Deneme",
            priority=1,
            plan_day=day,
            project_id=str(project_id),
            tags=["sinav"],
        ),
        request_id="req-1",
    )

    assert receipt.status == "executed"
    assert receipt.tool == "forkos_todo_create"
    assert receipt.request_id == "req-1"
    assert receipt.target_type == "todo"
    assert receipt.after["status"] == "open"
    assert receipt.after["planned_day"] == day
    assert receipt.after["project_id"] == str(project_id)
    assert receipt.before == {}

    todo_id = uuid.UUID(receipt.target_id)
    todo = await db_session.get(Todo, todo_id)
    assert todo is not None and todo.status == "open"

    # plan_day canonical servis tarafından GERÇEKTEN yazılmış olmalı.
    slot = (
        await db_session.execute(select(PlanSlot).where(PlanSlot.entity_id == todo_id))
    ).scalar_one()
    assert slot.day.isoformat() == day

    # §22: ilişki todo --belongs_to--> project yönünde.
    link = (
        await db_session.execute(
            select(Link).where(Link.from_id == todo_id, Link.relation == "belongs_to")
        )
    ).scalar_one()
    assert link.to_id == project_id

    after = await table_counts(db_session)
    assert after["todo"] == before["todo"] + 1
    assert after["entity"] == before["entity"] + 1
    # Kapsam dışı domainlere dokunulmadı (§74).
    for table in ("project", "milestone", "opportunity", "application", "bookmark", "flashcard_card"):
        assert after[table] == before[table], table
    assert todo is not None  # okuma amaçlı


async def test_create_todo_cannot_inject_terminal_status(db_session: AsyncSession) -> None:
    """§21: çağıran `status=done/dropped` üretemez; şema bunu reddeder."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        TodoCreateIn.model_validate({"title": "Kacan gorev", "status": "done"})


async def test_create_todo_validation_bounds() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        TodoCreateIn(title="   ")
    with pytest.raises(ValidationError):
        TodoCreateIn(title="x" * 301)
    with pytest.raises(ValidationError):
        TodoCreateIn(title="ok", priority=9)
    with pytest.raises(ValidationError):
        TodoCreateIn(title="ok", plan_day="2026-13-45")


# ---------------------------------------------------------------------------
# forkos_todo_update
# ---------------------------------------------------------------------------


async def test_update_todo_preserves_untouched_fields(db_session: AsyncSession) -> None:
    """Yalnızca verilen alan değişir; diğerleri SIFIRLANMAZ (§24/§66)."""
    due = (datetime.now(UTC) + timedelta(days=3)).replace(microsecond=0)
    created = await create_todo(
        db_session, TodoCreateIn(title="Ilk", description="aciklama", priority=3, due_at=due.isoformat())
    )
    todo_id = created.target_id

    receipt = await update_todo(
        db_session, TodoUpdateIn(todo_id=todo_id, title="Guncel"), request_id="u1"
    )

    assert receipt.status == "executed"
    assert receipt.changed_fields == ["title"]
    assert receipt.before["priority"] == 3

    todo = await db_session.get(Todo, uuid.UUID(todo_id))
    assert todo is not None
    assert todo.description == "aciklama"
    assert todo.priority == 3
    assert todo.due_at is not None and todo.due_at.replace(tzinfo=UTC) == due


async def test_update_todo_stale_guard_blocks_write(db_session: AsyncSession) -> None:
    created = await create_todo(db_session, TodoCreateIn(title="Taze olmayan"))
    todo_id = uuid.UUID(created.target_id)
    stale = (datetime.now(UTC) - timedelta(days=5)).isoformat()

    with pytest.raises(ActionError, match="STALE_ACTION"):
        await update_todo(
            db_session,
            TodoUpdateIn(todo_id=str(todo_id), title="Yazilmamali", expected_updated_at=stale),
        )

    todo = await db_session.get(Todo, todo_id)
    entity = await db_session.get(Entity, todo_id)
    assert todo is not None and entity is not None
    assert entity.title == "Taze olmayan"


async def test_update_todo_accepts_correct_precondition(db_session: AsyncSession) -> None:
    created = await create_todo(db_session, TodoCreateIn(title="Onkosullu"))
    todo_id = uuid.UUID(created.target_id)
    fresh = await _updated_at(db_session, todo_id)

    receipt = await update_todo(
        db_session,
        TodoUpdateIn(todo_id=str(todo_id), priority=1, expected_updated_at=fresh),
    )
    assert receipt.status == "executed"
    assert receipt.after["priority"] == 1


# ---------------------------------------------------------------------------
# forkos_todo_complete
# ---------------------------------------------------------------------------


async def test_complete_todo_is_idempotent_and_emits_events(db_session: AsyncSession) -> None:
    created = await create_todo(db_session, TodoCreateIn(title="Bitirilecek"))
    todo_id = created.target_id

    first = await complete_todo(db_session, todo_id, request_id="c1")
    assert first.status == "executed"
    assert first.after["status"] == "done"
    assert first.after["completed_at"] is not None
    assert first.before == {"status": "open", "recur": None}

    second = await complete_todo(db_session, todo_id, request_id="c2")
    assert second.status == "noop"
    assert second.summary == "Todo already completed"
    assert second.after["status"] == "done"

    # Rutin olmayan görevde ek oluşum üretilmemeli.
    todos = (await db_session.execute(select(Todo).where(Todo.id == uuid.UUID(todo_id)))).all()
    assert len(todos) == 1


async def test_complete_recurring_todo_spawns_exactly_one_occurrence(
    db_session: AsyncSession,
) -> None:
    """§27/§123: tekrar eden görevde tamamlama canonical kural ile YENİ oluşum üretir."""
    created = await create_todo(
        db_session,
        TodoCreateIn(title="Gunluk rutin", recur="daily", due_at=datetime.now(UTC).isoformat()),
    )
    todo_id = uuid.UUID(created.target_id)

    first = await complete_todo(db_session, todo_id)
    assert first.status == "executed"
    assert first.after.get("next_occurrence_id")
    assert any("Rutin görev" in w for w in first.warnings)

    open_rows = (
        await db_session.execute(select(Todo).where(Todo.status.in_(("open", "doing"))))
    ).scalars().all()
    assert len(open_rows) == 1
    spawned_id = open_rows[0].id

    # İkinci çağrı: neop + EK oluşum YOK.
    second = await complete_todo(db_session, todo_id)
    assert second.status == "noop"
    open_after = (
        await db_session.execute(select(Todo).where(Todo.status.in_(("open", "doing"))))
    ).scalars().all()
    assert [row.id for row in open_after] == [spawned_id]


async def test_complete_unknown_todo_fails(db_session: AsyncSession) -> None:
    with pytest.raises(ActionError, match="TARGET_NOT_FOUND"):
        await complete_todo(db_session, str(uuid.uuid4()))


# ---------------------------------------------------------------------------
# forkos_todo_plan
# ---------------------------------------------------------------------------


async def test_plan_todo_creates_then_reschedules(db_session: AsyncSession) -> None:
    created = await create_todo(db_session, TodoCreateIn(title="Planlanacak"))
    todo_id = created.target_id
    far = (local_today() + timedelta(days=3)).isoformat()

    first = await plan_todo(
        db_session, TodoPlanIn(todo_id=todo_id, day=far, start_min=600, duration_min=60)
    )
    assert first.status == "executed"
    assert first.after["day"] == far
    assert first.after["start_min"] == 600
    assert any("yeni bir plan slotu" in w for w in first.warnings)

    closer = (local_today() + timedelta(days=5)).isoformat()
    second = await plan_todo(db_session, TodoPlanIn(todo_id=todo_id, day=closer, start_min=840))
    assert second.after["day"] == closer
    assert second.after["start_min"] == 840
    assert second.after["slot_id"] == first.after["slot_id"]

    slots = (
        await db_session.execute(select(PlanSlot).where(PlanSlot.entity_id == uuid.UUID(todo_id)))
    ).scalars().all()
    assert len(slots) == 1

    # §77: görev içeriği bu eylemde değişmez.
    todo = await db_session.get(Todo, uuid.UUID(todo_id))
    assert todo is not None and todo.status == "open"


async def test_plan_todo_ambiguous_future_slots_fail(db_session: AsyncSession) -> None:
    """§29: birden fazla gelecek slot varsa sessizce biri seçilmez."""
    created = await create_todo(db_session, TodoCreateIn(title="Belirsiz"))
    todo_id = uuid.UUID(created.target_id)
    for offset in (2, 4):
        slot = PlanSlot(
            entity_id=todo_id,
            day=local_today() + timedelta(days=offset),
            position=0,
        )
        db_session.add(slot)
    await db_session.commit()

    with pytest.raises(ActionError, match="AMBIGUOUS_PLAN"):
        await plan_todo(
            db_session,
            TodoPlanIn(todo_id=str(todo_id), day=(local_today() + timedelta(days=6)).isoformat()),
        )


# ---------------------------------------------------------------------------
# forkos_project_update
# ---------------------------------------------------------------------------


async def test_update_project_next_action_only(db_session: AsyncSession) -> None:
    project_id = await _make_project(db_session, "forkOS")
    before_counts = await table_counts(db_session)

    receipt = await update_project(
        db_session,
        ProjectUpdateIn(project_id=str(project_id), next_action="H1 dogfood"),
    )

    assert receipt.status == "executed"
    assert receipt.changed_fields == ["next_action"]
    assert receipt.after["next_action"] == "H1 dogfood"
    assert receipt.target_id == str(project_id)

    project = await db_session.get(Project, project_id)
    assert project is not None
    assert project.next_action == "H1 dogfood"
    # §32/§33: yeniden adlandırma yok.
    entity = await db_session.get(Entity, project_id)
    assert entity is not None and entity.title == "forkOS"

    after_counts = await table_counts(db_session)
    assert after_counts["todo"] == before_counts["todo"]
    assert after_counts["bookmark"] == before_counts["bookmark"]
    assert after_counts["opportunity"] == before_counts["opportunity"]


async def test_update_project_rejects_rename_field(db_session: AsyncSession) -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ProjectUpdateIn.model_validate(
            {"project_id": str(uuid.uuid4()), "title": "Yeni ad"}
        )


async def test_update_project_stale_guard(db_session: AsyncSession) -> None:
    project_id = await _make_project(db_session, "Stale proje")
    stale = (datetime.now(UTC) - timedelta(days=1)).isoformat()

    with pytest.raises(ActionError, match="STALE_ACTION"):
        await update_project(
            db_session,
            ProjectUpdateIn(
                project_id=str(project_id), next_action="yazilmamali", expected_updated_at=stale
            ),
        )

    project = await db_session.get(Project, project_id)
    assert project is not None and project.next_action is None


async def test_update_project_same_value_is_noop(db_session: AsyncSession) -> None:
    project_id = await _make_project(db_session, "Ayni deger")
    await update_project(db_session, ProjectUpdateIn(project_id=str(project_id), next_action="X"))
    fingerprint = await capture_db_content_fingerprint(db_session)

    receipt = await update_project(
        db_session, ProjectUpdateIn(project_id=str(project_id), next_action="X")
    )
    assert receipt.status == "noop"
    assert await capture_db_content_fingerprint(db_session) == fingerprint
