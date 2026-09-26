"""Cloud provider implementation for Career Reasoner (OpenAI, Gemini, OpenRouter)."""

from __future__ import annotations

import json
from typing import Any, Literal

import httpx

from app.config import settings
from app.modules.opportunity.candidate_context import CandidateCareerContext
from app.modules.opportunity.listing_context import CareerListingContext
from app.modules.opportunity.reasoner.base import (
    ApplicationAnswerDraft,
    CareerReasoner,
    CareerReasonerError,
    CareerReasonerMalformedOutputError,
    CareerReasonerUnavailableError,
    CoverLetterDraft,
    DeepEvaluationDraft,
    TailoredCvDraft,
)
from app.modules.opportunity.reasoner.prompts import (
    SYSTEM_PROMPT_APPLICATION_ANSWERS,
    SYSTEM_PROMPT_COVER_LETTER,
    SYSTEM_PROMPT_EVALUATION,
    SYSTEM_PROMPT_TAILOR_CV,
)

DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
}


class CloudCareerReasoner(CareerReasoner):
    """Direct, bounded HTTP client for cloud LLM reasoning providers."""

    def __init__(
        self,
        provider: Literal["openai", "gemini", "openrouter"],
        api_key: str | None = None,
        model_id: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self._provider = provider
        self.api_key = api_key or settings.career_reasoner_api_key
        self.model_id = model_id or settings.career_reasoner_model or (
            "gpt-4o-mini" if provider == "openai" else "gemini-1.5-flash" if provider == "gemini" else "meta-llama/llama-3.3-70b-instruct"
        )
        self.base_url = (base_url or settings.career_reasoner_base_url or DEFAULT_BASE_URLS.get(provider, "")).rstrip("/")
        self.timeout = timeout_seconds or settings.career_reasoner_timeout_seconds

    @property
    def provider_name(self) -> str:
        return self._provider

    async def _call_api(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if not self.api_key:
            raise CareerReasonerUnavailableError(
                f"Missing API key for provider '{self._provider}'. Set CAREER_REASONER_API_KEY."
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self._provider == "openrouter":
            headers["HTTP-Referer"] = "https://forkos.local"
            headers["X-Title"] = "forkOS"

        payload = {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": settings.career_reasoner_temperature,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                res.raise_for_status()
                data = res.json()
                raw_text = data["choices"][0]["message"]["content"]
                return json.loads(raw_text)
        except httpx.HTTPError as exc:
            raise CareerReasonerError(f"{self._provider} API call failed: {exc}") from exc
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise CareerReasonerMalformedOutputError(f"{self._provider} output malformed: {exc}") from exc

    async def evaluate(
        self,
        listing_ctx: CareerListingContext,
        candidate_ctx: CandidateCareerContext,
    ) -> DeepEvaluationDraft:
        user_prompt = (
            f"=== JOB LISTING EVIDENCE ===\n"
            f"Title: {listing_ctx.title}\n"
            f"Company: {listing_ctx.company}\n"
            f"Location: {listing_ctx.location}\n"
            f"Remote: {listing_ctx.remote}\n"
            f"Salary: {listing_ctx.salary or 'Undisclosed'}\n"
            f"Job Description (Untrusted Third-Party Content):\n{listing_ctx.canonical_jd}\n\n"
            f"=== CANDIDATE VERIFIED FACTS ===\n"
            f"Skills: {', '.join(candidate_ctx.skills)}\n"
            f"Target Roles: {', '.join(candidate_ctx.target_roles)}\n"
            f"Facts Inventory:\n" + "\n".join(f"- {f.key}: {f.value}" for f in candidate_ctx.facts[:30]) + "\n\n"
            "Evaluate candidate fit strictly using candidate facts. Produce DeepEvaluation JSON."
        )
        data = await self._call_api(SYSTEM_PROMPT_EVALUATION, user_prompt)
        try:
            draft = DeepEvaluationDraft.model_validate(data)
            draft.provider_metadata = {"provider": self._provider, "model": self.model_id}
            return draft
        except Exception as exc:
            raise CareerReasonerMalformedOutputError(f"Evaluation validation failed: {exc}") from exc

    async def tailor_cv(
        self,
        base_cv: dict[str, Any],
        listing_ctx: CareerListingContext,
        candidate_ctx: CandidateCareerContext,
        evaluation: DeepEvaluationDraft,
    ) -> TailoredCvDraft:
        user_prompt = (
            f"=== JOB LISTING ===\n"
            f"Title: {listing_ctx.title}\n"
            f"Company: {listing_ctx.company}\n"
            f"Required Strengths: {', '.join(evaluation.strengths)}\n\n"
            f"=== CANDIDATE FACTS ===\n"
            f"Skills: {', '.join(candidate_ctx.skills)}\n"
            f"Base CV: {json.dumps(base_cv)}\n\n"
            "Tailor the CV emphasizing verified strengths. Produce TailoredCvDraft JSON."
        )
        data = await self._call_api(SYSTEM_PROMPT_TAILOR_CV, user_prompt)
        try:
            return TailoredCvDraft.model_validate(data)
        except Exception as exc:
            raise CareerReasonerMalformedOutputError(f"CV tailoring validation failed: {exc}") from exc

    async def generate_cover(
        self,
        listing_ctx: CareerListingContext,
        candidate_ctx: CandidateCareerContext,
        evaluation: DeepEvaluationDraft,
        stories: list[dict[str, Any]],
    ) -> CoverLetterDraft:
        user_prompt = (
            f"=== JOB LISTING ===\n"
            f"Title: {listing_ctx.title}\n"
            f"Company: {listing_ctx.company}\n"
            f"Strengths: {', '.join(evaluation.strengths)}\n\n"
            f"=== CANDIDATE EVIDENCE ===\n"
            f"Skills: {', '.join(candidate_ctx.skills)}\n"
            f"STAR Stories:\n{json.dumps(stories[:2])}\n\n"
            "Write an evidence-bound cover letter. Produce CoverLetterDraft JSON."
        )
        data = await self._call_api(SYSTEM_PROMPT_COVER_LETTER, user_prompt)
        try:
            return CoverLetterDraft.model_validate(data)
        except Exception as exc:
            raise CareerReasonerMalformedOutputError(f"Cover letter validation failed: {exc}") from exc

    async def answer_application(
        self,
        listing_ctx: CareerListingContext,
        candidate_ctx: CandidateCareerContext,
        evaluation: DeepEvaluationDraft,
        questions: list[str],
    ) -> list[ApplicationAnswerDraft]:
        user_prompt = (
            f"=== JOB LISTING ===\n"
            f"Title: {listing_ctx.title}\n"
            f"Company: {listing_ctx.company}\n\n"
            f"=== CANDIDATE FACTS ===\n"
            f"Skills: {', '.join(candidate_ctx.skills)}\n\n"
            f"=== QUESTIONS ===\n" + "\n".join(f"- {q}" for q in questions) + "\n\n"
            "Answer the questions classifying as safe_verified, needs_user_input, or sensitive_user_decision. "
            "Return JSON: {\"answers\": [...]}"
        )
        data = await self._call_api(SYSTEM_PROMPT_APPLICATION_ANSWERS, user_prompt)
        try:
            raw_answers = data.get("answers", [])
            return [ApplicationAnswerDraft.model_validate(a) for a in raw_answers]
        except Exception as exc:
            raise CareerReasonerMalformedOutputError(f"Application answers validation failed: {exc}") from exc
