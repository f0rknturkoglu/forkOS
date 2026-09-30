"""Batch 1 follows canonical ingestion/matching; isolated *_test DB only."""

import json
from pathlib import Path

from sqlalchemy import select

from app.db import SessionLocal
from app.modules.opportunity.candidate_context import CandidateCareerContext, CandidateFact
from app.modules.opportunity.candidate_fit import canonical_description
from app.modules.opportunity.candidate_match import calculate_candidate_match
from app.modules.opportunity.models import Opportunity, OpportunitySourceObservation
from app.modules.opportunity.service import ingest_jobs
from app.modules.opportunity.worker import NativeJob
from app.sources.forkjob_core.scrapers.techjobs_family import GermanTechJobsScraper
from app.sources.forkjob_port import job_to_raw


async def test_fixture_to_canonical_score_candidate_and_cross_source_observation():
    row = json.loads(
        (Path(__file__).parent / "sources/fixtures/native_batch1/german.json").read_text()
    )[0]
    row.update(
        name="Junior Backend Engineer",
        language="English",
        hasVisaSponsorship="Yes",
        technologies=["Python", "AWS"],
    )
    row["activeFrom"] = "2026-08-01T00:00:00Z"
    row["redirectJobUrl"] = "https://job-boards.greenhouse.io/synthetic/jobs/123456"
    job = GermanTechJobsScraper().build_job(row)
    rich = NativeJob(job_to_raw(job))
    async with SessionLocal() as session:
        assert await ingest_jobs(session, [rich], "forkjob_core:germantechjobs") == 1
        await session.commit()
        opportunity = (await session.execute(select(Opportunity))).scalar_one()
        assert (
            opportunity.score is not None
            and opportunity.raw["candidate_fit"]["reasons"]["visa"]["delta"] > 0
        )
        assert opportunity.raw["candidate_fit"]["reasons"]["freshness"]["source"] == "updated"
        description = canonical_description(opportunity.raw)
        assert "Visa sponsorship: Yes" in description and "Technologies: Python, AWS" in description
        context = CandidateCareerContext(
            revision="fixture",
            facts=[CandidateFact(key="skill:python", value="Python", source_type="config")],
        )
        native_match = calculate_candidate_match(opportunity, job.title, context)
        assert "Python" in native_match["matched"]
        # Employer observation supplies longer JD; native fact block must survive.
        ats = job_to_raw(job)
        ats.external_id = "ats-1"
        ats.url = row["redirectJobUrl"]
        ats.extra.pop("apply_url", None)
        ats.summary = "Full employer requirements Python AWS. " * 250
        ats.extra["forkjob"] = {**ats.extra["forkjob"], "description": ats.summary}
        assert (
            await ingest_jobs(session, [NativeJob(ats)], "forkjob_core:greenhouse:synthetic") == 0
        )
        await session.commit()
        assert (await session.execute(select(Opportunity))).scalars().all() == [opportunity]
        assert ats.summary.strip() in canonical_description(opportunity.raw)
        assert "Visa sponsorship: Yes" in canonical_description(opportunity.raw)
        # Later short native preview must not erase the full ATS description.
        assert await ingest_jobs(session, [rich], "forkjob_core:germantechjobs") == 0
        await session.commit()
        assert ats.summary.strip() in canonical_description(opportunity.raw)
        assert ats.summary.strip() in opportunity.raw["forkjob"]["description"]
        observations = (await session.execute(select(OpportunitySourceObservation))).scalars().all()
        assert {o.source for o in observations} == {
            "forkjob_core:germantechjobs",
            "forkjob_core:greenhouse:synthetic",
        }
        assert len({o.opportunity_id for o in observations}) == 1
        first = calculate_candidate_match(opportunity, job.title, context)
        opportunity.source = "careerops:companies"
        assert calculate_candidate_match(opportunity, job.title, context) == first
