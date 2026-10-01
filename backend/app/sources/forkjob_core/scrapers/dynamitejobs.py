"""Dynamite Jobs (dynamitejobs.com) — remote-first startup/KMİ jobs.

    GET https://dynamitejobs.com/sitemap/jobs-of-category.xml
    GET https://dynamitejobs.com/company/<c>/remote-job/<slug>

The main `/remote-jobs` index is client-rendered, but the public sitemap
(verified 2026-08-18: HTTP 200, ~4,446 posting URLs) plus fully-SSR detail
pages with schema.org JobPosting JSON-LD are open to an honest UA. robots.txt
disallows only `/api/`, `/admin/` and dashboard paths — listings and sitemap
are allowed, no Cloudflare.

Why it matters: a large remote-first board where "Anywhere in the World"
postings are common. The detail JSON-LD carries `datePosted`, hiring
organization, a country list under `applicantLocationRequirements`, and
salary when present.

Field notes:
- Posting URLs come from the category sitemap; each detail page is one
  request, so the run is capped by `max_offers` like Manfred/Tecnoempleo.
- `datePosted` is a real ISO publish timestamp → date_source is `employer`.
- The stable id is the trailing URL slug (the sitemap URL is unique).
"""

from __future__ import annotations

from typing import Any

from ..models import Job, Layer, WorkMode, date_source_for
from ..normalize import format_salary, html_to_text, parse_datetime, sitemap_locations
from .base import ScraperBase, ScraperError, ScraperHttpClient, ScraperPermanentError
from .schemaorg import find_type, ld_blocks, organisation_name, schema_job, text

SITEMAP_URL = "https://dynamitejobs.com/sitemap/jobs-of-category.xml"
BASE_URL = "https://dynamitejobs.com"
DEFAULT_MAX_OFFERS = 40


class DynamiteJobsScraper(ScraperBase):
    source_key = "dynamitejobs"
    label = "Dynamite Jobs"
    base_url = BASE_URL

    def __init__(self, config: Any = None, *, max_offers: int = DEFAULT_MAX_OFFERS) -> None:
        super().__init__(config)
        self.max_offers = max_offers

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        try:
            xml = await client.get_html(SITEMAP_URL)
        except ScraperError as exc:
            self.errors.append(str(exc))
            self.record_telemetry(
                items_seen=0,
                items_returned=0,
                pages_fetched=1,
                page_limit=None,
                result_limit=self.max_offers,
                cap_hit=False,
                stop_reason="sitemap_failed",
            )
            return []
        urls = _posting_urls(xml)
        if not urls:
            self.record_telemetry(
                items_seen=0,
                items_returned=0,
                pages_fetched=1,
                page_limit=None,
                result_limit=self.max_offers,
                cap_hit=False,
                stop_reason="empty_sitemap",
            )
            raise ScraperPermanentError("dynamitejobs: sitemap held no posting URLs")

        total_urls = len(urls)
        target_urls = urls[: self.max_offers]
        cap_hit = total_urls > self.max_offers
        pages_fetched = 1  # sitemap

        jobs: list[Job] = []
        for url in target_urls:
            try:
                html = await client.get_html(url)
                pages_fetched += 1
            except ScraperError as exc:
                self.errors.append(str(exc))
                continue
            job = self.parse_offer(html, url)
            if job is not None:
                jobs.append(job)

        stop_reason = "max_offers_reached" if cap_hit else "exhausted"
        self.record_telemetry(
            items_seen=total_urls,
            items_returned=len(jobs),
            pages_fetched=pages_fetched,
            page_limit=None,
            result_limit=self.max_offers,
            cap_hit=cap_hit,
            stop_reason=stop_reason,
            partial_reason=(
                f"max_offers_reached: {len(target_urls)} of {total_urls} sitemap URLs fetched"
                if cap_hit
                else None
            ),
        )
        return jobs

    def parse_offer(self, html: str, url: str) -> Job | None:
        posting = find_type(ld_blocks(html), "JobPosting")
        if posting is None:
            return None
        title = text(posting.get("title"))
        if not title:
            return None
        company = organisation_name(posting.get("hiringOrganization")) or "?"

        location = _countries(posting.get("applicantLocationRequirements"))
        work_mode = WorkMode.REMOTE
        if str(posting.get("jobLocationType") or "").upper() == "TELECOMMUTE":
            work_mode = WorkMode.REMOTE

        posted_at = parse_datetime(text(posting.get("datePosted")))
        salary = _salary(posting.get("baseSalary"))

        return schema_job(posting,
            url=url,
            source=self.source,
            layer=Layer.B,
            company=company,
            title=title,
            external_id=url.rstrip("/").rsplit("/", 1)[-1] or None,
            location=location,
            work_mode=work_mode,
            remote=True,
            description=html_to_text(posting.get("description")),
            salary=salary,
            posted_at=posted_at,
            date_source=date_source_for(posted_at)[1],
        )


def _posting_urls(xml: str) -> list[str]:
    """Only real posting URLs, not skill/category pages."""
    return [u for u in sitemap_locations(xml) if "/remote-job/" in u]


def _countries(req: Any) -> str | None:
    if isinstance(req, list):
        names = [c.get("name") for c in req if isinstance(c, dict) and c.get("name")]
        if names:
            return ", ".join(str(n) for n in names[:6])
    if isinstance(req, dict) and req.get("name"):
        return str(req["name"])
    return None


def _salary(sal: Any) -> str | None:
    if not isinstance(sal, dict):
        return None
    value = sal.get("value") or {}
    if isinstance(value, dict):
        low, high = value.get("minValue"), value.get("maxValue")
    else:
        low = high = None
    return format_salary(low, high, (sal.get("currency") or "").upper())
