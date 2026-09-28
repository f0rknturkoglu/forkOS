"""A5.2 caller authority is one read-only UUID, not injectable context."""

import pytest

from app.integrations.agent.mcp import mcp_server

pytestmark = pytest.mark.no_database


async def test_memory_judge_tool_is_narrow_and_read_only():
    tools = {tool.name: tool for tool in await mcp_server.list_tools()}
    tool = tools["forkos_memory_judge"]
    assert len(tools) == 36
    assert tool.annotations.read_only_hint is True
    assert tool.annotations.destructive_hint is False
    assert set(tool.input_schema["properties"]) == {"candidate_id"}
    assert tool.input_schema["required"] == ["candidate_id"]
