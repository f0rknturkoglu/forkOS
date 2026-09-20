import contextlib
import hashlib
import os
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.models import Entity, Event, Link, Notification
from app.db import SessionLocal
from app.integrations.agent.mcp import mcp_server
from app.modules.bookmark.models import Bookmark
from app.modules.flashcard.models import FlashcardCard
from app.modules.note.models import Note, NoteFolder
from app.modules.opportunity.models import Application, Opportunity
from app.modules.project.models import Milestone, Project
from app.modules.todo.models import Todo


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


@pytest.fixture
def mock_immutability_vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    v_dir = tmp_path / "ImmutabilityVault"
    v_dir.mkdir()

    (v_dir / "20 Projects").mkdir()
    (v_dir / "10 Daily").mkdir()
    (v_dir / ".obsidian").mkdir()
    (v_dir / ".git").mkdir()

    # Note 1
    proj_md = """---
forkos_id: 11111111-2222-3333-4444-555555555555
forkos_type: project
title: Immutability Project
---
# Immutability Project
This is a test project note.
"""
    (v_dir / "20 Projects" / "Immutability.md").write_text(proj_md, encoding="utf-8")

    # Note 2
    daily_md = """# 2026-09-20
Daily note content for test.
"""
    (v_dir / "10 Daily" / "2026-09-20.md").write_text(daily_md, encoding="utf-8")

    # Outside file and symlink pointing outside
    outside_dir = tmp_path / "Outside"
    outside_dir.mkdir()
    outside_file = outside_dir / "secret.txt"
    outside_file.write_text("outside secret", encoding="utf-8")

    symlink_file = v_dir / "20 Projects" / "escaping_link.md"
    with contextlib.suppress(OSError):
        os.symlink(outside_file, symlink_file)

    monkeypatch.setattr(settings, "obsidian_vault_path", str(v_dir))
    monkeypatch.setattr(settings, "obsidian_vault_name", "ImmutabilityVault")

    return v_dir


async def _capture_db_content_fingerprint(session: AsyncSession) -> str:
    """Capture deterministic SHA-256 fingerprint of row contents across all key tables."""
    hasher = hashlib.sha256()

    # 1. Entity
    rows = (await session.execute(
        select(Entity.id, Entity.type, Entity.title, Entity.search_text, Entity.archived_at)
        .order_by(Entity.id)
    )).all()
    hasher.update(str(rows).encode("utf-8"))

    # 2. Event
    rows = (await session.execute(
        select(Event.id, Event.entity_id, Event.verb, Event.payload, Event.occurred_at)
        .order_by(Event.id)
    )).all()
    hasher.update(str(rows).encode("utf-8"))

    # 3. Link
    rows = (await session.execute(
        select(Link.from_id, Link.to_id, Link.relation, Link.created_at)
        .order_by(Link.from_id, Link.to_id, Link.relation)
    )).all()
    hasher.update(str(rows).encode("utf-8"))

    # 4. Todo
    rows = (await session.execute(
        select(Todo.id, Todo.status, Todo.priority, Todo.due_at, Todo.completed_at)
        .order_by(Todo.id)
    )).all()
    hasher.update(str(rows).encode("utf-8"))

    # 5. Project
    rows = (await session.execute(
        select(Project.id, Project.status, Project.next_action, Project.github_repo, Project.stack)
        .order_by(Project.id)
    )).all()
    hasher.update(str(rows).encode("utf-8"))

    # 6. Milestone
    rows = (await session.execute(
        select(Milestone.id, Milestone.project_id, Milestone.title, Milestone.due_at, Milestone.completed_at)
        .order_by(Milestone.id)
    )).all()
    hasher.update(str(rows).encode("utf-8"))

    # 7. Notification
    rows = (await session.execute(
        select(Notification.id, Notification.title, Notification.body, Notification.read_at, Notification.dismissed_at)
        .order_by(Notification.id)
    )).all()
    hasher.update(str(rows).encode("utf-8"))

    # 8. Opportunity
    rows = (await session.execute(
        select(Opportunity.id, Opportunity.kind, Opportunity.status, Opportunity.organization, Opportunity.deadline_at)
        .order_by(Opportunity.id)
    )).all()
    hasher.update(str(rows).encode("utf-8"))

    # 9. Application
    rows = (await session.execute(
        select(Application.opportunity_id, Application.status, Application.status_changed_at)
        .order_by(Application.opportunity_id)
    )).all()
    hasher.update(str(rows).encode("utf-8"))

    # 10. FlashcardCard
    rows = (await session.execute(
        select(FlashcardCard.id, FlashcardCard.deck_id, FlashcardCard.reps, FlashcardCard.due_at)
        .order_by(FlashcardCard.id)
    )).all()
    hasher.update(str(rows).encode("utf-8"))

    # 11. Bookmark
    rows = (await session.execute(
        select(Bookmark.id, Bookmark.collection, Bookmark.url, Bookmark.read_status)
        .order_by(Bookmark.id)
    )).all()
    hasher.update(str(rows).encode("utf-8"))

    # 12. Note
    rows = (await session.execute(
        select(Note.id, Note.folder_id, Note.project_id, Note.pinned, Note.body)
        .order_by(Note.id)
    )).all()
    hasher.update(str(rows).encode("utf-8"))

    # 13. NoteFolder
    rows = (await session.execute(
        select(NoteFolder.id, NoteFolder.parent_id, NoteFolder.position)
        .order_by(NoteFolder.id)
    )).all()
    hasher.update(str(rows).encode("utf-8"))

    return hasher.hexdigest()


def _capture_vault_fingerprint(vault_dir: Path) -> dict[str, tuple[str, float]]:
    """Capture SHA-256 and mtime of every file in the Vault."""
    fingerprints = {}
    for root, _, files in os.walk(vault_dir):
        for f in files:
            p = Path(root) / f
            try:
                content = p.read_bytes()
                sha = hashlib.sha256(content).hexdigest()
                mtime = os.path.getmtime(p)
                rel = str(p.relative_to(vault_dir))
                fingerprints[rel] = (sha, mtime)
            except Exception:
                pass
    return fingerprints


async def test_db_content_fingerprint_sensitive_to_updates(db_session: AsyncSession):
    """Proves that an UPDATE on any record without row count change strictly alters the fingerprint."""
    todo_id = uuid.uuid4()
    todo_ent = Entity(id=todo_id, type="todo", title="Original Title", search_text="")
    db_session.add(todo_ent)
    todo = Todo(id=todo_id, status="open", priority=1)
    db_session.add(todo)
    await db_session.commit()

    fp_before = await _capture_db_content_fingerprint(db_session)

    # Modify an attribute in-place without adding/removing rows
    todo.priority = 99
    await db_session.commit()

    fp_after = await _capture_db_content_fingerprint(db_session)
    assert fp_before != fp_after, "Fingerprint MUST change on in-place row field updates!"


async def test_db_and_vault_immutability_under_all_mcp_tools(
    db_session: AsyncSession,
    mock_immutability_vault: Path,
):
    """Verify that calling all 8 MCP tools causes ZERO changes to PostgreSQL and the Vault filesystem."""
    # 1. Seed some operational data
    proj_id = uuid.uuid4()
    proj_ent = Entity(id=proj_id, type="project", title="Test Immutability Project", search_text="")
    db_session.add(proj_ent)
    proj = Project(id=proj_id, status="active", next_action="Verify immutability")
    db_session.add(proj)
    await db_session.flush()

    todo_id = uuid.uuid4()
    todo_ent = Entity(id=todo_id, type="todo", title="Verify immutability task", search_text="")
    db_session.add(todo_ent)
    todo = Todo(id=todo_id, status="open", priority=2)
    db_session.add(todo)

    link = Link(from_id=todo_id, to_id=proj_id, relation="belongs_to")
    db_session.add(link)

    event = Event(
        entity_id=proj_id,
        entity_type="project",
        verb="project.verified",
        payload={"status": "ok", "api_key": "super_secret_key"},
    )
    db_session.add(event)
    await db_session.commit()

    # 2. Capture baseline deterministic content fingerprints
    db_before = await _capture_db_content_fingerprint(db_session)
    vault_before = _capture_vault_fingerprint(mock_immutability_vault)

    # 3. Call ALL 8 MCP tools
    await mcp_server.call_tool("forkos_briefing", {})
    await mcp_server.call_tool("forkos_search", {"query": "Immutability"})
    await mcp_server.call_tool("forkos_entity_context", {"entity_id": str(proj_id)})
    await mcp_server.call_tool("forkos_project_context", {"project_id": str(proj_id)})
    await mcp_server.call_tool("forkos_recent_activity", {"limit": 10})
    await mcp_server.call_tool("brain_status", {})
    await mcp_server.call_tool("brain_search", {"query": "Immutability"})
    await mcp_server.call_tool("brain_read", {"relative_path": "20 Projects/Immutability.md"})

    # 4. Verify DB content state is 100% byte-identical
    db_after = await _capture_db_content_fingerprint(db_session)
    assert db_before == db_after, f"DB mutated during read-only tool calls! Before: {db_before}, After: {db_after}"

    # 5. Verify Vault files and mtimes are 100% identical
    vault_after = _capture_vault_fingerprint(mock_immutability_vault)
    assert vault_before == vault_after, "Vault filesystem mutated during read-only tool calls!"


async def test_security_constraints_and_traversal(
    db_session: AsyncSession,
    mock_immutability_vault: Path,
):
    """Verify path traversal, escaping symlinks, and credential masking."""
    # 1. Path traversal attempt via brain_read
    with pytest.raises(ToolError):
        await mcp_server.call_tool("brain_read", {"relative_path": "../../../etc/passwd"})

    # 2. Symlink escape attempt
    with pytest.raises(ToolError):
        await mcp_server.call_tool("brain_read", {"relative_path": "20 Projects/escaping_link.md"})

    # 3. Credential scrubbing
    ev = Event(
        verb="test.login",
        payload={"username": "alice", "api_key": "super_secret_key"},
    )
    db_session.add(ev)
    await db_session.commit()

    act_res = await mcp_server.call_tool("forkos_recent_activity", {"limit": 5})
    assert "super_secret_key" not in act_res.content[0].text
    assert "[REDACTED]" in act_res.content[0].text
