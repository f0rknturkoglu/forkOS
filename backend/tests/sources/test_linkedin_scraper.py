"""LinkedIn discovery is opt-in, bounded, and preserves partial results."""

from __future__ import annotations

import asyncio
import math
import sys

import pytest

from app.sources.forkjob_core.scrapers import linkedin
from app.sources.forkjob_core.scrapers.base import ScraperPermanentError


class Frame:
    def __init__(self, rows):
        self.rows = rows

    def to_dict(self, *, orient):
        assert orient == "records"
        return self.rows


@pytest.fixture
def scraper_factory(monkeypatch):
    monkeypatch.setattr(linkedin, "_merge_user_profiles", lambda defaults: defaults)

    def build(searches, runner, *, direct=True):
        return linkedin.LinkedInScraper(
            searches=searches, runner=runner, allow_direct=direct
        )

    return build


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_successful_profiles_survive_another_profile_failure(scraper_factory):
    calls = []

    def runner(**kwargs):
        calls.append(kwargs)
        if kwargs["search_term"] == "broken":
            raise RuntimeError("JobSpy failed")
        return Frame(
            [
                {
                    "id": "111",
                    "title": "Python Engineer",
                    "company": "Acme",
                    "job_url": "https://linkedin.com/jobs/view/111?trk=feed",
                    "job_url_direct": "https://acme.example/jobs/111?utm_source=linkedin",
                    "description": math.nan,
                    "date_posted": math.nan,
                }
            ]
        )

    scraper = scraper_factory(
        [
            {"term": "python", "results_wanted": 20, "hours_old": 72},
            {"term": "broken", "is_remote": True},
        ],
        runner,
    )
    result = await scraper.scrape(None)
    assert result.attempted == 2 and result.succeeded == 1
    assert len(result.errors) == 1 and result.errors[0].startswith("profile-2:")
    assert len(result.jobs) == 1
    assert result.jobs[0].url == "https://acme.example/jobs/111"
    assert result.jobs[0].external_id == "111"
    assert result.jobs[0].description is None
    assert calls[0]["linkedin_fetch_description"] is False
    assert calls[0]["hours_old"] == 72
    assert calls[1]["is_remote"] is True


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_all_profiles_fail_without_a_false_success(scraper_factory):
    def runner(**kwargs):
        raise RuntimeError(f"failed {kwargs['search_term']}")

    scraper = scraper_factory([{"term": "one"}, {"term": "two"}], runner)
    result = await scraper.scrape(None)
    assert result.attempted == 2 and result.succeeded == 0
    assert result.jobs == [] and len(result.errors) == 2


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_no_profiles_does_not_require_proxy_or_import_jobspy(scraper_factory):
    scraper = scraper_factory([], lambda **_: pytest.fail("runner must not run"), direct=False)
    result = await scraper.scrape(None)
    assert result.attempted == 0 and result.succeeded == 0
    assert result.errors == ["LinkedIn has no configured search profiles"]


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_proxy_or_direct_access_must_be_explicit(scraper_factory, monkeypatch):
    monkeypatch.delenv("FORKJOB_LINKEDIN_PROXIES_FILE", raising=False)
    monkeypatch.delenv("LINKEDIN_PROXIES_FILE", raising=False)
    scraper = scraper_factory([{"term": "python"}], lambda **_: Frame([]), direct=False)
    with pytest.raises(ScraperPermanentError, match="proxy file is required"):
        await scraper.scrape(None)


@pytest.mark.no_database
def test_dedup_by_linkedin_id_and_canonical_url():
    rows = [
        {"id": "111", "title": "Engineer", "job_url": "https://linkedin.com/jobs/view/111"},
        {"id": "111", "title": "Engineer", "job_url": "https://linkedin.com/jobs/view/111?trk=x"},
        {"id": "222", "title": "Engineer", "job_url": "https://linkedin.com/jobs/view/222"},
        {"id": "333", "title": "Engineer", "job_url": "https://linkedin.com/jobs/view/333", "job_url_direct": "https://acme.example/jobs/a?utm_source=x"},
        {"id": "444", "title": "Engineer", "job_url": "https://linkedin.com/jobs/view/444", "job_url_direct": "https://acme.example/jobs/a?utm_source=y"},
    ]
    jobs = [linkedin.job_from_row(row) for row in rows]
    assert len(linkedin._deduplicate([job for job in jobs if job])) == 3


@pytest.mark.no_database
def test_nullish_jobspy_values_do_not_become_identity():
    assert linkedin.job_from_row({"title": math.nan, "job_url": "https://example.com"}) is None
    assert linkedin.job_from_row({"title": "Engineer", "job_url": math.nan}) is None
    assert linkedin._text(float("nan")) is None


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_isolated_runner_kills_child_on_cancellation(monkeypatch):
    started = asyncio.Event()
    child = None
    create_process = asyncio.create_subprocess_exec

    async def launch(*_args, **kwargs):
        nonlocal child
        child = await create_process(
            sys.executable,
            "-c",
            "import time; time.sleep(60)",
            **kwargs,
        )
        started.set()
        return child

    monkeypatch.setattr(linkedin.asyncio, "create_subprocess_exec", launch)
    task = asyncio.create_task(linkedin._run_jobspy_isolated({}))
    await asyncio.wait_for(started.wait(), timeout=3)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, timeout=3)
    assert child is not None and child.returncode is not None
