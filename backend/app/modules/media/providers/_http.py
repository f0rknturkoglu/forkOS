from __future__ import annotations

import httpx

TIMEOUT = httpx.Timeout(20.0)


class HTTPProvider:
    def __init__(self, *, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        if self._client is not None:
            response = await self._client.request(method, url, **kwargs)
        else:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.request(method, url, **kwargs)
        response.raise_for_status()
        return response
