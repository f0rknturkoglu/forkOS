"""ApplicationPackageService: Application Package preparation, tailoring & verification (C5).

Guarantees:
- Master CV remains 100% immutable (derivatives only).
- Fact verification gate: any unsupported claim flags UNSUPPORTED_CLAIMS (NOT READY).
- CV change audit: added, removed, rewritten, reordered with evidence refs.
- Cover letter: strictly evidence-bound from STAR+R stories and verified facts.
- Application/Knockout answers: classified as safe_verified vs needs_user_input.
- Stale evaluation check: blocks producing READY package when inputs changed.
- No auto-submit or CRM status transition past 'preparing'.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import touch_entity
from app.core.events import log_event
from app.modules.opportunity.candidate_context import (
    build_candidate_career_context,
)
from app.modules.opportunity.evaluation_service import (
    CareerEvaluationService,
)
from app.modules.opportunity.evidence_integrity import valid_refs
from app.modules.opportunity.listing_context import (
    build_career_listing_context,
)
from app.modules.opportunity.models import Application, Opportunity
from app.modules.opportunity.reasoner.base import (
    ApplicationAnswerDraft,
    CareerReasoner,
    CoverLetterDraft,
    DeepEvaluationDraft,
    TailoredCvDraft,
)
from app.modules.opportunity.reasoner.factory import get_career_reasoner


class CvChangeItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    section: str = ""
    change_type: str = "reordered"
    original: str = ""
    new: str = ""
    summary: str = ""
    reason: str = ""
    justification: str = ""
    evidence_refs: list[str] = Field(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        if not self.justification and self.reason:
            self.justification = self.reason
        if not self.reason and self.justification:
            self.reason = self.justification
        if not self.summary:
            self.summary = f"{self.change_type} in {self.section or 'CV'}"


class CvFactVerification(BaseModel):
    model_config = ConfigDict(extra="ignore")

    claim: str
    status: Literal["verified", "unsupported", "ambiguous"]
    candidate_fact_ref: str | None = None
    note: str = ""


class ApplicationAnswer(BaseModel):
    model_config = ConfigDict(extra="ignore")

    question: str
    proposed_answer: str
    classification: Literal["safe_verified", "needs_user_input", "sensitive_user_decision"]
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    warning: str | None = None


class KnockoutAnswer(BaseModel):
    model_config = ConfigDict(extra="ignore")

    question: str
    proposed_answer: str
    classification: Literal["safe_verified", "needs_user_input", "sensitive_user_decision"] = (
        "needs_user_input"
    )
    evidence_refs: list[str] = Field(default_factory=list)
    evidence: str
    confidence: float = 1.0
    warning: str | None = None


class GeneratedDocumentRef(BaseModel):
    model_config = ConfigDict(extra="ignore")

    document_id: str | None = None
    doc_type: Literal["tailored_cv", "cover_letter", "pdf_cv"]
    title: str
    file_path: str | None = None
    mime: str = "text/plain"
    parent_document_id: str | None = None
    opportunity_id: str | None = None


class ApplicationPackage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    application_id: str | None = None
    opportunity_id: str
    evaluation_revision: str
    listing_fingerprint: str
    base_cv_document_id: str | None = None
    tailored_cv: dict[str, Any] = Field(default_factory=dict)
    cv_change_audit: list[CvChangeItem] = Field(default_factory=list)
    fact_verification: list[CvFactVerification] = Field(default_factory=list)
    cover_letter: str = ""
    application_answers: list[ApplicationAnswer] = Field(default_factory=list)
    knockout_answers: list[KnockoutAnswer] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    readiness_reasons: list[str] = Field(default_factory=list)
    generated_documents: list[GeneratedDocumentRef] = Field(default_factory=list)
    readiness: Literal[
        "READY", "NEEDS_INPUT", "UNSUPPORTED_CLAIMS", "STALE_EVALUATION", "RENDER_FAILED"
    ]
    provenance: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str

    @property
    def cv_changes(self) -> list[CvChangeItem]:
        return self.cv_change_audit


COMMON_APPLICATION_QUESTIONS = [
    "Why are you interested in this role and company?",
    "What relevant technical experience do you bring?",
    "What are your salary expectations?",
    "What is your notice period or earliest start date?",
    "Are you legally authorized to work in this location?",
    "Do you now or in the future require visa sponsorship?",
]


class ApplicationPackageService:
    def __init__(
        self,
        reasoner: CareerReasoner | None = None,
        eval_service: CareerEvaluationService | None = None,
    ) -> None:
        self.reasoner = reasoner or get_career_reasoner()
        self.eval_service = eval_service or CareerEvaluationService(reasoner=self.reasoner)

    async def get_package(
        self,
        session: AsyncSession,
        opportunity_id: uuid.UUID,
    ) -> ApplicationPackage | None:
        """Fetch persisted application package from Application entity."""
        app = await session.get(Application, opportunity_id)
        if app is None or not app.package:
            return None

        pkg_data = dict(app.package)
        pkg = ApplicationPackage.model_validate(pkg_data)

        # Re-check evaluation freshness
        evaluation = await self.eval_service.get_evaluation(session, opportunity_id)
        evaluation_revision = hashlib.sha256(
            json.dumps(
                evaluation.model_dump(exclude={"is_stale", "stale_reasons"}) if evaluation else {},
                sort_keys=True,
            ).encode()
        ).hexdigest()
        if (
            evaluation is None
            or evaluation.is_stale
            or pkg.evaluation_revision != evaluation_revision
        ):
            pkg.readiness = "STALE_EVALUATION"
            if (
                "Evaluation is stale. Please refresh evaluation before submitting."
                not in pkg.warnings
            ):
                pkg.warnings.append(
                    "Evaluation is stale. Please refresh evaluation before submitting."
                )

        if pkg.readiness == "READY":
            context = await build_candidate_career_context(session)
            from app.modules.document.models import Document
            from app.modules.document.service import get_local_file_path
            from app.modules.opportunity.evidence_integrity import claim_matches_fact

            artifact_invalid = False
            for ref in pkg.generated_documents:
                try:
                    ident = uuid.UUID(ref.document_id or "")
                    document = await session.get(Document, ident)
                    path = get_local_file_path(ident, ref.title)
                    artifact_invalid |= (
                        not document
                        or not path
                        or not path.is_file()
                        or ref.parent_document_id != pkg.base_cv_document_id
                        or ref.opportunity_id != str(opportunity_id)
                    )
                except (ValueError, OSError):
                    artifact_invalid = True
            if any(
                f.status == "unsupported"
                or (
                    f.status == "verified"
                    and not claim_matches_fact(
                        f.claim, context.get_fact(f.candidate_fact_ref or "")
                    )
                )
                for f in pkg.fact_verification
            ):
                pkg.readiness = "UNSUPPORTED_CLAIMS"
                return pkg
            if (
                not context.base_cv
                or not context.base_cv.get("content_available")
                or pkg.provenance.get("candidate_context_revision") != context.revision
                or not pkg.generated_documents
                or any(not ref.document_id for ref in pkg.generated_documents)
                or pkg.provenance.get("render_validation") != "passed"
                or pkg.cover_letter
                or artifact_invalid
                or any(f.status == "ambiguous" for f in pkg.fact_verification)
            ):
                pkg.readiness = "NEEDS_INPUT"
                pkg.warnings.append(
                    "Legacy or incomplete package requires current source/artifact verification."
                )
        return pkg

    get_application_package = get_package

    async def prepare_application_package(
        self,
        session: AsyncSession,
        opportunity_id: uuid.UUID,
        *,
        custom_questions: list[str] | None = None,
        now: datetime | None = None,
    ) -> ApplicationPackage:
        """Prepare complete, evidence-bound ApplicationPackage for opportunity."""
        now = now or datetime.now(UTC)
        opp = await session.get(Opportunity, opportunity_id)
        if opp is None:
            raise ValueError(f"Opportunity not found: {opportunity_id}")

        # 1. Fetch current DeepEvaluation and enforce non-staleness
        evaluation = await self.eval_service.get_evaluation(session, opportunity_id)
        if evaluation is None:
            raise ValueError(
                "Opportunity must be evaluated before preparing an application package."
            )

        if evaluation.is_stale:
            raise ValueError(
                "Evaluation is stale. Please run evaluation again before preparing application package."
            )

        # 2. Build candidate context
        cand_ctx = await build_candidate_career_context(session)
        listing_ctx = await build_career_listing_context(session, opp)

        # 3. Base CV selection (Immutable master CV)
        base_cv_id = cand_ctx.base_cv.get("document_id") if cand_ctx.base_cv else None
        base_cv_data = cand_ctx.base_cv or {
            "title": "Master CV",
            "skills": cand_ctx.skills,
            "summary": cand_ctx.profile_summary,
        }

        # 4. Tailor CV via reasoner
        eval_draft = DeepEvaluationDraft.model_validate(evaluation.model_dump())
        tailored_draft: TailoredCvDraft = await self.reasoner.tailor_cv(
            base_cv=base_cv_data,
            listing_ctx=listing_ctx,
            candidate_ctx=cand_ctx,
            evaluation=eval_draft,
        )

        # 5. Generate cover letter
        cover_draft: CoverLetterDraft = await self.reasoner.generate_cover(
            listing_ctx=listing_ctx,
            candidate_ctx=cand_ctx,
            evaluation=eval_draft,
            stories=cand_ctx.career_stories,
        )

        # 6. Answer application questions
        questions = custom_questions or COMMON_APPLICATION_QUESTIONS
        answers_draft: list[ApplicationAnswerDraft] = await self.reasoner.answer_application(
            listing_ctx=listing_ctx,
            candidate_ctx=cand_ctx,
            evaluation=eval_draft,
            questions=questions,
        )

        # 7. Fact verification gate & Readiness determination
        warnings: list[str] = []
        has_unsupported = False
        has_needs_input = False

        verified_fact_keys = {f.key for f in cand_ctx.facts if f.verified}

        cv_verifications: list[CvFactVerification] = []
        for fv in tailored_draft.fact_verifications:
            # Deterministic double-check: if a claim mentions a skill not in verified facts, reject it!
            status = fv.status
            if status == "unsupported":
                has_unsupported = True
                warnings.append(f"Unsupported claim in tailored CV: '{fv.claim}'")
            elif status == "verified":
                fact = cand_ctx.get_fact(fv.candidate_fact_ref or "")
                from app.modules.opportunity.evidence_integrity import claim_matches_fact

                if (
                    not fv.candidate_fact_ref
                    or fv.candidate_fact_ref not in verified_fact_keys
                    or not claim_matches_fact(fv.claim, fact)
                ):
                    status = "unsupported"
                    has_unsupported = True
                    warnings.append(
                        f"Claim references unverified fact key: '{fv.candidate_fact_ref}'"
                    )
            elif status == "ambiguous":
                has_needs_input = True
                warnings.append(f"Ambiguous material claim requires review: '{fv.claim}'")

            cv_verifications.append(
                CvFactVerification(
                    claim=fv.claim,
                    status=status,
                    candidate_fact_ref=fv.candidate_fact_ref,
                    note=fv.note,
                )
            )

        app_answers: list[ApplicationAnswer] = []
        for a in answers_draft:
            from app.modules.opportunity.evidence_integrity import claim_matches_fact

            if a.classification == "safe_verified" and (
                not valid_refs(a.evidence_refs, cand_ctx)
                or not any(
                    claim_matches_fact(a.proposed_answer, cand_ctx.get_fact(ref))
                    for ref in a.evidence_refs
                )
            ):
                a.classification = "needs_user_input"
                a.proposed_answer = ""
                a.evidence_refs = []
                a.warning = "No valid canonical evidence for answer."
            if any(
                term in a.question.casefold()
                for term in (
                    "authorized",
                    "authorization",
                    "visa",
                    "sponsor",
                    "clearance",
                    "citizenship",
                )
            ):
                a.classification = "sensitive_user_decision"
                a.proposed_answer = ""
                a.evidence_refs = []
            if a.classification in ("needs_user_input", "sensitive_user_decision"):
                has_needs_input = True
                warnings.append(f"Question requires user input: '{a.question}'")
            app_answers.append(
                ApplicationAnswer(
                    question=a.question,
                    proposed_answer=a.proposed_answer,
                    classification=a.classification,
                    evidence_refs=a.evidence_refs,
                    confidence=a.confidence,
                    warning=a.warning,
                )
            )

        if not cand_ctx.base_cv or not cand_ctx.base_cv.get("content_available"):
            has_needs_input = True
            warnings.append(
                "Actual canonical CV content is unavailable; metadata cannot establish readiness."
            )

        # Determine readiness state
        if has_unsupported:
            readiness = "UNSUPPORTED_CLAIMS"
        elif has_needs_input:
            readiness = "NEEDS_INPUT"
        else:
            readiness = "READY"

        # 8. Document Generation / Linking (HTML representation)
        generated_docs: list[GeneratedDocumentRef] = []
        html_cv_title = f"{listing_ctx.company} - Tailored CV"
        from app.modules.document.service import create_local_document
        from app.modules.opportunity.cv_artifacts import (
            build_cv_html,
            render_cv_pdf,
            verify_material_claims,
        )

        if not verify_material_claims(tailored_draft, cand_ctx):
            readiness = "UNSUPPORTED_CLAIMS"
            has_unsupported = True
            warnings.append(
                "Tailored content contains material claims not exactly supported by source evidence; review required."
            )
        html_cv = build_cv_html(tailored_draft, cand_ctx)
        cv_doc = await create_local_document(
            session,
            title=f"{opportunity_id}-tailored.html",
            category="tailored_cv",
            mime="text/html",
            content=html_cv.encode(),
            commit=False,
        )
        generated_docs.append(
            GeneratedDocumentRef(
                document_id=str(cv_doc["id"]),
                doc_type="tailored_cv",
                title=html_cv_title,
                file_path=f"/api/documents/{cv_doc['id']}/file",
                mime="text/html",
            )
        )
        pdf, render_validation = await render_cv_pdf(html_cv)
        if pdf:
            pdf_doc = await create_local_document(
                session,
                title=f"{opportunity_id}-tailored.pdf",
                category="tailored_cv",
                mime="application/pdf",
                content=pdf,
                commit=False,
            )
            generated_docs.append(
                GeneratedDocumentRef(
                    document_id=str(pdf_doc["id"]),
                    doc_type="pdf_cv",
                    title=html_cv_title,
                    file_path=f"/api/documents/{pdf_doc['id']}/file",
                    mime="application/pdf",
                )
            )
        elif readiness == "READY":
            readiness = "RENDER_FAILED"
            warnings.append("PDF rendering unavailable or failed; package cannot be READY.")
        if cover_draft.cover_letter:
            if not valid_refs(cover_draft.evidence_refs, cand_ctx):
                readiness = "UNSUPPORTED_CLAIMS"
                has_unsupported = True
                warnings.append("Cover letter lacks valid canonical candidate evidence.")
            # Referencing a true skill does not prove every sentence in generated prose.
            if readiness == "READY":
                readiness = "NEEDS_INPUT"
            warnings.append("Generated cover-letter prose requires explicit material-claim review.")
            cover_doc = await create_local_document(
                session,
                title=f"{opportunity_id}-cover.txt",
                category="cover_letter",
                mime="text/plain",
                content=cover_draft.cover_letter.encode(),
                commit=False,
            )
            generated_docs.append(
                GeneratedDocumentRef(
                    document_id=str(cover_doc["id"]),
                    doc_type="cover_letter",
                    title=f"{listing_ctx.company} - Cover Letter",
                    mime="text/plain",
                    file_path=f"/api/documents/{cover_doc['id']}/file",
                )
            )

        for reference in generated_docs:
            reference.parent_document_id = base_cv_id
            reference.opportunity_id = str(opportunity_id)

        package_model = ApplicationPackage(
            application_id=str(opportunity_id),
            opportunity_id=str(opportunity_id),
            evaluation_revision=hashlib.sha256(
                json.dumps(
                    evaluation.model_dump(exclude={"is_stale", "stale_reasons"}), sort_keys=True
                ).encode()
            ).hexdigest(),
            listing_fingerprint=evaluation.listing_fingerprint,
            base_cv_document_id=base_cv_id,
            tailored_cv={
                "base_cv_id": base_cv_id,
                "summary": tailored_draft.summary,
                "skills": tailored_draft.skills,
                "experience": tailored_draft.experience,
                "projects": tailored_draft.projects,
                "languages": tailored_draft.languages,
                "education": tailored_draft.education,
            },
            cv_change_audit=[
                CvChangeItem.model_validate(c.model_dump()) for c in tailored_draft.changes
            ],
            fact_verification=cv_verifications,
            cover_letter=cover_draft.cover_letter,
            application_answers=app_answers,
            knockout_answers=[
                KnockoutAnswer(
                    question=a.question,
                    proposed_answer=a.proposed_answer,
                    classification=a.classification,
                    evidence_refs=a.evidence_refs,
                    evidence=", ".join(a.evidence_refs),
                    confidence=a.confidence,
                    warning=a.warning,
                )
                for a in app_answers
                if any(
                    term in a.question.casefold()
                    for term in (
                        "years",
                        "degree",
                        "authorized",
                        "visa",
                        "sponsor",
                        "location",
                        "clearance",
                        "certification",
                    )
                )
            ],
            warnings=warnings,
            readiness_reasons=list(warnings),
            generated_documents=generated_docs,
            readiness=readiness,
            provenance={
                "provider": self.reasoner.provider_name,
                "base_cv_document_id": base_cv_id,
                "prepared_at": now.isoformat(),
                "candidate_context_revision": cand_ctx.revision,
                "render_validation": render_validation["status"],
                "render_details": render_validation,
                "visual_validation": "unavailable",
            },
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
        )

        # 9. Canonical Persistence: Application entity (preparing status, never auto-submitted)
        fresh_candidate = await build_candidate_career_context(session)
        fresh_listing = await build_career_listing_context(session, opp)
        if (
            fresh_candidate.revision != cand_ctx.revision
            or fresh_listing.listing_fingerprint != listing_ctx.listing_fingerprint
        ):
            raise ValueError("Evidence changed during package generation; retry required.")
        app = await session.get(Application, opportunity_id)
        if app is None:
            # Create Application entity backed via create_entity
            app = Application(
                opportunity_id=opportunity_id,
                status="preparing",
                cover_letter=cover_draft.cover_letter,
                cv_document_id=uuid.UUID(base_cv_id) if base_cv_id else None,
                cv_title=f"{listing_ctx.company} Tailored CV",
                package=package_model.model_dump(),
                created_at=now,
                updated_at=now,
            )
            session.add(app)
        else:
            app.package = package_model.model_dump()
            app.cover_letter = cover_draft.cover_letter
            app.updated_at = now
            if app.status == "preparing":
                await touch_entity(session, opp.id)

        await session.flush()

        await log_event(
            session,
            verb="opportunity.package_prepared",
            entity_id=opp.id,
            entity_type="opportunity",
            payload={
                "readiness": readiness,
                "unsupported_claims": has_unsupported,
                "needs_input": has_needs_input,
                "warnings_count": len(warnings),
            },
        )

        return package_model

    async def resolve_user_answer(
        self,
        session: AsyncSession,
        opportunity_id: uuid.UUID,
        question: str,
        user_answer: str,
    ) -> ApplicationPackage:
        """Resolve a 'needs_user_input' question with user-provided answer and re-evaluate readiness."""
        pkg = await self.get_package(session, opportunity_id)
        if pkg is None:
            raise ValueError("Application package does not exist.")
        if not user_answer.strip() or not any(
            a.question == question for a in pkg.application_answers
        ):
            raise ValueError("A known question and non-empty user answer are required.")
        import hashlib

        manual_ref = (
            f"manual_answer:{opportunity_id}:{hashlib.sha256(question.encode()).hexdigest()[:16]}"
        )
        provenance = dict(pkg.provenance)
        provenance["user_answers"] = dict(provenance.get("user_answers") or {})
        provenance["user_answers"][manual_ref] = {
            "question": question,
            "answer": user_answer,
            "source_type": "manual",
            "verified": True,
            "recorded_at": datetime.now(UTC).isoformat(),
        }
        pkg.provenance = provenance

        updated_answers = []
        for ans in pkg.application_answers:
            if ans.question == question:
                updated_answers.append(
                    ApplicationAnswer(
                        question=ans.question,
                        proposed_answer=user_answer,
                        classification="safe_verified",
                        evidence_refs=[manual_ref],
                        confidence=1.0,
                        warning=None,
                    )
                )
            else:
                updated_answers.append(ans)

        pkg.application_answers = updated_answers
        for knockout in pkg.knockout_answers:
            if knockout.question == question:
                knockout.proposed_answer = user_answer
                knockout.classification = "safe_verified"
                knockout.evidence_refs = [manual_ref]
                knockout.evidence = manual_ref
                knockout.confidence = 1
                knockout.warning = None

        # Re-check readiness
        has_unsupported = pkg.readiness == "UNSUPPORTED_CLAIMS" or any(
            fv.status == "unsupported" for fv in pkg.fact_verification
        )
        has_needs_input = any(
            a.classification in ("needs_user_input", "sensitive_user_decision")
            for a in pkg.application_answers
        )

        new_warnings = [
            w
            for w in pkg.warnings
            if not w.startswith(f"Question requires user input: '{question}'")
        ]

        if has_unsupported:
            pkg.readiness = "UNSUPPORTED_CLAIMS"
        elif has_needs_input:
            pkg.readiness = "NEEDS_INPUT"
        elif pkg.readiness in ("STALE_EVALUATION", "RENDER_FAILED"):
            pass
        elif (
            not pkg.base_cv_document_id
            or not pkg.generated_documents
            or pkg.provenance.get("render_validation") != "passed"
            or bool(pkg.cover_letter)
            or any(fv.status == "ambiguous" for fv in pkg.fact_verification)
        ):
            pkg.readiness = "NEEDS_INPUT"
        else:
            pkg.readiness = "READY"

        pkg.warnings = new_warnings
        pkg.updated_at = datetime.now(UTC).isoformat()

        # Update in database
        app = await session.get(Application, opportunity_id)
        if app is not None:
            app.package = pkg.model_dump()
            await session.flush()
            # Answer resolution cannot bypass the current source/artifact gate.
            # Revalidate before the outer transaction can commit or return READY.
            if pkg.readiness == "READY":
                checked = await self.get_package(session, opportunity_id)
                if checked is not None:
                    pkg = checked
                    app.package = pkg.model_dump()
                    await session.flush()
            await log_event(
                session,
                verb="opportunity.package_answer_resolved",
                entity_id=opportunity_id,
                entity_type="opportunity",
                payload={"evidence_ref": manual_ref},
            )

        return pkg
