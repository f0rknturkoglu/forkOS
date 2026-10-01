"""Explicit opt-in live policy smoke; denied policy makes zero guest/V1 calls."""

import os

import pytest

from app.sources.forkjob_core.scrapers.base import ScraperHttpClient
from app.sources.forkjob_core.scrapers.linkedin import LinkedInScraper
from app.sources.forkjob_core.scrapers.linkedin_policy import LinkedInPolicyGate

pytestmark = [
    pytest.mark.no_database,
    pytest.mark.live_network,
    pytest.mark.skipif(
        os.getenv("FORKOS_RUN_LIVE_CAREER_TESTS") != "1", reason="explicit live opt-in"
    ),
]


async def test_bounded_policy_safe_native_smoke(monkeypatch):
    monkeypatch.setattr(
        "app.sources.forkjob_core.scrapers.linkedin._merge_user_profiles", lambda profiles: profiles
    )
    gate = LinkedInPolicyGate()
    scraper = LinkedInScraper(
        searches=[{"term": "Software Engineer", "results_wanted": 2}],
        allow_direct=True,
        transport="native",
        policy_gate=gate,
        max_requests=2,
        max_pages=1,
        detail_enrich_max=0,
        max_wall_seconds=30,
    )
    async with ScraperHttpClient(scraper.config) as client:
        state = await gate.check(client, force=True)
        if not state.allowed:
            pytest.xfail(state.reason + "; zero guest requests, zero JobSpy network calls")
        result = await scraper.scrape(client)
        assert result.jobs and not result.errors
        assert len(result.jobs) <= 2
        assert result.telemetry.metadata["native_requests"] <= 2
