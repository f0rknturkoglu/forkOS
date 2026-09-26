"""None provider for Career Reasoner: Truthful degraded/unavailable state (Section 6)."""

from __future__ import annotations

from typing import Any

from app.modules.opportunity.candidate_context import CandidateCareerContext
from app.modules.opportunity.listing_context import CareerListingContext
from app.modules.opportunity.reasoner.base import (
    ApplicationAnswerDraft,
    CareerReasoner,
    CareerReasonerUnavailableError,
    CoverLetterDraft,
    DeepEvaluationDraft,
    TailoredCvDraft,
)


class NoneCareerReasoner(CareerReasoner):
    """When CAREER_REASONER_PROVIDER is 'none', LLM capabilities are truthfully unavailable."""

    @property
    def provider_name(self) -> str:
        return "none"

    async def evaluate(
        self,
        listing_ctx: CareerListingContext,
        candidate_ctx: CandidateCareerContext,
    ) -> DeepEvaluationDraft:
        raise CareerReasonerUnavailableError(
            "Career Reasoner is disabled (CAREER_REASONER_PROVIDER='none'). "
            "Configure ollama, openai, gemini, or openrouter to enable Deep Evaluation."
        )

    async def tailor_cv(
        self,
        base_cv: dict[str, Any],
        listing_ctx: CareerListingContext,
        candidate_ctx: CandidateCareerContext,
        evaluation: DeepEvaluationDraft,
    ) -> TailoredCvDraft:
        raise CareerReasonerUnavailableError(
            "Career Reasoner is disabled (CAREER_REASONER_PROVIDER='none'). "
            "Configure a provider to enable CV tailoring."
        )

    async def generate_cover(
        self,
        listing_ctx: CareerListingContext,
        candidate_ctx: CandidateCareerContext,
        evaluation: DeepEvaluationDraft,
        stories: list[dict[str, Any]],
    ) -> CoverLetterDraft:
        raise CareerReasonerUnavailableError(
            "Career Reasoner is disabled (CAREER_REASONER_PROVIDER='none'). "
            "Configure a provider to enable Cover Letter generation."
        )

    async def answer_application(
        self,
        listing_ctx: CareerListingContext,
        candidate_ctx: CandidateCareerContext,
        evaluation: DeepEvaluationDraft,
        questions: list[str],
    ) -> list[ApplicationAnswerDraft]:
        raise CareerReasonerUnavailableError(
            "Career Reasoner is disabled (CAREER_REASONER_PROVIDER='none'). "
            "Configure a provider to enable Application Answers."
        )
