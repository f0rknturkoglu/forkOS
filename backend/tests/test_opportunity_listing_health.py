from datetime import UTC, datetime, timedelta

import pytest

from app.modules.opportunity.intelligence import quick_signals
from app.modules.opportunity.models import Opportunity
from app.modules.opportunity.schemas import OpportunityIntelligenceOut


@pytest.mark.no_database
def test_listing_health_never_modifies_candidate_score():
    """Invariant: Opportunity.score (candidate fit) is NEVER modified by listing health signals."""
    opp = Opportunity(
        kind="job",
        organization="Poor Quality Corp",
        url="https://example.com/job/bad",
        notes="",  # stub description
        compensation=None,  # missing salary
        source_status="closed",  # expired source
        score=92.5,  # High candidate match
    )

    now = datetime.now(UTC)
    intelligence = quick_signals(opp, title="Staff Backend Engineer", repost_count=5, now=now)

    assert isinstance(intelligence, OpportunityIntelligenceOut)
    assert intelligence.listing_health is not None
    # Listing health should be heavily penalized:
    # 100 - 30 (stub) - 15 (missing salary) - 20 (frequent repost) - 30 (closed) = 5
    assert intelligence.listing_health.health_score <= 10
    assert intelligence.listing_health.jd_completeness == "stub"
    assert intelligence.listing_health.salary_transparency == "missing"
    assert intelligence.listing_health.repost_frequency == "frequent"
    assert intelligence.listing_health.liveness_status == "expired"

    # CRITICAL: Candidate score must remain completely untouched
    assert opp.score == 92.5


@pytest.mark.no_database
def test_listing_health_perfect_listing():
    long_desc = "Detailed job description explaining all responsibilities, technologies, requirements and perks. " * 15
    opp = Opportunity(
        kind="job",
        organization="Top Tech",
        url="https://example.com/job/good",
        raw={"description": long_desc},
        compensation="$160,000 - $190,000 / year",
        source_status="active",
        last_seen_at=datetime.now(UTC) - timedelta(hours=2),
        score=75.0,
    )

    intelligence = quick_signals(opp, title="Senior Python Engineer", repost_count=0)

    assert intelligence.listing_health is not None
    assert intelligence.listing_health.health_score == 100
    assert intelligence.listing_health.jd_completeness == "complete"
    assert intelligence.listing_health.salary_transparency == "transparent"
    assert intelligence.listing_health.repost_frequency == "none"
    assert intelligence.listing_health.liveness_status == "live"
    assert opp.score == 75.0
