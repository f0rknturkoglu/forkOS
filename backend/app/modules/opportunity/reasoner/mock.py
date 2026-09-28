"""Deterministic Mock Career Reasoner: Produces evidence-bound outputs for tests without external calls."""

from __future__ import annotations

import re
from typing import Any

from app.modules.opportunity.candidate_context import CandidateCareerContext
from app.modules.opportunity.listing_context import CareerListingContext
from app.modules.opportunity.reasoner.base import (
    ApplicationAnswerDraft,
    CareerReasoner,
    CoverLetterDraft,
    CvChangeItemDraft,
    CvFactVerificationDraft,
    DeepEvaluationDraft,
    RequirementAssessmentDraft,
    TailoredCvDraft,
)


class DeterministicMockCareerReasoner(CareerReasoner):
    """Deterministic, verified reasoner for unit/integration testing."""

    @property
    def provider_name(self) -> str:
        return "mock"

    async def evaluate(
        self,
        listing_ctx: CareerListingContext,
        candidate_ctx: CandidateCareerContext,
    ) -> DeepEvaluationDraft:
        jd_text = (listing_ctx.canonical_jd or "").casefold()
        candidate_skills = {s.casefold(): s for s in candidate_ctx.skills}

        # Deterministic extraction of requirements from JD
        detected_tech = []
        known_keywords = [
            "python",
            "fastapi",
            "react",
            "typescript",
            "c#",
            ".net",
            "sql",
            "postgresql",
            "docker",
            "kubernetes",
            "aws",
            "azure",
            "graphql",
            "rust",
            "go",
            "llm",
        ]
        for kw in known_keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", jd_text):
                detected_tech.append(kw)

        must_have: list[RequirementAssessmentDraft] = []
        strengths: list[str] = []
        partial_matches: list[str] = []
        missing_requirements: list[str] = []
        evidence_list: list[str] = []

        for req in detected_tech:
            if req in candidate_skills:
                fact_ref = f"skill:{req}"
                must_have.append(
                    RequirementAssessmentDraft(
                        requirement=f"Proficiency in {candidate_skills[req]}",
                        classification="strong",
                        reason=f"Candidate has verified skill {candidate_skills[req]}.",
                        candidate_evidence_refs=[fact_ref],
                        listing_evidence_refs=[f"jd_mention:{req}"],
                        confidence=1.0,
                    )
                )
                strengths.append(candidate_skills[req])
                evidence_list.append(fact_ref)
            else:
                must_have.append(
                    RequirementAssessmentDraft(
                        requirement=f"Experience with {req.upper()}",
                        classification="missing",
                        reason=f"No verified record of {req.upper()} found in candidate facts.",
                        candidate_evidence_refs=[],
                        listing_evidence_refs=[f"jd_mention:{req}"],
                        confidence=0.9,
                    )
                )
                missing_requirements.append(req.upper())

        # Seniority fit
        seniority = "mid_level"
        if "senior" in jd_text or "lead" in jd_text:
            seniority = "senior"
        elif "junior" in jd_text or "entry" in jd_text:
            seniority = "junior"

        # Work authorization detection
        work_auth_status = "unknown"
        work_auth_details = "Listing does not state explicit work authorization constraints."
        work_auth_evidence = []
        if (
            "must be authorized to work" in jd_text
            or "us citizenship" in jd_text
            or "no sponsorship" in jd_text
        ):
            work_auth_status = "likely_constraint"
            work_auth_details = (
                "Job posting indicates work authorization or citizenship requirement."
            )
            work_auth_evidence.append("jd_text:work_auth_statement")

        # Compensation alignment
        comp_alignment = "unknown"
        if listing_ctx.salary:
            comp_alignment = "disclosed"

        role_fit = (
            "strong"
            if len(strengths) > len(missing_requirements)
            else "partial"
            if strengths
            else "low"
        )

        return DeepEvaluationDraft(
            overall_assessment=(
                f"Candidate aligns on {len(strengths)} core requirements ({', '.join(strengths) if strengths else 'none'}), "
                f"with {len(missing_requirements)} missing areas ({', '.join(missing_requirements) if missing_requirements else 'none'})."
            ),
            confidence=0.95,
            role_fit=role_fit,
            seniority_fit=f"Appropriate for {seniority} level based on verified skills and background.",
            location_fit=f"Listing location '{listing_ctx.location}' evaluated against candidate preference.",
            must_have=must_have,
            nice_to_have=[],
            strengths=strengths,
            partial_matches=partial_matches,
            missing_requirements=missing_requirements,
            work_authorization={
                "status": work_auth_status,
                "details": work_auth_details,
                "evidence": work_auth_evidence,
            },
            sponsorship={
                "sponsorship_available": "unknown"
                if "sponsor" not in jd_text
                else "no sponsor" not in jd_text,
                "notes": "Extracted deterministically from listing text.",
            },
            compensation={
                "listing_compensation": listing_ctx.salary,
                "candidate_preference": str(candidate_ctx.salary_min)
                if candidate_ctx.salary_min
                else None,
                "alignment": comp_alignment,
                "details": "Deterministic salary comparison.",
            },
            risks=["Missing requirements: " + ", ".join(missing_requirements)]
            if missing_requirements
            else [],
            unknowns=["Specific team day-to-day workflow not detailed in JD."]
            if not missing_requirements
            else [],
            recommended_next_steps=[
                "Highlight verified strengths in application package.",
                "Address any skill gaps proactively in cover letter.",
            ],
            evidence=evidence_list,
            provider_metadata={
                "provider": "mock",
                "model": "deterministic-v1",
            },
        )

    async def tailor_cv(
        self,
        base_cv: dict[str, Any],
        listing_ctx: CareerListingContext,
        candidate_ctx: CandidateCareerContext,
        evaluation: DeepEvaluationDraft,
    ) -> TailoredCvDraft:
        # Reorder and emphasize verified skills that match listing strengths
        matched = set(evaluation.strengths)
        ordered_skills = sorted(candidate_ctx.skills, key=lambda s: (0 if s in matched else 1, s))

        changes = [
            CvChangeItemDraft(
                change_type="reordered",
                original="Standard skill ordering",
                new=f"Prioritized relevant skills: {', '.join(evaluation.strengths)}",
                reason="Match job posting requirements without adding unverified technologies",
                evidence_refs=[f"skill:{s.lower()}" for s in evaluation.strengths],
            )
        ]

        # Audit and verify claims against candidate facts
        fact_verifications = []
        for s in candidate_ctx.skills:
            fact_verifications.append(
                CvFactVerificationDraft(
                    claim=f"Technical proficiency in {s}",
                    status="verified",
                    candidate_fact_ref=f"skill:{s.lower()}",
                    note="Verified against canonical candidate context",
                )
            )

        return TailoredCvDraft(
            summary=" ".join(
                str(f.value.get("text", ""))
                for f in candidate_ctx.facts
                if isinstance(f.value, dict) and f.value.get("section") == "summary"
            ),
            skills=ordered_skills,
            experience=[
                {"text": f.value["text"]}
                for f in candidate_ctx.facts
                if isinstance(f.value, dict)
                and f.value.get("section") == "employment"
            ],
            education=[
                {"text": f.value["text"]}
                for f in candidate_ctx.facts
                if isinstance(f.value, dict) and f.value.get("section") == "education"
            ],
            changes=changes,
            projects=[{"text": f.value["text"]} for f in candidate_ctx.facts
                      if isinstance(f.value, dict) and f.value.get("section") == "projects"],
            languages=[f.value["text"] for f in candidate_ctx.facts
                       if isinstance(f.value, dict) and f.value.get("section") == "languages"],
            fact_verifications=fact_verifications,
        )

    async def generate_cover(
        self,
        listing_ctx: CareerListingContext,
        candidate_ctx: CandidateCareerContext,
        evaluation: DeepEvaluationDraft,
        stories: list[dict[str, Any]],
    ) -> CoverLetterDraft:
        company = listing_ctx.company or "the engineering team"
        role = listing_ctx.title or "this position"
        key_skills = (
            ", ".join(evaluation.strengths[:3])
            if evaluation.strengths
            else "modern software development"
        )

        story_paragraph = ""
        evidence_refs = []
        if stories:
            top_story = stories[0]
            story_title = top_story.get("title", "")
            action = top_story.get("action", "")
            result = top_story.get("result", "")
            story_paragraph = (
                f"\nIn my previous work on {story_title}, {action} which resulted in {result}.\n"
            )
            evidence_refs.append(f"career_story:{top_story.get('id')}")

        for s in evaluation.strengths[:3]:
            evidence_refs.append(f"skill:{s.lower()}")

        text = (
            f"Dear {company} Hiring Team,\n\n"
            f"I am writing to express my interest in the {role} role at {company}. "
            f"My technical background directly aligns with your requirements for {key_skills}."
            f"{story_paragraph}\n"
            f"I look forward to discussing how my experience can contribute to {company}'s goals.\n\n"
            "Sincerely,\n"
            "Candidate"
        )

        return CoverLetterDraft(
            cover_letter=text,
            evidence_refs=evidence_refs,
        )

    async def answer_application(
        self,
        listing_ctx: CareerListingContext,
        candidate_ctx: CandidateCareerContext,
        evaluation: DeepEvaluationDraft,
        questions: list[str],
    ) -> list[ApplicationAnswerDraft]:
        answers = []
        for q in questions:
            ql = q.lower()
            if "skill" in ql or "technolog" in ql or "experience with" in ql:
                answers.append(
                    ApplicationAnswerDraft(
                        question=q,
                        proposed_answer=f"I have extensive verified experience with {', '.join(candidate_ctx.skills[:4])}.",
                        classification="safe_verified",
                        evidence_refs=[f"skill:{s.lower()}" for s in candidate_ctx.skills[:4]],
                        confidence=1.0,
                    )
                )
            elif "salary" in ql or "compensation" in ql:
                if candidate_ctx.salary_min:
                    answers.append(
                        ApplicationAnswerDraft(
                            question=q,
                            proposed_answer=f"{candidate_ctx.salary_min} {candidate_ctx.salary_currency or 'USD'}",
                            classification="safe_verified",
                            evidence_refs=["salary_preference"],
                            confidence=0.9,
                        )
                    )
                else:
                    answers.append(
                        ApplicationAnswerDraft(
                            question=q,
                            proposed_answer="",
                            classification="needs_user_input",
                            evidence_refs=[],
                            confidence=0.0,
                            warning="Candidate salary expectation not specified in profile.",
                        )
                    )
            elif "authorized" in ql or "visa" in ql or "sponsorship" in ql:
                answers.append(
                    ApplicationAnswerDraft(
                        question=q,
                        proposed_answer="",
                        classification="sensitive_user_decision",
                        evidence_refs=[],
                        confidence=0.0,
                        warning="Work authorization answers require explicit user decision.",
                    )
                )
            else:
                answers.append(
                    ApplicationAnswerDraft(
                        question=q,
                        proposed_answer=f"Relevant experience demonstrated across {len(candidate_ctx.skills)} core technologies.",
                        classification="safe_verified",
                        evidence_refs=[f"skill:{s.lower()}" for s in candidate_ctx.skills[:2]],
                        confidence=0.85,
                    )
                )
        return answers
