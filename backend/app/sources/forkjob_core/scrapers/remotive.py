"""Remotive (remotive.com) — free public JSON API for remote jobs.

    GET https://remotive.com/api/remote-jobs

No key, no auth, no pagination needed. Returns all active jobs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..geo import country_from_name, region_for
from ..models import DateSource, Job, Layer, Region, WorkMode
from ..normalize import html_to_text
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError

API_URL = "https://remotive.com/api/remote-jobs"


class RemotiveScraper(ScraperBase):
    source_key = "remotive"
    label = "Remotive"
    base_url = "https://remotive.com"

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        payload = await client.get_json(API_URL)
        return self.parse(payload)

    def parse(self, payload: Any) -> list[Job]:
        if not isinstance(payload, dict) or "jobs" not in payload:
            raise ScraperPermanentError(
                f"remotive: expected dict with 'jobs', got {type(payload).__name__}"
            )
        jobs: list[Job] = []
        for entry in payload.get("jobs") or []:
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
        company = (entry.get("company_name") or "").strip() or "?"
        location = (entry.get("candidate_required_location") or "").strip() or None
        country = country_from_name(location) if location else None

        posted_str = entry.get("publication_date")
        posted_at = None
        if isinstance(posted_str, str):
            try:
                posted_at = datetime.fromisoformat(posted_str.replace("Z", "+00:00"))
            except ValueError:
                pass

        salary = entry.get("salary")
        salary_text = None
        if isinstance(salary, str) and salary.strip():
            salary_text = salary.strip()

        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=company,
            title=title,
            external_id=str(entry.get("id")) if entry.get("id") is not None else None,
            location=location,
            country=country,
            region=region_for(country) if country else Region.UNKNOWN,
            work_mode=WorkMode.REMOTE,
            remote=True,
            description=description,
            salary=salary_text,
            posted_at=posted_at,
            date_source=DateSource.EMPLOYER if posted_at else DateSource.DISCOVERED,
        )
