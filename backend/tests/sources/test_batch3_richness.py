"""Public reduced samples + explicitly synthetic optional contracts; no network."""

import json
from pathlib import Path

import httpx
import pytest

from app.sources.forkjob_core.config import ScoringConfig
from app.sources.forkjob_core.feeds import Feed
from app.sources.forkjob_core.match import detect
from app.sources.forkjob_core.models import Company, DateSource, Job, Layer, WorkMode
from app.sources.forkjob_core.normalize import detect_language, parse_datetime, parse_epoch_ms
from app.sources.forkjob_core.rich_text import enrich, scoring_evidence, scoring_tags, source_fact
from app.sources.forkjob_core.scrapers.base import (
    ScrapeBatch,
    ScraperBase,
    ScraperHttpClient,
    ScraperPermanentError,
    _recognized_json_empty,
)
from app.sources.forkjob_core.scrapers.customfeeds import CustomFeedsScraper
from app.sources.forkjob_core.scrapers.fourdayweek import FourDayWeekScraper
from app.sources.forkjob_core.scrapers.himalayas import HimalayasScraper
from app.sources.forkjob_core.scrapers.schemaorg import schema_job
from app.sources.forkjob_core.scrapers.solidjobs import SolidJobsScraper
from app.sources.forkjob_core.scrapers.wearedevelopers import WeAreDevelopersScraper
from app.sources.forkjob_core.scrapers.workingnomads import WorkingNomadsScraper
from app.sources.forkjob_core.sources.adapters import (
    ADAPTERS,
    AshbyAdapter,
    LeverAdapter,
    SmartRecruitersAdapter,
    WorkdayAdapter,
)
from app.sources.forkjob_core.sources.base import HttpClient, HttpConfig, PermanentError
from app.sources.forkjob_port import job_to_raw

pytestmark = pytest.mark.no_database
ROOT = Path(__file__).parent / "fixtures/batch3"


def sample(key):
    return json.loads((ROOT / (key + ".json")).read_text())


def company(ats):
    return Company(name="Synthetic", ats=ats, token="synthetic")


def test_live_himalayas_restrictions_epoch_and_specific_application():
    payload = sample("himalayas")
    row = payload["jobs"][0]
    job = HimalayasScraper().parse(payload)[0]
    assert job.external_id == row["guid"]
    assert job.date_source is DateSource.UPDATED and job.posted_at
    assert source_fact(job.description, "Application URL") == row["applicationLink"]
    if row["locationRestrictions"]:
        assert source_fact(job.description, "Remote scope") == ", ".join(row["locationRestrictions"])
    assert "Visa sponsorship:" not in job.description
    assert job_to_raw(job).extra["apply_url"] == row["applicationLink"]


def test_live_solid_full_prose_languages_and_expiry():
    payload = sample("solidjobs")
    row = payload["jobs"][0]
    job = SolidJobsScraper().parse(payload)[0]
    assert source_fact(job.description, "Expiry") == row["validTo"]
    assert job.language == ", ".join(x["name"] for x in row["languages"])
    assert source_fact(job.description, "Technologies")
    assert job.date_source is DateSource.UPDATED
    # Synthetic long JD must not hide the explicit discrete stack.
    row["description"] = "<p>Job-specific requirements.</p>" * 400
    row["skills"] = [{"name": "Python", "level": "Junior"}]
    job = SolidJobsScraper().parse(payload)[0]
    assert job.description.startswith("Job-specific requirements.")
    assert "Python" in scoring_tags(job.description)


def test_live_fourdayweek_minor_units_full_prose_and_no_company_scope_promotion():
    payload = sample("fourdayweek")
    row = payload["data"][0]
    job = FourDayWeekScraper().parse(payload)[0]
    assert job.salary == "121839 AUD /year"  # same public detail renders $121,839.00
    assert source_fact(job.description, "Technologies")
    assert job.description and not job.description.startswith("Schedule:")
    row["company"]["hires_worldwide"] = True
    row["work_arrangement"] = "remote"
    row["locations"] = [{"city": "Berlin", "country": "Germany", "is_primary": True}]
    job = FourDayWeekScraper().parse(payload)[0]
    assert source_fact(job.description, "Remote scope") == "Berlin, Germany"
    assert "Remote scope: Anywhere" not in job.description
    assert job.date_source is DateSource.UPDATED


def test_live_workingnomads_string_tags_survive():
    payload = sample("workingnomads")
    job = WorkingNomadsScraper().parse(payload)[0]
    assert source_fact(job.description, "Technologies") == ", ".join(t.strip() for t in payload[0]["tags"].split(",") if t.strip())
    assert job.date_source is DateSource.UPDATED


def test_live_wad_markdown_identity_apply_and_remote_availability():
    job = WeAreDevelopersScraper().parse_markdown((ROOT / "wearedevelopers.md").read_text())[0]
    assert job.external_id and job.external_id.isdecimal()
    assert job_to_raw(job).extra["apply_url"]
    assert job.date_source is DateSource.UPDATED
    assert job.work_mode is WorkMode.UNKNOWN  # Remote available != guaranteed remote
    with pytest.raises(ScraperPermanentError):
        WeAreDevelopersScraper().parse_markdown("<html>challenge</html>")
    assert WeAreDevelopersScraper().parse_markdown("# Developer Jobs\n0 jobs found") == []


def test_synthetic_lever_rich_contract_and_onsite():
    row = {"id": "job-1", "text": "Junior Backend Engineer", "hostedUrl": "https://jobs.example/1", "applyUrl": "https://apply.example/jobs/1", "description": "<p>Full employer prose.</p>", "categories": {"location": "Berlin, Germany", "commitment": "Full-time"}, "workplaceType": "on-site", "salaryRange": {"min": 50000, "max": 65000, "currency": "EUR", "interval": "year"}, "skills": ["Python"], "workingLanguage": "English", "visaSponsorship": True, "relocation": False}
    job = LeverAdapter(company("lever")).parse([row])[0]
    assert job.work_mode is WorkMode.ONSITE and job.language == "English"
    assert job.salary == "50000-65000 EUR /year"
    assert source_fact(job.description, "Visa sponsorship") == "Yes"
    assert source_fact(job.description, "Relocation") == "No"
    assert job_to_raw(job).extra["source_authority"] == "employer"
    assert job_to_raw(job).extra["apply_url"] == row["applyUrl"]


def test_synthetic_ashby_last_published_not_original_and_compensation():
    job = AshbyAdapter(company("ashby")).parse({"jobs": [{"id": "1", "title": "Engineer", "applyUrl": "https://jobs.example/1/apply", "descriptionPlain": "Full text", "publishedAt": "2026-09-01", "department": "Engineering", "compensation": {"compensationTierSummary": "50000-65000 EUR/year"}}]})[0]
    assert job.salary and job.department == "Engineering"
    assert job.date_source is DateSource.UPDATED


@pytest.mark.parametrize("ats", ["personio", "factorial", "teamtailor"])
def test_unknown_ats_envelope_not_healthy_empty(ats):
    with pytest.raises(PermanentError):
        ADAPTERS[ats](company(ats)).parse({"error": "challenge"})
    assert ADAPTERS[ats](company(ats)).parse({"jobs": []}) == []


def test_synthetic_schema_period_deadline_scope_and_zero_salary():
    kwargs = dict(url="https://jobs.example/1", source="synthetic", layer=Layer.B, company="Employer", title="Engineer")
    posting = {"baseSalary": {"currency": "EUR", "value": {"minValue": 100, "maxValue": 150, "unitText": "HOUR"}}, "employmentType": ["CONTRACT"], "validThrough": "2026-12-01", "applicantLocationRequirements": [{"name": "Germany"}, {"name": "Netherlands"}], "skills": "Python", "inLanguage": "de"}
    job = schema_job(posting, **kwargs)
    assert job.salary == "100-150 EUR /HOUR" and job.language is None
    assert source_fact(job.description, "Remote scope") == "Germany, Netherlands"
    assert source_fact(job.description, "Application deadline") == "2026-12-01"
    posting["baseSalary"]["value"] = {"minValue": 0, "maxValue": 0}
    assert schema_job(posting, **kwargs).salary is None


@pytest.mark.parametrize("text", ["100% remote", "fully remote", "remote-first", "Remote worldwide. US only."])
def test_remote_flexibility_is_not_worldwide_eligibility(text):
    job = Job.build(url="https://jobs.example/1", source="synthetic", layer=Layer.B, company="Employer", title="Engineer", description=text)
    assert detect(job, ScoringConfig()).open_remote_phrase is None


def test_board_sponsorship_tristate_preserved_but_not_employer_evidence():
    for value in ("Yes", "No"):
        description = enrich("Employer prose with no visa statement", "freehire", {"Source authority": "meta", "Board sponsorship claim": value})
        job = Job.build(url="https://jobs.example/1", source="freehire", layer=Layer.B, company="Employer", title="Engineer", description=description)
        assert value in job.description
        assert "Board sponsorship" not in scoring_evidence(job.description)
        assert detect(job, ScoringConfig()).visa == 0


@pytest.mark.parametrize("value", [None, {}, 1, [], "not a date"])
def test_optional_malformed_datetime_does_not_kill_source(value):
    assert parse_datetime(value) is None


@pytest.mark.parametrize("value", [float("inf"), float("nan"), 10**50, -1, {}])
def test_optional_malformed_epoch_does_not_kill_source(value):
    assert parse_epoch_ms(value) is None


def test_page_language_does_not_imply_working_language():
    assert detect_language("We are hiring a developer. You will work with us.") is None
    assert detect_language("", declared="English B2") == "English B2"


@pytest.mark.parametrize("payload", [{"error": "blocked"}, {"jobs": [{}]}, {"jobs": [], "totalCount": 2}])
def test_unknown_or_inconsistent_empty_contract(payload):
    assert not _recognized_json_empty(payload)


@pytest.mark.parametrize("payload", [[], {"jobs": []}, {"data": [], "totalCount": 0}])
def test_recognized_empty_contract(payload):
    assert _recognized_json_empty(payload)


def test_custom_feed_encoded_content_and_atom_xhtml():
    s = CustomFeedsScraper()
    feed = Feed("https://feed.example/jobs", name="Synthetic")
    rss = '<rss xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><item><guid>job-1</guid><title>Engineer</title><link>https://jobs.example/1</link><description>Preview</description><content:encoded>Full requirements Python</content:encoded><pubDate>Thu, 01 Oct 2026 10:00:00 GMT</pubDate></item></channel></rss>'
    job = s.parse(rss, feed)[0]
    assert "Full requirements Python" in job.description and "Preview" not in job.description
    assert job.external_id == "job-1" and job.date_source is DateSource.UPDATED
    atom = '<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>job-2</id><title>Engineer</title><link href="https://jobs.example/2"/><content type="xhtml"><div xmlns="http://www.w3.org/1999/xhtml"><p>Full</p><p>Python</p></div></content></entry></feed>'
    assert "Full Python" in s.parse(atom, feed)[0].description
    with pytest.raises(ScraperPermanentError):
        s.parse("<html>challenge</html>", feed)


async def test_ats_robots_denial_never_requests_jobs():
    requests = []
    def handler(request):
        requests.append(str(request.url))
        return httpx.Response(200, text="User-agent: LinkedInBot\nAllow: /\nUser-agent: *\nDisallow: /\n")
    client = HttpClient(HttpConfig(min_interval_per_host=0))
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(PermanentError, match="policy denies"):
            await client.get_json("https://api.smartrecruiters.com/v1/companies/wise/postings")
    finally:
        await client._client.aclose()
    assert requests == ["https://api.smartrecruiters.com/robots.txt"]


async def test_ats_foreign_redirect_is_not_followed():
    requests = []
    def handler(request):
        requests.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(302, headers={"location": "https://internal.example/secret"})
    client = HttpClient(HttpConfig(min_interval_per_host=0))
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(PermanentError, match="outside"):
            await client.get_json("https://api.example/jobs")
    finally:
        await client._client.aclose()
    assert not any("internal.example" in u for u in requests)


class EmptySource(ScraperBase):
    source_key = "synthetic"
    async def scrape(self, client):
        await client.get_html("https://board.example/jobs")
        return []


async def test_html_challenge_cannot_be_healthy_empty():
    client = ScraperHttpClient()
    async def response(*args, **kwargs):
        return httpx.Response(200, text="<html>Please log in</html>")
    client._request = response
    with pytest.raises(ScraperPermanentError, match="unrecognized empty"):
        await EmptySource().collect(client)


async def test_smartrecruiters_pagination_is_bounded_and_preserves_partial():
    class Client:
        async def get_json(self, url):
            return {"content": [{"id": "1", "name": "Engineer", "ref": "https://api.smartrecruiters.com/v1/companies/synthetic/postings/1"}], "totalFound": 200}
    adapter = SmartRecruitersAdapter(company("smartrecruiters"))
    raw = await adapter.fetch_raw(Client())
    assert len(raw) == 1 and adapter.telemetry.pages_fetched == 1
    assert adapter.telemetry.partial_reason and "repeat" in adapter.telemetry.partial_reason


async def test_workday_correct_cxs_tenant_route_and_requisition_not_url():
    c = company("workday")
    c.extra.update(host="https://synthetic.wd1.myworkdayjobs.com", tenant="synthetic", site="External")
    adapter = WorkdayAdapter(c)
    requests = []
    class Client:
        async def get_json(self, url):
            raise AssertionError("Workday search must POST")
        async def request(self, method, url, **kwargs):
            requests.append((method, url))
            return httpx.Response(200, json={"jobPostings": [], "total": 0})
    await adapter.fetch_raw(Client())
    assert requests == [("POST", "https://synthetic.wd1.myworkdayjobs.com/wday/cxs/synthetic/External/jobs")]
    assert adapter._parse_one({"title": "Engineer", "bulletFields": ["REQ-1"]}) is None


async def test_partial_useful_jobs_survive_failed_slice_counts(monkeypatch):
    from app.sources import forkjob_port
    from app.sources.forkjob_core.scrapers.registry import LayerBSource
    job = Job.build(url="https://jobs.example/1", source="synthetic", layer=Layer.B, company="Employer", title="Engineer")
    class Scraper:
        telemetry = None
        async def collect(self):
            return ScrapeBatch([job], ["detail failed"], 1, 0)
    monkeypatch.setattr(forkjob_port, "get_scraper", lambda source: Scraper())
    outcome = await forkjob_port.PortalSource(LayerBSource("synthetic", "Synthetic")).fetch()
    assert outcome.partial and len(outcome.items) == 1 and outcome.detail == "detail failed"


async def test_malformed_ats_optional_record_preserves_valid_partial():
    from app.sources.forkjob_core.sources.adapters import GreenhouseAdapter
    class Client:
        async def get_json(self, *args, **kwargs):
            return {"jobs": [{"id": "bad", "title": "Engineer", "absolute_url": "https://jobs.example/bad", "location": []}, {"id": "good", "title": "Engineer", "absolute_url": "https://jobs.example/good", "location": {"name": "Berlin"}}]}
    adapter = GreenhouseAdapter(company("greenhouse"))
    # An empty malformed optional location can still be harmless; use a truthy invalid value.
    class BadClient(Client):
        async def get_json(self, *args, **kwargs):
            payload = await super().get_json(*args, **kwargs)
            payload["jobs"][0]["location"] = ["bad shape"]
            return payload
    jobs = await adapter.collect(BadClient())
    assert [j.external_id for j in jobs] == ["good"]
    assert adapter.telemetry.partial_reason == "malformed_job_records"


async def test_layer_b_unverified_robots_is_failure_and_no_job_request():
    requests = []
    def handler(request):
        requests.append(str(request.url))
        return httpx.Response(403)
    client = ScraperHttpClient()
    client.config.min_interval = 0
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(ScraperPermanentError, match="policy could not be verified"):
            await client.get_html("https://board.example/jobs")
    finally:
        await client._client.aclose()
    assert requests == ["https://board.example/robots.txt"]


async def test_custom_empty_rss_is_legitimate_but_bad_xml_isolated(monkeypatch):
    from app.sources.forkjob_core.feeds import Feeds
    feeds = Feeds([Feed("https://feed.example/empty"), Feed("https://feed.example/bad")])
    monkeypatch.setattr(Feeds, "load", lambda *args: feeds)
    class Client:
        async def get_html(self, url):
            return '<rss><channel/></rss>' if url.endswith("empty") else '<rss>bad'
    result = await CustomFeedsScraper().scrape(Client())
    assert result.succeeded == 1 and result.attempted == 2 and len(result.errors) == 1


async def test_synthetic_daily_detail_budget_preserves_all_listing_identities():
    from app.sources.forkjob_core.scrapers.dailyremote import DailyRemoteScraper
    html = "".join(f'<article><div class="lst-card__content"><h2 class="lst-card__title"><a href="/remote-job/engineer-{i}">Engineer</a></h2><span class="lst-card__company">Employer</span><div class="lst-card__meta"><span class="lst-pill">$50 per hour</span></div><p class="lst-card__summary">Preview</p><div class="lst-card__tags"><span class="lst-tag">Python</span></div></div></article>' for i in range(1, 4))
    calls = []
    class Client:
        async def get_html(self, url):
            calls.append(url)
            if "remote-jobs" in url:
                return html
            return '<script type="application/ld+json">' + json.dumps({"@type": "JobPosting", "title": "Engineer", "hiringOrganization": {"name": "Employer"}, "description": "Full employer job-specific prose"}) + '</script>'
    scraper = DailyRemoteScraper(max_pages=1, detail_budget=1)
    jobs = await scraper.scrape(Client())
    assert len(jobs) == 3 and len(calls) == 2
    assert "Full employer job-specific prose" in jobs[0].description
    assert "Preview" in jobs[1].description and jobs[1].salary == "$50 per hour"
    assert scraper.telemetry.metadata["richness_partial"]
    assert scraper.telemetry.metadata["detail_requests"] == 1


async def test_wad_detail_identity_budget_and_unrelated_prose_exclusion():
    body = (ROOT / "wearedevelopers.md").read_text()
    scraper = WeAreDevelopersScraper(queries=[""], max_pages=1, detail_budget=1)
    job = scraper.parse_markdown(body)[0]
    calls = []
    class Client:
        async def get_html(self, url):
            calls.append(url)
            if "/jobs.md?" in url:
                return body
            return f'> Markdown version of [Job]({job.url}).\n# {job.title}\n- **Skills:** Python\n## About the Role\nFull employer requirements.\n## Description\nFull role.\n## Related Videos\nWrong JavaScript boilerplate'
    result = await scraper.scrape(Client())
    assert len(result.jobs) == 1 and len(calls) == 2 and not result.errors
    assert "Full employer requirements" in result.jobs[0].description
    assert "Wrong JavaScript boilerplate" not in result.jobs[0].description
    assert source_fact(result.jobs[0].description, "Technologies") == "Python"
    assert scraper.queries == ("country=all",)


def test_remoteok_salary_does_not_invent_currency_period_or_zero():
    from app.sources.forkjob_core.scrapers.remoteok import _salary
    assert _salary({"salary_min": 0, "salary_max": 0}) is None
    assert _salary({"salary_min": 100, "salary_max": 150}) == "100-150"
    assert _salary({"salary_min": 100, "salary_currency": "EUR", "salary_period": "hour"}) == "100 EUR /hour"


@pytest.mark.parametrize("key", ["nofluffjobs", "bulldogjob", "jobgether"])
async def test_reduced_public_details_recover_fields_and_keep_identity(key):
    from app.sources.forkjob_core.scrapers.detail_evidence import enrich_job_details
    from app.sources.forkjob_core.scrapers.schemaorg import field_text
    posting = sample(key + "-detail")
    job = Job.build(url=posting.get("url") or posting.get("@id") or "https://jobs.example/1", source=key, layer=Layer.B, company="?", title=posting["title"], external_id="native-id", description="Preview")
    class Client:
        async def get_html(self, url):
            return '<script type="application/ld+json">' + json.dumps(posting) + '</script>'
    class Scraper:
        errors = []
    metadata = await enrich_job_details(Scraper(), Client(), [job], 1)
    assert metadata["details_succeeded"] == 1
    assert job.external_id == "native-id" and job.company != "?"
    if posting.get("skills"):
        assert source_fact(job.description, "Technologies") == field_text(posting["skills"])
    if posting.get("validThrough"):
        assert source_fact(job.description, "Application deadline") == posting["validThrough"]


async def test_late_transient_page_retains_jobs_and_is_partial():
    from app.sources.forkjob_core.scrapers.base import ScraperTransientError
    from app.sources.forkjob_core.scrapers.freelancermap import FreelancermapScraper
    class Client:
        calls = 0
        async def get_html(self, url):
            self.calls += 1
            if self.calls > 1:
                raise ScraperTransientError("exhausted 503 retries")
            return '<script>{"id":42,"slug":"engineer-42","title":"Engineer","company":"Employer"}</script>'
    result = await FreelancermapScraper().collect(Client())
    assert isinstance(result, ScrapeBatch) and len(result.jobs) == 1
    assert "503" in result.errors[0]


def test_linkedin_detail_wrong_job_rejected_and_rich_facts_retained():
    from app.sources.forkjob_core.scrapers.linkedin_parsing import (
        LinkedInCard,
        LinkedInResponseError,
        detail_job,
    )
    card = LinkedInCard("42", "Engineer", "Employer", "Germany", "https://www.linkedin.com/jobs/view/42")
    posting = {"@type": "JobPosting", "title": "Engineer", "url": "https://www.linkedin.com/jobs/view/99", "description": "Full job prose", "skills": "Python", "applicantLocationRequirements": {"name": "Germany"}, "validThrough": "2026-12-01"}
    def html():
        return '<script type="application/ld+json">' + json.dumps(posting) + '</script>'
    with pytest.raises(LinkedInResponseError, match="detail_identity"):
        detail_job(html(), card)
    posting["url"] = card.url
    job = detail_job(html(), card)
    assert source_fact(job.description, "Technologies") == "Python"
    assert source_fact(job.description, "Remote scope") == "Germany"
    assert source_fact(job.description, "Application deadline") == "2026-12-01"


def test_manfred_translation_not_language_and_no_guessed_spain():
    from app.sources.forkjob_core.scrapers.manfred import ManfredScraper
    job = ManfredScraper().build_job({"title": "Engineer", "company": "Employer", "id": 42, "remote": 100, "languages": [{"code": "ES"}], "skillsSectionData": {"skills": {"must": [{"skill": "Python"}], "nice": [{"skill": "React"}]}, "minLanguages": [{"name": "English"}]}, "offerSectionData": {"offerInfo": "Real job benefits " * 10}}, "https://www.getmanfred.com/42/engineer")
    assert job.language == "English" and job.country is None
    assert source_fact(job.description, "Technologies") == "Python, React"
    assert "Real job benefits" in job.description


async def test_unverified_single_ats_window_is_not_exhaustive():
    adapter = ADAPTERS["teamtailor"](company("teamtailor"))
    class Client:
        async def get_json(self, url):
            return [{"id": 42, "title": "Engineer", "description": "Full prose"}]
    jobs = await adapter.collect(Client())
    assert len(jobs) == 1
    assert adapter.telemetry.cap_hit and adapter.telemetry.partial_reason == "upstream_window_unverified"


def test_nofluff_and_bulldog_board_dates_not_original_employer():
    from app.sources.forkjob_core.scrapers.bulldogjob import BulldogjobScraper
    from app.sources.forkjob_core.scrapers.nofluffjobs import NoFluffJobsScraper
    nofluff = NoFluffJobsScraper().parse({"postings": [{"id": "42", "title": "Engineer", "url": "engineer-42", "posted": 1786552236000}]})[0]
    bulldog = BulldogjobScraper().parse({"nodes": [{"id": "42", "position": "Engineer", "publishedAt": "2026-09-01"}]})[0]
    assert nofluff.date_source is DateSource.UPDATED and bulldog.date_source is DateSource.UPDATED


def test_wellfound_copied_ats_authority_and_explicit_remote_scope():
    from app.sources.forkjob_core.scrapers.wellfound import WellfoundScraper
    job = WellfoundScraper().build_job({"id": "42", "title": "Engineer", "slug": "engineer", "description": "Full source prose", "atsSource": "Greenhouse", "remote": True, "acceptedRemoteLocationNames": ["Germany"], "liveStartAt": 1786552236, "yearsExperienceMax": 3}, "Employer")
    assert source_fact(job.description, "Source authority") == "meta"
    assert source_fact(job.description, "Remote scope") == "Germany"
    assert job.date_source is DateSource.UPDATED


async def test_reduced_eurotech_detail_recovers_job_prose_and_keeps_identity():
    from selectolax.parser import HTMLParser

    from app.sources.forkjob_core.scrapers.eurotechjobs import EuroTechJobsScraper
    html = (ROOT / "eurotechjobs-detail.html").read_text()
    title = HTMLParser(html).css_first("h2").text(strip=True)
    job = Job.build(url="https://www.eurotechjobs.com/job_display/296809/example", title=title, company="Employer", external_id="296809", source="eurotechjobs", layer=Layer.B, description="Preview")
    scraper = EuroTechJobsScraper(countries=["spain"], detail_budget=1)
    scraper.parse = lambda _: [job]
    class Client:
        async def get_html(self, url):
            return html
    jobs = await scraper.scrape(Client())
    assert jobs[0].external_id == "296809"
    assert "Preview" not in jobs[0].description
    assert scraper.telemetry.metadata["details_succeeded"] == 1
