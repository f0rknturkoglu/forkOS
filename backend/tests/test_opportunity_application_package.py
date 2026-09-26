"""C5 Application Package test suite (Section 34 & 36)."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import create_entity
from app.db import SessionLocal
from app.modules.document.models import Document
from app.modules.opportunity.evaluation_service import CareerEvaluationService
from app.modules.opportunity.models import Application, CareerStory, Opportunity, OpportunitySourceObservation
from app.modules.opportunity.package_service import ApplicationPackageService
from app.modules.opportunity.reasoner.base import (
    ApplicationAnswerDraft,
    CareerReasoner,
    CoverLetterDraft,
    CvChangeItemDraft,
    CvFactVerificationDraft,
    DeepEvaluationDraft,
    KnockoutAnswerDraft,
    RequirementAssessmentDraft,
    TailoredCvDraft,
)
from app.modules.opportunity.reasoner.mock import DeterministicMockCareerReasoner


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
async def test_application_package_master_cv_immutability(db_session: AsyncSession):
    """C5: Master CV entity and document record remain strictly immutable during tailoring."""
    # Seed a Master CV document
    doc_entity = await create_entity(db_session, type="document", title="Furkan_Turkoglu_Master_CV.pdf")
    base_doc = Document(
        id=doc_entity.id,
        drive_file_id="drive-master-cv-123",
        category="cv",
        mime="application/pdf",
        synced_at=datetime.now(UTC),
    )
    db_session.add(base_doc)

    opp = await _seed_test_opportunity(db_session)

    reasoner = DeterministicMockCareerReasoner()
    eval_service = CareerEvaluationService(reasoner=reasoner)
    await eval_service.evaluate_opportunity(db_session, opp.id, force=True)

    package_service = ApplicationPackageService(reasoner=reasoner)
    pkg = await package_service.prepare_application_package(db_session, opp.id)

    # Verify base CV document record was untouched
    await db_session.refresh(base_doc)
    await db_session.refresh(doc_entity)
    assert base_doc.category == "cv"
    assert doc_entity.title == "Furkan_Turkoglu_Master_CV.pdf"
    assert pkg.base_cv_document_id == str(base_doc.id)


@pytest.mark.asyncio
async def test_application_package_fact_verification_gate_blocks_unsupported(db_session: AsyncSession):
    """C5: Any hallucinated/unsupported claim in tailored CV blocks readiness (UNSUPPORTED_CLAIMS)."""
    opp = await _seed_test_opportunity(db_session)

    eval_service = CareerEvaluationService(reasoner=DeterministicMockCareerReasoner())
    await eval_service.evaluate_opportunity(db_session, opp.id, force=True)

    # Reasoner that introduces an unverified claim
    class HallucinatingReasoner(DeterministicMockCareerReasoner):
        async def tailor_cv(self, base_cv, listing_ctx, candidate_ctx, evaluation=None):
            draft = await super().tailor_cv(base_cv, listing_ctx, candidate_ctx, evaluation)
            draft.fact_verifications = [
                CvFactVerificationDraft(
                    claim="Managed a team of 50 Kubernetes engineers (unverified).",
                    status="unsupported",
                    candidate_fact_ref=None,
                    note="Fabricated management experience detected.",
                )
            ]
            return draft

    package_service = ApplicationPackageService(reasoner=HallucinatingReasoner())
    pkg = await package_service.prepare_application_package(db_session, opp.id)

    assert any(v.status == "unsupported" for v in pkg.fact_verification)
    assert pkg.readiness == "UNSUPPORTED_CLAIMS"
    assert any("unsupported" in r.lower() for r in pkg.readiness_reasons)


@pytest.mark.asyncio
async def test_application_package_change_audit_and_cover_letter(db_session: AsyncSession):
    """C5: CV changes are audited with explicit justifications and cover letter is STAR-grounded."""
    opp = await _seed_test_opportunity(db_session)

    reasoner = DeterministicMockCareerReasoner()
    eval_service = CareerEvaluationService(reasoner=reasoner)
    await eval_service.evaluate_opportunity(db_session, opp.id, force=True)

    package_service = ApplicationPackageService(reasoner=reasoner)
    pkg = await package_service.prepare_application_package(db_session, opp.id)

    # Audit checks
    assert len(pkg.cv_changes) > 0
    first_change = pkg.cv_changes[0]
    assert first_change.change_type != ""
    assert first_change.justification != ""

    # Cover letter checks
    assert pkg.cover_letter != ""
    assert len(pkg.cover_letter.split("\n\n")) >= 2


@pytest.mark.asyncio
async def test_application_package_answers_needs_user_input_and_resolution(db_session: AsyncSession):
    """C5: Missing screening question answers require user input and resolve smoothly."""
    opp = await _seed_test_opportunity(db_session)

    eval_service = CareerEvaluationService(reasoner=DeterministicMockCareerReasoner())
    await eval_service.evaluate_opportunity(db_session, opp.id, force=True)

    # Reasoner that specifies a question needing user input (e.g. salary expectation)
    class MissingInputReasoner(DeterministicMockCareerReasoner):
        async def answer_application(self, listing_ctx, candidate_ctx, evaluation=None, questions=None):
            return [
                ApplicationAnswerDraft(
                    question="What is your notice period?",
                    proposed_answer="1 month",
                    classification="needs_user_input",
                    confidence=0.5,
                    warning="Notice period is not configured in candidate profile.",
                    evidence_refs=[],
                )
            ]

    package_service = ApplicationPackageService(reasoner=MissingInputReasoner())
    pkg = await package_service.prepare_application_package(db_session, opp.id)

    assert pkg.readiness == "NEEDS_INPUT"
    assert any("notice period" in r.lower() for r in pkg.readiness_reasons)

    # Resolve the answer
    updated_pkg = await package_service.resolve_user_answer(
        db_session,
        opp.id,
        question="What is your notice period?",
        user_answer="2 weeks notice period",
    )

    resolved_q = [a for a in updated_pkg.application_answers if a.question == "What is your notice period?"][0]
    assert resolved_q.proposed_answer == "2 weeks notice period"
    assert resolved_q.classification == "safe_verified"
    assert updated_pkg.readiness == "READY"


@pytest.mark.asyncio
async def test_application_package_persists_in_application_and_never_auto_submits(db_session: AsyncSession):
    """C5: Application is created/updated in 'preparing' status and NEVER auto-submits."""
    opp = await _seed_test_opportunity(db_session)

    reasoner = DeterministicMockCareerReasoner()
    eval_service = CareerEvaluationService(reasoner=reasoner)
    await eval_service.evaluate_opportunity(db_session, opp.id, force=True)

    package_service = ApplicationPackageService(reasoner=reasoner)
    pkg = await package_service.prepare_application_package(db_session, opp.id)

    assert pkg.application_id is not None
    app_record = await db_session.get(Application, uuid.UUID(pkg.application_id))
    assert app_record is not None
    assert app_record.status == "preparing"
    assert app_record.package.get("readiness") in ("READY", "NEEDS_INPUT", "UNSUPPORTED_CLAIMS")

    # Re-fetch package via get_application_package
    fetched_pkg = await package_service.get_application_package(db_session, opp.id)
    assert fetched_pkg is not None
    assert fetched_pkg.readiness == pkg.readiness
