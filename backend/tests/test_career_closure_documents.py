"""Real local artifacts in an isolated test DB; no personal source fixtures."""

import io
import zipfile

import pytest

from app.db import SessionLocal
from app.modules.document import service as documents
from app.modules.document.models import Document
from app.modules.opportunity.application import apply, upsert_application
from app.modules.opportunity.candidate_context import build_candidate_career_context
from app.modules.opportunity.cover_letter_integrity import cover_letter_hash
from app.modules.opportunity.evaluation_service import CareerEvaluationService
from app.modules.opportunity.models import Application
from app.modules.opportunity.package_service import ApplicationPackageService
from app.modules.opportunity.reasoner.base import CvFactVerificationDraft
from app.modules.opportunity.reasoner.mock import DeterministicMockCareerReasoner
from app.modules.opportunity.schemas import ApplicationIn, ApplyIn
from tests.test_opportunity_application_package import _seed_test_opportunity


def synthetic_cv():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>PROFESSIONAL SUMMARY</w:t></w:r></w:p><w:p><w:r><w:t>Synthetic engineer building source-bound tools.</w:t></w:r></w:p><w:p><w:r><w:t>TECHNICAL SKILLS</w:t></w:r></w:p><w:p><w:r><w:t>Tools: Python, FastAPI</w:t></w:r></w:p></w:body></w:document>',
        )
    return buffer.getvalue()


@pytest.mark.no_database
def test_cover_hash_normalizes_only_line_endings_and_outer_whitespace():
    assert cover_letter_hash(" \r\nCover A\r\nLine 2\r\n ") == cover_letter_hash(
        "Cover A\nLine 2"
    )
    assert cover_letter_hash("Cover A  Line 2") != cover_letter_hash("Cover A Line 2")


async def approved_cover_fixture(session, monkeypatch):
    async def local_test_renderer(_html):
        return b"%PDF-1.4\n%synthetic fixture\n", {"status": "passed"}

    monkeypatch.setattr(
        "app.modules.opportunity.cv_artifacts.render_cv_pdf", local_test_renderer
    )
    await documents.create_local_document(
        session, title="synthetic.docx", content=synthetic_cv(), category="cv", commit=False
    )
    opportunity = await _seed_test_opportunity(session)
    reasoner = DeterministicMockCareerReasoner()
    await CareerEvaluationService(reasoner).evaluate_opportunity(session, opportunity.id)
    service = ApplicationPackageService(reasoner)
    package = await service.prepare_application_package(session, opportunity.id)
    assert package.cover_letter_review.status == "pending"
    assert package.cover_letter_review.content_hash is None
    for answer in package.application_answers:
        if answer.classification != "safe_verified":
            package = await service.resolve_user_answer(
                session, opportunity.id, answer.question, "Explicit user response"
            )
    assert package.readiness == "NEEDS_INPUT"
    approved = await service.review_cover_letter(session, opportunity.id, "approved")
    assert approved.readiness == "READY"
    assert approved.cover_letter_review.content_hash == cover_letter_hash(approved.cover_letter)
    return opportunity, reasoner, service, approved


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


async def test_cover_letter_review_gate_and_regeneration(monkeypatch):
    from app.modules.opportunity.models import Application

    async def local_test_renderer(_html):
        return b"%PDF-1.4\n%synthetic fixture\n", {"status": "passed"}

    monkeypatch.setattr(
        "app.modules.opportunity.cv_artifacts.render_cv_pdf", local_test_renderer
    )
    async with SessionLocal() as session:
        await documents.create_local_document(
            session, title="synthetic.docx", content=synthetic_cv(), category="cv", commit=False
        )
        opportunity = await _seed_test_opportunity(session)
        reasoner = DeterministicMockCareerReasoner()
        await CareerEvaluationService(reasoner).evaluate_opportunity(session, opportunity.id)
        service = ApplicationPackageService(reasoner)
        package = await service.prepare_application_package(session, opportunity.id)
        assert package.cover_letter
        assert package.cover_letter_review.status == "pending"
        assert package.readiness == "NEEDS_INPUT"
        app = await session.get(Application, opportunity.id)
        original_status = app.status
        for answer in package.application_answers:
            if answer.classification != "safe_verified":
                package = await service.resolve_user_answer(
                    session, opportunity.id, answer.question, "Explicit user response"
                )
        assert package.readiness == "NEEDS_INPUT"
        approved = await service.review_cover_letter(session, opportunity.id, "approved")
        assert approved.cover_letter_review.status == "approved"
        assert approved.cover_letter_review.reviewed_at
        assert approved.cover_letter_review.content_hash == cover_letter_hash(approved.cover_letter)
        assert approved.readiness == "READY"
        assert app.status == original_status == "preparing"
        rejected = await service.review_cover_letter(session, opportunity.id, "rejected")
        assert rejected.readiness == "NEEDS_INPUT"
        assert rejected.cover_letter_review.content_hash == cover_letter_hash(rejected.cover_letter)
        assert app.status == original_status
        reapproved = await service.review_cover_letter(session, opportunity.id, "approved")
        assert reapproved.readiness == "READY"
        old_cover = reapproved.cover_letter
        generate_cover = reasoner.generate_cover

        async def changed_cover(*args, **kwargs):
            draft = await generate_cover(*args, **kwargs)
            draft.cover_letter += "\n\nVersion B."
            return draft

        monkeypatch.setattr(reasoner, "generate_cover", changed_cover)
        regenerated = await service.prepare_application_package(session, opportunity.id)
        assert regenerated.cover_letter != old_cover
        assert regenerated.cover_letter_review.status == "pending"
        assert regenerated.cover_letter_review.reviewed_at is None
        assert regenerated.cover_letter_review.content_hash is None
        assert regenerated.readiness != "READY"
        assert app.cover_letter == regenerated.cover_letter
        assert app.status == original_status


async def test_upsert_cover_edit_invalidates_only_review(monkeypatch):
    async with SessionLocal() as session:
        opportunity, _, service, approved = await approved_cover_fixture(session, monkeypatch)
        app = await session.get(Application, opportunity.id)
        assert app.status == "preparing"
        await upsert_application(
            session, opportunity.id, ApplicationIn(cover_letter="Cover B")
        )
        await session.refresh(app)
        package = await service.get_package(session, opportunity.id)
        assert app.cover_letter == package.cover_letter == "Cover B"
        assert package.cover_letter_review.status == "pending"
        assert package.cover_letter_review.reviewed_at is None
        assert package.cover_letter_review.content_hash is None
        assert package.readiness == "NEEDS_INPUT"
        assert any("explicit review required" in warning for warning in package.warnings)
        assert all(ref.doc_type != "cover_letter" for ref in package.generated_documents)
        assert app.status == "preparing"
        assert approved.cover_letter != package.cover_letter
        reapproved = await service.review_cover_letter(session, opportunity.id, "approved")
        assert reapproved.readiness == "READY"
        assert reapproved.cover_letter_review.content_hash == cover_letter_hash("Cover B")
        assert not any("explicit review required" in reason for reason in reapproved.readiness_reasons)
        assert app.status == "preparing"


async def test_same_normalized_cover_write_preserves_approval(monkeypatch):
    async with SessionLocal() as session:
        opportunity, _, service, approved = await approved_cover_fixture(session, monkeypatch)
        same_text = " \n" + approved.cover_letter.replace("\n", "\r\n") + "\n "
        await upsert_application(
            session, opportunity.id, ApplicationIn(cover_letter=same_text)
        )
        app = await session.get(Application, opportunity.id)
        package = await service.get_package(session, opportunity.id)
        assert app.cover_letter == package.cover_letter == same_text
        assert package.cover_letter_review.status == "approved"
        assert package.cover_letter_review.content_hash == cover_letter_hash(same_text)
        assert package.readiness == "READY"
        assert app.status == "preparing"


async def test_apply_cover_edit_invalidates_without_extra_lifecycle_change(monkeypatch):
    async with SessionLocal() as session:
        opportunity, _, service, _ = await approved_cover_fixture(session, monkeypatch)
        await apply(session, opportunity.id, ApplyIn(cover_letter="Applied Cover B"))
        app = await session.get(Application, opportunity.id)
        package = await service.get_package(session, opportunity.id)
        assert app.cover_letter == package.cover_letter == "Applied Cover B"
        assert package.cover_letter_review.status == "pending"
        assert package.cover_letter_review.content_hash is None
        assert package.readiness == "NEEDS_INPUT"
        assert app.status == "applied"  # Explicit apply action, not review/edit side effect.


async def test_legacy_approval_without_hash_fails_closed(monkeypatch):
    async with SessionLocal() as session:
        opportunity, _, service, _ = await approved_cover_fixture(session, monkeypatch)
        app = await session.get(Application, opportunity.id)
        legacy = dict(app.package)
        legacy_review = dict(legacy["cover_letter_review"])
        legacy_review.pop("content_hash")
        legacy["cover_letter_review"] = legacy_review
        app.package = legacy
        await session.flush()
        package = await service.get_package(session, opportunity.id)
        assert package.readiness == "NEEDS_INPUT"
        assert package.cover_letter_review.status == "pending"
        assert package.cover_letter_review.content_hash is None
        assert app.status == "preparing"
        reapproved = await service.review_cover_letter(session, opportunity.id, "approved")
        assert reapproved.readiness == "READY"
        assert reapproved.cover_letter_review.content_hash == cover_letter_hash(
            reapproved.cover_letter
        )


async def test_out_of_band_cover_mismatch_cannot_be_approved(monkeypatch):
    async with SessionLocal() as session:
        opportunity, _, service, _ = await approved_cover_fixture(session, monkeypatch)
        app = await session.get(Application, opportunity.id)
        app.cover_letter = "Out-of-band Cover B"
        await session.flush()
        package = await service.get_package(session, opportunity.id)
        assert package.readiness == "NEEDS_INPUT"
        assert package.cover_letter_review.status == "pending"
        with pytest.raises(ValueError, match="changed"):
            await service.review_cover_letter(session, opportunity.id, "approved")
        assert app.status == "preparing"
