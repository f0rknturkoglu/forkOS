import contextlib
import os
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.models import Entity, Event, Link
from app.db import SessionLocal
from app.integrations.agent.mcp import mcp_server
from app.modules.project.models import Project
from app.modules.todo.models import Todo
from tests.agent_test_utils import (
    capture_db_content_fingerprint as _capture_db_content_fingerprint,
)
from tests.agent_test_utils import (
    capture_vault_fingerprint as _capture_vault_fingerprint,
)


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
