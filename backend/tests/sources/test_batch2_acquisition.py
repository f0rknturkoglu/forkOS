"""Offline public-source contracts from actual observed Batch 2 shapes."""

import json
from pathlib import Path
from unittest.mock import AsyncMock
from urllib.robotparser import RobotFileParser

import httpx
import pytest

from app.sources.forkjob_core.config import Config
from app.sources.forkjob_core.match import detect
from app.sources.forkjob_core.models import DateSource, WorkMode
from app.sources.forkjob_core.score import score_job
from app.sources.forkjob_core.scrapers.base import ScraperPermanentError
from app.sources.forkjob_core.scrapers.freehire import FreeHireScraper
from app.sources.forkjob_core.scrapers.index import get_scraper
from app.sources.forkjob_core.scrapers.registry import load_registry_b

pytestmark = pytest.mark.no_database
ROOT = Path(__file__).parent / "fixtures/batch2"
KEYS = (
    "arbeidsplassen",
    "workindenmark",
    "devjobsat",
    "developerjobsch",
    "englishjobsde",
    "workationbase",
    "jumpintoeu",
    "freehire",
    "workcamino",
    "relocantly",
)


def read(name):
    return (ROOT / name).read_text()


def scraper(key, **kwargs):
    source = load_registry_b().by_key(key)
    source.config = {**source.config, **kwargs}
    return get_scraper(source)


def listing(key, instance=None):
    s = instance or scraper(key)
    if key in {"freehire", "workindenmark"}:
        data = json.loads(read(key + ".json"))
    else:
        data = read(key + "-listing.html")
    return s.listing(data) if key == "freehire" else s.listing(data, s.base_url)


@pytest.mark.parametrize("key", KEYS)
def test_actual_listing_contract_and_identity(key):
    jobs, count, _ = listing(key)
    assert len(jobs) == count == 3
    assert len({j.external_id for j in jobs}) == 3
    for j in jobs:
        assert j.source == key and j.title and j.company and j.url.startswith("https://")
        score_job(j, Config())
        assert j.score is not None


@pytest.mark.parametrize(
    "key", ["arbeidsplassen", "devjobsat", "developerjobsch", "workationbase", "relocantly"]
)
def test_actual_full_detail_schema(key):
    s = scraper(key)
    job = s.detail(read(key + "-detail.html"), s.base_url + "/observed")
    assert job and len(job.description) > 500
    assert job.date_source is DateSource.EMPLOYER
    assert job.country in {"NO", "AT", "CH", "DE", None}


def test_nav_explicit_language_workload_expiry_no_visa_guess():
    s = scraper("arbeidsplassen")
    job = s.detail(read("arbeidsplassen-detail.html"), s.base_url)
    assert job.work_mode is WorkMode.ONSITE
    assert "Engelsk" in job.language and "Workload: Heltid" in job.description
    assert "Expiry:" in job.description
    assert "Visa sponsorship:" not in job.description


def test_official_danish_full_description_and_pagination():
    s = scraper("workindenmark")
    jobs, _, n = s.listing(json.loads(read("workindenmark.json")), s.listing_urls[0])
    assert "pageNumber=2" in n and "resultsPerPage=50" in n
    assert len(jobs[0].description) > 2000 and "Application deadline:" in jobs[0].description
    assert jobs[0].language is None and "Visa sponsorship:" not in jobs[0].description


def test_remote_eligibility_and_inferred_false_not_employer_refusal():
    job = listing("workationbase")[0][0]
    assert "Remote scope: Anywhere" in job.description
    assert "Timezone requirements: eu-friendly" in job.description
    assert "Board sponsorship flag: False" in job.description
    score_job(job, Config())
    assert detect(job, Config().scoring).visa == 0


def test_jump_board_insertion_is_not_employer_publish_and_claims_not_promises():
    job = listing("jumpintoeu")[0][0]
    assert job.date_source is DateSource.UPDATED
    assert job.salary and "GBP" in job.salary
    assert "Technologies:" in job.description and "Board sponsorship claim: True" in job.description
    score_job(job, Config())
    assert detect(job, Config().scoring).visa == 0


def test_meta_original_source_and_inference_provenance():
    jobs, _, _ = listing("workcamino")
    assert jobs[0].url.startswith("https://candidat.francetravail.fr/")
    assert "Original source: francetravail" in jobs[0].description
    assert "Workcamino text inference" in jobs[0].description
    assert all("$" not in j.description for j in jobs)
    assert all("Visa sponsorship:" not in j.description for j in jobs)


@pytest.mark.parametrize("visa,expected", [(True, "Yes"), (False, "No"), (None, None)])
def test_freehire_explicit_visa_tristate_rich_projection(visa, expected):
    row = json.loads(read("freehire.json"))["data"][0]
    row["enrichment"].update(
        visa_sponsorship=visa,
        seniority="junior",
        salary_min=50000,
        salary_max=65000,
        salary_currency="EUR",
        salary_period="year",
        work_mode="remote",
        experience_years_min=2,
    )
    job = FreeHireScraper().parse_record(row)
    assert job.salary == "50000-65000 EUR/year"
    assert "Original source:" in job.description and "Experience years: 2" in job.description
    if expected:
        assert "Visa sponsorship: " + expected in job.description
    else:
        assert "Visa sponsorship:" not in job.description


def test_freehire_missing_optional_and_corrupt_records():
    s = FreeHireScraper()
    row = json.loads(read("freehire.json"))["data"][0]
    minimal = {
        k: row[k] for k in ["public_slug", "source", "external_id", "url", "title", "company"]
    }
    assert s.parse_record(minimal).date_source is DateSource.DISCOVERED
    assert s.parse_record({"title": "junk"}) is None
    assert s.parse_record({**minimal, "enrichment": {"salary_min": {}}}) is None
    with pytest.raises(ScraperPermanentError):
        s.listing({"data": [{}], "meta": {"total": 1, "limit": 1, "offset": 0}})
    assert s.listing({"data": [], "meta": {"total": 0, "limit": 50, "offset": 0}})[0] == []


@pytest.mark.parametrize("key", [k for k in KEYS if k not in {"freehire", "workindenmark"}])
def test_suspicious_html_empty_is_never_healthy(key):
    with pytest.raises(ScraperPermanentError):
        scraper(key).listing("<html>Login / challenge</html>", scraper(key).base_url)


@pytest.mark.parametrize(
    "key",
    [
        "arbeidsplassen",
        "devjobsat",
        "developerjobsch",
        "englishjobsde",
        "workationbase",
        "jumpintoeu",
        "workcamino",
        "relocantly",
    ],
)
async def test_bound_is_partial_and_no_detail_storm(key):
    s = scraper(key, max_pages=1, max_offers=2, detail_budget=0)
    if key in {"workcamino", "relocantly"}:
        with pytest.raises(ScraperPermanentError, match="terms prohibit"):
            await s.collect(AsyncMock())
        return
    client = AsyncMock()
    client.get_html.return_value = read(key + "-listing.html")
    batch = await s.collect(client)
    assert len(batch.jobs) == 2 and batch.telemetry.cap_hit
    assert batch.telemetry.stop_reason != "exhausted"
    assert client.get_html.await_count == 1


async def test_later_page_failure_preserves_acquired_data():
    s = scraper("developerjobsch", detail_budget=0, max_pages=2)
    c = AsyncMock()
    c.get_html.side_effect = [
        read("developerjobsch-listing.html"),
        ScraperPermanentError("HTTP 403"),
    ]
    batch = await s.collect(c)
    assert len(batch.jobs) == 3 and batch.errors and batch.succeeded == 1


async def test_detail_failure_keeps_card_and_detail_cap():
    s = scraper("workationbase", max_pages=1, detail_budget=1)
    c = AsyncMock()
    c.get_html.side_effect = [read("workationbase-listing.html"), "<html>login</html>"]
    batch = await s.collect(c)
    assert len(batch.jobs) == 3 and batch.errors and c.get_html.await_count == 2
    assert batch.jobs[0].work_mode is WorkMode.REMOTE


async def test_freehire_caps_rate_headers_and_no_auth():
    s = FreeHireScraper(max_pages=2, page_size=3, slices=[{"regions": ["eu"]}])
    c = AsyncMock()
    data = json.loads(read("freehire.json"))
    c._request.return_value = httpx.Response(
        200,
        json=data,
        headers={
            "X-RateLimit-Remaining": "1",
            "X-RateLimit-Limit": "100",
            "X-RateLimit-Reset": "1900000000",
        },
    )
    batch = await s.collect(c)
    assert len(batch.jobs) == 3 and batch.telemetry.cap_hit
    assert batch.telemetry.stop_reason == "rate_budget_reached"
    assert batch.telemetry.metadata["rate_remaining"] == 1
    call = c._request.call_args
    assert "posted_within_days=7" in call.args[1]
    assert "regions=eu" in call.args[1] and not call.kwargs


async def test_freehire_page_failure_retains_jobs():
    s = FreeHireScraper(max_pages=2, page_size=3, slices=[{"regions": ["eu"]}])
    c = AsyncMock()
    c._request.side_effect = [
        httpx.Response(200, json=json.loads(read("freehire.json"))),
        ScraperPermanentError("HTTP 429"),
    ]
    batch = await s.collect(c)
    assert len(batch.jobs) == 3 and batch.errors and batch.telemetry.stop_reason == "request_failed"


def test_linkedin_robot_policy_blocks_guest_search_geo_details_and_fallback():
    robot = RobotFileParser()
    robot.parse(read("linkedin-robots.txt").splitlines())
    for path in [
        "/jobs",
        "/jobs-guest/jobs/api/seeMoreJobPostings/search",
        "/jobs-guest/jobs/api/jobPosting/123",
        "/jobs-guest/api/typeahead/locations",
    ]:
        assert not robot.can_fetch("forkjob/0.1", "https://www.linkedin.com" + path)
    assert load_registry_b().by_key("linkedin").enabled is False


async def test_linkedin_denial_cannot_start_jobspy(monkeypatch):
    from app.sources.forkjob_core.scrapers import linkedin

    s = linkedin.LinkedInScraper(
        searches=[{"term": "backend", "location": "Turkey"}], allow_direct=True
    )
    c = AsyncMock()
    c._check_robots.side_effect = ScraperPermanentError("robots disallows")
    runner = AsyncMock()
    monkeypatch.setattr(linkedin, "_run_jobspy_isolated", runner)
    with pytest.raises(ScraperPermanentError):
        await s.scrape(c)
    runner.assert_not_called()


@pytest.mark.parametrize("native,meta,expected", [("Yes", "No", 1), ("No", "Yes", -1)])
def test_native_sponsorship_wins_conflicting_meta_fact(native, meta, expected):
    from app.sources.forkjob_core.rich_text import enrich, merge_descriptions

    job = listing("freehire")[0][0]
    job.description = merge_descriptions(
        enrich("Software job", "employer", {"Visa sponsorship": native}),
        enrich(None, "freehire", {"Source authority": "meta", "Visa sponsorship": meta}),
    )
    assert detect(job, Config().scoring).visa == expected


@pytest.mark.parametrize("key", ["workcamino", "relocantly"])
async def test_terms_block_never_calls_network(key):
    client = AsyncMock()
    with pytest.raises(ScraperPermanentError, match="terms prohibit"):
        await scraper(key).collect(client)
    client.get_html.assert_not_awaited()
    client.get_json.assert_not_awaited()


@pytest.mark.parametrize(
    "target",
    [
        "http://127.0.0.1/private",
        "https://other.example/job",
        "https://user:pass@board.example/job",
        "https://board.example:8787/job",
    ],
)
async def test_public_redirect_rejects_other_hosts_and_credentials(target):
    from app.sources.forkjob_core.scrapers.base import (
        RobotsPolicy,
        ScraperConfig,
        ScraperHttpClient,
    )

    visited = []

    def handler(request):
        visited.append(str(request.url))
        return httpx.Response(302, headers={"location": target})

    client = ScraperHttpClient(
        ScraperConfig(
            allowed_hosts=("board.example",),
            robots=RobotsPolicy.IGNORE,
            min_interval=0,
            max_response_bytes=1000,
        )
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as transport:
        client._client = transport
        with pytest.raises(ScraperPermanentError, match="fixed public host scope"):
            await client.get_html("https://board.example/jobs")
    assert visited == ["https://board.example/jobs"]


async def test_public_decoded_response_bound():
    import gzip

    from app.sources.forkjob_core.scrapers.base import (
        RobotsPolicy,
        ScraperConfig,
        ScraperHttpClient,
    )

    def handler(request):
        return httpx.Response(
            200, headers={"content-encoding": "gzip"}, content=gzip.compress(b"x" * 1025)
        )

    client = ScraperHttpClient(
        ScraperConfig(
            allowed_hosts=("board.example",),
            robots=RobotsPolicy.IGNORE,
            min_interval=0,
            max_response_bytes=1024,
        )
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as transport:
        client._client = transport
        with pytest.raises(ScraperPermanentError, match="decoded bytes"):
            await client.get_html("https://board.example/jobs")


async def test_repeated_page_preserves_records_and_reports_partial():
    s = scraper("developerjobsch", detail_budget=0, max_pages=3)
    client = AsyncMock()
    client.get_html.return_value = read("developerjobsch-listing.html")
    batch = await s.collect(client)
    assert len(batch.jobs) == 3
    assert "repeated_pagination_items" in batch.errors
    assert batch.telemetry.stop_reason != "exhausted"
    assert client.get_html.await_count == 2
