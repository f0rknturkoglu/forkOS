"""H1.1 — Gerçek `/mcp` taşıması üzerinden yazma yüzeyi doğruluğu.

Neden ayrı bir dosya: H1'in ilk sürümünde bir dizi hata yalnızca **taşıma**
katmanında görünüyordu. Adaptör testleri doğrudan Pydantic modeli kurduğu için
`model_fields_set` doğruydu; oysa MCP yolu tüm Python argümanlarını modele
geçiriyor ve "verilmedi" ile "null verildi" ayrımını yok ediyordu.

Bu dosya H1.1'in sözleşmesini kanıtlar:

    omitted  ≠  explicit null
    hata     →  DB ve Vault DEĞİŞMEZ
    makbuz   →  gerçek sonucu anlatır
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.models import Entity
from app.db import SessionLocal
from app.integrations.obsidian.service import vault_index
from app.modules.bookmark.models import Bookmark
from app.modules.opportunity.models import Application, Opportunity
from app.modules.project.models import Project
from app.modules.todo.models import PlanSlot, Todo
from tests.agent_test_utils import (
    capture_db_content_fingerprint,
    capture_vault_fingerprint,
    legacy_notes_counts,
    mcp_session,
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
    path = tmp_path / "TransportVault"
    path.mkdir()
    monkeypatch.setattr(settings, "obsidian_vault_path", str(path))
    monkeypatch.setattr(settings, "obsidian_vault_name", "TransportVault")
    return path


def receipt_of(result) -> dict:
    assert result.is_error is False, result.content
    payload = json.loads(result.content[0].text)
    return payload["data"]


async def _seed_todo(session: AsyncSession) -> uuid.UUID:
    todo_id = uuid.uuid4()
    due = (datetime.now(UTC) + timedelta(days=3)).replace(microsecond=0)
    reminder = (datetime.now(UTC) + timedelta(days=2)).replace(microsecond=0)
    session.add(
        Entity(id=todo_id, type="todo", title="Original", search_text="Original")
    )
    session.add(
        Todo(
            id=todo_id,
            description="Keep me",
            priority=3,
            status="open",
            due_at=due,
            reminder_at=reminder,
            recur="weekly",
        )
    )
    await session.commit()
    await _set_tags(session, todo_id, ["a", "b"])
    return todo_id


async def _set_tags(session: AsyncSession, entity_id: uuid.UUID, names: list[str]) -> None:
    from app.core import tags as tag_svc

    await tag_svc.set_tags(session, entity_id, names)
    await session.commit()


async def _seed_bookmark(session: AsyncSession) -> uuid.UUID:
    bookmark_id = uuid.uuid4()
    session.add(
        Entity(id=bookmark_id, type="bookmark", title="Seed", search_text="seed")
    )
    session.add(
        Bookmark(
            id=bookmark_id,
            url="https://example.com/seed",
            url_hash="seed-hash-" + bookmark_id.hex,
            collection="inbox",
            favorite=False,
            read_status="unread",
            source="manual",
        )
    )
    await session.commit()
    await _set_tags(session, bookmark_id, ["rust", "later"])
    return bookmark_id


async def _seed_project(session: AsyncSession, next_action: str = "Mevcut is") -> uuid.UUID:
    project_id = uuid.uuid4()
    session.add(Entity(id=project_id, type="project", title="Proje", search_text=""))
    session.add(Project(id=project_id, status="active", next_action=next_action))
    await session.commit()
    return project_id


async def _seed_opportunity(
    session: AsyncSession, *, status: str = "shortlisted"
) -> uuid.UUID:
    opportunity_id = uuid.uuid4()
    session.add(Entity(id=opportunity_id, type="opportunity", title="Acme", search_text=""))
    session.add(
        Opportunity(id=opportunity_id, kind="job", status=status, found_at=datetime.now(UTC))
    )
    await session.commit()
    return opportunity_id


async def _tags_of(session: AsyncSession, entity_id: uuid.UUID) -> list[str]:
    from app.core import tags as tag_svc

    return sorted((await tag_svc.tags_for(session, [entity_id])).get(entity_id, []))


# ---------------------------------------------------------------------------
# §5 — Todo kısmi güncelleme: verilmeyen alanlar KORUNUR
# ---------------------------------------------------------------------------


async def test_mcp_todo_partial_update_preserves_omitted_fields(
    db_session: AsyncSession,
) -> None:
    todo_id = await _seed_todo(db_session)
    async with mcp_session() as session:
        result = await session.call_tool(
            "forkos_todo_update", {"todo_id": str(todo_id), "priority": 1}
        )
    receipt = receipt_of(result)
    assert receipt["status"] == "executed"
    assert receipt["changed_fields"] == ["priority"]

    todo = await db_session.get(Todo, todo_id)
    entity = await db_session.get(Entity, todo_id)
    assert todo is not None and entity is not None
    assert todo.priority == 1
    assert entity.title == "Original"
    assert todo.description == "Keep me"
    assert todo.due_at is not None
    assert todo.reminder_at is not None
    assert todo.recur == "weekly"
    assert await _tags_of(db_session, todo_id) == ["a", "b"]


# ---------------------------------------------------------------------------
# §6 — Açık null, desteklenen alanda TEMİZLER
# ---------------------------------------------------------------------------


async def test_mcp_todo_explicit_null_can_clear_supported_field(
    db_session: AsyncSession,
) -> None:
    todo_id = await _seed_todo(db_session)
    async with mcp_session() as session:
        cleared = await session.call_tool(
            "forkos_todo_update", {"todo_id": str(todo_id), "recur": ""}
        )
    receipt = receipt_of(cleared)
    assert receipt["status"] == "executed"

    todo = await db_session.get(Todo, todo_id)
    assert todo is not None
    assert todo.recur is None
    # Diğer alanlar hâlâ korunur.
    assert todo.description == "Keep me"
    assert todo.priority == 3


# ---------------------------------------------------------------------------
# §7 — Bookmark kısmi güncelleme
# ---------------------------------------------------------------------------


async def test_mcp_bookmark_partial_update_preserves_omitted_fields(
    db_session: AsyncSession,
) -> None:
    bookmark_id = await _seed_bookmark(db_session)
    async with mcp_session() as session:
        result = await session.call_tool(
            "forkos_bookmark_update", {"bookmark_id": str(bookmark_id), "favorite": True}
        )
    receipt = receipt_of(result)
    assert receipt["status"] == "executed"

    bookmark = await db_session.get(Bookmark, bookmark_id)
    assert bookmark is not None
    assert bookmark.favorite is True
    assert bookmark.collection == "inbox"
    assert bookmark.read_status == "unread"
    assert await _tags_of(db_session, bookmark_id) == ["later", "rust"]


# ---------------------------------------------------------------------------
# §9 — Bookmark etiket güncellemesi gerçekten ÇALIŞIR
# ---------------------------------------------------------------------------


async def test_bookmark_tags_only_update_executes(db_session: AsyncSession) -> None:
    bookmark_id = await _seed_bookmark(db_session)
    await _set_tags(db_session, bookmark_id, ["old"])

    async with mcp_session() as session:
        result = await session.call_tool(
            "forkos_bookmark_update",
            {"bookmark_id": str(bookmark_id), "tags": ["new", "rust"]},
        )
    receipt = receipt_of(result)
    assert receipt["status"] == "executed", receipt
    assert "tags" in receipt["changed_fields"]
    assert await _tags_of(db_session, bookmark_id) == ["new", "rust"]


async def test_bookmark_same_tags_update_is_noop(db_session: AsyncSession) -> None:
    bookmark_id = await _seed_bookmark(db_session)
    async with mcp_session() as session:
        first = await session.call_tool(
            "forkos_bookmark_update",
            {"bookmark_id": str(bookmark_id), "tags": ["rust", "later"]},
        )
        fingerprint = await capture_db_content_fingerprint(db_session)
        second = await session.call_tool(
            "forkos_bookmark_update",
            {"bookmark_id": str(bookmark_id), "tags": ["rust", "later"]},
        )
    assert receipt_of(first)["status"] == "noop"
    assert receipt_of(second)["status"] == "noop"
    assert await capture_db_content_fingerprint(db_session) == fingerprint


# ---------------------------------------------------------------------------
# §10 — Proje: yalnızca project_id göndermek next_action'ı TEMİZLEMEZ
# ---------------------------------------------------------------------------


async def test_project_update_omitted_next_action_does_not_clear_it(
    db_session: AsyncSession,
) -> None:
    project_id = await _seed_project(db_session, next_action="Korunmali")
    before = await capture_db_content_fingerprint(db_session)

    async with mcp_session() as session:
        result = await session.call_tool(
            "forkos_project_update", {"project_id": str(project_id)}
        )
    receipt = receipt_of(result)
    assert receipt["status"] == "noop", receipt

    project = await db_session.get(Project, project_id)
    assert project is not None
    assert project.next_action == "Korunmali"
    assert await capture_db_content_fingerprint(db_session) == before


async def test_project_update_explicit_null_clears_next_action(
    db_session: AsyncSession,
) -> None:
    project_id = await _seed_project(db_session, next_action="Silinecek")
    async with mcp_session() as session:
        result = await session.call_tool(
            "forkos_project_update", {"project_id": str(project_id), "next_action": None}
        )
    receipt = receipt_of(result)
    assert receipt["status"] == "executed", receipt
    project = await db_session.get(Project, project_id)
    assert project is not None and project.next_action is None


# ---------------------------------------------------------------------------
# §19 — Başvuru: mevcut kayıtta expected_status ZORUNLU
# ---------------------------------------------------------------------------


async def test_application_first_apply_without_expected_status_is_allowed(
    db_session: AsyncSession,
) -> None:
    opportunity_id = await _seed_opportunity(db_session)
    async with mcp_session() as session:
        result = await session.call_tool(
            "forkos_application_transition",
            {"opportunity_id": str(opportunity_id), "to_status": "applied"},
        )
    assert receipt_of(result)["status"] == "executed"
    assert await db_session.get(Application, opportunity_id) is not None


async def test_existing_application_requires_expected_status(
    db_session: AsyncSession,
) -> None:
    opportunity_id = await _seed_opportunity(db_session)
    async with mcp_session() as session:
        await session.call_tool(
            "forkos_application_transition",
            {"opportunity_id": str(opportunity_id), "to_status": "applied"},
        )
        before = await capture_db_content_fingerprint(db_session)
        result = await session.call_tool(
            "forkos_application_transition",
            {"opportunity_id": str(opportunity_id), "to_status": "interview"},
        )

    assert result.is_error is True
    assert "EXPECTED_STATUS_REQUIRED" in result.content[0].text
    assert await capture_db_content_fingerprint(db_session) == before
    application = await db_session.get(Application, opportunity_id)
    assert application is not None and application.status == "applied"


# ---------------------------------------------------------------------------
# §25/§27 — todo_plan idempotansı
# ---------------------------------------------------------------------------


async def test_todo_plan_same_request_twice_is_noop_second_time(
    db_session: AsyncSession,
) -> None:
    todo_id = await _seed_todo(db_session)
    day = (datetime.now(UTC) + timedelta(days=5)).date().isoformat()
    payload = {"todo_id": str(todo_id), "day": day, "start_min": 840, "duration_min": 60}

    async with mcp_session() as session:
        first = await session.call_tool("forkos_todo_plan", payload)
        assert receipt_of(first)["status"] == "executed"

        slot = (
            await db_session.execute(select(PlanSlot).where(PlanSlot.entity_id == todo_id))
        ).scalar_one()
        fingerprint = await capture_db_content_fingerprint(db_session)

        second = await session.call_tool("forkos_todo_plan", payload)
        assert receipt_of(second)["status"] == "noop", receipt_of(second)
        assert await capture_db_content_fingerprint(db_session) == fingerprint

        third = await session.call_tool(
            "forkos_todo_plan", {**payload, "start_min": 900}
        )
        assert receipt_of(third)["status"] == "executed"

    assert slot.day.isoformat() == day


# ---------------------------------------------------------------------------
# §24 — Tamamlanmış görev noop makbuzu GERÇEK completed_at taşır
# ---------------------------------------------------------------------------


async def test_completed_todo_noop_receipt_returns_real_completed_at(
    db_session: AsyncSession,
) -> None:
    todo_id = await _seed_todo(db_session)
    async with mcp_session() as session:
        await session.call_tool("forkos_todo_complete", {"todo_id": str(todo_id)})
        result = await session.call_tool("forkos_todo_complete", {"todo_id": str(todo_id)})
    receipt = receipt_of(result)
    assert receipt["status"] == "noop"
    assert receipt["after"]["status"] == "done"
    assert receipt["after"]["completed_at"] is not None

    todo = await db_session.get(Todo, todo_id)
    assert todo is not None and todo.completed_at is not None
    assert receipt["after"]["completed_at"] == todo.completed_at.isoformat()


# ---------------------------------------------------------------------------
# §15 — Eksik not + geçersiz başlık: TAM değişmezlik
# ---------------------------------------------------------------------------


async def test_brain_save_missing_note_bad_heading_is_fully_immutable(
    db_session: AsyncSession, vault: Path
) -> None:
    project_id = await _seed_project(db_session)
    db_before = await capture_db_content_fingerprint(db_session)
    vault_before = capture_vault_fingerprint(vault)
    legacy_before = await legacy_notes_counts(db_session)

    async with mcp_session() as session:
        result = await session.call_tool(
            "brain_save_to_entity",
            {
                "forkos_id": str(project_id),
                "text": "must not remain",
                "heading": "Does Not Exist",
            },
        )

    assert result.is_error is True
    assert "HEADING_NOT_FOUND" in result.content[0].text

    assert await capture_db_content_fingerprint(db_session) == db_before
    assert capture_vault_fingerprint(vault) == vault_before
    assert await legacy_notes_counts(db_session) == legacy_before
    # Yönetilen not OLUŞMAMIŞ olmalı: yetim dosya bırakılmaz (§12).
    assert not list(vault.rglob("*.md"))


# ---------------------------------------------------------------------------
# §16 — Eksik not + başlıksız ekleme: canonical oluşturma ÇALIŞIR
# ---------------------------------------------------------------------------


async def test_brain_save_missing_note_without_heading_creates_and_appends(
    db_session: AsyncSession, vault: Path
) -> None:
    project_id = await _seed_project(db_session)
    legacy_before = await legacy_notes_counts(db_session)

    async with mcp_session() as session:
        result = await session.call_tool(
            "brain_save_to_entity",
            {"forkos_id": str(project_id), "text": "First knowledge entry"},
        )
    receipt = receipt_of(result)
    assert receipt["status"] == "executed"

    files = list(vault.rglob("*.md"))
    assert len(files) == 1
    assert "First knowledge entry" in files[0].read_text(encoding="utf-8")
    assert await legacy_notes_counts(db_session) == legacy_before


# ---------------------------------------------------------------------------
# §23 — Mutlak kasa yolu ajan çıktısına SIZMAZ
# ---------------------------------------------------------------------------


async def test_knowledge_pointer_does_not_expose_absolute_vault_path(
    db_session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§21/§22: tanılama gerçek kasa kökünü/kullanıcı adını göstermez."""
    secret = tmp_path / "secret-user" / "private" / "vault"  # var olmayan dizin
    monkeypatch.setattr(settings, "obsidian_vault_path", str(secret))
    monkeypatch.setattr(settings, "obsidian_vault_name", "FakeVault")

    project_id = await _seed_project(db_session)

    async with mcp_session() as session:
        project_ctx = await session.call_tool(
            "forkos_project_context", {"project_id": str(project_id)}
        )
        entity_ctx = await session.call_tool(
            "forkos_entity_context", {"entity_id": str(project_id)}
        )

    for result in (project_ctx, entity_ctx):
        assert result.is_error is False, result.content
        text = result.content[0].text
        for leak in ("secret-user", "/Users/", "private/vault", str(tmp_path)):
            assert leak not in text, f"sızıntı: {leak!r}"

    # Durum yine de doğru raporlanır.
    payload = json.loads(project_ctx.content[0].text)
    knowledge = payload["data"]["knowledge"]
    assert knowledge["state"] == "unavailable"
    assert knowledge["available"] is False
    assert knowledge["diagnostic"]
