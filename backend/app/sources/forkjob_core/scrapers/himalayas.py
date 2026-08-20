"""Himalayas (himalayas.app) — remote job board with public API.

    GET https://himalayas.app/jobs/api

No key required. Returns JSON with job listings including visa/relocation info.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..geo import country_from_name, region_for
from ..models import DateSource, Job, Layer, Region, WorkMode
from ..normalize import html_to_text
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError

API_URL = "https://himalayas.app/jobs/api"


class HimalayasScraper(ScraperBase):
    source_key = "himalayas"
    label = "Himalayas"
    base_url = "https://himalayas.app"

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        payload = await client.get_json(API_URL)
        return self.parse(payload)

    def parse(self, payload: Any) -> list[Job]:
        # Himalayas returns a list of jobs directly
        entries = payload
        if isinstance(payload, dict):
            entries = payload.get("jobs") or payload.get("results") or []
        if not isinstance(entries, list):
            raise ScraperPermanentError(
                f"himalayas: expected list or dict with jobs, got {type(payload).__name__}"
            )
        jobs: list[Job] = []
        for entry in entries:
            if isinstance(entry, dict):
                job = self._parse_one(entry)
                if job is not None:
                    jobs.append(job)
        return jobs

    def _parse_one(self, entry: dict[str, Any]) -> Job | None:
        title = (entry.get("title") or "").strip()
        if not title:
            return None

        slug = entry.get("slug") or entry.get("id")
        url = entry.get("url") or entry.get("applicationLink") or entry.get("link")
        if not url and slug:
            url = f"https://himalayas.app/jobs/{slug}"

        description = html_to_text(entry.get("description") or entry.get("descriptionHtml"))
        company = (entry.get("companyName") or entry.get("company") or "?").strip()

        # Location restrictions — Himalayas lists where candidates must be
        location_raw = entry.get("locationRestriction") or entry.get("location") or ""
        location = str(location_raw).strip() if location_raw else None
        country = country_from_name(location) if location else None

        posted_str = entry.get("createdAt") or entry.get("postedAt") or entry.get("date")
        posted_at = None
        if isinstance(posted_str, str):
            try:
                posted_at = datetime.fromisoformat(posted_str.replace("Z", "+00:00"))
            except ValueError:
                pass

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
            posted_at=posted_at,
            date_source=DateSource.EMPLOYER if posted_at else DateSource.DISCOVERED,
        )
