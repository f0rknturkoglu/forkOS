"""Opt-in bounded smoke of changed public contracts; no production DB writes."""

import json
import os
import time
from dataclasses import asdict
from pathlib import Path

import pytest

from app.sources.forkjob_core.scrapers.base import ScrapeBatch, ScraperConfig, ScraperHttpClient
from app.sources.forkjob_core.scrapers.bulldogjob import BulldogjobScraper
from app.sources.forkjob_core.scrapers.dailyremote import DailyRemoteScraper
from app.sources.forkjob_core.scrapers.eurotechjobs import EuroTechJobsScraper
from app.sources.forkjob_core.scrapers.fourdayweek import FourDayWeekScraper
from app.sources.forkjob_core.scrapers.himalayas import HimalayasScraper
from app.sources.forkjob_core.scrapers.jobgether import JobgetherScraper
from app.sources.forkjob_core.scrapers.nofluffjobs import NoFluffJobsScraper
from app.sources.forkjob_core.scrapers.solidjobs import SolidJobsScraper
from app.sources.forkjob_core.scrapers.wearedevelopers import WeAreDevelopersScraper
from app.sources.forkjob_core.scrapers.workingnomads import WorkingNomadsScraper

pytestmark = [pytest.mark.no_database, pytest.mark.skipif(os.getenv("FORKOS_RUN_LIVE_CAREER_TESTS") != "1", reason="bounded career live smoke is opt-in")]


@pytest.mark.parametrize("factory,options", [
    (HimalayasScraper, {}), (WorkingNomadsScraper, {}),
    (FourDayWeekScraper, {"max_pages": 1}), (SolidJobsScraper, {"max_pages": 1}),
    (WeAreDevelopersScraper, {"queries": [""], "max_pages": 1, "detail_budget": 1}),
    (DailyRemoteScraper, {"max_pages": 1, "detail_budget": 1}),
    (JobgetherScraper, {"keywords": ["developer"], "max_pages": 1, "detail_budget": 1}),
    (NoFluffJobsScraper, {"max_pages": 1, "detail_budget": 1}),
    (BulldogjobScraper, {"max_pages": 1, "detail_budget": 1}),
    (EuroTechJobsScraper, {"countries": ["spain"], "detail_budget": 1}),
])
async def test_changed_public_source_bounded_contract(factory, options):
    from app.sources.forkjob_core.rich_text import source_fact
    started = time.monotonic()
    scraper = factory(ScraperConfig(timeout=15, max_retries=1), **options)
    class MeteredClient(ScraperHttpClient):
        requests = 0
        async def _read_bounded_response(self, method, url, **kwargs):
            self.requests += 1
            return await super()._read_bounded_response(method, url, **kwargs)
    async with MeteredClient(scraper.config) as client:
        result = await scraper.collect(client)
    jobs = result.jobs if isinstance(result, ScrapeBatch) else result
    assert scraper.telemetry is not None
    assert all(j.title and j.url and j.external_id for j in jobs)
    if isinstance(result, ScrapeBatch):
        assert not result.errors, result.errors
    assert scraper.telemetry.items_returned == len(jobs)
    row = {"source": scraper.source, "jobs": len(jobs), "seconds": round(time.monotonic() - started, 3),
        "http_requests_including_robots": client.requests, "telemetry": asdict(scraper.telemetry),
        "parser_errors": list(scraper.errors),
        "fields": {"stable_external_id": sum(bool(j.external_id) for j in jobs),
            "country": sum(bool(j.country) for j in jobs), "salary": sum(bool(j.salary) for j in jobs),
            "language": sum(bool(j.language) for j in jobs), "technologies": sum(bool(source_fact(j.description, "Technologies")) for j in jobs),
            "remote_scope": sum(bool(source_fact(j.description, "Remote scope")) for j in jobs),
            "visa_relocation": sum(bool(source_fact(j.description, "Visa sponsorship") or source_fact(j.description, "Relocation")) for j in jobs),
            "specific_apply_url": sum(bool(source_fact(j.description, "Application URL")) for j in jobs),
            "employer_date": sum(j.date_source.value == "employer" for j in jobs)},
        "full_employer_jd_percentage": None}
    report = os.getenv("FORKOS_BATCH3_RECEIPTS")
    if report:
        with Path(report).open("a") as stream:
            stream.write(json.dumps(row) + "\n")
    print(f"\n{scraper.source}: jobs={len(jobs)} telemetry={scraper.telemetry}")
