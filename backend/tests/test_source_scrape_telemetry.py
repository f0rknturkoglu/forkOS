from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import httpx
import pytest
from sqlalchemy import select

from app.core import runs as run_svc
from app.core.models import SourceRun
from app.db import SessionLocal
from app.main import app
from app.modules.opportunity.worker import poll_source
from app.sources.base import FetchOutcome, RawItem, ScrapeTelemetry
from app.sources.forkjob_core.scrapers.base import ScraperPermanentError
from app.sources.forkjob_core.scrapers.fourdayweek import FourDayWeekScraper
from app.sources.forkjob_core.scrapers.manfred import ManfredScraper


class _DummyMockSource:
    def __init__(self, source_id: str, outcome: FetchOutcome) -> None:
        self.id = source_id
        self.source_class = "normal"
        self.interval_minutes = 60
        self.timeout_seconds = 10.0
        self.outcome = outcome

    async def fetch(self) -> FetchOutcome:
        return self.outcome


class _FailingSource:
    def __init__(self, source_id: str, error: Exception) -> None:
        self.id = source_id
        self.source_class = "normal"
        self.interval_minutes = 60
        self.timeout_seconds = 10.0
        self.error = error

    async def fetch(self) -> FetchOutcome:
        raise self.error


@pytest.mark.asyncio
async def test_scraper_hitting_page_limit_reports_cap_hit():
    scraper = FourDayWeekScraper(max_pages=2)
    mock_client = AsyncMock()

    def mock_get_json(url: str):
        page = 1 if "page=1" in url else 2
        return {
            "data": [
                {
                    "id": f"job-{page}-{i}",
                    "title": f"Engineer {page}-{i}",
                    "url": f"https://4dayweek.io/job/{page}-{i}",
                    "work_arrangement": "remote",
                    "posted_at": "2026-09-01T12:00:00Z",
                }
                for i in range(5)
            ],
            "has_more": True,
        }

    mock_client.get_json.side_effect = mock_get_json

    jobs = await scraper.scrape(mock_client)
    assert len(jobs) == 10
    telemetry = scraper.telemetry
    assert telemetry is not None
    assert telemetry.cap_hit is True
    assert telemetry.pages_fetched == 2
    assert telemetry.page_limit == 2
    assert telemetry.items_seen == 10
    assert telemetry.items_returned == 10
    assert "page_limit_reached" in (telemetry.partial_reason or "")


@pytest.mark.asyncio
async def test_scraper_finding_zero_items_reports_empty():
    source_id = f"test-empty-{uuid.uuid4().hex[:8]}"
    telemetry = ScrapeTelemetry(
        items_seen=0,
        items_returned=0,
        pages_fetched=1,
        cap_hit=False,
    )
    outcome = FetchOutcome(items=[], partial=False, telemetry=telemetry)
    source = _DummyMockSource(source_id, outcome)

    added = await poll_source(source)
    assert added == 0

    async with SessionLocal() as session:
        run = (
            await session.execute(
                select(SourceRun)
                .where(SourceRun.source == source_id)
                .order_by(SourceRun.started_at.desc())
            )
        ).scalar_one()
        assert run.status == run_svc.EMPTY
        assert run.items_seen == 0
        assert run.items_found == 0


@pytest.mark.asyncio
async def test_scraper_hitting_result_limit_reports_cap_hit():
    scraper = ManfredScraper(max_offers=2)
    mock_client = AsyncMock()
    mock_client.get_html = AsyncMock()

    sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://www.getmanfred.com/offer/1</loc><lastmod>2026-09-01</lastmod></url>
      <url><loc>https://www.getmanfred.com/offer/2</loc><lastmod>2026-09-02</lastmod></url>
      <url><loc>https://www.getmanfred.com/offer/3</loc><lastmod>2026-09-03</lastmod></url>
      <url><loc>https://www.getmanfred.com/offer/4</loc><lastmod>2026-09-04</lastmod></url>
      <url><loc>https://www.getmanfred.com/offer/5</loc><lastmod>2026-09-05</lastmod></url>
    </urlset>"""

    offer_html = """
    <html>
      <script id="__NEXT_DATA__" type="application/json">
        {"props":{"pageProps":{"offer":{"id":"123","title":"Dev","company":"Acme","status":"ACTIVE"}}}}
      </script>
    </html>
    """

    def mock_get(url: str):
        if "sitemap" in url:
            return sitemap_xml
        return offer_html

    mock_client.get_html.side_effect = mock_get

    jobs = await scraper.scrape(mock_client)
    assert len(jobs) == 2
    telemetry = scraper.telemetry
    assert telemetry is not None
    assert telemetry.cap_hit is True
    assert telemetry.items_seen == 5
    assert telemetry.items_returned == 2
    assert telemetry.result_limit == 2
    assert "max_offers_reached" in (telemetry.partial_reason or "")


@pytest.mark.asyncio
async def test_native_scraper_error_records_status_error():
    source_id = f"test-err-{uuid.uuid4().hex[:8]}"
    source = _FailingSource(
        source_id, ScraperPermanentError("HTTP 403 (blocked) for test url")
    )

    added = await poll_source(source)
    assert added == 0

    async with SessionLocal() as session:
        run = (
            await session.execute(
                select(SourceRun)
                .where(SourceRun.source == source_id)
                .order_by(SourceRun.started_at.desc())
            )
        ).scalar_one()
        assert run.status == run_svc.ERROR
        assert run.items_found == 0
        assert "403" in (run.error or "")


@pytest.mark.asyncio
async def test_source_run_records_both_items_seen_and_items_returned():
    source_id = f"test-seen-found-{uuid.uuid4().hex[:8]}"
    telemetry = ScrapeTelemetry(
        items_seen=12,
        items_returned=2,
        pages_fetched=1,
        cap_hit=True,
        partial_reason="result_limit",
    )
    items = [
        RawItem(
            external_id=f"ext-{source_id}-{i}",
            title=f"Role {i}",
            url=f"https://example.com/jobs/{source_id}/{i}",
            extra={"kind": "job"},
        )
        for i in range(2)
    ]
    outcome = FetchOutcome(items=items, partial=True, detail="result_limit", telemetry=telemetry)
    source = _DummyMockSource(source_id, outcome)

    added = await poll_source(source)
    assert added == 2

    async with SessionLocal() as session:
        run = (
            await session.execute(
                select(SourceRun)
                .where(SourceRun.source == source_id)
                .order_by(SourceRun.started_at.desc())
            )
        ).scalar_one()
        assert run.status == run_svc.PARTIAL
        assert run.items_seen == 12
        assert run.items_found == 2


@pytest.mark.asyncio
async def test_sources_health_exposes_truthful_telemetry():
    source_id = f"test-health-{uuid.uuid4().hex[:8]}"
    telemetry = ScrapeTelemetry(
        items_seen=42,
        items_returned=5,
        pages_fetched=2,
        cap_hit=True,
        partial_reason="cap reached",
    )
    items = [
        RawItem(
            external_id=f"ext-h-{source_id}-{i}",
            title=f"Role H {i}",
            url=f"https://example.com/jobs/health/{source_id}/{i}",
            extra={"kind": "job"},
        )
        for i in range(5)
    ]
    outcome = FetchOutcome(items=items, partial=True, detail="cap reached", telemetry=telemetry)
    source = _DummyMockSource(source_id, outcome)

    await poll_source(source)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/sources/health")
        assert res.status_code == 200
        data = res.json()
        matching = next((r for r in data if r["source"] == source_id), None)
        assert matching is not None
        assert matching["status"] == "partial"
        assert matching["items_found"] == 5
        assert matching["items_seen"] == 42
