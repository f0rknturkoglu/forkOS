"""Explicit real-source smoke against an EMPTY isolated test DB, never personal state."""

import argparse
import asyncio
import hashlib
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import httpx
from selectolax.parser import HTMLParser
from sqlalchemy import func, select

import app.modules  # noqa: F401
from app.config import settings
from app.core.entity import create_entity
from app.core.models import Entity
from app.core.test_guard import assert_safe_test_database
from app.db import SessionLocal, engine
from app.modules.document import service as documents
from app.modules.opportunity import interview_intelligence as interview_ai
from app.modules.opportunity.candidate_context import build_candidate_career_context
from app.modules.opportunity.career_analytics import snapshot
from app.modules.opportunity.evaluation_service import CareerEvaluationService
from app.modules.opportunity.models import ApplicationHistory, Interview, Opportunity
from app.modules.opportunity.package_service import ApplicationPackageService
from app.modules.opportunity.reasoner.mock import DeterministicMockCareerReasoner


async def run(cv: Path, jd_url: str, qa_dir: Path | None = None):
    assert_safe_test_database(settings.database_url)
    source = cv.read_bytes()
    original_hash = hashlib.sha256(source).hexdigest()
    if not jd_url.startswith("https://boards-api.greenhouse.io/v1/boards/"):
        raise ValueError("This smoke accepts only explicit public Greenhouse job API URLs.")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(jd_url)
        response.raise_for_status()
        job = response.json()
    jd = HTMLParser(job["content"]).text(separator="\n", strip=True)
    if len(jd) < 300 or not job.get("absolute_url"):
        raise ValueError("Real JD unavailable")
    with tempfile.TemporaryDirectory(prefix="forkos-career-smoke-") as directory:
        documents.DOCUMENTS_DIR = Path(directory) / "documents"
        async with SessionLocal() as session:
            if await session.scalar(select(func.count()).select_from(Entity)):
                raise ValueError("Smoke requires an empty isolated test database.")
            doc = await documents.create_local_document(
                session,
                title=cv.name,
                content=source,
                category="cv",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                commit=False,
            )
            entity = await create_entity(session, type="opportunity", title=job["title"])
            opportunity = Opportunity(
                id=entity.id,
                kind="job",
                organization="Greenhouse live source",
                url=job["absolute_url"],
                raw={"description": jd},
                found_at=datetime.now(UTC),
            )
            session.add(opportunity)
            await session.flush()
            context = await build_candidate_career_context(session)
            assert context.base_cv and context.base_cv["content_available"]
            reasoner = DeterministicMockCareerReasoner()
            evaluation = await CareerEvaluationService(reasoner).evaluate_opportunity(
                session, opportunity.id
            )
            package = await ApplicationPackageService(reasoner).prepare_application_package(
                session, opportunity.id
            )
            assert all(ref.document_id for ref in package.generated_documents)
            assert cv.read_bytes() == source
            interview = Interview(opportunity_id=opportunity.id, stage="technical_screen")
            session.add(interview)
            await session.flush()
            prep = await interview_ai.prepare(session, interview.id)
            report = await interview_ai.debrief(
                session,
                interview.id,
                interview_ai.DebriefIn(
                    occurred_at=datetime.now(UTC),
                    candidate_notes="Synthetic interview fixture, not a real-world event.",
                    topics=["Python"],
                    perceived_gaps=["Python"],
                ),
            )
            session.add(
                ApplicationHistory(
                    opportunity_id=opportunity.id,
                    scope="application",
                    from_status="preparing",
                    to_status="applied",
                    at=datetime.now(UTC),
                )
            )
            await session.flush()
            analytics = await snapshot(session)
            assert prep.candidate_context_revision == context.revision
            assert report.outcome_if_known is None
            assert analytics.funnel["applied"] == analytics.funnel["interview"] == 1
            if qa_dir:
                qa_dir.mkdir(parents=True, exist_ok=True)
                for ref in package.generated_documents:
                    if ref.doc_type == "pdf_cv":
                        from uuid import UUID

                        target = qa_dir / "career-smoke.pdf"
                        if target.exists():
                            raise ValueError("Refusing to overwrite an existing QA artifact.")
                        original = documents.get_local_file_path(UUID(ref.document_id), "unused")
                        target.write_bytes(original.read_bytes())
            print(
                json.dumps(
                    {
                        "provider": "mock",
                        "live_model": False,
                        "source_sha256": original_hash,
                        "source_unchanged": True,
                        "cv_facts": sum(f.source_id == str(doc["id"]) for f in context.facts),
                        "jd_chars": len(jd),
                        "candidate_revision": context.revision,
                        "evaluation_refs": len(evaluation.evidence),
                        "documents": len(package.generated_documents),
                        "pdf_produced": any(
                            d.doc_type == "pdf_cv" for d in package.generated_documents
                        ),
                        "readiness": package.readiness,
                        "render": package.provenance["render_details"],
                        "auto_send_submit": False,
                        "interview_fixture": True,
                        "prep_provider": prep.provider,
                        "prep_revision_bound": True,
                        "debrief_source": report.source_type,
                        "analytics_population": analytics.population,
                        "analytics_fingerprint": analytics.fingerprint,
                    },
                    indent=2,
                )
            )
            await session.rollback()
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cv", type=Path, required=True)
    parser.add_argument("--jd-url", required=True)
    parser.add_argument("--qa-dir", type=Path)
    args = parser.parse_args()
    asyncio.run(run(args.cv, args.jd_url, args.qa_dir))
