from __future__ import annotations

import pytest

from app.modules.opportunity.candidate_context import CandidateCareerContext, CandidateFact
from app.modules.opportunity.candidate_match import apply_candidate_match
from app.modules.opportunity.models import Opportunity
from app.modules.opportunity.service import _calculate_skill_match


@pytest.mark.no_database
def test_calculate_skill_match_job():
    opp = Opportunity(
        kind="job",
        raw={"description": "Experience with Python, Docker, Kubernetes and Redis is required."},
    )
    context = CandidateCareerContext(
        revision="cv-1",
        base_cv={"content_available": True},
        facts=[
            CandidateFact(
                key="cv:line:1",
                value={"text": "Python and Docker projects"},
                source_type="document",
                verified=True,
            )
        ],
    )
    apply_candidate_match(opp, "Python Software Engineer", context)
    match = _calculate_skill_match(opp, "Python Software Engineer", {"skills": ["fake"]})
    assert match is not None
    assert "Python" in match.matched
    assert "Docker" in match.matched
    assert "Kubernetes" not in match.missing
    assert "Redis" not in match.missing
    assert match.match_ratio > 0.0
    assert match.match_ratio <= 1.0


@pytest.mark.no_database
def test_calculate_skill_match_announcement_returns_none():
    opp = Opportunity(
        kind="announcement",
        raw={},
    )
    match = _calculate_skill_match(opp, "ÖSYM 2026/1 KPSS Tercih Kılavuzu", None)
    assert match is None
