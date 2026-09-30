"""Opt-in public transport checks; no normal test makes HTTP requests."""

import os

import pytest

from app.sources.forkjob_core.scrapers.base import ScrapeBatch, ScraperPermanentError
from app.sources.forkjob_core.scrapers.index import get_scraper
from app.sources.forkjob_core.scrapers.registry import load_registry_b

pytestmark = [
    pytest.mark.no_database,
    pytest.mark.live_network,
    pytest.mark.skipif(
        os.getenv("FORKOS_RUN_LIVE_CAREER_TESTS") != "1", reason="opt-in live network only"
    ),
]


@pytest.mark.parametrize(
    "key",
    ["germantechjobs", "swissdevjobs", "devitjobs", "remotecom", "berlinstartupjobs", "eustartups"],
)
async def test_current_public_schema(key):
    source = load_registry_b().by_key(key)
    source.config = {**source.config, "max_offers": 5, "detail_budget": 1}
    if key in ("remotecom", "berlinstartupjobs", "eustartups"):
        source.config["max_pages"] = 1
    scraper = get_scraper(source)
    try:
        result = await scraper.collect()
    except ScraperPermanentError as exc:
        if key == "devitjobs" and "403" in str(exc):
            pytest.xfail("Documented local public HTTP 403; disabled source, no bypass")
        raise
    assert isinstance(result, ScrapeBatch)
    assert result.succeeded > 0 and not result.errors
    assert result.telemetry.pages_fetched >= 1
    assert result.telemetry.items_returned == len(result.jobs)
