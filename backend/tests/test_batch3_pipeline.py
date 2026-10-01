"""Synthetic rich contracts, real canonical persistence in the isolated test DB."""

import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.modules.opportunity.candidate_context import CandidateCareerContext, CandidateFact
from app.modules.opportunity.candidate_fit import canonical_description
from app.modules.opportunity.candidate_match import calculate_candidate_match
from app.modules.opportunity.models import Opportunity, OpportunitySourceObservation
from app.modules.opportunity.service import ingest_jobs
from app.modules.opportunity.worker import NativeJob
from app.sources.forkjob_core.models import Company, Job, Layer, WorkMode
from app.sources.forkjob_core.rich_text import enrich
from app.sources.forkjob_core.scrapers.schemaorg import schema_job
from app.sources.forkjob_core.scrapers.solidjobs import SolidJobsScraper
from app.sources.forkjob_core.sources.adapters import LeverAdapter
from app.sources.forkjob_port import job_to_raw

APPLY = "https://jobs.lever.co/synthetic/00000000-0000-4000-8000-000000000001"


def rich_job(family):
    common = dict(url=APPLY, title="Junior Backend Engineer", company="Synthetic Employer")
    if family == "lever":
        return LeverAdapter(Company("Synthetic Employer", "lever", "synthetic")).parse([
            {"id": "1", "text": common["title"], "hostedUrl": APPLY, "applyUrl": APPLY,
             "categories": {"location": "Berlin, Germany"}, "workplaceType": "remote",
             "description": "Employer requirements Python AWS. Visa sponsorship: Yes. English required.",
             "skills": ["Python", "AWS"], "visaSponsorship": True, "workingLanguage": "English",
             "salaryRange": {"min": 50000, "max": 65000, "currency": "EUR", "interval": "year"}}
        ])[0]
    if family == "solidjobs":
        job = SolidJobsScraper().build_job({**common, "jobOfferKey": "1", "isRemote": True,
            "locations": ["Berlin"], "description": "Employer requirements Python AWS. Visa sponsorship: Yes.",
            "skills": [{"name": "Python"}, {"name": "AWS"}], "languages": [{"name": "English", "level": "B2"}],
            "salary": {"from": 50000, "to": 65000, "currency": "EUR", "period": "year"}, "validFrom": "2026-10-01"})
        job.description = enrich(job.description, job.source, {"Application URL": APPLY})
        return job
    job = schema_job({"skills": "Python, AWS", "baseSalary": {"currency": "EUR", "value": {"minValue": 50000, "maxValue": 65000, "unitText": "YEAR"}}, "applicantLocationRequirements": {"name": "Germany"}},
        **common, source="schema-board", layer=Layer.B, external_id="1", work_mode=WorkMode.REMOTE,
        language="English", description="Employer requirements Python AWS. Visa sponsorship: Yes.")
    job.description = enrich(job.description, job.source, {"Application URL": APPLY})
    return job


@pytest.mark.parametrize("family", ["lever", "solidjobs", "schema"])
@pytest.mark.parametrize("meta_first", [False, True])
async def test_rich_families_survive_meta_native_orders_matching_and_identity(family, meta_first):
    native = rich_job(family)
    meta = Job.build(url="https://meta.example/job/1", source="freehire", layer=Layer.B,
        external_id="meta-1", company=native.company, title=native.title,
        description=enrich("Long inferior copy. " * 500, "freehire", {"Source authority": "meta", "Application URL": APPLY, "Board sponsorship claim": "No", "Original source": family}), salary="1 USD/year")
    rows = [meta, native] if meta_first else [native, meta]
    async with SessionLocal() as session:
        for index, job in enumerate(rows):
            assert await ingest_jobs(session, [NativeJob(job_to_raw(job))], "forkjob_core:" + job.source) == (1 if index == 0 else 0)
        await session.commit()
        opportunity = (await session.execute(select(Opportunity))).scalar_one()
        description = canonical_description(opportunity.raw)
        assert "Employer requirements" in description and "Long inferior copy" not in description
        assert "Python" in description and "Application URL: " + APPLY in description
        assert opportunity.compensation == native.salary and opportunity.raw["forkjob"]["salary"] == native.salary
        assert opportunity.raw["forkjob"]["language"] == "English"
        assert opportunity.raw["forkjob"]["date_source"] == native.date_source.value
        assert "Remote scope:" in description and "Visa sponsorship: Yes" in description
        assert opportunity.score is not None and opportunity.raw["candidate_fit"]["reasons"]["visa"]["delta"] > 0
        context = CandidateCareerContext(revision="batch3", facts=[CandidateFact(key="skill:python", value="Python", source_type="config")])
        assert "Python" in calculate_candidate_match(opportunity, native.title, context)["matched"]
        observations = (await session.execute(select(OpportunitySourceObservation))).scalars().all()
        assert len(observations) == 2 and len({r.opportunity_id for r in observations}) == 1
        # A preview refresh cannot erase employer prose or source-attributed facts.
        native.description = enrich("Short preview", native.source, {"Application URL": APPLY})
        assert await ingest_jobs(session, [NativeJob(job_to_raw(native))], "forkjob_core:" + native.source) == 0
        await session.commit()
        assert "Employer requirements" in canonical_description(opportunity.raw)


async def test_employer_prose_wins_over_longer_native_board_copy():
    employer = rich_job("lever")
    board = rich_job("schema")
    board.description = enrich("Long board copy. " * 800, board.source, {"Application URL": APPLY, "Source authority": "native"})
    async with SessionLocal() as session:
        assert await ingest_jobs(session, [NativeJob(job_to_raw(board))], "forkjob_core:" + board.source) == 1
        assert await ingest_jobs(session, [NativeJob(job_to_raw(employer))], "forkjob_core:" + employer.source) == 0
        assert await ingest_jobs(session, [NativeJob(job_to_raw(board))], "forkjob_core:" + board.source) == 0
        await session.commit()
        row = (await session.execute(select(Opportunity))).scalar_one()
        assert "Employer requirements" in canonical_description(row.raw)
        assert "Long board copy" not in canonical_description(row.raw)
        assert row.raw["source_authority"] == "employer"


async def test_source_refresh_corrects_old_inferred_language_and_meta_authority():
    job = rich_job("schema")
    job.source = "englishjobsde"
    job.language = "en"  # Synthetic representation of an old UI-language guess.
    job.description = "Long board copy. " * 500
    async with SessionLocal() as session:
        assert await ingest_jobs(session, [NativeJob(job_to_raw(job))], "forkjob_core:englishjobsde") == 1
        job.language = None
        job.description = enrich("Board preview", job.source, {"Source authority": "meta", "Application URL": APPLY})
        assert await ingest_jobs(session, [NativeJob(job_to_raw(job))], "forkjob_core:englishjobsde") == 0
        await session.commit()
        row = (await session.execute(select(Opportunity))).scalar_one()
        assert row.raw["source_authority"] == "meta" and row.raw["forkjob"]["language"] is None
        employer = rich_job("lever")
        assert await ingest_jobs(session, [NativeJob(job_to_raw(employer))], "forkjob_core:" + employer.source) == 0
        await session.commit()
        assert "Employer requirements" in canonical_description(row.raw)


async def test_workingnomads_native_url_id_upgrades_legacy_url_hash_without_duplicate():
    from app.sources.forkjob_core.scrapers.workingnomads import WorkingNomadsScraper
    job = WorkingNomadsScraper().parse([{"url": "https://www.workingnomads.com/job/go/1906010/", "title": "Junior Backend Engineer", "company_name": "Synthetic Employer", "description": "Job-specific prose"}])[0]
    assert job.external_id == "1906010"
    old = job_to_raw(job)
    old.external_id = job.job_id  # Old bridge fallback when API ID was missed.
    async with SessionLocal() as session:
        assert await ingest_jobs(session, [NativeJob(old)], "forkjob_core:workingnomads") == 1
        assert await ingest_jobs(session, [NativeJob(job_to_raw(job))], "forkjob_core:workingnomads") == 0
        await session.commit()
        assert len((await session.execute(select(Opportunity))).scalars().all()) == 1


@pytest.mark.parametrize("family", ["himalayas", "solidjobs", "fourdayweek"])
async def test_reduced_public_sample_canonical_replay_preserves_evidence(family):
    import json
    from pathlib import Path

    from app.sources.forkjob_core.scrapers.fourdayweek import FourDayWeekScraper
    from app.sources.forkjob_core.scrapers.himalayas import HimalayasScraper

    fixture = Path(__file__).parent / "sources/fixtures/batch3" / (family + ".json")
    factory = {"himalayas": HimalayasScraper, "solidjobs": SolidJobsScraper, "fourdayweek": FourDayWeekScraper}[family]
    job = factory().parse(json.loads(fixture.read_text()))[0]
    raw = job_to_raw(job)
    async with SessionLocal() as session:
        assert await ingest_jobs(session, [NativeJob(raw)], "forkjob_core:" + family) == 1
        assert await ingest_jobs(session, [NativeJob(raw)], "forkjob_core:" + family) == 0
        await session.commit()
        rows = (await session.execute(select(Opportunity))).scalars().all()
        assert len(rows) == 1
        row = rows[0]
        stored_description = row.raw["forkjob"]["description"]
        assert stored_description.split("\n\nSource facts")[0] == job.description.split("\n\nSource facts")[0]
        assert set(job.description.splitlines()) <= set(stored_description.splitlines())
        assert row.raw["forkjob"]["salary"] == job.salary
        assert row.raw["forkjob"]["language"] == job.language
        assert row.raw["forkjob"]["date_source"] == job.date_source.value
        assert row.raw["forkjob"]["external_id"] == job.external_id
