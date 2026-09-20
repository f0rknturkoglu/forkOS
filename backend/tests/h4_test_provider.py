"""H4 testleri ve eval koşucusu için DETERMİNİSTİK sağlayıcı (§98).

Ollama gerektirmez: sağlık, yanıtlar ve hatalar betiklenir. Her çağrı kaydedilir
böylece "kaç kez, hangi şemayla, hangi seçeneklerle" soruları test edilebilir.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.integrations.local_cognition.policy import ModelHealth
from app.integrations.local_cognition.provider import (
    GenerationRequest,
    GenerationResult,
    ProviderError,
)

HEALTHY = ModelHealth(
    configured=True, provider_reachable=True, model_available=True, healthy=True
)
MODEL_MISSING = ModelHealth(
    configured=True, provider_reachable=True, model_available=False, healthy=False
)
UNCONFIGURED = ModelHealth(
    configured=False, provider_reachable=False, model_available=False, healthy=False
)

#: Desteklenen betikler.
SCRIPTS: tuple[str, ...] = (
    "ok",
    "malformed_json",
    "empty_output",
    "timeout",
    "model_missing",
)


@dataclass
class ScriptedProvider:
    """Betiklenmiş yerel sağlayıcı."""

    responses: list[str] = field(default_factory=list)
    script: str = "ok"
    latency_ms: float = 1.0
    calls: list[GenerationRequest] = field(default_factory=list)
    health_calls: list[str] = field(default_factory=list)
    health_by_model: dict[str, ModelHealth] = field(default_factory=dict)
    name: str = "scripted"

    async def health(self, model_id: str) -> ModelHealth:
        self.health_calls.append(model_id)
        return self.health_by_model.get(model_id, HEALTHY)

    async def generate_structured(self, request: GenerationRequest) -> GenerationResult:
        self.calls.append(request)
        if self.script == "timeout":
            raise ProviderError("MODEL_PROVIDER_UNAVAILABLE", "local model provider timed out")
        if self.script == "model_missing":
            raise ProviderError("MODEL_UNAVAILABLE", "the configured local model is not installed")
        if self.script == "empty_output":
            return GenerationResult(content="", latency_ms=self.latency_ms)
        if self.script == "malformed_json":
            return GenerationResult(content="this is not json at all", latency_ms=self.latency_ms)
        if not self.responses:
            return GenerationResult(content="{}", latency_ms=self.latency_ms)
        index = min(len(self.calls) - 1, len(self.responses) - 1)
        return GenerationResult(content=self.responses[index], latency_ms=self.latency_ms)

    @property
    def call_count(self) -> int:
        return len(self.calls)
