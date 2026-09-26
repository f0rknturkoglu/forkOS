"""CareerEvaluationService: Deep, evidence-bound fit evaluation service (C4).

Coordinates:
- CandidateCareerContext & CareerListingContext
- Deterministic pre-analysis
- Career Specialist Reasoner (Ollama, Cloud, None, Mock)
- Non-destructive persistence on Opportunity.evaluation
- Dynamic staleness detection and evaluation caching
- NEVER overwrites Opportunity.score with LLM evaluation
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
import uuid

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import log_event
from app.modules.opportunity.candidate_context import (
    CandidateCareerContext,
    build_candidate_career_context,
)
from app.modules.opportunity.listing_context import (
    CareerListingContext,
    build_career_listing_context,
)
from app.modules.opportunity.models import Opportunity
from app.modules.opportunity.reasoner.base import (
    CareerReasoner,
    CareerReasonerError,
    DeepEvaluationDraft,
    RequirementAssessmentDraft,
)
from app.modules.opportunity.reasoner.factory import get_career_reasoner


class RequirementAssessment(BaseModel):
    model_config = ConfigDict(extra="ignore")

    requirement: str
    classification: Literal["strong", "partial", "missing", "unknown", "not_applicable"]
    reason: str
    candidate_evidence_refs: list[str] = Field(default_factory=list)
    listing_evidence_refs: list[str] = Field(default_factory=list)
    confidence: float = 1.0


class DeepEvaluation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    opportunity_id: str
    listing_fingerprint: str
    candidate_context_revision: str
    provider: str
    model: str
    created_at: str

    overall_assessment: str
    confidence: float = 1.0

    role_fit: str
    seniority_fit: str
    location_fit: str

    must_have: list[RequirementAssessment] = Field(default_factory=list)
    nice_to_have: list[RequirementAssessment] = Field(default_factory=list)

    strengths: list[str] = Field(default_factory=list)
    partial_matches: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)

    work_authorization: dict[str, Any] = Field(default_factory=dict)
    sponsorship: dict[str, Any] = Field(default_factory=dict)
    compensation: dict[str, Any] = Field(default_factory=dict)

    risks: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)

    is_stale: bool = False
    stale_reasons: list[str] = Field(default_factory=list)


class CareerEvaluationService:
    def __init__(self, reasoner: CareerReasoner | None = None) -> None:
        self.reasoner = reasoner or get_career_reasoner()

    async def get_evaluation(
        self,
        session: AsyncSession,
        opportunity_id: uuid.UUID,
    ) -> DeepEvaluation | None:
        """Fetch current evaluation for opportunity and compute dynamic staleness."""
        opp = await session.get(Opportunity, opportunity_id)
        if opp is None:
            return None

        raw_eval = dict(opp.evaluation or {})
        if not raw_eval or not raw_eval.get("listing_fingerprint"):
            return None

        # Build contexts to evaluate staleness
        listing_ctx = await build_career_listing_context(session, opp)
        cand_ctx = await build_candidate_career_context(session)

        stale_reasons: list[str] = []
        is_stale = False

        if raw_eval.get("listing_fingerprint") != listing_ctx.listing_fingerprint:
            is_stale = True
            stale_reasons.append("Job description or listing details modified since evaluation.")

        if raw_eval.get("candidate_context_revision") != cand_ctx.revision:
            is_stale = True
            stale_reasons.append("Candidate facts or profile modified since evaluation.")

        evaluation = DeepEvaluation.model_validate(raw_eval)
        evaluation.is_stale = is_stale
        evaluation.stale_reasons = stale_reasons
        return evaluation

    async def evaluate_opportunity(
        self,
        session: AsyncSession,
        opportunity_id: uuid.UUID,
        *,
        force: bool = False,
        now: datetime | None = None,
    ) -> DeepEvaluation:
        """Evaluate opportunity fit against candidate context using configured Career Reasoner."""
        now = now or datetime.now(UTC)
        opp = await session.get(Opportunity, opportunity_id)
        if opp is None:
            raise ValueError(f"Opportunity not found: {opportunity_id}")

        listing_ctx = await build_career_listing_context(session, opp)
        if not listing_ctx.is_jd_valid:
            raise ValueError(
                f"Cannot evaluate opportunity: Job description is invalid or rejected "
                f"({listing_ctx.jd_rejection_reason}). Extract or provide a valid JD first."
            )

        cand_ctx = await build_candidate_career_context(session)

        # Cache check (Cost control): if not force, and existing evaluation is not stale, reuse it!
        if not force:
            existing = await self.get_evaluation(session, opportunity_id)
            if existing is not None and not existing.is_stale:
                return existing

        # Execute reasoner draft
        draft: DeepEvaluationDraft = await self.reasoner.evaluate(listing_ctx, cand_ctx)

        eval_model = DeepEvaluation(
            opportunity_id=str(opportunity_id),
            listing_fingerprint=listing_ctx.listing_fingerprint,
            candidate_context_revision=cand_ctx.revision,
            provider=draft.provider_metadata.get("provider", self.reasoner.provider_name),
            model=draft.provider_metadata.get("model", "default"),
            created_at=now.isoformat(),
            overall_assessment=draft.overall_assessment,
            confidence=draft.confidence,
            role_fit=draft.role_fit,
            seniority_fit=draft.seniority_fit,
            location_fit=draft.location_fit,
            must_have=[RequirementAssessment.model_validate(m.model_dump()) for m in draft.must_have],
            nice_to_have=[RequirementAssessment.model_validate(n.model_dump()) for n in draft.nice_to_have],
            strengths=draft.strengths,
            partial_matches=draft.partial_matches,
            missing_requirements=draft.missing_requirements,
            work_authorization=draft.work_authorization,
            sponsorship=draft.sponsorship,
            compensation=draft.compensation,
            risks=draft.risks,
            unknowns=draft.unknowns,
            recommended_next_steps=draft.recommended_next_steps,
            evidence=draft.evidence,
            is_stale=False,
            stale_reasons=[],
        )

        # Persist non-destructively: Do NOT mutate opp.score!
        opp.evaluation = eval_model.model_dump()
        opp.evaluated_at = now

        await session.flush()

        await log_event(
            session,
            verb="opportunity.evaluated",
            entity_id=opp.id,
            entity_type="opportunity",
            payload={
                "provider": eval_model.provider,
                "model": eval_model.model,
                "listing_fingerprint": eval_model.listing_fingerprint,
                "candidate_revision": eval_model.candidate_context_revision,
                "strengths_count": len(eval_model.strengths),
                "missing_count": len(eval_model.missing_requirements),
            },
        )

        return eval_model
