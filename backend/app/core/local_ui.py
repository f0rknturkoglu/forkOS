"""Bounded loopback UI requests for contextual sessions and plan preparation."""

from urllib.parse import urlsplit

from fastapi import HTTPException, Request
from fastapi.routing import APIRoute


class StudioRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def bounded(request: Request):
            # No forwarded Host trust or extension/MCP approval path. Browser same-origin mutations only.
            host = urlsplit("http://" + request.headers.get("host", "")).hostname
            if host not in {"127.0.0.1", "localhost", "::1"}:
                raise HTTPException(403, "Bağlamsal işlem yalnız yerel host üzerinde kullanılabilir")
            if request.method != "GET":
                origin = request.headers.get("origin")
                if origin not in {"http://127.0.0.1:5173", "http://localhost:5173"}:
                    raise HTTPException(403, "Bağlamsal işlem forkOS arayüzünden gelmeli")
                if request.headers.get("x-forkos-goal-studio") != "1":
                    raise HTTPException(403, "Yerel arayüz CSRF koruması eksik")
                if request.headers.get("content-type", "").split(";")[0] != "application/json":
                    raise HTTPException(415, "JSON gerekli")
                body = bytearray()
                async for chunk in request.stream():
                    body.extend(chunk)
                    if len(body) > 64_000:
                        raise HTTPException(413, "Yerel arayüz istek sınırı aşıldı")
                request._body = bytes(body)
            return await handler(request)

        return bounded
