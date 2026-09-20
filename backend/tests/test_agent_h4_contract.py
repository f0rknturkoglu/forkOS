"""H4 MCP yüzeyi: tek yeni araç, anotasyonlar, şema sınırları, gizli parametre yok."""

from __future__ import annotations

import json

from app.integrations.agent.mcp import mcp_server
from app.integrations.local_cognition import models as lc

H0_TOOLS = {
    "forkos_briefing",
    "forkos_search",
    "forkos_entity_context",
    "forkos_project_context",
    "forkos_recent_activity",
    "brain_status",
    "brain_search",
    "brain_read",
}
H1_TOOLS = {
    "forkos_todo_create",
    "forkos_todo_update",
    "forkos_todo_complete",
    "forkos_todo_plan",
    "forkos_project_update",
    "forkos_opportunity_transition",
    "forkos_application_transition",
    "forkos_bookmark_capture",
    "forkos_bookmark_update",
    "brain_capture",
    "brain_save_to_entity",
}
H2_TOOLS = {
    "hot_memory_context",
    "hot_memory_list",
    "hot_memory_store",
    "hot_memory_update",
    "hot_memory_retire",
}
H3_TOOLS = {"forkos_evidence"}
H4_TOOLS = {"forkos_local_cognition"}
H5_TOOLS = {"forkos_review_intelligence"}
H6_TOOLS = {"forkos_proactivity"}

#: H4'ün genel yüzeye ASLA koymadığı parametreler (§27).
FORBIDDEN_PARAMETERS = {
    "model",
    "model_id",
    "base_url",
    "endpoint",
    "temperature",
    "system_prompt",
    "prompt",
    "provider",
    "tools",
    "api_key",
    "options",
}


async def _tools() -> dict:
    return {tool.name: tool for tool in await mcp_server.list_tools()}


async def test_h4_adds_exactly_one_mcp_tool() -> None:
    tools = await _tools()
    assert len(tools) == 28
    assert set(tools) & H4_TOOLS == H4_TOOLS
    assert set(tools) == H0_TOOLS | H1_TOOLS | H2_TOOLS | H3_TOOLS | H4_TOOLS | H5_TOOLS | H6_TOOLS
    assert len(H0_TOOLS) == 8 and len(H1_TOOLS) == 11 and len(H2_TOOLS) == 5


async def test_h4_tool_is_read_only() -> None:
    tool = (await _tools())["forkos_local_cognition"]
    wire = tool.annotations.model_dump(by_alias=True, exclude_none=True)
    assert wire["readOnlyHint"] is True
    assert wire["destructiveHint"] is False
    assert wire["idempotentHint"] is True


async def test_h4_schema_has_only_supported_lanes() -> None:
    schema = (await _tools())["forkos_local_cognition"].input_schema
    assert schema["properties"]["lane"]["enum"] == ["classify", "structured_extract", "query_rewrite"]
    assert schema["required"] == ["lane", "text"]


async def test_h4_schema_exposes_all_bounds() -> None:
    properties = (await _tools())["forkos_local_cognition"].input_schema["properties"]

    assert properties["text"]["minLength"] == lc.MIN_TEXT_CHARS
    assert properties["text"]["maxLength"] == lc.MAX_TEXT_CHARS

    labels = properties["labels"]["anyOf"][0]
    assert labels["minItems"] == lc.MIN_LABELS
    assert labels["maxItems"] == lc.MAX_LABELS
    assert labels["items"]["maxLength"] == lc.MAX_LABEL_CHARS

    assert properties["classification_goal"]["anyOf"][0]["maxLength"] == lc.MAX_CLASSIFICATION_GOAL_CHARS

    protected = properties["protected_terms"]["anyOf"][0]
    assert protected["maxItems"] == lc.MAX_PROTECTED_TERMS
    assert protected["items"]["maxLength"] == lc.MAX_PROTECTED_TERM_CHARS

    contracts = properties["contract"]["anyOf"][0]["enum"]
    assert contracts == list(lc.EXTRACTION_CONTRACTS)


async def test_h4_does_not_expose_model_or_base_url() -> None:
    properties = (await _tools())["forkos_local_cognition"].input_schema["properties"]
    assert not (set(properties) & FORBIDDEN_PARAMETERS)


async def test_deferred_and_reasoning_lanes_are_not_public() -> None:
    enum = (await _tools())["forkos_local_cognition"].input_schema["properties"]["lane"]["enum"]
    for lane in (*lc.DEFERRED_LANES, *lc.REJECTED_LANES):
        assert lane not in enum


def test_response_contract_has_no_hidden_reasoning() -> None:
    dumped = json.dumps(lc.LocalCognitionResponse.model_json_schema()).lower()
    for forbidden in ("confidence", "probability", "chain_of_thought", "reasoning", "explanation"):
        assert forbidden not in dumped


def test_only_three_lanes_are_active() -> None:
    assert lc.ACTIVE_LANES == ("classify", "structured_extract", "query_rewrite")
    assert lc.DEFERRED_LANES == ("rerank", "compress")


async def test_existing_surfaces_are_untouched() -> None:
    tools = await _tools()
    assert tools["forkos_evidence"].annotations.read_only_hint is True
    assert tools["forkos_todo_create"].annotations.read_only_hint is False
    assert tools["hot_memory_store"].annotations.read_only_hint is False


async def test_h4_tool_stays_registered_when_disabled() -> None:
    """§166: yüzey yapılandırmaya göre DEĞİŞMEZ (28 araç sabittir)."""
    from app.config import settings

    assert settings.h4_enabled is False  # varsayılan
    assert "forkos_local_cognition" in await _tools()
