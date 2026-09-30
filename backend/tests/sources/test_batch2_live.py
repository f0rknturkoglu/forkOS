"""Gated and bounded live public acquisition; no account/user state mutations."""

import os

import pytest

from app.sources.forkjob_core.scrapers.base import ScraperPermanentError
from app.sources.forkjob_core.scrapers.index import get_scraper
from app.sources.forkjob_core.scrapers.registry import load_registry_b

pytestmark = [
    pytest.mark.no_database,
    pytest.mark.live_network,
    pytest.mark.skipif(
        os.getenv("FORKOS_RUN_LIVE_CAREER_TESTS") != "1", reason="explicit live opt-in"
    ),
]


@pytest.mark.parametrize(
    "key",
    [
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
        "linkedin",
    ],
)
async def test_verified_public_surface(key):
    source = load_registry_b().by_key(key)
    source.config = {**source.config, "max_offers": 5, "max_pages": 1}
    if key != "freehire":
        source.config["detail_budget"] = 1
    else:
        source.config.update(page_size=5, slices=[{"regions": ["eu", "uk"]}])
    s = get_scraper(source)
    if key in {"workcamino", "relocantly"}:
        with pytest.raises(ScraperPermanentError, match="terms prohibit"):
            await s.collect()
        pytest.xfail("Public terms prohibit automated scraping; no network acquisition")
    try:
        batch = await s.collect()
    except ScraperPermanentError as exc:
        if key == "linkedin" and "robots.txt disallows" in str(exc):
            pytest.xfail(
                "Guest V2 not implementable under verified LinkedIn robots policy; no bypass/fallback network"
            )
        raise
    assert batch.succeeded and batch.jobs and not batch.errors
    assert len(batch.jobs) <= 5 and batch.telemetry.items_returned == len(batch.jobs)
    if key == "freehire":
        assert batch.telemetry.metadata["requests"] == 1
