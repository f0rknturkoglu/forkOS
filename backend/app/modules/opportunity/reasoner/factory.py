"""Factory for instantiating Career Reasoner providers."""

from __future__ import annotations

from app.integrations.career_ops.models import CapabilityStatus
from app.integrations.career_ops.reasoner_status import get_career_reasoner_runtime_status
from app.modules.opportunity.reasoner.base import CareerReasoner
from app.modules.opportunity.reasoner.mock import DeterministicMockCareerReasoner
from app.modules.opportunity.reasoner.none import NoneCareerReasoner
from app.modules.opportunity.reasoner.ollama import OllamaCareerReasoner


def get_career_reasoner(provider: str | None = None) -> CareerReasoner:
    """Return configured Career Reasoner instance."""
    status = get_career_reasoner_runtime_status(provider)
    prov = status.provider

    if prov == "none":
        return NoneCareerReasoner()
    elif prov == "mock":
        return DeterministicMockCareerReasoner()
    elif prov == "ollama" and status.capability != CapabilityStatus.DISABLED:
        return OllamaCareerReasoner()
    elif prov in ("openai", "gemini", "openrouter"):
        # Personal career evidence must not leave the local-only boundary.
        return NoneCareerReasoner()
    else:
        return NoneCareerReasoner()
