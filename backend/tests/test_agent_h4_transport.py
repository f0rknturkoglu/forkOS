"""H4 — gerçek `/mcp` taşıması: yüzey, doğrulama, gizlilik ve değişmezlik.

Sağlayıcı betiklidir (Ollama gerekmez) ama taşıma, oturum ve hata zarfı
GERÇEKTİR. H4'ün veritabanına ve kasa'ya dokunmadığı burada kanıtlanır.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.models import Entity, Event, Link
from app.db import SessionLocal
from app.integrations.local_cognition import models as lc
from app.integrations.local_cognition import service as lc_svc
from tests.agent_test_utils import (
    capture_db_content_fingerprint,
    capture_vault_fingerprint,
    forbid_outbound_network,  # noqa: F401  (autouse: H4 yalnız loopback kullanır)
    legacy_notes_counts,
    mcp_session,
    table_counts,
    tool_payload,
)
from tests.h4_test_provider import ScriptedProvider

CLASSIFY_ARGS = {
    "lane": "classify",
    "text": "29 Kasım ALES sınavı var.",
    "labels": ["calendar_event", "deadline", "task", "knowledge"],
    "classification_goal": "Metni en uygun kategoriye ata.",
}
CALENDAR_TEXT = (
    "Kayıt yenileme: 1 - 5 Eylül 2026\n"
    "Derslerin başlangıcı: 21 Eylül 2026\n"
)
EXTRACT_ARGS = {
    "lane": "structured_extract",
    "text": CALENDAR_TEXT,
    "contract": "academic_calendar_v1",
}
REWRITE_ARGS = {
    "lane": "query_rewrite",
    "text": "forkjobda rustu neden seçtik",
    "protected_terms": ["forkjob", "Rust"],
}


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


@pytest.fixture
def vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "H4Vault"
    path.mkdir()
    (path / "30 Knowledge").mkdir()
    (path / "30 Knowledge" / "Rust.md").write_text("# Rust\n\nRust notu.\n", encoding="utf-8")
    monkeypatch.setattr(settings, "obsidian_vault_path", str(path))
    monkeypatch.setattr(settings, "obsidian_vault_name", "H4Vault")
    return path


@pytest.fixture
def h4_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    """H4 açık ve bir yerel model yapılandırılmış (sağlayıcı betikli)."""
    monkeypatch.setattr(settings, "h4_enabled", True)
    monkeypatch.setattr(settings, "h4_small_model", "small-model")
    monkeypatch.setattr(settings, "h4_medium_model", "medium-model")
    monkeypatch.setattr(settings, "h4_ollama_base_url", "http://127.0.0.1:11434")


def _patch_provider(monkeypatch: pytest.MonkeyPatch, provider: ScriptedProvider) -> None:
    """Aracın içindeki sağlayıcı kurulumunu betikli sağlayıcıyla değiştirir."""
    monkeypatch.setattr(lc_svc, "OllamaProvider", lambda *args, **kwargs: provider)


async def test_surface_and_annotations_over_transport() -> None:
    async with mcp_session() as session:
        tools = {tool.name: tool for tool in (await session.list_tools()).tools}

    assert len(tools) == 26
    wire = tools["forkos_local_cognition"].annotations.model_dump(by_alias=True, exclude_none=True)
    assert wire["readOnlyHint"] is True
    assert wire["destructiveHint"] is False
    assert wire["idempotentHint"] is True


async def test_schema_bounds_over_transport() -> None:
    async with mcp_session() as session:
        tools = {tool.name: tool for tool in (await session.list_tools()).tools}

    properties = tools["forkos_local_cognition"].input_schema["properties"]
    assert properties["lane"]["enum"] == ["classify", "structured_extract", "query_rewrite"]
    assert properties["text"]["maxLength"] == lc.MAX_TEXT_CHARS
    assert properties["labels"]["anyOf"][0]["maxItems"] == lc.MAX_LABELS
    assert not (set(properties) & {"model", "base_url", "temperature", "provider"})


async def test_classify_succeeds_over_transport(
    h4_ready: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = ScriptedProvider(responses=['{"label": "deadline"}'])
    _patch_provider(monkeypatch, provider)

    async with mcp_session() as session:
        result = await session.call_tool("forkos_local_cognition", CLASSIFY_ARGS)

    assert result.is_error is False, result.content
    payload = tool_payload(result)
    assert payload["status"] == "success"
    assert payload["result"]["label"] == "deadline"
    assert payload["route_decision"]["execution_boundary"] == "local_loopback"
    assert provider.call_count == 1


async def test_structured_extraction_succeeds_over_transport(
    h4_ready: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = ScriptedProvider(
        responses=[
            json.dumps(
                {
                    "events": [
                        {
                            "title": "Kayıt yenileme",
                            "category": "registration",
                            "date_text": "1 - 5 Eylül 2026",
                            "start_date": "2026-09-01",
                            "end_date": "2026-09-05",
                            "source_excerpt": "Kayıt yenileme: 1 - 5 Eylül 2026",
                        }
                    ]
                }
            )
        ]
    )
    _patch_provider(monkeypatch, provider)

    async with mcp_session() as session:
        result = await session.call_tool("forkos_local_cognition", EXTRACT_ARGS)

    assert result.is_error is False, result.content
    payload = tool_payload(result)
    assert payload["status"] == "success"
    assert payload["result"]["contract"] == "academic_calendar_v1"
    assert payload["result"]["items"][0]["category"] == "registration"


async def test_query_rewrite_succeeds_over_transport(
    h4_ready: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = ScriptedProvider(
        responses=['{"rewritten_query": "forkjob Rust mimari kararı"}']
    )
    _patch_provider(monkeypatch, provider)

    async with mcp_session() as session:
        result = await session.call_tool("forkos_local_cognition", REWRITE_ARGS)

    payload = tool_payload(result)
    assert payload["status"] == "success"
    assert "forkjob" in payload["result"]["rewritten_query"]
    assert "Rust" in payload["result"]["rewritten_query"]


async def test_incompatible_lane_arguments_are_rejected_over_transport(
    h4_ready: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Şemadan geçen ama anlamsız çağrı çalışma zamanında reddedilir (§42)."""
    provider = ScriptedProvider(responses=['{"label": "task"}'])
    _patch_provider(monkeypatch, provider)

    async with mcp_session() as session:
        result = await session.call_tool(
            "forkos_local_cognition", {**CLASSIFY_ARGS, "contract": "academic_calendar_v1"}
        )

    assert result.is_error is True
    assert "INVALID_ARGUMENT" in result.content[0].text
    assert provider.call_count == 0


async def test_unsupported_lane_is_rejected_before_the_handler(
    h4_ready: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = ScriptedProvider(responses=['{"label": "task"}'])
    _patch_provider(monkeypatch, provider)

    async with mcp_session() as session:
        result = await session.call_tool("forkos_local_cognition", {"lane": "reason", "text": "x y"})

    assert result.is_error is True
    assert provider.call_count == 0


async def test_disabled_h4_reports_cleanly_over_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "h4_enabled", False)
    provider = ScriptedProvider(responses=['{"label": "task"}'])
    _patch_provider(monkeypatch, provider)

    async with mcp_session() as session:
        result = await session.call_tool("forkos_local_cognition", CLASSIFY_ARGS)

    assert result.is_error is True
    assert "H4_DISABLED" in result.content[0].text
    assert provider.call_count == 0


async def test_cloud_endpoint_is_rejected_over_transport(
    h4_ready: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "h4_ollama_base_url", "https://api.somecloud.com")
    provider = ScriptedProvider(responses=['{"label": "task"}'])
    _patch_provider(monkeypatch, provider)

    async with mcp_session() as session:
        result = await session.call_tool("forkos_local_cognition", CLASSIFY_ARGS)

    assert result.is_error is True
    assert "INVALID_LOCAL_MODEL_ENDPOINT" in result.content[0].text
    assert provider.call_count == 0


async def test_h4_is_read_only_over_transport(
    h4_ready: None, monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession, vault: Path
) -> None:
    provider = ScriptedProvider(responses=['{"label": "deadline"}'])
    _patch_provider(monkeypatch, provider)

    db_before = await capture_db_content_fingerprint(db_session)
    vault_before = capture_vault_fingerprint(vault)
    counts_before = await table_counts(db_session)
    legacy_before = await legacy_notes_counts(db_session)

    async with mcp_session() as session:
        await session.call_tool("forkos_local_cognition", CLASSIFY_ARGS)
        await session.call_tool("forkos_local_cognition", EXTRACT_ARGS)
        await session.call_tool("forkos_local_cognition", REWRITE_ARGS)

    assert await capture_db_content_fingerprint(db_session) == db_before
    assert capture_vault_fingerprint(vault) == vault_before
    assert await table_counts(db_session) == counts_before
    assert await legacy_notes_counts(db_session) == legacy_before
    for model in (Entity, Link, Event):
        assert (await db_session.execute(select(func.count(model.id)))).scalar_one() == 0


async def test_h4_needs_no_database_and_no_vault(
    h4_ready: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§168: DB oturumu ve kasa okuyucuları patlatılsa bile H4 çalışır."""
    provider = ScriptedProvider(responses=['{"label": "task"}'])
    _patch_provider(monkeypatch, provider)

    def _boom(*args, **kwargs):
        raise AssertionError("hidden context was touched")

    monkeypatch.setattr("app.integrations.obsidian.evidence.scan_evidence_notes", _boom)
    monkeypatch.setattr("app.integrations.obsidian.evidence.read_note_lines", _boom)
    monkeypatch.setattr("app.integrations.agent.evidence._expand_graph", _boom)
    monkeypatch.setattr("app.integrations.agent.knowledge.search_vault", _boom)
    monkeypatch.setattr("app.integrations.obsidian.hot_memory.scan_memories", _boom)
    monkeypatch.setattr(SessionLocal, "__init__", _boom)

    async with mcp_session() as session:
        result = await session.call_tool("forkos_local_cognition", CLASSIFY_ARGS)

    assert result.is_error is False, result.content
    assert tool_payload(result)["status"] == "success"


async def test_h4_does_not_log_source_text(
    h4_ready: None, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """§93: kaynak metin ve prompt forkOS uygulama loglarında YER ALMAZ.

    MCP taşıma katmanı (SDK) JSON-RPC yüklerini DEBUG seviyesinde loglar; bu
    forkOS'un uygulama logu değildir. Ölçüm `app.*` logger'larıyla sınırlıdır.
    """
    marker = "OZEL-ISARET-METNI-42"
    provider = ScriptedProvider(responses=['{"label": "task"}'])
    _patch_provider(monkeypatch, provider)

    with caplog.at_level("DEBUG"):
        async with mcp_session() as session:
            await session.call_tool(
                "forkos_local_cognition", {**CLASSIFY_ARGS, "text": f"{marker} 29 Kasım sınavı"}
            )

    h4_records = [
        record
        for record in caplog.records
        if record.name.startswith("app.integrations.local_cognition")
    ]
    assert h4_records == []  # H4 hiçbir şey loglamaz: sızıntı yüzeyi yoktur
    assert all(
        marker not in record.getMessage()
        for record in caplog.records
        if record.name.startswith("app")
    )
