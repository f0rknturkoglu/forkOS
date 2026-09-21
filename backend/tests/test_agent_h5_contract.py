"""H5 MCP yüzeyi: 29 araç, tek yeni araç, anotasyonlar, şema, iç düğme yok."""

from __future__ import annotations

import json

from app.integrations.agent.mcp import mcp_server
from app.integrations.review_intelligence import models as ri

H0_TOOLS = {
    "forkos_briefing", "forkos_search", "forkos_entity_context", "forkos_project_context",
    "forkos_recent_activity", "brain_status", "brain_search", "brain_read",
}
H1_TOOLS = {
    "forkos_todo_create", "forkos_todo_update", "forkos_todo_complete", "forkos_todo_plan",
    "forkos_project_update", "forkos_opportunity_transition", "forkos_application_transition",
    "forkos_bookmark_capture", "forkos_bookmark_update", "brain_capture", "brain_save_to_entity",
}
H2_TOOLS = {
    "hot_memory_context", "hot_memory_list", "hot_memory_store", "hot_memory_update",
    "hot_memory_retire",
}
H3_TOOLS = {"forkos_evidence"}
H4_TOOLS = {"forkos_local_cognition"}
H5_TOOLS = {"forkos_review_intelligence"}
H6_TOOLS = {"forkos_proactivity"}
H7_TOOLS = {"forkos_execution"}

#: H5'in genel yüzeye ASLA koymadığı iç düğmeler (§20).
FORBIDDEN_PARAMETERS = {
    "event_scan_limit", "candidate_limit", "model", "provider", "max_depth", "resurface_age",
    "timeout", "budget", "temperature", "base_url", "internal",
}


async def _tools() -> dict:
    return {tool.name: tool for tool in await mcp_server.list_tools()}


async def test_h5_adds_exactly_one_mcp_tool() -> None:
    tools = await _tools()
    assert len(tools) == 29
    assert set(tools) & H5_TOOLS == H5_TOOLS
    assert set(tools) == H0_TOOLS | H1_TOOLS | H2_TOOLS | H3_TOOLS | H4_TOOLS | H5_TOOLS | H6_TOOLS | H7_TOOLS


async def test_h5_tool_is_read_only() -> None:
    tool = (await _tools())["forkos_review_intelligence"]
    wire = tool.annotations.model_dump(by_alias=True, exclude_none=True)
    assert wire["readOnlyHint"] is True
    assert wire["destructiveHint"] is False
    assert wire["idempotentHint"] is True


async def test_h5_schema_exposes_only_the_five_modes() -> None:
    schema = (await _tools())["forkos_review_intelligence"].input_schema
    assert schema["properties"]["mode"]["enum"] == list(ri.ACTIVE_MODES)
    assert schema["required"] == ["mode"]
    assert not (set(schema["properties"]) & FORBIDDEN_PARAMETERS)


async def test_h5_schema_argument_shapes() -> None:
    properties = (await _tools())["forkos_review_intelligence"].input_schema["properties"]
    assert properties["reference_date"]["anyOf"][0]["pattern"] == "^\\d{4}-\\d{2}-\\d{2}$"
    assert properties["focus_entity_id"]["anyOf"][0]["maxLength"] == ri.MAX_FOCUS_ENTITY_LEN
    assert properties["include_knowledge"]["type"] == "boolean"


async def test_no_new_write_tool_was_added() -> None:
    """H5 kendisi yazan arac EKLEMEZ; yazan kume H1+H2 ve (H6 ile) kontroldur."""
    tools = await _tools()
    writing = {
        name for name, tool in tools.items()
        if tool.annotations is not None and tool.annotations.read_only_hint is False
    }
    assert writing == H1_TOOLS | {
        "hot_memory_store",
        "hot_memory_update",
        "hot_memory_retire",
        "forkos_proactivity",
        "forkos_execution",
    }


def test_h5_contract_has_no_scores_or_mood_fields() -> None:
    dumped = json.dumps(ri.ReviewIntelligenceResponse.model_json_schema()).lower()
    for forbidden in (
        "confidence", "probability", "truth_score", "importance", "productivity",
        "discipline", "alignment", "mood", "life_score",
    ):
        assert forbidden not in dumped


def test_h5_response_is_not_prose_only() -> None:
    """§122: çıktı yapıdır; anlatıyı Hermes kurar."""
    names = set(ri.ReviewIntelligenceResponse.model_fields)
    assert {"mode", "coverage", "payload", "sources", "source_manifest", "trace", "warnings"} <= names
    assert "answer" not in names and "summary_text" not in names


async def test_existing_surfaces_are_untouched() -> None:
    tools = await _tools()
    assert tools["forkos_evidence"].annotations.read_only_hint is True
    assert tools["forkos_local_cognition"].annotations.read_only_hint is True
    assert tools["forkos_todo_create"].annotations.read_only_hint is False
