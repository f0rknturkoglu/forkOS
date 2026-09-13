from __future__ import annotations

import pytest

from app.sources.announcements import SOURCES as ANNOUNCEMENT_SOURCES
from app.sources.forkjob_port import forkjob_sources

pytestmark = pytest.mark.no_database


def test_automatic_catalog_has_unique_valid_adapter_metadata():
    sources = [*forkjob_sources(), *ANNOUNCEMENT_SOURCES]
    ids = [source.id for source in sources]

    assert ids
    assert len(ids) == len(set(ids))
    assert all(source_id.strip() for source_id in ids)
    assert all(source.interval_minutes > 0 for source in sources)


def test_opt_in_linkedin_is_manual_only():
    automatic = {source.id for source in forkjob_sources()}
    manual = {source.id for source in forkjob_sources(include_opt_in=True)}

    assert "jobhunter:linkedin" not in automatic
    assert "jobhunter:linkedin" in manual


async def test_portal_keeps_partial_scrape_as_partial(monkeypatch: pytest.MonkeyPatch):
    """Bazi sayfalar alindiysa sonuc `partial` olur; hata listesi kaybolmaz."""
    from app.sources.forkjob_port import PortalSource, job_to_raw
    from app.sources.forkjob_core.scrapers.base import ScrapeBatch

    class _Scraper:
        async def collect(self):
            return ScrapeBatch(
                jobs=[_job()],
                errors=["page 3: TimeoutError"],
                attempted=4,
                succeeded=3,
            )

    monkeypatch.setattr("app.sources.forkjob_port.get_scraper", lambda portal: _Scraper())
    source = PortalSource(portal=_portal())

    outcome = await source.fetch()

    assert outcome.partial is True
    assert "TimeoutError" in outcome.detail
    assert [item.external_id for item in outcome.items] == ["ext-1"]


async def test_portal_total_failure_raises_so_the_run_is_error(monkeypatch: pytest.MonkeyPatch):
    """Hicbir sayfa alinamadiysa kosum hatadir; bos liste donmez."""
    from app.sources.forkjob_port import PortalSource
    from app.sources.forkjob_core.scrapers.base import ScrapeBatch

    class _Scraper:
        async def collect(self):
            return ScrapeBatch(jobs=[], errors=["HTTP 503"], attempted=3, succeeded=0)

    monkeypatch.setattr("app.sources.forkjob_port.get_scraper", lambda portal: _Scraper())
    source = PortalSource(portal=_portal())

    with pytest.raises(RuntimeError, match="503"):
        await source.fetch()


def _portal():
    from app.sources.forkjob_core.scrapers.registry import LayerBSource

    return LayerBSource(key="testportal", label="Test", url="https://example.invalid")


def _job():
    from app.sources.forkjob_core.models import Job, Layer

    return Job(
        job_id="job-1",
        cluster_id="cluster-1",
        source="testportal",
        layer=Layer.B,
        company="Acme",
        title="Backend Developer",
        url="https://example.invalid/jobs/1",
        external_id="ext-1",
    )
