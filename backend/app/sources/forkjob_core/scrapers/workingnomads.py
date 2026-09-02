"""Working Nomads (workingnomads.com) — remote job board, JSON API + RSS.

    GET https://www.workingnomads.com/api/exposed_jobs

Public API, no key. Software and data roles focused.
"""

from __future__ import annotations

import contextlib
from datetime import datetime
from typing import Any

from ..geo import country_from_name, region_for
from ..models import date_source_for, Job, Layer, Region, WorkMode
from ..normalize import html_to_text
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError

API_URL = "https://www.workingnomads.com/api/exposed_jobs"


class WorkingNomadsScraper(ScraperBase):
    source_key = "workingnomads"
    label = "Working Nomads"
    base_url = "https://www.workingnomads.com"

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        payload = await client.get_json(API_URL)
        return self.parse(payload)

    def parse(self, payload: Any) -> list[Job]:
        entries = payload
        if isinstance(payload, dict):
            entries = payload.get("jobs") or payload.get("data") or payload.get("results") or []
        if not isinstance(entries, list):
            raise ScraperPermanentError(
                f"workingnomads: expected list, got {type(payload).__name__}"
            )
        jobs: list[Job] = []
        for entry in entries:
            if isinstance(entry, dict):
                job = self._parse_one(entry)
                if job is not None:
                    jobs.append(job)
        return jobs

    def _parse_one(self, entry: dict[str, Any]) -> Job | None:
        title = (entry.get("title") or entry.get("job_title") or "").strip()
        url = entry.get("url") or entry.get("link") or entry.get("apply_url")
        if not title or not url:
            return None

        company = (entry.get("company") or entry.get("company_name") or "?").strip()
        description = html_to_text(entry.get("description") or entry.get("body") or "")

        location = (entry.get("location") or entry.get("region") or "").strip() or None
        country = country_from_name(location) if location else None

        # Tags / categories
        tags = entry.get("tags") or entry.get("categories") or []
        if isinstance(tags, list) and tags:
            description = f"Tags: {', '.join(str(t) for t in tags)}\n\n{description}"

        posted_str = entry.get("pub_date") or entry.get("date") or entry.get("published_at")
        posted_at = None
        if isinstance(posted_str, str):
            with contextlib.suppress(ValueError):
                posted_at = datetime.fromisoformat(posted_str.replace("Z", "+00:00"))

        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=company,
            title=title,
            external_id=str(entry.get("id")) if entry.get("id") else None,
            location=location,
            country=country,
            region=region_for(country) if country else Region.UNKNOWN,
            work_mode=WorkMode.REMOTE,
            remote=True,
            description=description,
            posted_at=posted_at,
            date_source=date_source_for(posted_at)[1],
        )
