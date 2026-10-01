"""Offline synthetic V1/V2 identity, evidence and ordinary candidate integration."""

from pathlib import Path

from sqlalchemy import select

from app.db import SessionLocal
from app.modules.opportunity.models import Opportunity, OpportunitySourceObservation
from app.modules.opportunity.service import ingest_jobs
from app.modules.opportunity.worker import NativeJob
from app.sources.forkjob_core.scrapers.linkedin_jobspy import job_from_row
from app.sources.forkjob_core.scrapers.linkedin_parsing import detail_job, parse_cards
from app.sources.forkjob_port import job_to_raw

ROOT = Path(__file__).parent / "sources/fixtures/linkedin-v2"


async def test_native_and_jobspy_one_canonical_identity_richer_evidence():
    card = parse_cards((ROOT / "cards.html").read_text())[0][0]
    native = detail_job((ROOT / "detail.html").read_text(), card)
    legacy = job_from_row(
        {
            "id": "li-111",
            "title": card.title,
            "company": card.company,
            "job_url": card.url,
            "description": "short preview",
        }
    )
    async with SessionLocal() as session:
        assert (
            await ingest_jobs(session, [NativeJob(job_to_raw(native))], "forkjob_core:linkedin")
            == 1
        )
        assert (
            await ingest_jobs(session, [NativeJob(job_to_raw(legacy))], "forkjob_core:linkedin")
            == 0
        )
        await session.commit()
        row = (await session.execute(select(Opportunity))).scalar_one()
        assert "Build software" in row.raw["forkjob"]["description"]
        assert row.score is not None and row.raw["candidate_match"]
        observations = (await session.execute(select(OpportunitySourceObservation))).scalars().all()
        assert len(observations) == 1 and observations[0].source == "forkjob_core:linkedin"


async def test_linkedin_freehire_employer_specific_application_overlap():
    card = parse_cards((ROOT / "cards.html").read_text())[0][0]
    job = detail_job((ROOT / "detail.html").read_text(), card)
    linked = job_to_raw(job)
    meta = job_to_raw(job)
    meta.external_id = "meta-copy"
    meta.url = "https://employer.example/jobs/111"
    meta.extra["source_authority"] = "meta"
    meta.extra["forkjob"] = {**meta.extra["forkjob"], "source": "freehire", "url": meta.url}
    employer = job_to_raw(job)
    employer.external_id = "ats-111"
    employer.url = meta.url
    employer.extra["forkjob"] = {**employer.extra["forkjob"], "source": "lever", "url": meta.url}
    async with SessionLocal() as session:
        assert await ingest_jobs(session, [NativeJob(linked)], "forkjob_core:linkedin") == 1
        assert await ingest_jobs(session, [NativeJob(meta)], "forkjob_core:freehire") == 0
        assert await ingest_jobs(session, [NativeJob(employer)], "forkjob_core:lever:employer") == 0
        await session.commit()
        rows = (await session.execute(select(Opportunity))).scalars().all()
        assert len(rows) == 1
        observations = (await session.execute(select(OpportunitySourceObservation))).scalars().all()
        assert {r.source for r in observations} == {
            "forkjob_core:linkedin",
            "forkjob_core:freehire",
            "forkjob_core:lever:employer",
        }
