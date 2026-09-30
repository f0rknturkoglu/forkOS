"""One canonical owner for official/native and lower-authority meta evidence."""

import json
from pathlib import Path

from sqlalchemy import select

from app.db import SessionLocal
from app.modules.opportunity.candidate_fit import canonical_description
from app.modules.opportunity.models import Opportunity, OpportunitySourceObservation
from app.modules.opportunity.service import ingest_jobs
from app.modules.opportunity.worker import NativeJob
from app.sources.forkjob_core.scrapers.freehire import FreeHireScraper
from app.sources.forkjob_core.scrapers.official_batch2 import WorkInDenmarkScraper
from app.sources.forkjob_port import job_to_raw

ROOT = Path(__file__).parent / "sources/fixtures/batch2"


def native():
    s = WorkInDenmarkScraper()
    return s.listing(json.loads((ROOT / "workindenmark.json").read_text()), s.listing_urls[0])[0][0]


def meta(job):
    row = json.loads((ROOT / "freehire.json").read_text())["data"][0]
    row.update(
        title=job.title,
        company=job.company,
        url=job.url,
        location=job.location,
        source="employer",
        public_slug="integration-shared",
        description="Long copied meta description. " * 500,
        countries=["DK"],
    )
    row["enrichment"] = {
        "salary_min": 1,
        "salary_max": 2,
        "salary_currency": "USD",
        "work_mode": "onsite",
    }
    return FreeHireScraper().parse_record(row)


async def test_official_freehire_meta_overlap_preserves_employer_and_scores():
    job = native()
    job.salary = "60000 EUR/year"
    async with SessionLocal() as session:
        assert (
            await ingest_jobs(session, [NativeJob(job_to_raw(job))], "forkjob_core:workindenmark")
            == 1
        )
        await session.commit()
        raw = job_to_raw(meta(job))
        assert raw.extra["source_authority"] == "meta"
        assert await ingest_jobs(session, [NativeJob(raw)], "forkjob_core:freehire") == 0
        raw.external_id = "relocantly-observed"
        raw.extra["forkjob"]["source"] = "relocantly"
        assert await ingest_jobs(session, [NativeJob(raw)], "forkjob_core:relocantly") == 0
        await session.commit()
        opportunity = (await session.execute(select(Opportunity))).scalar_one()
        assert opportunity.compensation == job.salary
        assert opportunity.raw["forkjob"]["salary"] == job.salary
        assert "Brand Manager" in canonical_description(opportunity.raw)
        assert "Long copied meta description." not in canonical_description(opportunity.raw)
        assert "Original source: employer" in canonical_description(opportunity.raw)
        assert opportunity.score is not None and opportunity.raw["candidate_match"]
        observations = (await session.execute(select(OpportunitySourceObservation))).scalars().all()
        assert {o.source for o in observations} == {
            "forkjob_core:workindenmark",
            "forkjob_core:freehire",
            "forkjob_core:relocantly",
        }
        assert len({o.opportunity_id for o in observations}) == 1


async def test_native_upgrade_of_first_meta_record():
    job = native()
    job.salary = "60000 EUR/year"
    async with SessionLocal() as session:
        assert (
            await ingest_jobs(session, [NativeJob(job_to_raw(meta(job)))], "forkjob_core:freehire")
            == 1
        )
        assert (
            await ingest_jobs(session, [NativeJob(job_to_raw(job))], "forkjob_core:workindenmark")
            == 0
        )
        await session.commit()
        opportunity = (await session.execute(select(Opportunity))).scalar_one()
        assert opportunity.compensation == job.salary
        assert opportunity.raw["source_authority"] == "native"
        assert "Long copied meta description." not in canonical_description(opportunity.raw)


async def test_similar_title_company_distinct_locations_not_merged():
    first = native()
    second = native()
    first.external_id = "separate-copenhagen"
    first.location = "Copenhagen, Denmark"
    first.city = "Copenhagen"
    second.external_id = "separate-oslo"
    second.location = "Oslo, Norway"
    second.city = "Oslo"
    second.country = "NO"
    second.url = "https://careers.st-group.com/job/different-oslo-posting/9999-en_US"
    second.description = second.description.replace(first.url, second.url)
    async with SessionLocal() as session:
        assert (
            await ingest_jobs(
                session,
                [NativeJob(job_to_raw(first)), NativeJob(job_to_raw(second))],
                "forkjob_core:workindenmark",
            )
            == 2
        )
        await session.commit()
        assert len((await session.execute(select(Opportunity))).scalars().all()) == 2
