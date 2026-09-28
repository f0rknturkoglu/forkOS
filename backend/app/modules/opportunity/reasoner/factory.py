"""Factory for instantiating Career Reasoner providers."""

from __future__ import annotations

from app.config import settings
from app.modules.opportunity.reasoner.base import CareerReasoner
from app.modules.opportunity.reasoner.mock import DeterministicMockCareerReasoner
from app.modules.opportunity.reasoner.none import NoneCareerReasoner
from app.modules.opportunity.reasoner.ollama import OllamaCareerReasoner


def get_career_reasoner(provider: str | None = None) -> CareerReasoner:
    """Return configured Career Reasoner instance."""
    prov = (provider or settings.career_reasoner_provider or "none").lower()

    if prov == "none":
        return NoneCareerReasoner()
    elif prov == "mock":
        return DeterministicMockCareerReasoner()
    elif prov == "ollama":
        return OllamaCareerReasoner()
    elif prov in ("openai", "gemini", "openrouter"):
        # Personal career evidence must not leave the local-only boundary.
        return NoneCareerReasoner()
    else:
        return NoneCareerReasoner()
