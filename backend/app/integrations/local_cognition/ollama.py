"""Ollama sağlayıcısı — yalnızca LOOPBACK, yalnızca yapılandırılmış çıktı.

Kararlar:

  - **Mevcut `httpx` kullanılır.** Ollama Python SDK'sı eklenmez (§45).
  - **Yalnızca loopback.** `localhost`, `127.0.0.1`, `::1` dışındaki host
    `INVALID_LOCAL_MODEL_ENDPOINT` ile reddedilir (§46/§47): H4 yanlışlıkla bir
    bulut geçidine dönüşemez.
  - **Yönlendirme yok, proxy yok.** `follow_redirects=False`, `trust_env=False`
    (§48): ortam değişkenlerinden gelen proxy ayarları devralınmaz ve uzak bir
    yönlendirme izlenmez.
  - **Araç yok, ajan döngüsü yok.** `/api/chat` çağrısına `tools` verilmez;
    model yalnızca istenen JSON'u üretir (§49).
  - **Model indirilmez.** Eksik model `MODEL_UNAVAILABLE` döner; çalışma
    zamanında gigabaytlarca indirme başlamaz (§59/§60).
"""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.integrations.local_cognition.models import MAX_PROVIDER_RESPONSE_BYTES
from app.integrations.local_cognition.policy import ModelHealth
from app.integrations.local_cognition.provider import (
    GenerationRequest,
    GenerationResult,
    ProviderError,
)

#: Kabul edilen tek host kümesi.
LOOPBACK_HOSTS: frozenset[str] = frozenset({"localhost", "127.0.0.1", "::1"})

#: Kabul edilen şemalar (loopback üzerinde TLS gerekmez ama yasak değildir).
ALLOWED_SCHEMES: frozenset[str] = frozenset({"http", "https"})


def validate_loopback_base_url(base_url: str) -> str:
    """Sağlayıcı adresini doğrular ve normalleştirilmiş hâlini döner.

    Loopback dışı her host REDDEDİLİR. Bu, yapılandırma yoluyla uzak bir
    sağlayıcıya bağlanmayı yapısal olarak imkânsız kılar.
    """
    candidate = (base_url or "").strip()
    if not candidate:
        raise ProviderError(
            "INVALID_LOCAL_MODEL_ENDPOINT", "local model endpoint is not configured"
        )
    parsed = urlsplit(candidate)
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise ProviderError(
            "INVALID_LOCAL_MODEL_ENDPOINT", "local model endpoint must be an http(s) URL"
        )
    host = (parsed.hostname or "").lower()
    if host not in LOOPBACK_HOSTS:
        raise ProviderError(
            "INVALID_LOCAL_MODEL_ENDPOINT",
            "local model endpoint must be a loopback host (localhost, 127.0.0.1 or ::1)",
        )
    return candidate.rstrip("/")


def _model_matches(available: str, configured: str) -> bool:
    """Ollama etiketleri esnek eşleşir: `llama3` ≡ `llama3:latest`."""
    if available == configured:
        return True
    if available.split(":")[0] == configured:
        return True
    return available == f"{configured}:latest"


class OllamaProvider:
    """Ollama `/api/chat` üzerinden yapılandırılmış yerel üretim."""

    name = "ollama"

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 45.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        # Yapıcıda doğrula: geçersiz adresle HİÇBİR istek denenmez.
        self._base_url = validate_loopback_base_url(base_url)
        self._timeout_seconds = max(1.0, float(timeout_seconds))
        self._transport = transport

    @property
    def base_url(self) -> str:
        return self._base_url

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(self._timeout_seconds),
            follow_redirects=False,
            trust_env=False,
            transport=self._transport,
        )

    async def health(self, model_id: str) -> ModelHealth:
        """Sağlayıcı erişilebilir mi ve model kurulu mu?

        Model İNDİRİLMEZ; yalnızca var olan listelenir.
        """
        configured = bool((model_id or "").strip())
        if not configured:
            return ModelHealth(
                configured=False,
                provider_reachable=False,
                model_available=False,
                healthy=False,
            )
        try:
            async with self._client() as client:
                response = await client.get("/api/tags")
        except httpx.HTTPError as exc:
            raise ProviderError(
                "MODEL_PROVIDER_UNAVAILABLE", "local model provider is not reachable"
            ) from exc

        if response.status_code != 200:
            raise ProviderError(
                "MODEL_PROVIDER_UNAVAILABLE", "local model provider returned an error"
            )
        try:
            payload: dict[str, Any] = response.json()
        except ValueError as exc:
            raise ProviderError(
                "MODEL_PROVIDER_UNAVAILABLE", "local model provider returned invalid JSON"
            ) from exc

        names = [
            str(entry.get("name") or entry.get("model") or "")
            for entry in (payload.get("models") or [])
            if isinstance(entry, dict)
        ]
        available = any(_model_matches(name, model_id) for name in names)
        return ModelHealth(
            configured=True,
            provider_reachable=True,
            model_available=available,
            healthy=available,
        )

    async def generate_structured(self, request: GenerationRequest) -> GenerationResult:
        """JSON şemalı tek üretim çağrısı. Araç verilmez, akış kapalıdır."""
        body = {
            "model": request.model_id,
            "stream": False,
            "format": request.json_schema,
            "options": {"temperature": request.temperature},
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
        }
        started = time.perf_counter()
        try:
            async with self._client() as client:
                response = await client.post("/api/chat", json=body)
        except httpx.TimeoutException as exc:
            raise ProviderError(
                "MODEL_PROVIDER_UNAVAILABLE", "local model provider timed out"
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(
                "MODEL_PROVIDER_UNAVAILABLE", "local model provider is not reachable"
            ) from exc
        latency_ms = (time.perf_counter() - started) * 1000

        if len(response.content) > MAX_PROVIDER_RESPONSE_BYTES:
            raise ProviderError("OUTPUT_TOO_LARGE", "local model response exceeded the size budget")
        if response.status_code == 404:
            raise ProviderError("MODEL_UNAVAILABLE", "the configured local model is not installed")
        if response.status_code != 200:
            raise ProviderError(
                "MODEL_PROVIDER_UNAVAILABLE", "local model provider returned an error"
            )

        try:
            payload: dict[str, Any] = response.json()
        except ValueError as exc:
            raise ProviderError(
                "MODEL_PROVIDER_UNAVAILABLE", "local model provider returned invalid JSON"
            ) from exc

        message = payload.get("message") if isinstance(payload, dict) else None
        content = ""
        if isinstance(message, dict):
            content = str(message.get("content") or "")
        elif isinstance(payload, dict):
            content = str(payload.get("response") or "")

        return GenerationResult(content=content, latency_ms=latency_ms)


__all__ = ["LOOPBACK_HOSTS", "OllamaProvider", "validate_loopback_base_url"]
