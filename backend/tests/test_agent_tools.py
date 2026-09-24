import pytest

from app.integrations.agent.mcp import mcp_server

pytestmark = pytest.mark.no_database


async def test_mcp_tool_registration_and_metadata():
    """H0 okuma araçları korunur; toplam yüzey H1 ile 19'a çıkar (§2/§8).

    Ayrıntılı yazma anotasyon sözleşmesi `test_agent_h1_contract.py`'dedir;
    burada H0 tarafının DEĞİŞMEDİĞİ kanıtlanır.
    """
    tools = await mcp_server.list_tools()
    tool_map = {t.name: t for t in tools}

    expected_read_tools = [
        "forkos_briefing",
        "forkos_search",
        "forkos_entity_context",
        "forkos_project_context",
        "forkos_recent_activity",
        "brain_status",
        "brain_search",
        "brain_read",
    ]

    # 1. H0 araçları yerinde ve toplam MCP yüzeyi A5.2 ile 33.
    assert set(expected_read_tools) <= set(tool_map)
    assert "forkos_evidence" in tool_map
    assert "forkos_local_cognition" in tool_map
    assert "forkos_review_intelligence" in tool_map
    assert len(tool_map) == 33

    # 2. Okuma araçlarının sözleşmesi zayıflatılmadı.
    for name in expected_read_tools:
        tool = tool_map[name]
        assert "Read-only. Does not modify forkOS or the Vault." in (tool.description or ""), (
            f"Tool {name} description missing read-only contract clause"
        )
        assert tool.annotations is not None, f"Tool {name} missing annotations"
        assert tool.annotations.read_only_hint is True, f"Tool {name} must have read_only_hint=True"
        assert tool.annotations.destructive_hint is False, f"Tool {name} destructive_hint must be False"

    # 3. Okuma araçları dışındaki HER araç yazma yetkili işaretlenmelidir
    #    (H2 sıcak hafıza ve H3 kanıt okuma araçları da okuma tarafındadır).
    read_only_names = set(expected_read_tools) | {
        "hot_memory_context",
        "hot_memory_list",
        "forkos_evidence",
        "forkos_local_cognition",
        "forkos_review_intelligence",
        "semantic_memory_candidates",
        "forkos_context_judge",
        "forkos_memory_judge",
    }
    for name, tool in tool_map.items():
        if name in read_only_names:
            continue
        assert tool.annotations.read_only_hint is False, name


async def test_brain_status_tool_call():
    result = await mcp_server.call_tool("brain_status", {})
    assert result.is_error is False
    assert len(result.content) >= 1
    assert "brain_interface_version" in result.content[0].text
    assert "f0rknbrain" in result.content[0].text


async def test_forkos_search_input_validation():
    with pytest.raises(Exception, match="QUERY_TOO_SHORT"):
        await mcp_server.call_tool("forkos_search", {"query": "a"})
    with pytest.raises(Exception, match="QUERY_TOO_LONG"):
        await mcp_server.call_tool("forkos_search", {"query": "x" * 201})


async def test_forkos_entity_context_uuid_validation():
    with pytest.raises(Exception, match="INVALID_UUID"):
        await mcp_server.call_tool("forkos_entity_context", {"entity_id": "not-a-uuid"})


async def test_forkos_project_context_uuid_validation():
    with pytest.raises(Exception, match="INVALID_UUID"):
        await mcp_server.call_tool("forkos_project_context", {"project_id": "not-a-uuid"})


async def test_forkos_recent_activity_since_validation():
    with pytest.raises(Exception, match="INVALID_SINCE"):
        await mcp_server.call_tool("forkos_recent_activity", {"since": "not-a-date"})


async def test_brain_search_input_validation():
    with pytest.raises(Exception, match="QUERY_TOO_SHORT"):
        await mcp_server.call_tool("brain_search", {"query": " "})
    with pytest.raises(Exception, match="QUERY_TOO_LONG"):
        await mcp_server.call_tool("brain_search", {"query": "x" * 201})
    with pytest.raises(Exception, match="INVALID_SCOPE|literal_error"):
        await mcp_server.call_tool("brain_search", {"query": "hello", "scope": "invalid_scope_name"})


async def test_brain_read_uuid_validation():
    with pytest.raises(Exception, match="INVALID_UUID"):
        await mcp_server.call_tool("brain_read", {"forkos_id": "not-a-uuid"})
