"""Local-only career reasoner policy and metadata-only health probe."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.integrations.career_ops.models import CapabilityStatus


@dataclass(frozen=True)
class CareerReasonerRuntimeStatus:
    provider: str
    capability: CapabilityStatus
    reason: str


def get_career_reasoner_runtime_status(
    provider: str | None = None, *, ollama_healthy: bool = False
) -> CareerReasonerRuntimeStatus:
    """One policy shared by factory, doctor and capability reporting."""
    prov = (provider or settings.career_reasoner_provider or "none").lower()
    if prov in {"openai", "gemini", "openrouter"}:
        return CareerReasonerRuntimeStatus(
            prov, CapabilityStatus.DISABLED, "Cloud career reasoners are disabled by local-only privacy policy."
        )
    if prov == "mock":
        return CareerReasonerRuntimeStatus(
            prov, CapabilityStatus.DEGRADED, "Mock is for tests only, not a production reasoner."
        )
    if prov != "ollama":
        return CareerReasonerRuntimeStatus(prov, CapabilityStatus.DEGRADED, "No operational career reasoner is configured.")
    model_id = settings.career_reasoner_model or settings.h4_medium_model or settings.h4_small_model
    if not model_id:
        return CareerReasonerRuntimeStatus(prov, CapabilityStatus.DEGRADED, "No Ollama career model is configured.")
    base_url = (settings.career_reasoner_base_url or settings.h4_ollama_base_url).rstrip("/")
    if (urlparse(base_url).hostname or "").lower() not in {"127.0.0.1", "localhost", "::1"}:
        return CareerReasonerRuntimeStatus(prov, CapabilityStatus.DISABLED, "Ollama URL must use loopback.")
    if not ollama_healthy:
        return CareerReasonerRuntimeStatus(prov, CapabilityStatus.DEGRADED, "Configured local Ollama model is unavailable.")
    return CareerReasonerRuntimeStatus(prov, CapabilityStatus.SUPPORTED, "Configured local Ollama model is available.")


async def probe_local_career_reasoner() -> CareerReasonerRuntimeStatus:
    """Read only loopback /api/tags; never send candidate evidence."""
    status = get_career_reasoner_runtime_status()
    if status.provider != "ollama" or status.capability == CapabilityStatus.DISABLED:
        return status
    base_url = (settings.career_reasoner_base_url or settings.h4_ollama_base_url).rstrip("/")
    model_id = settings.career_reasoner_model or settings.h4_medium_model or settings.h4_small_model
    if not model_id:
        return status
    try:
        async with httpx.AsyncClient(timeout=2.0, trust_env=False) as client:
            response = await client.get(f"{base_url}/api/tags")
            response.raise_for_status()
            models = response.json().get("models", [])
        healthy = any(
            item.get("name") in {model_id, f"{model_id}:latest"}
            for item in models
            if isinstance(item, dict)
        )
    except (httpx.HTTPError, ValueError, TypeError, AttributeError):
        healthy = False
    return get_career_reasoner_runtime_status(ollama_healthy=healthy)
