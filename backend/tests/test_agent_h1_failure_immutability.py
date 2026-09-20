"""H1 başarısızlık değişmezliği (§84).

Kural: başarısız bir eylem HİÇBİR ŞEY değiştirmez. Bu dosya, her hata
sınıfında hem veritabanı içerik özetinin hem Vault dosya ağacının
DEĞİŞMEDİĞİNİ kanıtlar.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.models import Entity
from app.core.time import local_today
from app.db import SessionLocal
from app.integrations.agent.actions import (
    ActionError,
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
from app.modules.todo.models import PlanSlot
from tests.agent_test_utils import (
    capture_db_content_fingerprint,
    capture_vault_fingerprint,
    forbid_outbound_network,  # noqa: F401  (autouse ağ koruması)
    legacy_notes_counts,
)


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
    path = tmp_path / "FailureVault"
    path.mkdir()
    monkeypatch.setattr(settings, "obsidian_vault_path", str(path))
    monkeypatch.setattr(settings, "obsidian_vault_name", "FailureVault")
    return path


async def _assert_failure_is_mutation_free(
    session: AsyncSession,
    action: Callable[[], Awaitable[object]],
    *,
    match: str,
    vault: Path | None = None,
) -> None:
    """Eylem hata vermeli ve ne DB ne Vault değişmemeli."""
    db_before = await capture_db_content_fingerprint(session)
    legacy_before = await legacy_notes_counts(session)
    vault_before = capture_vault_fingerprint(vault) if vault is not None else None

    with pytest.raises((ActionError, ValidationError), match=match):
        await action()

    assert await capture_db_content_fingerprint(session) == db_before
    assert await legacy_notes_counts(session) == legacy_before
    if vault is not None:
        assert capture_vault_fingerprint(vault) == vault_before


async def _project(session: AsyncSession, title: str = "P") -> uuid.UUID:
    project_id = uuid.uuid4()
    session.add(Entity(id=project_id, type="project", title=title, search_text=""))
    session.add(Project(id=project_id, status="active"))
    await session.commit()
    return project_id


async def _opportunity(
    session: AsyncSession, *, status: str = "discovered", kind: str = "job"
) -> uuid.UUID:
    opportunity_id = uuid.uuid4()
    session.add(Entity(id=opportunity_id, type="opportunity", title="Acme", search_text=""))
    session.add(
        Opportunity(id=opportunity_id, kind=kind, status=status, found_at=datetime.now(UTC))
    )
    await session.commit()
    return opportunity_id


# ---------------------------------------------------------------------------
# Geçersiz kimlik / bulunamayan hedef
# ---------------------------------------------------------------------------


async def test_invalid_uuid_and_missing_targets_are_mutation_free(
    db_session: AsyncSession, vault: Path
) -> None:
    await _assert_failure_is_mutation_free(
        db_session,
        lambda: complete_todo(db_session, "geçersiz-uuid"),
        match="TARGET_NOT_FOUND",
        vault=vault,
    )
    await _assert_failure_is_mutation_free(
        db_session,
        lambda: update_todo(db_session, TodoUpdateIn(todo_id=str(uuid.uuid4()), title="x")),
        match="TARGET_NOT_FOUND",
        vault=vault,
    )
    await _assert_failure_is_mutation_free(
        db_session,
        lambda: update_project(
            db_session, ProjectUpdateIn(project_id=str(uuid.uuid4()), next_action="x")
        ),
        match="TARGET_NOT_FOUND",
        vault=vault,
    )
    await _assert_failure_is_mutation_free(
        db_session,
        lambda: update_bookmark(
            db_session, BookmarkUpdateIn(bookmark_id=str(uuid.uuid4()), favorite=True)
        ),
        match="TARGET_NOT_FOUND",
        vault=vault,
    )
    await _assert_failure_is_mutation_free(
        db_session,
        lambda: transition_opportunity(
            db_session,
            OpportunityTransitionIn(
                opportunity_id=str(uuid.uuid4()),
                expected_status="discovered",
                to_status="shortlisted",
            ),
        ),
        match="TARGET_NOT_FOUND",
        vault=vault,
    )
    await _assert_failure_is_mutation_free(
        db_session,
        lambda: plan_todo(
            db_session,
            TodoPlanIn(todo_id=str(uuid.uuid4()), day=local_today().isoformat()),
        ),
        match="TARGET_NOT_FOUND",
        vault=vault,
    )


# ---------------------------------------------------------------------------
# Bayat durum (STALE_ACTION)
# ---------------------------------------------------------------------------


async def test_stale_updated_at_is_mutation_free(db_session: AsyncSession, vault: Path) -> None:
    todo = await create_todo(db_session, TodoCreateIn(title="Bayat"))
    project_id = await _project(db_session, "Bayat proje")
    bookmark = await capture_bookmark(
        db_session, BookmarkCaptureIn(url="https://example.com/stale", title="Bayat")
    )
    stale = (datetime.now(UTC) - timedelta(days=3)).isoformat()

    for action in (
        lambda: update_todo(
            db_session,
            TodoUpdateIn(todo_id=todo.target_id, priority=1, expected_updated_at=stale),
        ),
        lambda: update_project(
            db_session,
            ProjectUpdateIn(project_id=str(project_id), next_action="x", expected_updated_at=stale),
        ),
        lambda: update_bookmark(
            db_session,
            BookmarkUpdateIn(bookmark_id=bookmark.target_id, favorite=True, expected_updated_at=stale),
        ),
    ):
        await _assert_failure_is_mutation_free(
            db_session, action, match="STALE_ACTION", vault=vault
        )


async def test_stale_status_is_mutation_free(db_session: AsyncSession, vault: Path) -> None:
    opportunity_id = await _opportunity(db_session, status="discovered")

    await _assert_failure_is_mutation_free(
        db_session,
        lambda: transition_opportunity(
            db_session,
            OpportunityTransitionIn(
                opportunity_id=str(opportunity_id),
                expected_status="shortlisted",  # gerçek durum: discovered
                to_status="dismissed",
            ),
        ),
        match="STALE_ACTION",
        vault=vault,
    )

    # Başvuru hattı da aynı şekilde fail-closed davranır.
    await transition_application(
        db_session,
        ApplicationTransitionIn(opportunity_id=str(opportunity_id), to_status="applied"),
    )
    await _assert_failure_is_mutation_free(
        db_session,
        lambda: transition_application(
            db_session,
            ApplicationTransitionIn(
                opportunity_id=str(opportunity_id),
                expected_status="interview",  # gerçek durum: applied
                to_status="offer",
            ),
        ),
        match="STALE_ACTION",
        vault=vault,
    )


# ---------------------------------------------------------------------------
# Geçersiz geçiş / plan belirsizliği
# ---------------------------------------------------------------------------


async def test_invalid_transitions_are_mutation_free(
    db_session: AsyncSession, vault: Path
) -> None:
    opportunity_id = await _opportunity(db_session, status="discovered")

    await _assert_failure_is_mutation_free(
        db_session,
        lambda: transition_opportunity(
            db_session,
            OpportunityTransitionIn(
                opportunity_id=str(opportunity_id),
                expected_status="discovered",
                to_status="interview",  # keşif akışında geçersiz
            ),
        ),
        match="INVALID_TRANSITION",
        vault=vault,
    )

    await _assert_failure_is_mutation_free(
        db_session,
        lambda: transition_application(
            db_session,
            ApplicationTransitionIn(
                opportunity_id=str(opportunity_id),
                to_status="interview",  # başvuru kaydı yok
            ),
        ),
        match="APPLICATION_NOT_FOUND",
        vault=vault,
    )


async def test_ambiguous_plan_is_mutation_free(db_session: AsyncSession, vault: Path) -> None:
    todo = await create_todo(db_session, TodoCreateIn(title="Belirsiz plan"))
    todo_id = uuid.UUID(todo.target_id)
    for offset in (2, 5):
        db_session.add(
            PlanSlot(entity_id=todo_id, day=local_today() + timedelta(days=offset), position=0)
        )
    await db_session.commit()

    await _assert_failure_is_mutation_free(
        db_session,
        lambda: plan_todo(
            db_session,
            TodoPlanIn(
                todo_id=str(todo_id), day=(local_today() + timedelta(days=9)).isoformat()
            ),
        ),
        match="AMBIGUOUS_PLAN",
        vault=vault,
    )


# ---------------------------------------------------------------------------
# Geçersiz girdi (şema)
# ---------------------------------------------------------------------------


async def test_invalid_payloads_are_rejected_before_any_write(
    db_session: AsyncSession, vault: Path
) -> None:
    cases: list[tuple[Callable[[], object], str]] = [
        (lambda: TodoCreateIn(title="   "), "Title cannot be empty"),
        (lambda: TodoCreateIn(title="x" * 301), "Title cannot exceed 300"),
        (lambda: TodoCreateIn(title="ok", tags=[f"t{i}" for i in range(21)]), "20 tags"),
        (lambda: TodoCreateIn(title="ok", plan_day="2026-13-01"), "Invalid"),
        (lambda: TodoPlanIn(todo_id=str(uuid.uuid4()), day="2026-1-1"), "YYYY-MM-DD"),
        (lambda: BookmarkCaptureIn(url="ftp://example.com"), "http"),
        (lambda: BookmarkCaptureIn.model_validate(
            {"url": "https://example.com", "collection": "geçersiz"}
        ), "collection"),
        (lambda: BrainCaptureIn(body=""), "Body cannot be empty"),
        (lambda: BrainCaptureIn(body="x" * 40001), "40000"),
        (lambda: BrainSaveToEntityIn(forkos_id=str(uuid.uuid4()), text="x" * 20001), "20000"),
        (lambda: BrainSaveToEntityIn.model_validate(
            {"forkos_id": str(uuid.uuid4()), "text": "x", "relative_path": "a.md"}
        ), "relative_path"),
    ]

    db_before = await capture_db_content_fingerprint(db_session)
    vault_before = capture_vault_fingerprint(vault)

    for factory, match in cases:
        with pytest.raises(ValidationError, match=match):
            factory()

    assert await capture_db_content_fingerprint(db_session) == db_before
    assert capture_vault_fingerprint(vault) == vault_before


async def test_invalid_date_is_rejected_without_write(db_session: AsyncSession, vault: Path) -> None:
    """§30: planner geçersiz tarih/saat kabul etmez."""
    todo = await create_todo(db_session, TodoCreateIn(title="Tarih kontrolü"))

    await _assert_failure_is_mutation_free(
        db_session,
        lambda: plan_todo(
            db_session,
            TodoPlanIn(todo_id=todo.target_id, day="2026-02-30"),
        ),
        match="Invalid",
        vault=vault,
    )


# ---------------------------------------------------------------------------
# Vault hata sınıfları
# ---------------------------------------------------------------------------


async def test_vault_unavailable_is_mutation_free(db_session: AsyncSession) -> None:
    """§54: Vault yoksa bilgi yazması hata verir; legacy arşive düşmez."""
    project_id = await _project(db_session, "Vaultsuz")
    backup = settings.obsidian_vault_path
    settings.obsidian_vault_path = ""
    try:
        await _assert_failure_is_mutation_free(
            db_session,
            lambda: capture_brain_note(db_session, BrainCaptureIn(body="yazılamamalı")),
            match="VAULT_UNAVAILABLE",
        )
        await _assert_failure_is_mutation_free(
            db_session,
            lambda: save_to_entity_brain(
                db_session, BrainSaveToEntityIn(forkos_id=str(project_id), text="yazılamamalı")
            ),
            match="VAULT_UNAVAILABLE",
        )
    finally:
        settings.obsidian_vault_path = backup


async def test_vault_conflict_is_mutation_free(db_session: AsyncSession, vault: Path) -> None:
    """§54: aynı kimlik iki dosyada varsa yazma REDDEDİLİR."""
    project_id = await _project(db_session, "Çakışan")
    target = vault / "20 Projects" / "Çakışan"
    target.mkdir(parents=True)
    for name in ("Bir.md", "İki.md"):
        (target / name).write_text(
            f"---\nforkos_id: {project_id}\nforkos_type: project\ntitle: Çakışma\n---\n\ngövde\n",
            encoding="utf-8",
        )

    await _assert_failure_is_mutation_free(
        db_session,
        lambda: save_to_entity_brain(
            db_session, BrainSaveToEntityIn(forkos_id=str(project_id), text="yazılmamalı")
        ),
        match="VAULT_CONFLICT",
        vault=vault,
    )


async def test_vault_stale_write_is_mutation_free(db_session: AsyncSession, vault: Path) -> None:
    """§18: kullanıcı düzenlemesi EZİLMEZ."""
    project_id = await _project(db_session, "Bayat vault")
    created = await save_to_entity_brain(
        db_session, BrainSaveToEntityIn(forkos_id=str(project_id), text="ilk")
    )
    path = vault / created.after["relative_path"]
    stat = path.stat()
    os.utime(path, (stat.st_atime + 60, stat.st_mtime + 60))

    await _assert_failure_is_mutation_free(
        db_session,
        lambda: save_to_entity_brain(
            db_session, BrainSaveToEntityIn(forkos_id=str(project_id), text="ezilmemeli")
        ),
        match="VAULT_STALE",
        vault=vault,
    )


async def test_heading_failures_are_mutation_free(db_session: AsyncSession, vault: Path) -> None:
    """§53: belirsiz ya da bulunamayan başlıkta TAHMİN EDİLMEZ."""
    project_id = await _project(db_session, "Başlık")
    await save_to_entity_brain(
        db_session, BrainSaveToEntityIn(forkos_id=str(project_id), text="gövde")
    )

    await _assert_failure_is_mutation_free(
        db_session,
        lambda: save_to_entity_brain(
            db_session,
            BrainSaveToEntityIn(forkos_id=str(project_id), text="x", heading="Yok"),
        ),
        match="HEADING_NOT_FOUND",
        vault=vault,
    )


async def test_repeated_failures_leave_no_residue(db_session: AsyncSession, vault: Path) -> None:
    """Aynı hata tekrar tekrar denense de hiçbir kalıntı bırakmaz."""
    opportunity_id = await _opportunity(db_session, status="discovered")
    db_before = await capture_db_content_fingerprint(db_session)
    vault_before = capture_vault_fingerprint(vault)

    for _ in range(3):
        with pytest.raises(ActionError, match="STALE_ACTION"):
            await transition_opportunity(
                db_session,
                OpportunityTransitionIn(
                    opportunity_id=str(opportunity_id),
                    expected_status="shortlist",
                    to_status="dismissed",
                ),
            )

    assert await capture_db_content_fingerprint(db_session) == db_before
    assert capture_vault_fingerprint(vault) == vault_before
