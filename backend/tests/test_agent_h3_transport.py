"""H3 — gerçek `/mcp` taşıması üzerinden kanıt sözleşmesi.

H3 salt-okunurdur, ama bu tek başına yeterli kanıt değildir: şema sınırları,
anotasyonlar ve "hiçbir şey değişmedi" iddiası TAŞIMA katmanından geçmelidir.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.models import Entity, Event, Link
from app.db import SessionLocal
from app.integrations.agent.evidence_models import MAX_QUERY_LENGTH, MAX_TOTAL_EVIDENCE_CHARS
from app.integrations.obsidian.service import refresh_vault_index
from app.modules.project.models import Project
from app.modules.todo.models import Todo
from tests.agent_test_utils import (
    capture_db_content_fingerprint,
    capture_vault_fingerprint,
    forbid_outbound_network,  # noqa: F401  (autouse: H3 dış ağ çağrısı yapmaz)
    legacy_notes_counts,
    mcp_session,
    table_counts,
    tool_payload,
)

H3_TOOLS = {"forkos_evidence"}
H2_TOOLS = {
    "hot_memory_context",
    "hot_memory_list",
    "hot_memory_store",
    "hot_memory_update",
    "hot_memory_retire",
}


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


@pytest.fixture
def vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "H3TransportVault"
    path.mkdir()
    monkeypatch.setattr(settings, "obsidian_vault_path", str(path))
    monkeypatch.setattr(settings, "obsidian_vault_name", "H3TransportVault")
    return path


@pytest.fixture(autouse=True)
def reset_vault_index() -> AsyncIterator[None]:
    from app.integrations.obsidian.service import vault_index

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


async def _seed_world(session: AsyncSession, vault: Path) -> dict[str, str]:
    project_id = uuid4()
    todo_id = uuid4()
    session.add_all(
        [
            Entity(id=project_id, type="project", title="forkjob", search_text="Rust mimarisi"),
            Entity(id=todo_id, type="todo", title="Rust görevi", search_text=""),
        ]
    )
    await session.flush()
    session.add(
        Project(
            id=project_id,
            status="active",
            next_action="Mimariyi yaz",
            stack=["Rust", "PostgreSQL"],
            github_repo="f0rknturkoglu/forkjob",
        )
    )
    session.add(Todo(id=todo_id, status="open", priority=2))
    session.add(Link(from_id=todo_id, to_id=project_id, relation="belongs_to"))
    session.add(
        Event(
            entity_id=project_id,
            entity_type="project",
            verb="project.updated",
            payload={"stack": ["Rust"], "token": "should-not-leak"},
            occurred_at=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
        )
    )
    await session.commit()

    (vault / "20 Projects").mkdir(parents=True, exist_ok=True)
    (vault / "30 Knowledge").mkdir(parents=True, exist_ok=True)
    (vault / "20 Projects" / "forkjob.md").write_text(
        "---\n"
        f"forkos_id: {project_id}\n"
        "forkos_type: project\n"
        "forkos_updated_at: 2026-09-01T10:00:00+03:00\n"
        "---\n"
        "# forkjob\n\n## Teknoloji Kararı\n\nRust seçildi.\n\n[[Rust]]\n",
        encoding="utf-8",
    )
    (vault / "30 Knowledge" / "Rust.md").write_text(
        "# Rust\n\nRust bellek güvenliği sağlar.\n", encoding="utf-8"
    )
    refresh_vault_index()
    return {"project_id": str(project_id), "todo_id": str(todo_id)}


def uuid4():
    import uuid

    return uuid.uuid4()


EVIDENCE_ARGS = {"query": "Rust mimari kararı"}


async def test_tool_surface_and_annotations_over_transport() -> None:
    async with mcp_session() as session:
        tools = {tool.name: tool for tool in (await session.list_tools()).tools}

    assert len(tools) == 32
    assert set(tools) & H3_TOOLS == H3_TOOLS
    assert set(tools) & H2_TOOLS == H2_TOOLS

    wire = tools["forkos_evidence"].annotations.model_dump(by_alias=True, exclude_none=True)
    assert wire["readOnlyHint"] is True
    assert wire["destructiveHint"] is False
    assert wire["idempotentHint"] is True


async def test_schema_bounds_over_transport() -> None:
    async with mcp_session() as session:
        tools = {tool.name: tool for tool in (await session.list_tools()).tools}

    properties = tools["forkos_evidence"].input_schema["properties"]
    assert properties["query"]["minLength"] == 2
    assert properties["query"]["maxLength"] == MAX_QUERY_LENGTH
    assert properties["max_depth"]["minimum"] == 0
    assert properties["max_depth"]["maximum"] == 2
    assert properties["limit"]["minimum"] == 1
    assert properties["limit"]["maximum"] == 15
    assert properties["scope"]["enum"] == ["all", "operational", "knowledge"]


async def test_evidence_over_transport_is_read_only(
    db_session: AsyncSession, vault: Path
) -> None:
    world = await _seed_world(db_session, vault)
    db_before = await capture_db_content_fingerprint(db_session)
    vault_before = capture_vault_fingerprint(vault)
    counts_before = await table_counts(db_session)
    legacy_before = await legacy_notes_counts(db_session)

    async with mcp_session() as session:
        result = await session.call_tool(
            "forkos_evidence", {**EVIDENCE_ARGS, "entity_id": world["project_id"], "scope": "all"}
        )

    assert result.is_error is False, result.content
    payload = tool_payload(result)
    data = payload["data"]
    assert payload["source"] == "forkos"
    assert data["entity_seed"] == world["project_id"]
    assert data["sources_used"] == ["forkos", "f0rknbrain"]
    assert {item["source_type"] for item in data["evidence"]} <= {"entity", "event", "vault"}

    assert await capture_db_content_fingerprint(db_session) == db_before
    assert capture_vault_fingerprint(vault) == vault_before
    assert await table_counts(db_session) == counts_before
    assert await legacy_notes_counts(db_session) == legacy_before

    for model in (Entity, Link, Event):
        count = (await db_session.execute(select(func.count(model.id)))).scalar_one()
        expected = {"Entity": 2, "Link": 1, "Event": 1}[model.__name__]
        assert count == expected


async def test_transport_output_has_no_secret_leak(
    db_session: AsyncSession, vault: Path
) -> None:
    world = await _seed_world(db_session, vault)

    async with mcp_session() as session:
        result = await session.call_tool("forkos_evidence", {**EVIDENCE_ARGS, "entity_id": world["project_id"]})

    text = json.dumps(tool_payload(result))
    assert "should-not-leak" not in text
    assert "[REDACTED]" in text  # kanonik payload sanitizer'ı çalıştı


async def test_transport_rejects_out_of_range_and_invalid_input(
    db_session: AsyncSession, vault: Path
) -> None:
    """İki savunma katmanı AYRI kanıtlanır.

    - Şema ilk savunmadır: aralık/dize ihlalleri handler'a ULAŞMADAN reddedilir.
    - Çalışma zamanı otoritedir: şemadan geçen ama anlamsız girdiler (geçersiz
      UUID, çapasız zaman filtresi) servis katmanında reddedilir -- doğrudan
      çağıranlar şemayı atlayabildiği için bu katman gereklidir.
    """
    await _seed_world(db_session, vault)
    db_before = await capture_db_content_fingerprint(db_session)

    async with mcp_session() as session:
        too_long = await session.call_tool("forkos_evidence", {"query": "x" * (MAX_QUERY_LENGTH + 1)})
        invalid_scope = await session.call_tool("forkos_evidence", {"query": "Rust", "scope": "everything"})
        bad_uuid = await session.call_tool("forkos_evidence", {"query": "Rust", "entity_id": "not-a-uuid"})
        missing_seed = await session.call_tool(
            "forkos_evidence", {"query": "Rust", "since": "2026-09-01T00:00:00Z"}
        )

    for result in (too_long, invalid_scope, bad_uuid, missing_seed):
        assert result.is_error is True
        assert result.content

    # Şema katmanı (ilk savunma)
    assert "200 characters" in too_long.content[0].text
    # Çalışma zamanı katmanı (otorite)
    assert "INVALID_UUID" in bad_uuid.content[0].text
    assert "TIME_FILTER_REQUIRES_ENTITY_SEED" in missing_seed.content[0].text
    assert await capture_db_content_fingerprint(db_session) == db_before


async def test_transport_output_is_deterministic(db_session: AsyncSession, vault: Path) -> None:
    world = await _seed_world(db_session, vault)

    async with mcp_session() as session:
        first = tool_payload(
            await session.call_tool("forkos_evidence", {**EVIDENCE_ARGS, "entity_id": world["project_id"]})
        )
        second = tool_payload(
            await session.call_tool("forkos_evidence", {**EVIDENCE_ARGS, "entity_id": world["project_id"]})
        )

    assert first["data"] == second["data"]


async def test_transport_enforces_character_budget(db_session: AsyncSession, vault: Path) -> None:
    world = await _seed_world(db_session, vault)
    for index in range(12):
        (vault / "30 Knowledge" / f"Not-{index:02d}.md").write_text(
            f"# Rust notu {index}\n\nRust mimari kararı. " + ("dolgu " * 400), encoding="utf-8"
        )
    refresh_vault_index()

    async with mcp_session() as session:
        payload = tool_payload(
            await session.call_tool(
                "forkos_evidence",
                {**EVIDENCE_ARGS, "entity_id": world["project_id"], "limit": 15},
            )
        )

    data = payload["data"]
    assert len(data["evidence"]) <= 15
    assert sum(len(item["excerpt"]) for item in data["evidence"]) <= MAX_TOTAL_EVIDENCE_CHARS
    assert data["truncated"] is True


async def test_transport_returns_canonical_direction_in_relation_path(
    db_session: AsyncSession, vault: Path
) -> None:
    """§95: kanonik Link yönü gerçek `/mcp` yanıtında da korunur."""
    world = await _seed_world(db_session, vault)

    async with mcp_session() as session:
        payload = tool_payload(
            await session.call_tool(
                "forkos_evidence",
                {**EVIDENCE_ARGS, "entity_id": world["project_id"], "scope": "operational"},
            )
        )

    item = next(
        entry for entry in payload["data"]["evidence"] if entry["source_id"] == world["todo_id"]
    )
    hop = item["relation_path"][0]

    assert hop["kind"] == "entity_link"
    assert hop["relation"] == "belongs_to"
    assert hop["direction"] == "incoming"
    assert hop["from_ref"] == f"entity:{world['project_id']}"
    assert hop["to_ref"] == f"entity:{world['todo_id']}"


async def test_transport_rejects_out_of_range_bounds_before_handler(
    db_session: AsyncSession, vault: Path
) -> None:
    """§42: gerçek MCP'de şema ilk savunmadır; aralık dışı sınır handler'a ulaşmaz."""
    await _seed_world(db_session, vault)

    async with mcp_session() as session:
        too_deep = await session.call_tool("forkos_evidence", {"query": "Rust", "max_depth": 99})
        too_many = await session.call_tool("forkos_evidence", {"query": "Rust", "limit": 10000})

    assert too_deep.is_error is True
    assert too_many.is_error is True
    assert "2" in too_deep.content[0].text
    assert "15" in too_many.content[0].text
