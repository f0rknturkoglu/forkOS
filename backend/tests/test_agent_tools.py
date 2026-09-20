import pytest

from app.integrations.agent.mcp import mcp_server

pytestmark = pytest.mark.no_database


async def test_mcp_tool_registration_and_metadata():
    tools = await mcp_server.list_tools()
    tool_map = {t.name: t for t in tools}

    expected_tools = [
        "forkos_briefing",
        "forkos_search",
        "forkos_entity_context",
        "forkos_project_context",
        "forkos_recent_activity",
        "brain_status",
        "brain_search",
        "brain_read",
    ]

    # 1. Assert exact 8 tool names
    assert sorted(tool_map.keys()) == sorted(expected_tools)

    # 2. Assert read-only description and annotations on every single tool
    for name, tool in tool_map.items():
        assert "Read-only. Does not modify forkOS or the Vault." in (tool.description or ""), (
            f"Tool {name} description missing read-only contract clause"
        )
        assert tool.annotations is not None, f"Tool {name} missing annotations"
        assert tool.annotations.read_only_hint is True, f"Tool {name} must have read_only_hint=True"
        assert tool.annotations.destructive_hint is False, f"Tool {name} destructive_hint must be False"


async def test_brain_status_tool_call():
    result = await mcp_server.call_tool("brain_status", {})
    assert result.is_error is False
    assert len(result.content) >= 1
    assert "brain_interface_version" in result.content[0].text
    assert "f0rknbrain" in result.content[0].text
