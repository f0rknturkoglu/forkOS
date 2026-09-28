"""Real local artifacts in an isolated test DB; no personal source fixtures."""

import io
import zipfile

import pytest

from app.db import SessionLocal
from app.modules.document import service as documents
from app.modules.document.models import Document
from app.modules.opportunity.candidate_context import build_candidate_career_context
from app.modules.opportunity.evaluation_service import CareerEvaluationService
from app.modules.opportunity.package_service import ApplicationPackageService
from app.modules.opportunity.reasoner.base import CvFactVerificationDraft
from app.modules.opportunity.reasoner.mock import DeterministicMockCareerReasoner
from tests.test_opportunity_application_package import _seed_test_opportunity


def synthetic_cv():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>PROFESSIONAL SUMMARY</w:t></w:r></w:p><w:p><w:r><w:t>Synthetic engineer building source-bound tools.</w:t></w:r></w:p><w:p><w:r><w:t>TECHNICAL SKILLS</w:t></w:r></w:p><w:p><w:r><w:t>Tools: Python, FastAPI</w:t></w:r></w:p></w:body></w:document>',
        )
    return buffer.getvalue()


@pytest.mark.parametrize("ref", [None, "fake-python-key", "skill:python"])
async def test_unproven_claim_never_verified_even_with_real_skill_ref(ref):
    class BadReasoner(DeterministicMockCareerReasoner):
        async def tailor_cv(self, *args, **kwargs):
            draft = await super().tailor_cv(*args, **kwargs)
            draft.fact_verifications = [
                CvFactVerificationDraft(
                    claim="Led 50 Python engineers", status="verified", candidate_fact_ref=ref
                )
            ]
            return draft

    async with SessionLocal() as session:
        await documents.create_local_document(
            session, title="synthetic.docx", content=synthetic_cv(), category="cv", commit=False
        )
        opportunity = await _seed_test_opportunity(session)
        reasoner = BadReasoner()
        await CareerEvaluationService(reasoner).evaluate_opportunity(session, opportunity.id)
        package = await ApplicationPackageService(reasoner).prepare_application_package(
            session, opportunity.id
        )
        assert package.readiness == "UNSUPPORTED_CLAIMS"
        assert package.fact_verification[0].status == "unsupported"


async def test_source_content_derivative_lineage_and_master_immutable(monkeypatch):
    async with SessionLocal() as session:
        content = synthetic_cv()
        master = await documents.create_local_document(
            session, title="synthetic.docx", content=content, category="cv", commit=False
        )
        source_path = documents.get_local_file_path(master["id"], "synthetic.docx")
        opportunity = await _seed_test_opportunity(session)
        reasoner = DeterministicMockCareerReasoner()
        context = await build_candidate_career_context(session)
        assert context.base_cv["content_available"]
        assert any(f.source_locator for f in context.facts if f.source_id == str(master["id"]))
        await CareerEvaluationService(reasoner).evaluate_opportunity(session, opportunity.id)
        package = await ApplicationPackageService(reasoner).prepare_application_package(
            session, opportunity.id
        )
        assert package.readiness != "READY"  # No renderer/user review.
        for ref in package.generated_documents:
            assert ref.document_id and ref.parent_document_id == str(master["id"])
            assert ref.opportunity_id == str(opportunity.id)
            import uuid

            assert await session.get(Document, uuid.UUID(ref.document_id))
        assert source_path.read_bytes() == content
        assert any(
            answer.classification == "sensitive_user_decision"
            for answer in package.knockout_answers
        )
        assert all(
            not answer.proposed_answer
            for answer in package.knockout_answers
            if answer.classification == "sensitive_user_decision"
        )


async def test_answer_resolution_cannot_bypass_metadata_or_missing_artifacts():
    import uuid

    from app.modules.opportunity.models import Application
    from app.modules.opportunity.package_service import ApplicationAnswer

    async with SessionLocal() as session:
        opportunity = await _seed_test_opportunity(session)
        reasoner = DeterministicMockCareerReasoner()
        await CareerEvaluationService(reasoner).evaluate_opportunity(session, opportunity.id)
        service = ApplicationPackageService(reasoner)
        package = await service.prepare_application_package(session, opportunity.id)
        package.readiness = "NEEDS_INPUT"
        package.cover_letter = ""
        package.base_cv_document_id = str(uuid.uuid4())
        package.provenance["render_validation"] = "passed"
        package.fact_verification = []
        package.application_answers = [
            ApplicationAnswer(
                question="Notice period?", proposed_answer="", classification="needs_user_input"
            )
        ]
        app = await session.get(Application, opportunity.id)
        app.package = package.model_dump()
        await session.flush()
        resolved = await service.resolve_user_answer(
            session, opportunity.id, "Notice period?", "Two weeks"
        )
        assert resolved.readiness != "READY"
        assert app.package["readiness"] != "READY"
