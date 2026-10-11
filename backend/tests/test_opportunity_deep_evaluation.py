"""C4 Deep Evaluation test suite (Section 33 & 35)."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import create_entity
from app.db import SessionLocal
from app.modules.opportunity.evaluation_service import (
    CareerEvaluationService,
    DeepEvaluation,
)
from app.modules.opportunity.intelligence import evaluate_opportunity as evaluate_candidate
from app.modules.opportunity.models import CareerStory, Opportunity, OpportunitySourceObservation
from app.modules.opportunity.reasoner.base import (
    CareerReasonerUnavailableError,
)
from app.modules.opportunity.reasoner.mock import DeterministicMockCareerReasoner
from app.modules.opportunity.reasoner.none import NoneCareerReasoner


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def _seed_test_opportunity(
    session: AsyncSession,
    *,
    title: str = "Senior Backend Engineer",
    description: str = "We need Python, FastAPI, and PostgreSQL expertise for distributed backend microservices. The candidate will design scalable systems and collaborate with cross-functional product teams across Europe.",
    location: str = "Remote, TR",
    score: float = 75.0,
) -> Opportunity:
    entity = await create_entity(session, type="opportunity", title=title)
    opp = Opportunity(
        id=entity.id,
        kind="job",
        organization="TestCorp",
        location=location,
        remote="remote",
        compensation="80000 USD",
        score=score,
        score_source="forkjob_rule",
        score_computed_at=datetime.now(UTC),
        found_at=datetime.now(UTC),
        raw={"description": description},
    )
    session.add(opp)

    obs = OpportunitySourceObservation(
        opportunity_id=entity.id,
        source="test_feed",
        canonical_url="https://example.com/jobs/123",
        source_status="active",
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
        enrichment={
            "jd_extraction": {
                "identity_status": "valid_job",
                "promoted": True,
                "jd_text_length": len(description),
            }
        },
    )
    session.add(obs)
    await session.flush()
    return opp


@pytest.mark.asyncio
async def test_deep_evaluation_evidence_matching_and_no_invention(db_session: AsyncSession):
    """C4: Verified candidate evidence maps to strong, missing to missing, never invented."""
    opp = await _seed_test_opportunity(
        db_session,
        description="Must have strong Python, FastAPI, and Rust knowledge. Docker experience is nice to have. The role involves designing distributed systems, microservices, and high-performance databases.",
    )

    reasoner = DeterministicMockCareerReasoner()
    service = CareerEvaluationService(reasoner=reasoner)

    evaluation = await service.evaluate_opportunity(db_session, opp.id, force=True)

    assert isinstance(evaluation, DeepEvaluation)
    assert evaluation.opportunity_id == str(opp.id)
    assert not evaluation.is_stale

    # Must have matches
    # Python & FastAPI are in candidate facts (from config.yaml) -> strong
    python_req = [r for r in evaluation.must_have if "python" in r.requirement.casefold()]
    assert python_req and python_req[0].classification == "strong"
    assert "skill:python" in python_req[0].candidate_evidence_refs

    # Rust is NOT in candidate facts -> missing, never invented!
    rust_req = [r for r in evaluation.must_have if "rust" in r.requirement.casefold()]
    assert rust_req and rust_req[0].classification == "missing"
    assert rust_req[0].candidate_evidence_refs == []

    # Opportunity.score must NEVER be overwritten by evaluation (Section 9)
    await db_session.refresh(opp)
    assert opp.score == 75.0
    assert opp.score_source == "forkjob_rule"


@pytest.mark.asyncio
async def test_deep_evaluation_staleness_on_jd_change(db_session: AsyncSession):
    """C4: Listing fingerprint change causes evaluation to become stale."""
    opp = await _seed_test_opportunity(
        db_session,
        description="Initial description with Python and SQL requirements. The role requires building microservices, writing tests, and maintaining PostgreSQL databases for production.",
    )

    service = CareerEvaluationService(reasoner=DeterministicMockCareerReasoner())
    eval1 = await service.evaluate_opportunity(db_session, opp.id, force=True)
    assert not eval1.is_stale

    # Material JD change
    raw = dict(opp.raw or {})
    raw["description"] = "Updated description with completely new Golang and Kubernetes requirements. The engineer will maintain cloud-native systems, monitor clusters, and deploy via GitOps."
    opp.raw = raw
    await db_session.flush()

    # Re-fetch evaluation -> dynamically detected as stale!
    eval_fetched = await service.get_evaluation(db_session, opp.id)
    assert eval_fetched is not None
    assert eval_fetched.is_stale is True
    assert any("Job description or listing details modified" in r for r in eval_fetched.stale_reasons)


@pytest.mark.asyncio
async def test_deep_evaluation_staleness_on_candidate_facts_change(db_session: AsyncSession):
    """C4: Adding or modifying verified candidate facts causes evaluation to become stale."""
    opp = await _seed_test_opportunity(db_session)
    service = CareerEvaluationService(reasoner=DeterministicMockCareerReasoner())

    eval1 = await service.evaluate_opportunity(db_session, opp.id, force=True)
    assert not eval1.is_stale

    # Add a new verified CareerStory
    story_entity = await create_entity(db_session, type="career_story", title="Scaling API")
    story = CareerStory(
        id=story_entity.id,
        situation="High latency under load",
        task="Optimize database queries",
        action="Introduced read replicas",
        result="Reduced latency by 40%",
        provenance="supported",
        tags=["python", "postgresql"],
    )
    db_session.add(story)
    await db_session.flush()

    # Re-fetch evaluation -> dynamically detected as stale because candidate facts revision changed!
    eval_fetched = await service.get_evaluation(db_session, opp.id)
    assert eval_fetched is not None
    assert eval_fetched.is_stale is True
    assert any("Candidate facts or profile modified" in r for r in eval_fetched.stale_reasons)


@pytest.mark.asyncio
async def test_deep_evaluation_cache_reuse(db_session: AsyncSession):
    """C4: Unchanged inputs reuse existing evaluation without wasting calls (Cost control)."""
    opp = await _seed_test_opportunity(db_session)

    call_count = 0

    class CountingMockReasoner(DeterministicMockCareerReasoner):
        async def evaluate(self, listing_ctx, candidate_ctx):
            nonlocal call_count
            call_count += 1
            return await super().evaluate(listing_ctx, candidate_ctx)

    service = CareerEvaluationService(reasoner=CountingMockReasoner())

    # Call 1: fresh evaluation
    eval1 = await service.evaluate_opportunity(db_session, opp.id, force=False)
    assert call_count == 1

    # Call 2: not force, unchanged -> reuses cache!
    eval2 = await service.evaluate_opportunity(db_session, opp.id, force=False)
    assert call_count == 1
    assert eval2.listing_fingerprint == eval1.listing_fingerprint

    # Call 3: force=True -> runs fresh
    await service.evaluate_opportunity(db_session, opp.id, force=True)
    assert call_count == 2


@pytest.mark.asyncio
async def test_deep_evaluation_none_provider_fails_safely(db_session: AsyncSession):
    """C4: When provider is 'none', evaluation fails truthfully without corrupting state."""
    opp = await _seed_test_opportunity(db_session)
    service = CareerEvaluationService(reasoner=NoneCareerReasoner())

    with pytest.raises(CareerReasonerUnavailableError) as exc_info:
        await service.evaluate_opportunity(db_session, opp.id)

    assert "CAREER_REASONER_PROVIDER='none'" in str(exc_info.value)
    # Opportunity remains uncorrupted
    await db_session.refresh(opp)
    assert opp.deep_evaluation == {}
    assert opp.score == 75.0


@pytest.mark.asyncio
async def test_candidate_and_deep_evaluations_do_not_overwrite_each_other(
    db_session: AsyncSession,
):
    opp = await _seed_test_opportunity(db_session)
    candidate = await evaluate_candidate(db_session, opp.id)
    assert candidate is not None
    await db_session.refresh(opp)
    candidate_payload = dict(opp.candidate_evaluation)

    service = CareerEvaluationService(reasoner=DeterministicMockCareerReasoner())
    deep = await service.evaluate_opportunity(db_session, opp.id, force=True)
    await db_session.refresh(opp)
    assert opp.candidate_evaluation == candidate_payload
    assert opp.deep_evaluation["overall_assessment"] == deep.overall_assessment

    refreshed_candidate = await evaluate_candidate(db_session, opp.id)
    assert refreshed_candidate is not None
    await db_session.refresh(opp)
    assert opp.deep_evaluation["overall_assessment"] == deep.overall_assessment
    assert (await service.get_evaluation(db_session, opp.id)).is_stale is False


@pytest.mark.asyncio
async def test_deep_evaluation_rejects_invalid_non_job_jd(db_session: AsyncSession):
    """C4: Rejected/generic/error-page extractions must NEVER enter Specialist JD context."""
    entity = await create_entity(db_session, type="opportunity", title="Expired Job")
    opp = Opportunity(
        id=entity.id,
        kind="job",
        found_at=datetime.now(UTC),
        raw={"description": ""},
    )
    db_session.add(opp)
    obs = OpportunitySourceObservation(
        opportunity_id=entity.id,
        source="test_feed",
        canonical_url="https://boards.greenhouse.io/gitlab/jobs/4279007005",
        source_status="active",
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
        enrichment={
            "jd_extraction": {
                "identity_status": "invalid_non_job",
                "promoted": False,
                "promotion_reason": "provider_error_redirect",
            }
        },
    )
    db_session.add(obs)
    await db_session.flush()

    service = CareerEvaluationService(reasoner=DeterministicMockCareerReasoner())
    with pytest.raises(ValueError) as exc_info:
        await service.evaluate_opportunity(db_session, opp.id)

    assert "Job description is invalid or rejected" in str(exc_info.value)
