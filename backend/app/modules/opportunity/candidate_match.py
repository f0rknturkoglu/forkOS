"""Evidence-bound, source-independent candidate matching for canonical jobs."""

from __future__ import annotations

import re
from typing import Any

from app.modules.opportunity.candidate_context import CandidateCareerContext
from app.modules.opportunity.candidate_fit import canonical_description
from app.modules.opportunity.intelligence import (
    IMPORTANCE_WEIGHTS,
    _mentions_term,
    extract_requirements,
    listing_fingerprint,
)
from app.modules.opportunity.models import Opportunity

ALGORITHM = "candidate-requirements-v2"
_YEARS_RE = re.compile(r"\b(\d+)\+?\s*(?:years?|yrs?|yıl)\b", re.IGNORECASE)


def _document_text(context: CandidateCareerContext) -> str:
    return "\n".join(
        str(fact.value.get("text") or "")
        for fact in context.facts
        if fact.source_type == "document"
        and fact.verified
        and isinstance(fact.value, dict)
    )


def _candidate_years(context: CandidateCareerContext, text: str) -> int | None:
    if context.experience_years is not None:
        return int(context.experience_years)
    matches = [int(match) for match in _YEARS_RE.findall(text)]
    return max(matches) if matches else None


def calculate_candidate_match(
    opportunity: Opportunity, title: str, context: CandidateCareerContext
) -> dict[str, Any]:
    """Return an auditable match; unknown evidence never becomes a fake zero."""
    description = canonical_description(opportunity.raw) or ""
    requirements = extract_requirements(title, description)
    document_text = _document_text(context)
    has_cv = bool(context.base_cv and context.base_cv.get("content_available"))
    verified_skills = [
        str(fact.value)
        for fact in context.facts
        if fact.key.startswith("skill:")
        and fact.verified
        and (not has_cv or fact.source_type != "config")
    ]
    story_tags = [
        str(fact.value)
        for fact in context.facts
        if fact.key.startswith("story_tag:") and fact.verified
    ]
    has_evidence = bool(document_text or verified_skills or story_tags)
    results: list[dict[str, str]] = []
    known_weight = 0.0
    earned_weight = 0.0
    total_weight = 0.0
    for requirement in requirements:
        weight = float(IMPORTANCE_WEIGHTS[requirement.importance])
        total_weight += weight
        terms = [term for term in [requirement.name, *requirement.terms] if term.strip()]
        cv_hit = any(_mentions_term(document_text, term) for term in terms) if document_text else False
        skill_hit = any(
            _mentions_term(skill, term) or _mentions_term(term, skill)
            for skill in verified_skills
            for term in terms
        )
        story_hit = any(
            _mentions_term(tag, term) or _mentions_term(term, tag)
            for tag in story_tags
            for term in terms
        )
        match = "unknown"
        if has_evidence and (cv_hit or skill_hit):
            match = "strong"
        elif story_hit:
            match = "partial"
        elif requirement.name == "Deneyim süresi":
            requested = [int(value) for value in _YEARS_RE.findall(requirement.excerpt or "")]
            years = _candidate_years(context, document_text)
            if requested and years is not None:
                match = "strong" if years >= max(requested) else "missing"
        elif (
            not has_cv
            and context.target_roles
            and requirement.name.startswith("Rol odağı:")
            and any(_mentions_term(title, role) for role in context.target_roles)
        ):
            match = "partial"
        if match != "unknown":
            known_weight += weight
            earned_weight += weight * {"strong": 1.0, "partial": 0.5, "missing": 0.0}[match]
        results.append(
            {"requirement": requirement.name, "importance": requirement.importance, "match": match}
        )

    coverage = round(known_weight / total_weight, 3) if total_weight else 0.0
    ratio = round(earned_weight / known_weight, 3) if known_weight and coverage >= 0.25 else None
    return {
        "algorithm": ALGORITHM,
        "candidate_revision": context.revision,
        "listing_fingerprint": listing_fingerprint(opportunity, title=title),
        "ratio": ratio,
        "coverage": coverage,
        "requirements": results,
        "matched": [item["requirement"] for item in results if item["match"] in {"strong", "partial"}],
        "missing": [item["requirement"] for item in results if item["match"] == "missing"],
        "unknown": [item["requirement"] for item in results if item["match"] == "unknown"],
    }


def apply_candidate_match(
    opportunity: Opportunity, title: str, context: CandidateCareerContext
) -> None:
    if opportunity.kind != "job":
        return
    result = calculate_candidate_match(opportunity, title, context)
    opportunity.skill_match_ratio = result["ratio"]
    opportunity.raw = {**(opportunity.raw or {}), "candidate_match": result}
