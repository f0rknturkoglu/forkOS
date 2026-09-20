from __future__ import annotations

from typing import TYPE_CHECKING

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from app.integrations.agent.tools import register_agent_tools

if TYPE_CHECKING:
    from starlette.applications import Starlette

mcp_server = MCPServer(
    name="forkos-brain",
    instructions="forkOS Brain Interface: Safe, bounded, read-only observer for operational state and f0rknbrain knowledge.",
)

# Register the 8 public read-only tools
register_agent_tools(mcp_server)

_starlette_app: Starlette | None = None


def get_streamable_http_app(force_new: bool = False) -> Starlette:
    """Return the Starlette ASGI app implementing the Streamable HTTP MCP transport with localhost security."""
    global _starlette_app
    if _starlette_app is None or force_new:
        _starlette_app = mcp_server.streamable_http_app(
            streamable_http_path="/",
            transport_security=TransportSecuritySettings(
                enable_dns_rebinding_protection=True,
                allowed_hosts=["127.0.0.1", "127.0.0.1:*", "localhost", "localhost:*", "[::1]", "[::1]:*"],
                allowed_origins=[
                    "http://127.0.0.1",
                    "http://127.0.0.1:*",
                    "http://localhost",
                    "http://localhost:*",
                    "http://[::1]",
                    "http://[::1]:*",
                ],
            ),
        )
    return _starlette_app
