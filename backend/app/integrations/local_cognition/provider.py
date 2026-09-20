"""H4 sağlayıcı soyutlaması — DAR tutulur (§44).

H4'ün sağlayıcıdan istediği üç şey vardır: sağlık, model varlığı ve
yapılandırılmış yerel üretim. Her olası LLM özelliği soyutlanmaz.

Sağlayıcı katmanı **hiçbir zaman** doğrulama yapmaz: ham çıktıyı döner,
karar `contracts.py` içindeki deterministik doğrulayıcılara aittir.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from app.integrations.local_cognition.policy import ModelHealth


@dataclass(frozen=True)
class GenerationRequest:
    """Sağlayıcıya giden tek istek biçimi."""

    model_id: str
    system_prompt: str
    user_prompt: str
    json_schema: dict[str, Any]
    temperature: float = 0.0
    timeout_seconds: float = 45.0


@dataclass(frozen=True)
class GenerationResult:
    """Sağlayıcıdan dönen ham içerik ve gecikme."""

    content: str
    latency_ms: float


class ProviderError(Exception):
    """Sınırlı sağlayıcı hatası.

    Ham istisna metni, URL, yığın izi veya model çıktısı DIŞARI ÇIKMAZ (§76).
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@runtime_checkable
class LocalModelProvider(Protocol):
    """Yerel model sağlayıcısı sözleşmesi."""

    name: str

    async def health(self, model_id: str) -> ModelHealth:
        """Sağlayıcı erişilebilir mi ve model kurulu mu (§57/§59)."""
        ...

    async def generate_structured(self, request: GenerationRequest) -> GenerationResult:
        """Yapılandırılmış (JSON şemalı) üretim. Araç/ajan döngüsü YOKTUR."""
        ...


__all__ = [
    "GenerationRequest",
    "GenerationResult",
    "LocalModelProvider",
    "ProviderError",
]
