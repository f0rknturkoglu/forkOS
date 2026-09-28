"""C4-C5 closure regressions; synthetic source data only."""

import zipfile

import pytest

from app.modules.opportunity.candidate_context import (
    CandidateCareerContext,
    CandidateFact,
    compute_candidate_context_revision,
)
from app.modules.opportunity.cv_artifacts import (
    build_cv_html,
    render_cv_pdf,
    verify_material_claims,
)
from app.modules.opportunity.cv_evidence import extract_cv_evidence
from app.modules.opportunity.evidence_integrity import (
    claim_matches_fact,
    valid_refs,
    validate_evaluation,
)
from app.modules.opportunity.reasoner.base import (
    DeepEvaluationDraft,
    RequirementAssessmentDraft,
    TailoredCvDraft,
)

pytestmark = pytest.mark.no_database


def context():
    return CandidateCareerContext(
        facts=[
            CandidateFact(
                key="skill:python",
                value="Python",
                source_type="document",
                source_id="synthetic",
                source_locator="skills/paragraph:3",
            )
        ]
    )


@pytest.mark.parametrize(
    "refs,expected",
    [([], False), (["fake"], False), (["skill:python", "fake"], False), (["skill:python"], True)],
)
def test_refs_fail_closed(refs, expected):
    assert valid_refs(refs, context()) is expected


@pytest.mark.parametrize(
    "claim,expected",
    [
        ("Python", True),
        ("Technical proficiency in Python", True),
        ("Led 50 Python engineers", False),
    ],
)
def test_real_ref_does_not_verify_unrelated_claim(claim, expected):
    assert claim_matches_fact(claim, context().facts[0]) is expected
    assert not claim_matches_fact(claim, None)


def test_fake_evaluation_refs_never_survive():
    draft = DeepEvaluationDraft(
        overall_assessment="draft",
        role_fit="strong",
        seniority_fit="unknown",
        location_fit="unknown",
        strengths=["Invented management"],
        evidence=["fake"],
        work_authorization={"candidate_authorized": True},
        must_have=[
            RequirementAssessmentDraft(
                requirement="Python",
                classification="strong",
                reason="fake",
                candidate_evidence_refs=["fake"],
            )
        ],
    )
    validate_evaluation(draft, context())
    assert draft.must_have[0].classification == "unknown"
    assert draft.must_have[0].candidate_evidence_refs == []
    assert not draft.strengths and not draft.evidence
    assert draft.work_authorization["status"] == "unknown"


def test_cv_docx_content_and_locator(tmp_path):
    path = tmp_path / "source.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>PROJECTS</w:t></w:r></w:p><w:p><w:r><w:t>Built a synthetic search prototype.</w:t></w:r></w:p></w:body></w:document>',
        )
    before = path.read_bytes()
    facts = extract_cv_evidence(path, "synthetic-doc")
    assert facts[0].value == {"section": "projects", "text": "Built a synthetic search prototype."}
    assert facts[0].source_locator == "projects/paragraph:2"
    assert facts[0].verified and facts[0].source_type == "document"
    assert path.read_bytes() == before
    revision = compute_candidate_context_revision(facts)
    facts[0].value["text"] = "Changed source evidence"
    assert compute_candidate_context_revision(facts) != revision


def test_unrelated_tailored_content_blocked_and_html_escaped():
    draft = TailoredCvDraft(summary="Led 50 engineers <script>alert(1)</script>", skills=["Python"])
    assert not verify_material_claims(draft, context())
    html = build_cv_html(draft)
    assert "<script>" not in html and "&lt;script&gt;" in html


async def test_disabled_renderer_truthful(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "career_ops_enabled", False)
    content, status = await render_cv_pdf("unused")
    assert content is None and status["status"] == "unavailable"
    assert status["visual"] == "unavailable"
