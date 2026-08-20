"""Landing.jobs — European tech jobs with visa/relocation tags."""

from __future__ import annotations
from typing import Any
from ..geo import country_from_name, region_for
from ..models import DateSource, Job, Layer, Region, WorkMode
from ..normalize import html_to_text, parse_datetime
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError

BASE_URL = "https://landing.jobs"
API_URL = "https://landing.jobs/api/v1/jobs"


class LandingJobsScraper(ScraperBase):
    source_key = "landingjobs"
    label = "Landing.jobs"
    base_url = BASE_URL

    def __init__(self, config: Any = None, *, max_pages: int = 10) -> None:
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
            entries = payload.get("jobs") or payload.get("results") or payload.get("data") or []
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
        url = entry.get("url") or entry.get("link")
        if not title or not url:
            return None
        company = (entry.get("company_name") or entry.get("company") or "?").strip()
        location = (entry.get("location") or entry.get("city") or "").strip() or None
        country = country_from_name(location) if location else None
        description = html_to_text(entry.get("description") or "")
        # Landing.jobs has visa/relocation tags
        tags = []
        if entry.get("visa_sponsorship"):
            tags.append("Visa Sponsorship")
        if entry.get("relocation"):
            tags.append("Relocation Package")
        if tags:
            description = f"Tags: {', '.join(tags)}\n\n{description}"
        posted_at = parse_datetime(entry.get("published_at") or entry.get("created_at"))
        return Job.build(
            url=url, source=self.source, layer=Layer.B,
            company=company, title=title,
            external_id=str(entry.get("id")) if entry.get("id") else None,
            location=location, country=country,
            region=region_for(country) if country else Region.EU,
            work_mode=(WorkMode.REMOTE if entry.get("remote") else WorkMode.UNKNOWN),
            remote=True if entry.get("remote") else None,
            description=description,
            posted_at=posted_at,
            date_source=DateSource.EMPLOYER if posted_at else DateSource.DISCOVERED,
        )
