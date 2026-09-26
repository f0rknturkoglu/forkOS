"""Base contracts and typed draft models for Career Reasoner abstraction (C4/C5)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.opportunity.candidate_context import CandidateCareerContext
from app.modules.opportunity.listing_context import CareerListingContext


class RequirementAssessmentDraft(BaseModel):
    model_config = ConfigDict(extra="ignore")

    requirement: str
    classification: Literal["strong", "partial", "missing", "unknown", "not_applicable"]
    reason: str
    candidate_evidence_refs: list[str] = Field(default_factory=list)
    listing_evidence_refs: list[str] = Field(default_factory=list)
    confidence: float = 1.0


class DeepEvaluationDraft(BaseModel):
    model_config = ConfigDict(extra="ignore")

    overall_assessment: str
    confidence: float = 1.0
    role_fit: str
    seniority_fit: str
    location_fit: str
    must_have: list[RequirementAssessmentDraft] = Field(default_factory=list)
    nice_to_have: list[RequirementAssessmentDraft] = Field(default_factory=list)
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
    provider_metadata: dict[str, Any] = Field(default_factory=dict)


class CvChangeItemDraft(BaseModel):
    model_config = ConfigDict(extra="ignore")

    change_type: Literal["added", "removed", "rewritten", "reordered"]
    original: str
    new: str
    reason: str
    evidence_refs: list[str] = Field(default_factory=list)


class CvFactVerificationDraft(BaseModel):
    model_config = ConfigDict(extra="ignore")

    claim: str
    status: Literal["verified", "unsupported", "ambiguous"]
    candidate_fact_ref: str | None = None
    note: str = ""


class TailoredCvDraft(BaseModel):
    model_config = ConfigDict(extra="ignore")

    summary: str
    experience: list[dict[str, Any]] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    education: list[dict[str, Any]] = Field(default_factory=list)
    changes: list[CvChangeItemDraft] = Field(default_factory=list)
    fact_verifications: list[CvFactVerificationDraft] = Field(default_factory=list)


class CoverLetterDraft(BaseModel):
    model_config = ConfigDict(extra="ignore")

    cover_letter: str
    evidence_refs: list[str] = Field(default_factory=list)


class ApplicationAnswerDraft(BaseModel):
    model_config = ConfigDict(extra="ignore")

    question: str
    proposed_answer: str
    classification: Literal["safe_verified", "needs_user_input", "sensitive_user_decision"]
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    warning: str | None = None


class KnockoutAnswerDraft(BaseModel):
    model_config = ConfigDict(extra="ignore")

    question: str
    proposed_answer: str
    evidence: str
    confidence: float = 1.0
    warning: str | None = None


class CareerReasonerError(Exception):
    """Base exception for reasoner failures."""
    pass


class CareerReasonerUnavailableError(CareerReasonerError):
    """Raised when reasoner provider is 'none' or offline."""
    pass


class CareerReasonerMalformedOutputError(CareerReasonerError):
    """Raised when structured output fails schema validation."""
    pass


class CareerReasoner(ABC):
    """Bounded Career Reasoner provider contract."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @abstractmethod
    async def evaluate(
        self,
        listing_ctx: CareerListingContext,
        candidate_ctx: CandidateCareerContext,
    ) -> DeepEvaluationDraft:
        """Perform deep fit evaluation between canonical listing evidence and candidate facts."""
        ...

    @abstractmethod
    async def tailor_cv(
        self,
        base_cv: dict[str, Any],
        listing_ctx: CareerListingContext,
        candidate_ctx: CandidateCareerContext,
        evaluation: DeepEvaluationDraft,
    ) -> TailoredCvDraft:
        """Tailor CV to listing without inventing facts, returning audit and claim verifications."""
        ...

    @abstractmethod
    async def generate_cover(
        self,
        listing_ctx: CareerListingContext,
        candidate_ctx: CandidateCareerContext,
        evaluation: DeepEvaluationDraft,
        stories: list[dict[str, Any]],
    ) -> CoverLetterDraft:
        """Generate evidence-bound cover letter from verified candidate context and current evaluation."""
        ...

    @abstractmethod
    async def answer_application(
        self,
        listing_ctx: CareerListingContext,
        candidate_ctx: CandidateCareerContext,
        evaluation: DeepEvaluationDraft,
        questions: list[str],
    ) -> list[ApplicationAnswerDraft]:
        """Classify and answer common application questions without guessing unknown information."""
        ...
