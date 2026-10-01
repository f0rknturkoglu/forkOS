"""Frozen rich-source parsing/telemetry/evidence contracts; no network."""

import copy
import json
import re
from pathlib import Path

import pytest

from app.sources.forkjob_core.config import Config
from app.sources.forkjob_core.models import DateSource, Region, WorkMode
from app.sources.forkjob_core.rich_text import enrich, merge_descriptions
from app.sources.forkjob_core.score import score_job
from app.sources.forkjob_core.scrapers.base import ScraperPermanentError
from app.sources.forkjob_core.scrapers.devitjobs import DevITJobsScraper
from app.sources.forkjob_core.scrapers.index import get_scraper
from app.sources.forkjob_core.scrapers.registry import load_registry_b
from app.sources.forkjob_core.scrapers.remotecom import RemoteComScraper, flight_records
from app.sources.forkjob_core.scrapers.startup_boards import (
    BerlinStartupJobsScraper,
    EUStartupsScraper,
    next_page,
)
from app.sources.forkjob_core.scrapers.techjobs_family import (
    GermanTechJobsScraper,
    SwissDevJobsScraper,
)
from app.sources.forkjob_port import PortalSource, job_to_raw

pytestmark = pytest.mark.no_database
FIX = Path(__file__).parent / "fixtures/native_batch1"
FAMILY = [
    (GermanTechJobsScraper, "german", "DE", "EUR"),
    (SwissDevJobsScraper, "swiss", "CH", "CHF"),
    (DevITJobsScraper, "devit_contract", "NL", "EUR"),
]
KEYS = [
    "germantechjobs",
    "swissdevjobs",
    "devitjobs",
    "remotecom",
    "berlinstartupjobs",
    "eustartups",
]


def read(name):
    return (FIX / name).read_text()


@pytest.mark.parametrize("cls,fixture,country,currency", FAMILY)
def test_family_rich_fields(cls, fixture, country, currency):
    row = json.loads(read(fixture + ".json"))[0]
    job = cls().parse([row])[0]
    assert job.source == cls.source_key and job.country == country
    assert currency in job.salary
    assert job.external_id == row["_id"]
    assert job.language == row["language"]
    for label in ("Visa sponsorship", "Technologies", "Experience level", "Employment type"):
        assert label + ":" in job.description
    assert job.date_source in (DateSource.UPDATED, DateSource.DISCOVERED)
    assert job.work_mode in (WorkMode.REMOTE, WorkMode.HYBRID)
    assert job_to_raw(job).extra["forkjob"]["description"] == job.description


@pytest.mark.parametrize("cls,fixture,country,currency", FAMILY)
@pytest.mark.parametrize("visa,signal", [("Yes", "sponsors"), ("No", "refuses"), (None, None)])
def test_visa_three_states_reach_scoring(cls, fixture, country, currency, visa, signal):
    row = json.loads(read(fixture + ".json"))[0]
    # Isolate structured evidence from unrelated prose when testing unknown.
    for key in (
        "description",
        "requirementsMustTextArea",
        "requirementsNiceTextArea",
        "responsibilitiesTextArea",
    ):
        row.pop(key, None)
    row["hasVisaSponsorship"] = visa
    job = cls().build_job(row)
    score_job(job, Config())
    assert job.reasons.get("visa", {}).get("signal") == signal
    if signal:
        assert (
            job.reasons["visa"]["delta"] > 0 if visa == "Yes" else job.reasons["visa"]["delta"] < 0
        )
    else:
        assert "Visa sponsorship:" not in job.description


@pytest.mark.parametrize("cls,fixture,country,currency", FAMILY)
def test_family_missing_optional_malformed_dedup(cls, fixture, country, currency):
    row = {"name": "Senior Software Engineer", "company": "Acme", "jobUrl": "stable-role"}
    jobs = cls().parse([row, row, {}, None, {"name": "broken"}])
    assert len(jobs) == 1
    assert jobs[0].salary is None and jobs[0].language is None
    assert jobs[0].work_mode is WorkMode.UNKNOWN
    assert jobs[0].date_source is DateSource.DISCOVERED
    assert "Visa sponsorship:" not in (jobs[0].description or "")
    with pytest.raises(ScraperPermanentError):
        cls().parse({"error": "login"})


def test_remote_listing_detail_and_text_reference():
    scraper = RemoteComScraper()
    data = scraper.listing(read("remote-all.html"))
    assert len(data["jobs"]) == 20 and data["totalPages"] > 1
    job = scraper.parse_offer(read("remote-detail.html"))
    assert job.company == "Tru7 Group"
    assert len(job.description) > 3000 and "<h2>" not in job.description
    assert job.salary == "11,000 - 16,000 USD/yearly"
    assert job.country == "ZA" and "South Africa only" in job.description
    assert job.date_source is DateSource.EMPLOYER
    assert "$32" not in job.description
    assert scraper.build_job({}) is None
    with pytest.raises(ScraperPermanentError):
        scraper.listing("<h1>Please log in / CAPTCHA</h1>")


@pytest.mark.parametrize(
    "kind,names,scope,country",
    [
        ("global", [], "Anywhere", None),
        ("location", [("continent", "Europe", None)], "Europe only", None),
        ("location", [("country", "Germany", "DE")], "Germany only", "DE"),
        ("location", [("country", "United States", "US")], "United States only", "US"),
    ],
)
def test_remote_scopes(kind, names, scope, country):
    row = copy.deepcopy(RemoteComScraper().listing(read("remote-all.html"))["jobs"][0])
    row["hiringLocation"] = {
        "type": kind,
        "includedLocations": [
            {"type": t, "value": {"name": n, "alpha2Code": cc}} for t, n, cc in names
        ],
    }
    row["description"] = ""
    job = RemoteComScraper().build_job(row)
    assert f"Remote scope: {scope}" in job.description and job.country == country
    score_job(job, Config())
    if scope == "Anywhere":
        assert job.reasons["earning"]["open_remote"]
    else:
        assert "open_remote" not in job.reasons.get("earning", {})
        assert job.reasons["earning"]["geo_locked"]


@pytest.mark.parametrize(
    "cls,prefix,url",
    [
        (BerlinStartupJobsScraper, "berlin", "https://berlinstartupjobs.com/engineering/"),
        (EUStartupsScraper, "eu", "https://www.eu-startups.com/startup-jobs/"),
    ],
)
def test_startup_listing_detail(cls, prefix, url):
    scraper = cls()
    jobs, seen = scraper.parse_listing(read(prefix + "_listing.html"), url)
    assert len(jobs) == seen == 3
    assert next_page(read(prefix + "_listing.html"), url).endswith("/page/2/")
    job = scraper.parse_offer(read(prefix + "_detail.html"), jobs[0].url)
    assert job.external_id and job.company and job.description and job.posted_at
    assert job.date_source is DateSource.EMPLOYER
    assert job.work_mode is WorkMode.REMOTE
    assert scraper.parse_offer("<h1>Editorial</h1>", url) is None
    with pytest.raises(ScraperPermanentError):
        scraper.parse_listing("<h1>challenge</h1>", url)
    assert "language:" not in job.description.lower()  # page locale is not a requirement


def test_eustartups_actual_geography():
    scraper = EUStartupsScraper()
    jobs, _ = scraper.parse_listing(read("eu_listing.html"), scraper.listing_urls[0])
    assert jobs[2].country == "US" and jobs[2].region is Region.OTHER
    assert jobs[1].remote is True and "Worldwide" in jobs[1].description


def test_registry_and_historical_endpoint_regression():
    registry = load_registry_b()
    for key in KEYS:
        source = registry.by_key(key)
        assert source and source.category in ("regional", "remote", "startup")
        assert get_scraper(source).source == key
        assert source.enabled is (key != "devitjobs")
    nl = registry.by_key("devitjobs")
    assert nl.url == "https://devitjobs.nl"
    assert "403" in nl.status and "not source death" in nl.status


class Replay:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.urls = []

    async def get_html(self, url):
        self.urls.append(url)
        reply = next(self.replies)
        if isinstance(reply, Exception):
            raise reply
        return reply

    async def get_json(self, url):
        reply = await self.get_html(url)
        return json.loads(reply)


async def test_family_detail_failure_retains_rich_listing():
    scraper = GermanTechJobsScraper(detail_budget=1)
    result = await scraper.collect(
        Replay([read("german.json"), "<rss><channel /></rss>", ScraperPermanentError("HTTP 503")])
    )
    assert len(result.jobs) == 2 and result.errors
    assert result.telemetry.pages_fetched == 2
    assert not result.telemetry.cap_hit and result.telemetry.metadata["details_succeeded"] == 0
    assert result.telemetry.partial_reason is None
    assert result.telemetry.metadata["listing_complete"]
    assert "detail_request_failed" in result.telemetry.metadata["richness_partial_reason"]
    assert "Visa sponsorship: No" in result.jobs[0].description


async def test_remote_pagination_partial_failure_and_offer_cap(monkeypatch):
    scraper = RemoteComScraper(max_pages=2, detail_budget=0)
    result = await scraper.collect(
        Replay([read("remote-all.html"), ScraperPermanentError("HTTP 429")])
    )
    assert len(result.jobs) == 20 and result.errors and result.telemetry.pages_fetched == 1
    portal = PortalSource(load_registry_b().by_key("remotecom"))
    monkeypatch.setattr(scraper, "collect", lambda: async_result(result))
    monkeypatch.setattr("app.sources.forkjob_port.get_scraper", lambda p: scraper)
    assert (await portal.fetch()).partial
    capped = await RemoteComScraper(max_pages=1, max_offers=5, detail_budget=0).collect(
        Replay([read("remote-all.html")])
    )
    assert len(capped.jobs) == 5 and capped.telemetry.items_seen == 20
    assert capped.telemetry.cap_hit and capped.telemetry.stop_reason == "max_offers_reached"


async def async_result(value):
    return value


async def test_remote_natural_exhaustion_is_complete():
    html = re.sub(r'(\\"totalPages\\"\s*:\s*)\d+', r"\g<1>1", read("remote-all.html"))
    result = await RemoteComScraper(max_pages=1, max_offers=30, detail_budget=30).collect(
        Replay([html, *[read("remote-detail.html")] * 20])
    )
    # One real detail matches; mismatches affect enrichment only.
    assert not result.telemetry.cap_hit and result.telemetry.stop_reason == "exhausted"
    assert result.errors and result.succeeded == 2


async def test_startup_later_page_failure_retains_first_page():
    scraper = EUStartupsScraper(max_pages=2, detail_budget=0)
    result = await scraper.collect(
        Replay([read("eu_listing.html"), ScraperPermanentError("HTTP 403")])
    )
    assert len(result.jobs) == 3 and result.errors
    assert result.telemetry.pages_fetched == 1 and result.telemetry.items_seen == 3


def test_richer_description_and_source_evidence_merge_idempotently():
    full = "Full ATS requirements Python. " * 100
    incoming = enrich(
        "Short preview", "germantechjobs", {"Visa sponsorship": "Yes", "Language": "English"}
    )
    merged = merge_descriptions(full, incoming)
    assert full.strip() in merged and "Visa sponsorship: Yes" in merged
    assert merge_descriptions(merged, incoming) == merged
    job = GermanTechJobsScraper().build_job(
        {"name": "Junior Backend Engineer", "company": "Acme", "jobUrl": "1", "description": merged}
    )
    score_job(job, Config())
    assert job.reasons["visa"]["delta"] > 0 and job.reasons["language"]["delta"] > 0


def test_flight_unicode_text_bytes_and_no_separator():
    body = "<p>€ Türkçe</p>"
    stream = f'1:T{len(body.encode()):x},{body}2:["after"]\n'
    html = "<script>self.__next_f.push(" + json.dumps([1, stream]) + ")</script>"
    assert flight_records(html) == {"1": body, "2": ["after"]}


async def test_family_rss_enriches_without_detail_storm():
    scraper = GermanTechJobsScraper(detail_budget=0)
    result = await scraper.collect(Replay([read("german.json"), read("german_rss.xml")]))
    assert result.telemetry.pages_fetched == 2
    assert result.telemetry.metadata["rss_enriched"] > 0
    assert result.telemetry.metadata["details_attempted"] == 0
    assert len(result.jobs[0].description) > 1000
    assert "Visa sponsorship: No" in result.jobs[0].description
    with pytest.raises(ScraperPermanentError):
        scraper.parse_feed("<html>challenge</html>")


async def test_bounded_http_decoded_body_and_gzip():
    import gzip

    import httpx

    from app.sources.forkjob_core.scrapers.base import (
        RobotsPolicy,
        ScraperConfig,
        ScraperHttpClient,
    )

    config = ScraperConfig(min_interval=0, robots=RobotsPolicy.IGNORE, max_response_bytes=16)
    async with ScraperHttpClient(config) as client:
        await client._client.aclose()
        client._client = httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200, content=gzip.compress(b"hello"), headers={"Content-Encoding": "gzip"}
                )
            )
        )
        assert await client.get_html("https://example.test/feed") == "hello"
        client.config.max_response_bytes = 4
        with pytest.raises(ScraperPermanentError, match="decoded bytes"):
            await client.get_html("https://example.test/feed")


def test_application_url_identity_rejects_generic_boards_and_conflicting_roles():
    from app.modules.opportunity.identity import (
        ListingIdentity,
        same_real_world_posting,
        specific_application_url,
    )

    url = "https://job-boards.greenhouse.io/acme/jobs/123456"
    common = dict(
        external_id=None,
        provider=None,
        requisition_id=None,
        company="Acme",
        location=None,
        description=None,
        published_at=None,
    )
    board = ListingIdentity(
        source="board",
        url="https://board.test/job/1",
        apply_url=url,
        title="Junior Backend Engineer",
        **common,
    )
    employer = ListingIdentity(
        source="ats", url=url, apply_url=None, title="Junior Backend Engineer", **common
    )
    assert same_real_world_posting(board, employer)
    assert not same_real_world_posting(
        board,
        ListingIdentity(
            source="ats", url=url, apply_url=None, title="Senior Frontend Engineer", **common
        ),
    )
    assert specific_application_url("https://job-boards.greenhouse.io/acme") is None
    assert specific_application_url("https://example.test/apply") is None
    assert specific_application_url("https://greenhouse.io.evil.test/acme/jobs/123456") is None


async def test_startup_complete_empty_and_malformed_card():
    scraper = EUStartupsScraper(detail_budget=0)
    batch = await scraper.collect(Replay(['<div class="wpjb-grid"></div>']))
    assert batch.jobs == [] and not batch.errors
    assert not batch.telemetry.cap_hit and batch.telemetry.stop_reason == "exhausted"
    html = (
        read("eu_listing.html") + '<div class="wpjb-grid-row wpjb-click-area"><p>Broken</p></div>'
    )
    jobs, count = scraper.parse_listing(html, scraper.listing_urls[0])
    assert len(jobs) == 3 and count == 4


def test_family_salary_unknown_and_monthly_contract_keeps_period():
    row = {
        "name": "Software Engineer",
        "company": "Acme",
        "jobUrl": "role",
        "contractRateFrom": 3000,
        "contractRateTo": 6000,
        "contractRateType": "month",
    }
    job = GermanTechJobsScraper().build_job(row)
    assert job.salary == "EUR 3,000 - 6,000 per month"
    assert job.language is None and "Visa sponsorship:" not in job.description


def test_remote_missing_optional_values_and_timezone_scope():
    row = copy.deepcopy(RemoteComScraper().listing(read("remote-all.html"))["jobs"][0])
    for key in (
        "compensation",
        "visaSponsorshipOffered",
        "employmentType",
        "seniority",
        "publishedAt",
        "updatedAt",
    ):
        row.pop(key, None)
    row["hiringLocation"] = {"type": "timezone", "timezone": {"name": "Berlin"}, "timezoneRange": 3}
    job = RemoteComScraper().build_job(row)
    assert job.salary is None and job.date_source is DateSource.DISCOVERED
    assert "Visa sponsorship:" not in job.description
    assert "Remote scope: Berlin timezone ±3 hours" in job.description


def test_pagination_handles_empty_href_on_later_pages():
    html = '<a href>Missing link</a><a href="/startup-jobs/page/3/">3</a>'
    assert (
        next_page(html, "https://www.eu-startups.com/startup-jobs/page/2/")
        == "https://www.eu-startups.com/startup-jobs/page/3/"
    )


def test_one_corrupt_structured_record_does_not_discard_others():
    scraper = GermanTechJobsScraper()
    row = json.loads(read("german.json"))[0]
    corrupt = {**row, "_id": "broken", "description": {"not": "text"}}
    assert len(scraper.parse([corrupt, row])) == 1
    remote = RemoteComScraper()
    remote_row = remote.listing(read("remote-all.html"))["jobs"][0]
    assert remote.build_job({**remote_row, "hiringLocation": {"includedLocations": [None]}}) is None
    assert remote.build_job(remote_row) is not None


def test_structured_stack_survives_long_description_scoring():
    from app.sources.forkjob_core.config import SkillWeight

    config = Config()
    config.scoring.skills = [SkillWeight(name="python", points=5)]
    row = {
        "name": "Software Engineer",
        "company": "Acme",
        "jobUrl": "role",
        "description": "Unrelated company background. " * 500,
        "technologies": ["Python"],
    }
    job = GermanTechJobsScraper().build_job(row)
    assert job.description.index("Technologies: Python") > 6000
    score_job(job, config)
    assert job.reasons["skills"]["python"] == 5
