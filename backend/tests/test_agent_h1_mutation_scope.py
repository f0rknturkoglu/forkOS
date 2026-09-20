"""H1 mutasyon kapsamı kanıtları (§73-§83).

Her yazma aracı yalnızca BEKLENEN domain'i değiştirmelidir. Kanıt, tablo
bazında ayrı deterministik özetlerle yapılır: ilgisiz tablolar bayt baytına
aynı kalmalıdır.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.models import Entity
from app.core.time import local_today
from app.db import SessionLocal
from app.integrations.agent.actions import (
    capture_bookmark,
    capture_brain_note,
    complete_todo,
    create_todo,
    plan_todo,
    save_to_entity_brain,
    transition_application,
    transition_opportunity,
    update_bookmark,
    update_project,
    update_todo,
)
from app.integrations.agent.write_models import (
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
from app.integrations.obsidian.service import vault_index
from app.modules.opportunity.models import Opportunity
from app.modules.project.models import Project
from app.modules.todo.models import Todo
from tests.agent_test_utils import (
    capture_db_content_fingerprint,
    changed_tables,
    forbid_h1_network,  # noqa: F401  (autouse ağ koruması)
    legacy_notes_counts,
    table_fingerprints,
)

#: Araç -> dokunmasına İZİN VERİLEN tablolar. Liste canonical servislerin
#: bugünkü davranışının üst kümesidir; burada amaç "yalnızca bu domain"
#: sınırını kanıtlamaktır, servis içi ayrıntıyı dondurmak değil.
ALLOWED_TABLES: dict[str, set[str]] = {
    "forkos_todo_create": {"entity", "todo", "plan_slot", "link", "entity_tag", "event"},
    "forkos_todo_update": {"entity", "todo", "entity_tag", "event"},
    "forkos_todo_complete": {"entity", "todo", "link", "event"},
    "forkos_todo_plan": {"plan_slot", "event"},
    "forkos_project_update": {"entity", "project", "event"},
    "forkos_opportunity_transition": {
        "entity",
        "opportunity",
        "application",
        "application_history",
        "event",
    },
    "forkos_application_transition": {
        "entity",
        "opportunity",
        "application",
        "application_history",
        "event",
    },
    "forkos_bookmark_capture": {"entity", "bookmark", "entity_tag", "event"},
    "forkos_bookmark_update": {"entity", "bookmark", "entity_tag", "event"},
    # Bilgi yazmaları forkOS veritabanına HİÇ dokunmaz (§82/§83).
    "brain_capture": set(),
    "brain_save_to_entity": set(),
}


@pytest.fixture(autouse=True)
def reset_vault_index():
    def clear() -> None:
        vault_index._items.clear()
        vault_index._conflicts.clear()
        vault_index._invalid_files.clear()
        vault_index._last_scanned = None
        vault_index._last_status = None
        vault_index._last_root = None

    clear()
    yield
    clear()


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


@pytest.fixture
def vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "ScopeVault"
    path.mkdir()
    monkeypatch.setattr(settings, "obsidian_vault_path", str(path))
    monkeypatch.setattr(settings, "obsidian_vault_name", "ScopeVault")
    return path


async def _make_project(session: AsyncSession, title: str = "Scope Project") -> uuid.UUID:
    project_id = uuid.uuid4()
    session.add(Entity(id=project_id, type="project", title=title, search_text=""))
    session.add(Project(id=project_id, status="active"))
    await session.commit()
    return project_id


async def _make_opportunity(
    session: AsyncSession, *, kind: str = "job", status: str = "discovered", title: str = "Acme"
) -> uuid.UUID:
    opportunity_id = uuid.uuid4()
    session.add(Entity(id=opportunity_id, type="opportunity", title=title, search_text=""))
    session.add(
        Opportunity(
            id=opportunity_id, kind=kind, status=status, found_at=datetime.now(UTC)
        )
    )
    await session.commit()
    return opportunity_id


async def _assert_scope(
    session: AsyncSession, tool: str, action, *, expect_change: bool = True
) -> set[str]:
    """Eylemi çalıştırır ve YALNIZCA izinli tabloların değiştiğini kanıtlar."""
    before = await table_fingerprints(session)
    await action()
    after = await table_fingerprints(session)
    changed = changed_tables(before, after)

    allowed = ALLOWED_TABLES[tool]
    unexpected = changed - allowed
    assert not unexpected, f"{tool} beklenmeyen tabloları değiştirdi: {sorted(unexpected)}"
    if expect_change:
        assert changed, f"{tool} hiçbir şey değiştirmedi"
    return changed


# ---------------------------------------------------------------------------
# Todo
# ---------------------------------------------------------------------------


async def test_todo_create_scope(db_session: AsyncSession) -> None:
    project_id = await _make_project(db_session)
    changed = await _assert_scope(
        db_session,
        "forkos_todo_create",
        lambda: create_todo(
            db_session,
            TodoCreateIn(
                title="Kapsam görevi",
                plan_day=local_today().isoformat(),
                project_id=str(project_id),
            ),
        ),
    )
    assert {"entity", "todo", "plan_slot"} <= changed
    # §74: proje satırı DEĞİŞMEZ (yalnızca ilişki yazılır).
    assert "project" not in changed


async def test_todo_update_scope(db_session: AsyncSession) -> None:
    created = await create_todo(db_session, TodoCreateIn(title="Güncellenecek"))
    todo_id = uuid.UUID(created.target_id)

    changed = await _assert_scope(
        db_session,
        "forkos_todo_update",
        lambda: update_todo(db_session, TodoUpdateIn(todo_id=str(todo_id), priority=1)),
    )
    assert "todo" in changed
    assert "plan_slot" not in changed


async def test_todo_complete_scope(db_session: AsyncSession) -> None:
    created = await create_todo(db_session, TodoCreateIn(title="Tamamlanacak"))
    todo_id = uuid.UUID(created.target_id)

    changed = await _assert_scope(
        db_session, "forkos_todo_complete", lambda: complete_todo(db_session, str(todo_id))
    )
    assert {"entity", "todo", "event"} <= changed


async def test_todo_complete_recurring_scope(db_session: AsyncSession) -> None:
    """§76: rutin tamamlama yeni görev üretir ama kapsam yine Todo domainidir."""
    created = await create_todo(
        db_session,
        TodoCreateIn(
            title="Rutin kapsam", recur="daily", due_at=datetime.now(UTC).isoformat()
        ),
    )

    changed = await _assert_scope(
        db_session,
        "forkos_todo_complete",
        lambda: complete_todo(db_session, created.target_id),
    )
    assert {"entity", "todo"} <= changed
    rows = (await db_session.execute(__import__("sqlalchemy").select(Todo))).scalars().all()
    assert len(rows) == 2  # tamamlanan + yeni oluşum


async def test_todo_plan_scope(db_session: AsyncSession) -> None:
    created = await create_todo(db_session, TodoCreateIn(title="Planlanacak"))

    changed = await _assert_scope(
        db_session,
        "forkos_todo_plan",
        lambda: plan_todo(
            db_session,
            TodoPlanIn(
                todo_id=created.target_id,
                day=(local_today() + timedelta(days=2)).isoformat(),
            ),
        ),
    )
    # §77: görev içeriği bu eylemde DEĞİŞMEZ.
    assert "plan_slot" in changed
    assert "todo" not in changed


# ---------------------------------------------------------------------------
# Project / Opportunity / Application
# ---------------------------------------------------------------------------


async def test_project_update_scope(db_session: AsyncSession, vault: Path) -> None:
    project_id = await _make_project(db_session, "Kapsam projesi")
    vault_before = sorted(p.name for p in vault.rglob("*"))

    changed = await _assert_scope(
        db_session,
        "forkos_project_update",
        lambda: update_project(
            db_session, ProjectUpdateIn(project_id=str(project_id), next_action="H1 kapsamı")
        ),
    )
    assert {"entity", "project", "event"} <= changed
    # §78: operasyonel güncelleme Vault'a DOKUNMAZ.
    assert sorted(p.name for p in vault.rglob("*")) == vault_before


async def test_opportunity_transition_scope(db_session: AsyncSession) -> None:
    opportunity_id = await _make_opportunity(db_session)

    changed = await _assert_scope(
        db_session,
        "forkos_opportunity_transition",
        lambda: transition_opportunity(
            db_session,
            OpportunityTransitionIn(
                opportunity_id=str(opportunity_id),
                expected_status="discovered",
                to_status="shortlisted",
            ),
        ),
    )
    assert {"entity", "opportunity"} <= changed
    # §79: ilgisiz başvuru kayıtlarına dokunulmaz.
    assert "application" not in changed


async def test_application_transition_scope(db_session: AsyncSession) -> None:
    opportunity_id = await _make_opportunity(db_session, status="shortlisted")
    await transition_application(
        db_session,
        ApplicationTransitionIn(opportunity_id=str(opportunity_id), to_status="applied"),
    )

    changed = await _assert_scope(
        db_session,
        "forkos_application_transition",
        lambda: transition_application(
            db_session,
            ApplicationTransitionIn(
                opportunity_id=str(opportunity_id),
                expected_status="applied",
                to_status="interview",
            ),
        ),
    )
    assert {"application"} <= changed


# ---------------------------------------------------------------------------
# Bookmark
# ---------------------------------------------------------------------------


async def test_bookmark_capture_scope(db_session: AsyncSession) -> None:
    changed = await _assert_scope(
        db_session,
        "forkos_bookmark_capture",
        lambda: capture_bookmark(
            db_session, BookmarkCaptureIn(url="https://example.com/scope", title="Kapsam")
        ),
    )
    assert {"entity", "bookmark"} <= changed


async def test_bookmark_update_scope(db_session: AsyncSession) -> None:
    created = await capture_bookmark(
        db_session, BookmarkCaptureIn(url="https://example.com/scope2", title="Kapsam 2")
    )

    changed = await _assert_scope(
        db_session,
        "forkos_bookmark_update",
        lambda: update_bookmark(
            db_session, BookmarkUpdateIn(bookmark_id=created.target_id, read_status="read")
        ),
    )
    assert "bookmark" in changed
    # §81: yer imi güncellemesi bilgi notu OLUŞTURMAZ.
    assert "note" not in changed


# ---------------------------------------------------------------------------
# Bilgi (Vault)
# ---------------------------------------------------------------------------


async def test_brain_capture_scope_touches_no_database_table(
    db_session: AsyncSession, vault: Path
) -> None:
    """§82: hızlı bilgi yakalama forkOS veritabanında HİÇBİR satır değiştirmez."""
    before_fingerprint = await capture_db_content_fingerprint(db_session)
    before_legacy = await legacy_notes_counts(db_session)

    # Bu iki araç için VERİTABANI değişmemesi beklenen sonuçtur; kanıt Vault'ta.
    changed = await _assert_scope(
        db_session,
        "brain_capture",
        lambda: capture_brain_note(db_session, BrainCaptureIn(body="Kapsam notu")),
        expect_change=False,
    )

    assert changed == set()
    assert await capture_db_content_fingerprint(db_session) == before_fingerprint
    assert await legacy_notes_counts(db_session) == before_legacy
    assert len(list(vault.rglob("*.md"))) == 1


async def test_brain_save_to_entity_scope_touches_no_database_table(
    db_session: AsyncSession, vault: Path
) -> None:
    """§83: yönetilen nota ekleme yalnızca Vault'u değiştirir."""
    project_id = await _make_project(db_session, "Vault kapsamı")
    before_fingerprint = await capture_db_content_fingerprint(db_session)

    changed = await _assert_scope(
        db_session,
        "brain_save_to_entity",
        lambda: save_to_entity_brain(
            db_session, BrainSaveToEntityIn(forkos_id=str(project_id), text="karar")
        ),
        expect_change=False,
    )

    assert changed == set()
    assert await capture_db_content_fingerprint(db_session) == before_fingerprint
    # Yalnızca tek bir yönetilen dosya oluşur (§83).
    files = list(vault.rglob("*.md"))
    assert len(files) == 1


async def test_no_h1_action_writes_to_the_legacy_notes_archive(
    db_session: AsyncSession, vault: Path
) -> None:
    """§120: tüm H1 araçları sonrası legacy Notlar arşivi DEĞİŞMEZ."""
    before_legacy = await legacy_notes_counts(db_session)
    project_id = await _make_project(db_session, "Arşiv sınırı")
    opportunity_id = await _make_opportunity(db_session, status="shortlisted")
    todo = await create_todo(db_session, TodoCreateIn(title="Arşiv görevi"))

    await update_todo(db_session, TodoUpdateIn(todo_id=todo.target_id, priority=1))
    await complete_todo(db_session, todo.target_id)
    await plan_todo(
        db_session,
        TodoPlanIn(todo_id=todo.target_id, day=(local_today() + timedelta(days=1)).isoformat()),
    )
    await update_project(
        db_session, ProjectUpdateIn(project_id=str(project_id), next_action="arşiv")
    )
    await transition_opportunity(
        db_session,
        OpportunityTransitionIn(
            opportunity_id=str(opportunity_id),
            expected_status="shortlisted",
            to_status="dismissed",
        ),
    )
    bookmark = await capture_bookmark(
        db_session, BookmarkCaptureIn(url="https://example.com/archive", title="Arşiv")
    )
    await update_bookmark(
        db_session, BookmarkUpdateIn(bookmark_id=bookmark.target_id, favorite=True)
    )
    await capture_brain_note(db_session, BrainCaptureIn(body="arşiv notu"))
    await save_to_entity_brain(
        db_session, BrainSaveToEntityIn(forkos_id=str(project_id), text="arşiv eki")
    )

    assert await legacy_notes_counts(db_session) == before_legacy
