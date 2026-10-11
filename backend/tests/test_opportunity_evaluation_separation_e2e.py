from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.core.models import Entity
from app.db import SessionLocal
from app.modules.opportunity import intelligence, service
from app.modules.opportunity.candidate_context import build_candidate_career_context
from app.modules.opportunity.candidate_fit import score_canonical_opportunity
from app.modules.opportunity.candidate_match import apply_candidate_match
from app.modules.opportunity.evaluation_service import CareerEvaluationService
from app.modules.opportunity.models import Opportunity
from app.modules.opportunity.reasoner.base import CareerReasoner, DeepEvaluationDraft
from app.modules.opportunity.reasoner.mock import DeterministicMockCareerReasoner
from app.modules.opportunity.schemas import OpportunityIn


@pytest.mark.asyncio
async def test_evaluation_separation_coexistence_both_orders():
    """Ensure candidate_evaluation and deep_evaluation coexist and preserve both execution orders."""
    async with SessionLocal() as session:
        # 1. Create opportunity
        opp_in = OpportunityIn(
            kind="job",
            title="Senior Python Backend Engineer",
            organization="Acme Labs",
            location="Berlin, Germany",
            remote="remote",
            compensation="€80,000 - €95,000",
            raw={
                "description": (
                    "We are seeking a Senior Python Backend Engineer with strong expertise in FastAPI, "
                    "PostgreSQL, and distributed architectures. You will design, build, and maintain "
                    "mission-critical backend services and APIs for our high-throughput platform."
                )
            },
        )
        opp_out = await service.create(session, opp_in)
        opp_id = opp_out.id
        await session.commit()

    # --- ORDER 1: Fast Candidate Match first -> Deep Evaluation second ---
    async with SessionLocal() as session:
        cand_eval = await intelligence.evaluate_opportunity(session, opp_id)
        assert cand_eval is not None
        await session.commit()

    async with SessionLocal() as session:
        opp = await session.get(Opportunity, opp_id)
        assert opp is not None
        assert opp.score is not None
        score_v1 = opp.score

        # Verify fast match is populated
        assert opp.candidate_evaluation is not None
        assert opp.candidate_evaluated_at is not None
        cand_eval_v1 = dict(opp.candidate_evaluation)
        cand_eval_time_v1 = opp.candidate_evaluated_at

        # Run Deep Evaluation via mock reasoner
        eval_service = CareerEvaluationService(reasoner=DeterministicMockCareerReasoner())
        deep_result = await eval_service.evaluate_opportunity(session, opp_id)
        assert deep_result is not None
        await session.commit()

    async with SessionLocal() as session:
        opp = await session.get(Opportunity, opp_id)
        assert opp is not None
        # Verify both coexist
        assert opp.candidate_evaluation == cand_eval_v1
        assert opp.candidate_evaluated_at == cand_eval_time_v1
        assert opp.deep_evaluation is not None
        assert len(opp.deep_evaluation) > 0
        assert opp.deep_evaluated_at is not None
        deep_eval_v1 = dict(opp.deep_evaluation)
        deep_eval_time_v1 = opp.deep_evaluated_at

        # Fast score must NOT be modified by deep evaluation
        assert opp.score == score_v1

    # --- ORDER 2: Deep Evaluation exists -> Fast Candidate Match runs again ---
    async with SessionLocal() as session:
        opp = await session.get(Opportunity, opp_id)
        assert opp is not None
        entity = await session.get(Entity, opp_id)
        assert entity is not None

        # Re-apply candidate match and intelligence evaluation
        candidate_ctx = await build_candidate_career_context(session)
        apply_candidate_match(opp, entity.title, candidate_ctx)
        await intelligence.evaluate_opportunity(session, opp_id)
        await session.commit()

    async with SessionLocal() as session:
        opp = await session.get(Opportunity, opp_id)
        assert opp is not None

        # Verify deep_evaluation and deep_evaluated_at are COMPLETELY PRESERVED
        assert opp.deep_evaluation == deep_eval_v1
        assert opp.deep_evaluated_at == deep_eval_time_v1

        # Fast match updated without touching deep eval
        assert opp.candidate_evaluation is not None
        assert opp.candidate_evaluated_at is not None
        assert opp.score == score_v1


@pytest.mark.asyncio
async def test_deep_evaluation_never_overwrites_fast_score():
    async with SessionLocal() as session:
        opp_in = OpportunityIn(
            kind="job",
            title="Lead Data Engineer",
            organization="Data Corp",
            location="Remote",
            remote="remote",
            raw={
                "description": (
                    "We are looking for a Lead Data Engineer to lead our data platform engineering team. "
                    "Required skills include advanced SQL, Python data pipelines, distributed data processing, "
                    "and cloud database optimization across large-scale analytics warehouses."
                )
            },
        )
        opp_out = await service.create(session, opp_in)
        opp_id = opp_out.id
        await session.commit()

    async with SessionLocal() as session:
        opp = await session.get(Opportunity, opp_id)
        assert opp is not None
        initial_score = opp.score
        assert initial_score is not None

        eval_service = CareerEvaluationService(reasoner=DeterministicMockCareerReasoner())
        await eval_service.evaluate_opportunity(session, opp_id)
        await session.commit()

    async with SessionLocal() as session:
        opp = await session.get(Opportunity, opp_id)
        assert opp is not None
        # Score must stay identical to initial fast score
        assert opp.score == initial_score
        assert opp.score_source == "forkjob_core-candidate-fit-v2"
        assert opp.deep_evaluation is not None


class FailingCareerReasoner(CareerReasoner):
    @property
    def provider_name(self) -> str:
        return "failing_mock"

    async def evaluate(self, listing_ctx, candidate_ctx) -> DeepEvaluationDraft:
        raise RuntimeError("External reasoning engine unavailable or timed out")

    async def tailor_cv(self, base_cv, listing_ctx, candidate_ctx, evaluation):
        raise NotImplementedError

    async def generate_cover(self, listing_ctx, candidate_ctx, evaluation, stories):
        raise NotImplementedError

    async def answer_application(self, listing_ctx, candidate_ctx, evaluation, questions):
        raise NotImplementedError


@pytest.mark.asyncio
async def test_deep_evaluation_failure_preserves_fast_match_and_score():
    async with SessionLocal() as session:
        opp_in = OpportunityIn(
            kind="job",
            title="Systems Architect",
            organization="Infra Co",
            location="Remote",
            remote="remote",
            raw={
                "description": (
                    "We are hiring a Systems Architect to oversee our cloud infrastructure and Linux engineering operations. "
                    "You will be responsible for system reliability, container orchestration, and multi-region deployment architectures."
                )
            },
        )
        opp_out = await service.create(session, opp_in)
        opp_id = opp_out.id
        await session.commit()

    async with SessionLocal() as session:
        await intelligence.evaluate_opportunity(session, opp_id)
        await session.commit()

    async with SessionLocal() as session:
        opp = await session.get(Opportunity, opp_id)
        assert opp is not None
        initial_score = opp.score
        initial_cand_eval = dict(opp.candidate_evaluation)

        eval_service = CareerEvaluationService(reasoner=FailingCareerReasoner())
        with pytest.raises(RuntimeError, match="External reasoning engine unavailable"):
            await eval_service.evaluate_opportunity(session, opp_id)

    async with SessionLocal() as session:
        opp = await session.get(Opportunity, opp_id)
        assert opp is not None
        assert opp.score == initial_score
        assert opp.candidate_evaluation == initial_cand_eval
        assert opp.deep_evaluation is None or opp.deep_evaluation == {}


@pytest.mark.asyncio
async def test_rescore_preserves_both_evaluations():
    now = datetime.now(UTC)
    opp = Opportunity(
        id=uuid.uuid4(),
        kind="job",
        source="forkjob_core:fourdayweek",
        organization="Tech Co",
        location="Remote, ES",
        published_at=now,
        raw={"description": "Senior Backend Developer in Python"},
        candidate_evaluation={"version": "career-ops-v1", "archetype": "general_ic"},
        candidate_evaluated_at=now,
        deep_evaluation={"role_fit": "strong", "confidence": 0.95},
        deep_evaluated_at=now,
    )
    score_canonical_opportunity(opp, "Senior Backend Developer", now=now)

    assert opp.score is not None
    assert opp.score_source == "forkjob_core-candidate-fit-v2"
    # Rescore never mutates either evaluation payload or timestamp
    assert opp.candidate_evaluation == {"version": "career-ops-v1", "archetype": "general_ic"}
    assert opp.candidate_evaluated_at == now
    assert opp.deep_evaluation == {"role_fit": "strong", "confidence": 0.95}
    assert opp.deep_evaluated_at == now


@pytest.mark.asyncio
async def test_source_independent_scoring_identical():
    """Verify that identical opportunity inputs from different sources produce identical scores."""
    now = datetime.now(UTC)
    opp1 = Opportunity(
        id=uuid.uuid4(),
        kind="job",
        source="forkjob_core:fourdayweek",
        organization="Tech Co",
        location="Remote, ES",
        country="ES",
        region="EU",
        remote="remote",
        compensation="€70,000",
        published_at=now,
        raw={"description": "Senior Backend Developer in Python"},
    )
    score_canonical_opportunity(opp1, "Senior Backend Developer", now=now)

    opp2 = Opportunity(
        id=uuid.uuid4(),
        kind="job",
        source="careerops:boards",
        organization="Tech Co",
        location="Remote, ES",
        country="ES",
        region="EU",
        remote="remote",
        compensation="€70,000",
        published_at=now,
        raw={"description": "Senior Backend Developer in Python"},
    )
    score_canonical_opportunity(opp2, "Senior Backend Developer", now=now)

    assert opp1.score == opp2.score
    assert opp1.score is not None
    assert opp1.score > 0
    assert opp1.raw["candidate_fit"]["reasons"] == opp2.raw["candidate_fit"]["reasons"]


@pytest.mark.asyncio
async def test_zero_evidence_candidate_matching():
    """Verify that zero evidence produces 0/null score, never synthetic guesses."""
    async with SessionLocal() as session:
        opp_in = OpportunityIn(
            kind="job",
            title="Senior Theoretical High Energy Nuclear Physicist",
            organization="CERN",
            location="Geneva, Switzerland",
            raw={"description": "Lattice gauge theory, quantum chromodynamics, hadron phenomenology."},
        )
        opp_out = await service.create(session, opp_in)
        opp_id = opp_out.id
        await session.commit()

    async with SessionLocal() as session:
        opp = await session.get(Opportunity, opp_id)
        assert opp is not None
        # Check skill match ratio: no matching skills found -> 0.0 or None
        assert opp.skill_match_ratio is None or opp.skill_match_ratio == 0.0
        cm = (opp.raw or {}).get("candidate_match")
        assert cm is not None
        assert cm["ratio"] is None or cm["ratio"] == 0.0
