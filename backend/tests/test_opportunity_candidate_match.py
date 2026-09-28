"""Candidate matching uses evidence, not acquisition-source score reasons."""

from __future__ import annotations

import pytest

from app.modules.opportunity.candidate_context import CandidateCareerContext, CandidateFact
from app.modules.opportunity.candidate_match import apply_candidate_match, calculate_candidate_match
from app.modules.opportunity.models import Opportunity
from app.modules.opportunity.service import _calculate_skill_match


def _opportunity(source: str, description: str) -> Opportunity:
    return Opportunity(kind="job", source=source, raw={"description": description})


@pytest.mark.no_database
def test_same_listing_matches_identically_across_sources():
    context = CandidateCareerContext(
        revision="cv-1",
        base_cv={"content_available": True},
        facts=[
            CandidateFact(
                key="cv:line:1",
                value={"text": "Built Python services on AWS"},
                source_type="document",
            ),
            CandidateFact(key="skill:kubernetes", value="Kubernetes", source_type="config", verified=False),
        ],
    )
    description = "Must have Python, AWS, and Kubernetes experience."
    results = [
        calculate_candidate_match(_opportunity(source, description), "Backend Engineer", context)
        for source in ("forkjob_core", "careerops", "linkedin")
    ]
    assert results[0] == results[1] == results[2]
    assert "Python" in results[0]["matched"]
    assert "AWS" in results[0]["matched"]
    assert "Kubernetes" in results[0]["unknown"]
    assert "Kubernetes" not in results[0]["matched"]


@pytest.mark.no_database
def test_no_candidate_evidence_is_null_not_zero():
    opportunity = _opportunity("careerops", "Must have Python experience")
    apply_candidate_match(opportunity, "Backend Engineer", CandidateCareerContext(revision="empty"))
    assert opportunity.skill_match_ratio is None
    assert opportunity.raw["candidate_match"]["ratio"] is None
    assert _calculate_skill_match(opportunity, "Backend Engineer", {"skills": ["Python"]}) is None


@pytest.mark.no_database
def test_jd_change_invalidates_cached_match():
    opportunity = _opportunity("linkedin", "Must have Python experience")
    context = CandidateCareerContext(
        revision="cv-1",
        facts=[CandidateFact(key="skill:python", value="Python", source_type="config")],
    )
    apply_candidate_match(opportunity, "Backend Engineer", context)
    assert _calculate_skill_match(opportunity, "Backend Engineer", None) is not None
    opportunity.raw = {**opportunity.raw, "description": "Must have Kubernetes experience"}
    assert _calculate_skill_match(opportunity, "Backend Engineer", None) is None


@pytest.mark.no_database
def test_candidate_revision_changes_cached_result_on_recalculation():
    opportunity = _opportunity("forkjob_core", "Must have Python experience")
    first = CandidateCareerContext(
        revision="cv-1",
        facts=[CandidateFact(key="skill:python", value="Python", source_type="config")],
    )
    apply_candidate_match(opportunity, "Backend Engineer", first)
    assert opportunity.raw["candidate_match"]["candidate_revision"] == "cv-1"
    apply_candidate_match(opportunity, "Backend Engineer", CandidateCareerContext(revision="cv-2"))
    assert opportunity.raw["candidate_match"]["candidate_revision"] == "cv-2"
    assert opportunity.skill_match_ratio is None
