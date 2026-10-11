"""A5.3 Answer Evidence Judge MCP contract tests: read-only, bounded, no caller evidence."""

import pytest

from app.config import settings
from app.integrations.agent.mcp import mcp_server


@pytest.mark.no_database
async def test_answer_judge_tool_contract():
    tools = {tool.name: tool for tool in await mcp_server.list_tools()}
    assert len(tools) == 37  # Existing Goals/Strategy tool is retained in V1.
    tool = tools["forkos_answer_judge"]
    assert tool.annotations.read_only_hint is True
    assert tool.annotations.destructive_hint is False

    properties = tool.input_schema["properties"]
    assert set(properties) == {
        "claim",
        "retrieval_query",
        "entity_id",
        "scope",
        "since",
        "until",
        "max_depth",
        "limit",
    }
    assert tool.input_schema["required"] == ["claim"]
    assert properties["claim"]["minLength"] == 2
    assert properties["claim"]["maxLength"] == 1000
    rq = properties["retrieval_query"]
    str_schema = next(s for s in rq["anyOf"] if s.get("type") == "string")
    assert str_schema["minLength"] == 2
    assert str_schema["maxLength"] == 200
    assert properties["limit"]["maximum"] == 15

    # Invariant: Caller cannot supply evidence, sources, verdicts, prompts, or control mode
    forbidden = {
        "evidence",
        "evidence_items",
        "source_text",
        "quotes",
        "context",
        "prior_verdicts",
        "provider",
        "mode",
        "instructions",
        "support",
        "expected_verdict",
    }
    assert forbidden.isdisjoint(properties)


@pytest.mark.no_database
def test_answer_settings_defaults():
    assert settings.a5_answer_mode == "off"
    assert settings.a5_answer_provider == "poorjev"
    assert settings.a5_answer_timeout_seconds == 20.0
