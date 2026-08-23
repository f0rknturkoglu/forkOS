"""Arbeitnow (arbeitnow.com) — free public job API, Europe-focused.

Verified 2026-08-08: HTTP 200, 175 postings per page, paginated, updated
hourly. No key, no OAuth, no scraping — the site publishes this API itself:

    GET https://www.arbeitnow.com/api/job-board-api?page=N

Its own terms, returned in the payload:

    "This is a free public API for jobs, please do not abuse. I would
     appreciate linking back to the site."

So the request rate stays at the Layer B default and `url` always points back
at the original posting.

Field notes from the live response:
- Fields are: slug, company_name, title, description, remote, url, tags,
  job_types, location, created_at.
- **There is no `visa_sponsorship` field.** Older write-ups mention one and it
  is documented in places; it is not in the current payload, and every probe
  returned nothing for it. The visa signal for these postings therefore comes
  from `match.py` reading the description, same as any other source.
- `created_at` is a Unix timestamp and is a publish date, so `employer`.
- `location` is prose ("Berlin, Berlin, Germany", "London (hybrid)").
- Heavily German and British: Berlin, München, Hamburg, London dominate — which
  is squarely in the second-priority country list.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ..models import DateSource, Job, Layer, WorkMode
from ..normalize import html_to_text, parse_location
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError

API_URL = "https://www.arbeitnow.com/api/job-board-api"
DEFAULT_MAX_PAGES = 3


class ArbeitnowScraper(ScraperBase):
    source_key = "arbeitnow"
    label = "Arbeitnow"
    base_url = "https://www.arbeitnow.com"

    def __init__(self, config: Any = None, *, max_pages: int = DEFAULT_MAX_PAGES) -> None:
        super().__init__(config)
        self.max_pages = max_pages

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        jobs: list[Job] = []
        for page in range(1, self.max_pages + 1):
            try:
                payload = await client.get_json(f"{API_URL}?page={page}")
            except ScraperPermanentError:
                break
            page_jobs = self.parse(payload)
            if not page_jobs:
                break
            jobs.extend(page_jobs)
        return jobs

    def parse(self, payload: Any) -> list[Job]:
        """Pure: payload in, Jobs out."""
        if not isinstance(payload, dict) or "data" not in payload:
            raise ScraperPermanentError(
                f"{self.source}: unexpected payload shape {type(payload).__name__}"
            )
        jobs: list[Job] = []
        for entry in payload.get("data") or []:
            if isinstance(entry, dict):
                job = self._parse_one(entry)
                if job is not None:
                    jobs.append(job)
        return jobs

    def _parse_one(self, entry: dict[str, Any]) -> Job | None:
        title = (entry.get("title") or "").strip()
        url = entry.get("url")
        if not title or not url:
            return None

        description = html_to_text(entry.get("description"))
        location_text = entry.get("location")
        info = parse_location(location_text, description=description)

        is_remote = bool(entry.get("remote"))
        work_mode = WorkMode.REMOTE if is_remote else info.work_mode

        created = entry.get("created_at")
        posted_at = None
        if isinstance(created, (int, float)) and created > 0:
            posted_at = datetime.fromtimestamp(created, tz=UTC)

        tags = [t for t in (entry.get("tags") or []) if isinstance(t, str)]

        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=(entry.get("company_name") or "").strip() or "?",
            title=title,
            external_id=entry.get("slug"),
            location=location_text,
            city=info.city,
            country=info.country,
            region=info.region,
            work_mode=work_mode,
            remote=True if is_remote else info.work_mode is WorkMode.REMOTE or None,
            department=", ".join(tags[:3]) or None,
            description=description,
            posted_at=posted_at,
            date_source=DateSource.EMPLOYER if posted_at else DateSource.DISCOVERED,
        )
