"""H3 — genel yüzey, anotasyon, şema ve hata sözleşmeleri.

H3'ün sözleşmesi üç yerde kanıtlanır: MCP yüzeyi (tek yeni araç, 25 toplam),
şema sınırları (ilk savunma) ve çalışma zamanı doğrulaması (otorite).
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.models import Entity
from app.db import SessionLocal
from app.integrations.agent import capabilities
from app.integrations.agent import evidence as ev
from app.integrations.agent.evidence_models import (
    DEFAULT_EVIDENCE_DEPTH,
    DEFAULT_EVIDENCE_LIMIT,
    MAX_EVIDENCE_DEPTH,
    MAX_EVIDENCE_LIMIT,
    MAX_QUERY_LENGTH,
    EvidenceBundle,
    EvidenceItem,
)
from app.integrations.agent.mcp import mcp_server
from tests.agent_test_utils import (
    capture_db_content_fingerprint,
    capture_vault_fingerprint,
    forbid_outbound_network,  # noqa: F401  (autouse: H3 de dış ağ kullanmaz)
    legacy_notes_counts,
)

H0_TOOLS = capabilities.family_tools("H0")
H1_TOOLS = capabilities.family_tools("H1")
H2_TOOLS = capabilities.family_tools("H2")
H3_TOOLS = capabilities.family_tools("H3")
H4_TOOLS = capabilities.family_tools("H4")
H5_TOOLS = capabilities.family_tools("H5")
H6_TOOLS = capabilities.family_tools("H6")
H7_TOOLS = capabilities.family_tools("H7")

#: Aile adları TEK kaynaktan (`capabilities`) gelir; burada yinelenmez.
ALL_FAMILY_TOOLS = H0_TOOLS | H1_TOOLS | H2_TOOLS | H3_TOOLS | H4_TOOLS | H5_TOOLS | H6_TOOLS | H7_TOOLS

#: Yasak alan adları: sahte kesinlik ve yanıt üretimi sözleşmeye SIZAMAZ.
FORBIDDEN_FIELD_NAMES = (
    "confidence",
    "probability",
    "truth_score",
    "certainty",
    "answer",
    "summary_answer",
    "conclusion",
    "recommendation",
)


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


@pytest.fixture
def vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "H3ContractVault"
    path.mkdir()
    monkeypatch.setattr(settings, "obsidian_vault_path", str(path))
    monkeypatch.setattr(settings, "obsidian_vault_name", "H3ContractVault")
    return path


async def _tools() -> dict:
    return {tool.name: tool for tool in await mcp_server.list_tools()}


def _property_names(schema: dict) -> set[str]:
    """Şema ağacındaki TÜM property adlarını toplar (iç içe dahil)."""
    names: set[str] = set()

    def walk(node: object) -> None:
        if isinstance(node, dict):
            properties = node.get("properties")
            if isinstance(properties, dict):
                names.update(properties.keys())
                for value in properties.values():
                    walk(value)
            for key in ("items", "anyOf", "allOf", "oneOf", "$defs", "definitions", "additionalProperties"):
                if key in node:
                    walk(node[key])
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(schema)
    return names


# ---------------------------------------------------------------------------
# Genel yüzey
# ---------------------------------------------------------------------------


async def test_tool_surface_is_exactly_26_with_one_h3_tool() -> None:
    tools = await _tools()
    assert len(tools) == 31
    assert set(tools) & H3_TOOLS == H3_TOOLS
    assert set(tools) == ALL_FAMILY_TOOLS == capabilities.all_tools()
    assert len(H0_TOOLS) == 8 and len(H1_TOOLS) == 11 and len(H2_TOOLS) == 5
    assert len(ALL_FAMILY_TOOLS) == capabilities.tool_count() == 31


async def test_h0_h1_h2_tools_are_unchanged() -> None:
    tools = await _tools()
    assert tools["forkos_search"].annotations.read_only_hint is True
    assert tools["forkos_todo_create"].annotations.read_only_hint is False
    assert tools["hot_memory_store"].annotations.read_only_hint is False
    assert tools["hot_memory_context"].annotations.read_only_hint is True


async def test_h3_annotations_mark_read_only() -> None:
    tool = (await _tools())["forkos_evidence"]
    wire = tool.annotations.model_dump(by_alias=True, exclude_none=True)
    assert wire["readOnlyHint"] is True
    assert wire["destructiveHint"] is False
    assert wire["idempotentHint"] is True


async def test_h3_input_schema_exposes_bounds() -> None:
    schema = (await _tools())["forkos_evidence"].input_schema
    properties = schema["properties"]

    assert properties["query"]["minLength"] == 2
    assert properties["query"]["maxLength"] == MAX_QUERY_LENGTH
    assert properties["max_depth"]["minimum"] == 0
    assert properties["max_depth"]["maximum"] == MAX_EVIDENCE_DEPTH
    assert properties["limit"]["minimum"] == 1
    assert properties["limit"]["maximum"] == MAX_EVIDENCE_LIMIT
    assert properties["scope"]["enum"] == ["all", "operational", "knowledge"]
    assert schema["required"] == ["query"]


# ---------------------------------------------------------------------------
# Kanıt sözleşmesi
# ---------------------------------------------------------------------------


def test_evidence_contract_has_no_confidence_or_answer_fields() -> None:
    names = _property_names(EvidenceItem.model_json_schema()) | _property_names(
        EvidenceBundle.model_json_schema()
    )
    for forbidden in FORBIDDEN_FIELD_NAMES:
        assert forbidden not in names


def test_source_type_union_is_exactly_entity_event_vault() -> None:
    schema = EvidenceItem.model_json_schema()
    assert schema["properties"]["source_type"]["enum"] == ["entity", "event", "vault"]


def test_bundle_has_no_hot_memory_source() -> None:
    dumped = json.dumps(EvidenceBundle.model_json_schema())
    assert "hot_memory" not in dumped
    assert "conversation" not in dumped
    assert "inference" not in dumped


# ---------------------------------------------------------------------------
# Girdi doğrulaması (otorite çalışma zamanındadır)
# ---------------------------------------------------------------------------


async def test_blank_query_is_rejected(db_session: AsyncSession, vault: Path) -> None:
    with pytest.raises(ev.EvidenceError, match="INVALID_QUERY"):
        await ev.retrieve_evidence(db_session, query="   ")


async def test_short_and_long_queries_are_rejected(db_session: AsyncSession, vault: Path) -> None:
    with pytest.raises(ev.EvidenceError, match="QUERY_TOO_SHORT"):
        await ev.retrieve_evidence(db_session, query="a")
    with pytest.raises(ev.EvidenceError, match="QUERY_TOO_LONG"):
        await ev.retrieve_evidence(db_session, query="x" * (MAX_QUERY_LENGTH + 1))


async def test_invalid_scope_is_rejected(db_session: AsyncSession, vault: Path) -> None:
    with pytest.raises(ev.EvidenceError, match="INVALID_SCOPE"):
        await ev.retrieve_evidence(db_session, query="rust", scope="everything")  # type: ignore[arg-type]


async def test_invalid_uuid_and_missing_entity(db_session: AsyncSession, vault: Path) -> None:
    with pytest.raises(ev.EvidenceError, match="INVALID_UUID"):
        await ev.retrieve_evidence(db_session, query="rust", entity_id="not-a-uuid")
    with pytest.raises(ev.EvidenceError, match="ENTITY_NOT_FOUND"):
        await ev.retrieve_evidence(db_session, query="rust", entity_id=str(uuid.uuid4()))


async def test_time_range_validation(db_session: AsyncSession, vault: Path) -> None:
    seed = Entity(type="project", title="TimeSeed", search_text="")
    db_session.add(seed)
    await db_session.flush()

    with pytest.raises(ev.EvidenceError, match="INVALID_TIME_RANGE"):
        await ev.retrieve_evidence(db_session, query="rust", entity_id=str(seed.id), since="dun")
    with pytest.raises(ev.EvidenceError, match="INVALID_TIME_RANGE"):
        await ev.retrieve_evidence(
            db_session, query="rust", entity_id=str(seed.id), since="2026-09-01T00:00:00"
        )
    with pytest.raises(ev.EvidenceError, match="INVALID_TIME_RANGE"):
        await ev.retrieve_evidence(
            db_session,
            query="rust",
            entity_id=str(seed.id),
            since="2026-09-10T00:00:00Z",
            until="2026-09-01T00:00:00Z",
        )


async def test_time_filter_without_seed_is_rejected(db_session: AsyncSession, vault: Path) -> None:
    with pytest.raises(ev.EvidenceError, match="TIME_FILTER_REQUIRES_ENTITY_SEED"):
        await ev.retrieve_evidence(db_session, query="rust", since="2026-09-01T00:00:00Z")


async def test_frozen_legacy_entity_is_refused(db_session: AsyncSession, vault: Path) -> None:
    legacy = Entity(type="note", title="Eski not", search_text="")
    db_session.add(legacy)
    await db_session.flush()

    with pytest.raises(ev.EvidenceError, match="FROZEN_ENTITY_UNAVAILABLE"):
        await ev.retrieve_evidence(db_session, query="eski not", entity_id=str(legacy.id))


async def test_rejected_request_changes_nothing(
    db_session: AsyncSession, vault: Path
) -> None:
    (vault / "30 Knowledge").mkdir()
    (vault / "30 Knowledge" / "Rust.md").write_text("# Rust\n", encoding="utf-8")
    db_before = await capture_db_content_fingerprint(db_session)
    vault_before = capture_vault_fingerprint(vault)
    legacy_before = await legacy_notes_counts(db_session)

    for kwargs in (
        {"query": "a"},
        {"query": "rust", "scope": "nope"},
        {"query": "rust", "entity_id": "not-a-uuid"},
        {"query": "rust", "since": "2026-09-01"},
    ):
        with pytest.raises(ev.EvidenceError):
            await ev.retrieve_evidence(db_session, **kwargs)  # type: ignore[arg-type]

    assert await capture_db_content_fingerprint(db_session) == db_before
    assert capture_vault_fingerprint(vault) == vault_before
    assert await legacy_notes_counts(db_session) == legacy_before


# ---------------------------------------------------------------------------
# Sınırlar ve determinizm
# ---------------------------------------------------------------------------


async def _seed_for_bounds(db_session: AsyncSession) -> Entity:
    seed = Entity(type="project", title="BoundSeed", search_text="")
    db_session.add(seed)
    await db_session.flush()
    return seed


async def test_direct_service_rejects_depth_below_min(
    db_session: AsyncSession, vault: Path
) -> None:
    seed = await _seed_for_bounds(db_session)
    with pytest.raises(ev.EvidenceError, match="INVALID_MAX_DEPTH"):
        await ev.retrieve_evidence(db_session, query="bound", entity_id=str(seed.id), max_depth=-1)


async def test_direct_service_rejects_depth_above_max(
    db_session: AsyncSession, vault: Path
) -> None:
    """§39/§135: aralık dışı derinlik KIRPILMAZ; sessizce 2'ye düşürülmez."""
    seed = await _seed_for_bounds(db_session)
    with pytest.raises(ev.EvidenceError, match="INVALID_MAX_DEPTH"):
        await ev.retrieve_evidence(db_session, query="bound", entity_id=str(seed.id), max_depth=3)


async def test_direct_service_rejects_limit_below_min(
    db_session: AsyncSession, vault: Path
) -> None:
    seed = await _seed_for_bounds(db_session)
    with pytest.raises(ev.EvidenceError, match="INVALID_LIMIT"):
        await ev.retrieve_evidence(db_session, query="bound", entity_id=str(seed.id), limit=0)


async def test_direct_service_rejects_limit_above_max(
    db_session: AsyncSession, vault: Path
) -> None:
    """§39/§135: `limit=16` reddedilir; sessizce 15'e düşürülmez."""
    seed = await _seed_for_bounds(db_session)
    with pytest.raises(ev.EvidenceError, match="INVALID_LIMIT"):
        await ev.retrieve_evidence(db_session, query="bound", entity_id=str(seed.id), limit=MAX_EVIDENCE_LIMIT + 1)


async def test_rejected_bounds_perform_no_retrieval_work(
    db_session: AsyncSession, vault: Path
) -> None:
    """Geçersiz sınır pahalı işe GİRMEDEN reddedilir ve hiçbir şey değiştirmez."""
    (vault / "30 Knowledge").mkdir()
    (vault / "30 Knowledge" / "Rust.md").write_text("# Rust\n", encoding="utf-8")
    seed = await _seed_for_bounds(db_session)
    db_before = await capture_db_content_fingerprint(db_session)
    vault_before = capture_vault_fingerprint(vault)

    for kwargs in ({"max_depth": 3}, {"limit": 16}, {"max_depth": -1}, {"limit": 0}):
        with pytest.raises(ev.EvidenceError):
            await ev.retrieve_evidence(
                db_session, query="bound", entity_id=str(seed.id), **kwargs  # type: ignore[arg-type]
            )

    assert await capture_db_content_fingerprint(db_session) == db_before
    assert capture_vault_fingerprint(vault) == vault_before


async def test_query_only_forces_depth_zero(db_session: AsyncSession, vault: Path) -> None:
    entity = Entity(type="project", title="Rust CLI", search_text="rust cli")
    db_session.add(entity)
    await db_session.flush()

    bundle = await ev.retrieve_evidence(db_session, query="Rust", max_depth=2, scope="operational")

    assert bundle.entity_seed is None
    assert all(ref.expanded is False for ref in bundle.resolved_entities)
    graph_step = next(step for step in bundle.retrieval_trace if step.stage == "graph")
    assert "skipped" in graph_step.description
    assert graph_step.accepted == 0


async def test_default_bounds_are_documented_values() -> None:
    assert DEFAULT_EVIDENCE_DEPTH == 1
    assert DEFAULT_EVIDENCE_LIMIT == 12
