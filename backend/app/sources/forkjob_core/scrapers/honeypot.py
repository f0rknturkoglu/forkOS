"""Honeypot.io — reverse recruiting for DE/NL/AT tech jobs."""

from __future__ import annotations

from typing import Any

from ..geo import country_from_name, region_for
from ..models import DateSource, Job, Layer, Region, WorkMode
from ..normalize import html_to_text, parse_datetime
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError

BASE_URL = "https://www.honeypot.io"
API_URL = "https://www.honeypot.io/api/v1/jobs"


class HoneypotScraper(ScraperBase):
    source_key = "honeypot"
    label = "Honeypot.io"
    base_url = BASE_URL

    def __init__(self, config: Any = None, *, max_pages: int = 5) -> None:
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
        entries = payload
        if isinstance(payload, dict):
            entries = payload.get("jobs") or payload.get("results") or []
        if not isinstance(entries, list):
            return []
        jobs: list[Job] = []
        for entry in entries:
            if isinstance(entry, dict):
                job = self._parse_one(entry)
                if job:
                    jobs.append(job)
        return jobs

    def _parse_one(self, entry: dict) -> Job | None:
        title = (entry.get("title") or "").strip()
        slug = entry.get("slug") or entry.get("id")
        url = entry.get("url") or (f"{BASE_URL}/jobs/{slug}" if slug else None)
        if not title or not url:
            return None
        company = (entry.get("company_name") or entry.get("company") or "?").strip()
        loc = entry.get("location") or entry.get("city")
        location = str(loc).strip() if loc else None
        country = country_from_name(location) if location else None
        description = html_to_text(entry.get("description") or "")

        # Honeypot shows visa status explicitly
        visa = entry.get("visa_sponsorship") or entry.get("visa")
        if visa:
            description = f"Visa: {visa}\n\n{description}"

        skills = entry.get("skills") or entry.get("technologies") or []
        if isinstance(skills, list) and skills:
            description = f"Skills: {', '.join(str(s) for s in skills)}\n\n{description}"

        posted_at = parse_datetime(entry.get("published_at") or entry.get("created_at"))
        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=company,
            title=title,
            external_id=str(entry.get("id")) if entry.get("id") else None,
            location=location,
            country=country,
            region=region_for(country) if country else Region.EU,
            work_mode=(WorkMode.REMOTE if entry.get("remote") else WorkMode.UNKNOWN),
            remote=True if entry.get("remote") else None,
            description=description,
            posted_at=posted_at,
            date_source=DateSource.EMPLOYER if posted_at else DateSource.DISCOVERED,
        )
