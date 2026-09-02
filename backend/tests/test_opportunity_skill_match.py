from __future__ import annotations

import pytest
from app.modules.opportunity.models import Opportunity
from app.modules.opportunity.service import _calculate_skill_match


@pytest.mark.no_database
def test_calculate_skill_match_job():
    opp = Opportunity(
        kind="job",
        notes="We are looking for a backend developer skilled in Kubernetes, AWS and Redis.",
        raw={
            "forkjob": {
                "score": 85,
                "reasons": {
                    "skills": [
                        {"name": "python", "points": 8.0, "where": "title"},
                        {"name": "docker", "points": 6.0, "where": "body"},
                    ]
                },
                "description": "Experience with Python, Docker, Kubernetes and Redis is required.",
            }
        },
    )

    match = _calculate_skill_match(opp, "Python Software Engineer", opp.raw["forkjob"]["reasons"])
    assert match is not None
    assert "python" in match.matched
    assert "docker" in match.matched
    assert "kubernetes" in match.missing
    assert "redis" in match.missing
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
