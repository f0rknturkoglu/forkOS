"""Offline real scraper -> bridge -> worker closure eligibility regressions."""

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.modules.opportunity import service, worker
from app.modules.opportunity.models import OpportunitySourceObservation
from app.sources.base import ScrapeTelemetry, telemetry_acquisition_partial
from app.sources.forkjob_core.models import Job, Layer
from app.sources.forkjob_core.scrapers.base import ScraperPermanentError
from app.sources.forkjob_core.scrapers.dailyremote import DailyRemoteScraper
from app.sources.forkjob_core.scrapers.eurotechjobs import EuroTechJobsScraper
from app.sources.forkjob_core.scrapers.nofluffjobs import NoFluffJobsScraper
from app.sources.forkjob_core.scrapers.registry import load_registry_b
from app.sources.forkjob_core.scrapers.wearedevelopers import WeAreDevelopersScraper
from app.sources.forkjob_port import PortalSource

ROOT = Path(__file__).parent / "sources/fixtures/batch3"
LISTING = "".join(
    f'<div class="lst-card__content"><h2 class="lst-card__title"><a href="/remote-job/engineer-{i}">Engineer</a></h2><span class="lst-card__company">Employer</span><p class="lst-card__summary">Preview</p></div>'
    for i in range(1, 4)
)
DETAIL = (
    '<script type="application/ld+json">'
    + json.dumps(
        {
            "@type": "JobPosting",
            "title": "Engineer",
            "description": "Full employer prose",
            "hiringOrganization": {"name": "Employer"},
        }
    )
    + "</script>"
)


@pytest.mark.parametrize(
    "scenario,partial",
    [("budget", False), ("detail_failure", False), ("page_cap", True), ("listing_failure", True)],
)
async def test_real_daily_bridge_worker_eligibility(monkeypatch, scenario, partial):
    class Client:
        async def get_html(self, url):
            if "remote-jobs" in url:
                if "page=2" in url:
                    if scenario == "listing_failure":
                        raise ScraperPermanentError("listing HTTP 503")
                    return "<div data-empty-results></div>"
                return LISTING
            if scenario == "detail_failure":
                raise ScraperPermanentError("detail HTTP 503")
            return DETAIL

    scraper = DailyRemoteScraper(
        max_pages=1 if scenario == "page_cap" else 2,
        detail_budget=3 if scenario == "detail_failure" else 1,
    )
    batch = await scraper.collect(Client())

    async def collect():
        return batch

    monkeypatch.setattr(scraper, "collect", collect)
    monkeypatch.setattr("app.sources.forkjob_port.get_scraper", lambda _: scraper)
    source = PortalSource(load_registry_b().by_key("dailyremote"))
    outcome = await source.fetch()
    assert len(outcome.items) == 3
    assert outcome.partial is partial
    telemetry = outcome.telemetry
    assert telemetry.metadata["listing_complete"] is (not partial)
    assert telemetry.metadata["richness_partial"]
    if not partial:
        assert not telemetry.cap_hit and telemetry.partial_reason is None
        assert telemetry.stop_reason == "exhausted"
    if scenario == "detail_failure":
        assert telemetry.metadata["richness_partial_reason"] == "detail_request_failed"
    missing = Job.build(
        url="https://dailyremote.com/remote-job/missing-999",
        source="dailyremote",
        layer=Layer.B,
        title="Previously acquired missing job",
        company="Employer",
        external_id="999",
    )
    async with SessionLocal() as session:
        await service.ingest_jobs(session, [missing], source.id)
        await session.commit()
    sweep = AsyncMock(wraps=worker._sweep_missing)
    monkeypatch.setattr(worker, "_sweep_missing", sweep)
    await worker.poll_source(source)
    assert sweep.await_count == (0 if partial else 1)
    async with SessionLocal() as session:
        observation = (
            await session.execute(
                select(OpportunitySourceObservation).where(
                    OpportunitySourceObservation.source == source.id,
                    OpportunitySourceObservation.external_id == "999",
                )
            )
        ).scalar_one()
        assert observation.source_status == ("active" if partial else "missing")


@pytest.mark.no_database
async def test_nofluff_exhaustion_with_bounded_enrichment():
    class Client:
        async def post_json(self, *args, **kwargs):
            return {
                "totalPages": 1,
                "postings": [
                    {"id": str(i), "title": f"Engineer {i}", "url": f"engineer-{i}"}
                    for i in range(3)
                ],
            }

        async def get_html(self, url):
            return DETAIL

    scraper = NoFluffJobsScraper(max_pages=1, detail_budget=1)
    jobs = await scraper.scrape(Client())
    assert len(jobs) == 3
    assert not telemetry_acquisition_partial(scraper.telemetry)
    assert scraper.telemetry.stop_reason == "exhausted"
    assert scraper.telemetry.metadata["richness_partial"]


@pytest.mark.no_database
async def test_wad_page_bound_and_richness_independent():
    body = (
        ROOT / "wearedevelopers.md"
    ).read_text() + "\n[Next page](https://www.wearedevelopers.com/jobs?page=2)"

    class Client:
        async def get_html(self, url):
            return body

    scraper = WeAreDevelopersScraper(queries=[""], max_pages=1, detail_budget=0)
    result = await scraper.scrape(Client())
    assert result.jobs and telemetry_acquisition_partial(result.telemetry)
    assert not result.telemetry.metadata["listing_complete"]
    assert result.telemetry.metadata["richness_partial"]


@pytest.mark.no_database
async def test_euro_window_stays_incomplete_when_details_succeed(monkeypatch):
    from app.sources.forkjob_core.models import Job, Layer

    job = Job.build(
        url="https://www.eurotechjobs.com/job_display/123/example",
        source="eurotechjobs",
        layer=Layer.B,
        title="Engineer",
        company="Employer",
        external_id="123",
    )

    class Client:
        async def get_html(self, url):
            return '<div class="jobDisplay"><h2>Engineer</h2><p>Full employer prose</p></div>'

    scraper = EuroTechJobsScraper(countries=["germany"], detail_budget=1)
    monkeypatch.setattr(scraper, "parse", lambda _: [job])
    assert len(await scraper.scrape(Client())) == 1
    assert telemetry_acquisition_partial(scraper.telemetry)
    assert not scraper.telemetry.metadata["listing_complete"]
    assert not scraper.telemetry.metadata["richness_partial"]


@pytest.mark.no_database
@pytest.mark.parametrize(
    "metadata,cap,reason,expected",
    [
        ({"listing_complete": False}, False, None, True),
        ({"listing_complete": True, "richness_partial": True}, False, None, False),
        ({"listing_complete": True}, True, None, True),
        ({}, False, "legacy_window", True),
    ],
)
def test_conservative_generic_contract(metadata, cap, reason, expected):
    assert (
        telemetry_acquisition_partial(
            ScrapeTelemetry(metadata=metadata, cap_hit=cap, partial_reason=reason)
        )
        is expected
    )
