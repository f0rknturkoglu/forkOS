from __future__ import annotations

from contextlib import asynccontextmanager
from contextvars import ContextVar

import httpx

TIMEOUT = httpx.Timeout(20.0)


class HTTPProvider:
    def __init__(self, *, client: httpx.AsyncClient | None = None) -> None:
        self._client = client
        self._snapshot_responses: ContextVar[
            dict[tuple[str, str, str], httpx.Response] | None
        ] = ContextVar(f"provider_snapshot_{id(self)}", default=None)

    @asynccontextmanager
    async def snapshot(self):
        token = self._snapshot_responses.set({})
        try:
            yield
        finally:
            self._snapshot_responses.reset(token)

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        cache = self._snapshot_responses.get()
        cache_key = (method.upper(), url, repr(kwargs))
        if cache is not None and method.upper() == "GET" and cache_key in cache:
            return cache[cache_key]
        if self._client is not None:
            response = await self._client.request(method, url, **kwargs)
        else:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.request(method, url, **kwargs)
        response.raise_for_status()
        if cache is not None and method.upper() == "GET":
            cache[cache_key] = response
        return response
