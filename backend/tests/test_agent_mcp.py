import httpx
import pytest
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

from app.main import app

pytestmark = pytest.mark.no_database


async def test_mcp_fastapi_mount_and_smoke():
    """Verify that /mcp mounted in FastAPI responds correctly to official MCP streamable_http_client."""
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1") as http_client,
        streamable_http_client("http://127.0.0.1/mcp/", http_client=http_client) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        # 1. Initialize
        init_result = await session.initialize()
        assert init_result.server_info.name == "forkos-brain"

        # 2. List tools
        tools = await session.list_tools()
        tool_names = [t.name for t in tools.tools]
        assert "forkos_briefing" in tool_names
        assert "brain_status" in tool_names
        assert "brain_search" in tool_names
        assert "brain_read" in tool_names
        assert len(tool_names) == 8

        # 3. Call brain_status
        status_res = await session.call_tool("brain_status", {})
        assert status_res.is_error is False
        assert len(status_res.content) >= 1
        assert "brain_interface_version" in status_res.content[0].text


async def test_mcp_dns_rebinding_rejection():
    """Verify that requests with non-localhost host/origin headers are rejected by DNS rebinding protection."""
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://evil.com",
            headers={"host": "evil.com", "origin": "http://evil.com"},
        ) as http_client,
    ):
        res = await http_client.post(
            "http://evil.com/mcp/",
            json={"jsonrpc": "2.0", "method": "initialize", "params": {}, "id": 1},
        )
        assert res.status_code in (400, 403, 421)

