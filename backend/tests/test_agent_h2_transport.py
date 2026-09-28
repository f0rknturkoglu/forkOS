"""H2 — gerçek `/mcp` taşıması üzerinden sıcak hafıza sözleşmesi.

H2 yalnızca doğrudan Python çağrılarıyla kanıtlanamaz: kısmi güncellemenin
verilmeyen alanları koruması, açık `null`un temizlemesi ve revizyon
önkoşulunun taşıma katmanından geçmesi gerekir.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.models import Entity
from app.db import SessionLocal
from app.integrations.obsidian import hot_memory as storage
from tests.agent_test_utils import (
    capture_db_content_fingerprint,
    capture_vault_fingerprint,
    forbid_outbound_network,  # noqa: F401  (autouse: H2 de yereldir)
    legacy_notes_counts,
    mcp_session,
    tool_payload,
    tool_receipt,
)

MEMORY_DIR = "90 Agent/Memory"

H2_TOOL_NAMES = {
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
    path = tmp_path / "H2TransportVault"
    path.mkdir()
    monkeypatch.setattr(settings, "obsidian_vault_path", str(path))
    monkeypatch.setattr(settings, "obsidian_vault_name", "H2TransportVault")
    return path


STORE_ARGS = {
    "kind": "preference",
    "title": "Planning style",
    "text": "Prefers project-level plans over hourly schedules.",
    "source_mode": "explicit_user",
}


async def _store(session, **overrides) -> dict:
    args = {**STORE_ARGS, **overrides}
    result = await session.call_tool("hot_memory_store", args)
    return tool_receipt(result)


def _memory_files(vault: Path) -> list[Path]:
    directory = vault / MEMORY_DIR
    return sorted(directory.glob("*.md")) if directory.is_dir() else []


async def _current_revision(vault: Path, memory_id: str) -> str:
    snapshot = storage.scan_memories(vault.resolve())
    record = storage.find_memory(snapshot, memory_id)
    assert record is not None
    return record.revision


# ---------------------------------------------------------------------------
# §117 — yüzey ve okuma turları
# ---------------------------------------------------------------------------


async def test_mcp_tool_surface_is_29() -> None:
    async with mcp_session() as session:
        tools = {t.name: t for t in (await session.list_tools()).tools}
    assert len(tools) == 36
    assert set(tools) >= H2_TOOL_NAMES


async def test_h2_annotations_over_the_wire() -> None:
    async with mcp_session() as session:
        tools = {t.name: t for t in (await session.list_tools()).tools}

    for name in ("hot_memory_context", "hot_memory_list"):
        annotations = tools[name].annotations
        assert annotations.read_only_hint is True, name
        assert annotations.destructive_hint is False, name
        assert annotations.idempotent_hint is True, name

    for name in H2_TOOL_NAMES - {"hot_memory_context", "hot_memory_list"}:
        annotations = tools[name].annotations
        assert annotations.read_only_hint is False, name
        assert annotations.destructive_hint is False, name
    assert tools["hot_memory_store"].annotations.idempotent_hint is False
    assert tools["hot_memory_update"].annotations.idempotent_hint is True
    assert tools["hot_memory_retire"].annotations.idempotent_hint is True


async def test_context_and_list_read_over_transport(db_session: AsyncSession, vault: Path) -> None:
    async with mcp_session() as session:
        stored = await _store(session, tags=["planning"])
        context = tool_payload(await session.call_tool("hot_memory_context", {}))["data"]
        listed = tool_payload(
            await session.call_tool("hot_memory_list", {"effective_status": "all"})
        )["data"]

    assert context["returned_total"] == 1
    assert [item["memory_id"] for item in context["preferences"]] == [stored["target_id"]]
    assert context["invalid_count"] == 0
    assert context["truncated"] is False

    assert [item["memory_id"] for item in listed["items"]] == [stored["target_id"]]
    assert listed["items"][0]["tags"] == ["planning"]
    assert listed["items"][0]["relative_path"] == f"{MEMORY_DIR}/{stored['target_id']}.md"


# ---------------------------------------------------------------------------
# §101/§102 — store ve tekrar
# ---------------------------------------------------------------------------


async def test_store_over_transport_writes_one_file(db_session: AsyncSession, vault: Path) -> None:
    db_before = await capture_db_content_fingerprint(db_session)
    legacy_before = await legacy_notes_counts(db_session)

    async with mcp_session() as session:
        receipt = await _store(session)

    assert receipt["tool"] == "hot_memory_store"
    assert receipt["status"] == "executed"
    assert receipt["target_type"] == "hot_memory"
    assert len(_memory_files(vault)) == 1
    # Gövde makbuza kopyalanmaz.
    assert "hourly schedules" not in json.dumps(receipt)
    assert await capture_db_content_fingerprint(db_session) == db_before
    assert await legacy_notes_counts(db_session) == legacy_before


async def test_duplicate_store_over_transport_is_noop(
    db_session: AsyncSession, vault: Path
) -> None:
    async with mcp_session() as session:
        first = await _store(session)
        vault_before = capture_vault_fingerprint(vault)
        second = await _store(session, title="Farklı başlık")

    assert first["status"] == "executed"
    assert second["status"] == "noop"
    assert second["target_id"] == first["target_id"]
    assert len(_memory_files(vault)) == 1
    assert capture_vault_fingerprint(vault) == vault_before


# ---------------------------------------------------------------------------
# §104 — omitted vs null (gerçek taşıma)
# ---------------------------------------------------------------------------


async def test_update_omitted_field_preserved_and_null_clears_over_transport(
    db_session: AsyncSession, vault: Path
) -> None:
    future = (datetime.now(UTC) + timedelta(days=45)).isoformat()
    async with mcp_session() as session:
        created = await _store(session, expires_at=future, tags=["a"])
        revision = await _current_revision(vault, created["target_id"])

        # Yalnızca başlık gönderilir → süre ve etiketler KORUNUR.
        updated = tool_receipt(
            await session.call_tool(
                "hot_memory_update",
                {
                    "memory_id": created["target_id"],
                    "expected_revision": revision,
                    "title": "Yeni başlık",
                },
            )
        )
        assert updated["status"] == "executed"

        snapshot = storage.scan_memories(vault.resolve())
        record = storage.find_memory(snapshot, created["target_id"])
        assert record is not None
        assert record.expires_at == future
        assert record.tags == ["a"]

        # Açık null → süre TEMİZLENİR.
        cleared = tool_receipt(
            await session.call_tool(
                "hot_memory_update",
                {
                    "memory_id": created["target_id"],
                    "expected_revision": record.revision,
                    "expires_at": None,
                },
            )
        )
        assert cleared["status"] == "executed"
        assert cleared["after"]["expires_at"] is None

        snapshot = storage.scan_memories(vault.resolve())
        record = storage.find_memory(snapshot, created["target_id"])
        assert record is not None and record.expires_at is None
        assert record.tags == ["a"]


# ---------------------------------------------------------------------------
# §105 — bayat revizyon
# ---------------------------------------------------------------------------


async def test_stale_revision_over_transport_fails_closed(
    db_session: AsyncSession, vault: Path
) -> None:
    async with mcp_session() as session:
        created = await _store(session)
        revision = await _current_revision(vault, created["target_id"])

    path = vault / f"{MEMORY_DIR}/{created['target_id']}.md"
    human = path.read_text(encoding="utf-8").replace("hourly schedules", "elle düzenlendi")
    path.write_text(human, encoding="utf-8")
    vault_before = capture_vault_fingerprint(vault)
    db_before = await capture_db_content_fingerprint(db_session)

    async with mcp_session() as session:
        result = await session.call_tool(
            "hot_memory_update",
            {
                "memory_id": created["target_id"],
                "expected_revision": revision,
                "title": "Yazılmamalı",
            },
        )

    assert result.is_error is True
    assert "HOT_MEMORY_STALE" in result.content[0].text
    assert "Traceback" not in result.content[0].text
    assert path.read_text(encoding="utf-8") == human
    assert capture_vault_fingerprint(vault) == vault_before
    assert await capture_db_content_fingerprint(db_session) == db_before


# ---------------------------------------------------------------------------
# §106 — emeklilik
# ---------------------------------------------------------------------------


async def test_retire_over_transport_keeps_file(db_session: AsyncSession, vault: Path) -> None:
    async with mcp_session() as session:
        created = await _store(session)
        revision = await _current_revision(vault, created["target_id"])

        retired = tool_receipt(
            await session.call_tool(
                "hot_memory_retire",
                {
                    "memory_id": created["target_id"],
                    "expected_revision": revision,
                    "reason": "artık geçerli değil",
                },
            )
        )
        assert retired["status"] == "executed"
        assert retired["after"]["status"] == "retired"

        context = tool_payload(await session.call_tool("hot_memory_context", {}))["data"]
        assert context["returned_total"] == 0

        listed = tool_payload(
            await session.call_tool("hot_memory_list", {"effective_status": "retired"})
        )["data"]
        assert [item["memory_id"] for item in listed["items"]] == [created["target_id"]]

        # İkinci emeklilik: noop, yeniden yazma yok.
        vault_before = capture_vault_fingerprint(vault)
        revision = await _current_revision(vault, created["target_id"])
        again = tool_receipt(
            await session.call_tool(
                "hot_memory_retire",
                {"memory_id": created["target_id"], "expected_revision": revision},
            )
        )
        assert again["status"] == "noop"
        assert capture_vault_fingerprint(vault) == vault_before

    assert (vault / f"{MEMORY_DIR}/{created['target_id']}.md").is_file()


# ---------------------------------------------------------------------------
# §113/§114 — politika ve ilgili kayıt
# ---------------------------------------------------------------------------


async def test_secret_rejected_over_transport(db_session: AsyncSession, vault: Path) -> None:
    vault_before = capture_vault_fingerprint(vault)
    async with mcp_session() as session:
        result = await session.call_tool(
            "hot_memory_store",
            {**STORE_ARGS, "text": "api_key=sk-abcdefghijklmnopqrstuvwx"},
        )
    assert result.is_error is True
    assert "HOT_MEMORY_POLICY_REJECTED" in result.content[0].text
    assert capture_vault_fingerprint(vault) == vault_before


async def test_related_entity_validated_over_transport(
    db_session: AsyncSession, vault: Path
) -> None:
    project_id = uuid.uuid4()
    db_session.add(Entity(id=project_id, type="project", title="Proje", search_text=""))
    await db_session.commit()
    db_before = await capture_db_content_fingerprint(db_session)

    async with mcp_session() as session:
        ok = await _store(session, related_forkos_ids=[str(project_id)])
        assert ok["status"] == "executed"

        bad = await session.call_tool(
            "hot_memory_store",
            {
                **STORE_ARGS,
                "title": "Başka",
                "text": "Başka metin",
                "related_forkos_ids": [str(uuid.uuid4())],
            },
        )
        assert bad.is_error is True
        assert "INVALID_RELATED_ENTITY" in bad.content[0].text

    assert await capture_db_content_fingerprint(db_session) == db_before


# ---------------------------------------------------------------------------
# §127 — Vault yok
# ---------------------------------------------------------------------------


async def test_vault_unavailable_over_transport(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "obsidian_vault_path", "")
    async with mcp_session() as session:
        for tool, args in (
            ("hot_memory_context", {}),
            ("hot_memory_list", {}),
            ("hot_memory_store", STORE_ARGS),
        ):
            result = await session.call_tool(tool, args)
            assert result.is_error is True, tool
            assert "HOT_MEMORY_UNAVAILABLE" in result.content[0].text


# ---------------------------------------------------------------------------
# H2.2 §25/§27 — sorgu sınırı şemada ve taşımada
# ---------------------------------------------------------------------------


def _max_lengths(schema: object) -> list[int]:
    """Bir JSON şema alt ağacındaki TÜM `maxLength` değerlerini toplar."""
    found: list[int] = []
    if isinstance(schema, dict):
        if isinstance(schema.get("maxLength"), int):
            found.append(schema["maxLength"])
        for value in schema.values():
            found.extend(_max_lengths(value))
    elif isinstance(schema, list):
        for item in schema:
            found.extend(_max_lengths(item))
    return found


async def test_h2_transport_query_schema_is_bounded(db_session: AsyncSession) -> None:
    async with mcp_session() as session:
        tools = {t.name: t for t in (await session.list_tools()).tools}

    query_schema = tools["hot_memory_list"].input_schema["properties"]["query"]

    assert 200 in _max_lengths(query_schema)
    assert all(bound <= 200 for bound in _max_lengths(query_schema))


async def test_h2_transport_rejects_oversized_query(
    db_session: AsyncSession, vault: Path
) -> None:
    created = await _store_via_service(db_session)
    vault_before = capture_vault_fingerprint(vault)
    db_before = await capture_db_content_fingerprint(db_session)

    async with mcp_session() as session:
        result = await session.call_tool("hot_memory_list", {"query": "a" * 201})

    assert result.is_error is True
    # Şema ilk savunmadır; hiçbir mutasyon olmamalı.
    assert capture_vault_fingerprint(vault) == vault_before
    assert await capture_db_content_fingerprint(db_session) == db_before
    assert created["target_id"]


async def _store_via_service(session: AsyncSession) -> dict:
    from app.integrations.agent import hot_memory as hm
    from app.integrations.agent.hot_memory_models import HotMemoryStoreIn

    receipt = await hm.store_memory(
        session,
        HotMemoryStoreIn(
            kind="preference",
            title="Sorgu sınırı",
            text="Sorgu sınırı gövdesi.",
            source_mode="explicit_user",
        ),
        request_id="t",
    )
    return {"target_id": receipt.target_id}
