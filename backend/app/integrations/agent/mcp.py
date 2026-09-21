from __future__ import annotations

from typing import TYPE_CHECKING

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from app.integrations.agent import capabilities
from app.integrations.agent.tools import register_agent_tools

if TYPE_CHECKING:
    from starlette.applications import Starlette

# Talimat metni TEK kaynaktan gelir: yüzey yalnızca okuma değildir, onaylı
# yazma araçları da içerir (capabilities.py).
mcp_server = MCPServer(
    name=capabilities.SERVER_NAME,
    instructions=capabilities.instructions(),
)

# Register the full public tool surface (H0–H7)
register_agent_tools(mcp_server)

#: Yerel-only taşıma güvenliği. Değerler capabilities.LOOPBACK_ONLY ile
#: tutarlıdır ve testler tarafından GERÇEK hâliyle doğrulanır: modül düzeyinde
#: durmasının nedeni, testin uygulamayı yeniden kurup oturum yöneticisini
#: değiştirmek zorunda kalmamasıdır.
TRANSPORT_SECURITY = TransportSecuritySettings(
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
)

_starlette_app: Starlette | None = None


def get_streamable_http_app(force_new: bool = False) -> Starlette:
    """Return the Starlette ASGI app implementing the Streamable HTTP MCP transport with localhost security."""
    global _starlette_app
    if _starlette_app is None or force_new:
        _starlette_app = mcp_server.streamable_http_app(
            streamable_http_path="/",
            transport_security=TRANSPORT_SECURITY,
        )
    return _starlette_app
