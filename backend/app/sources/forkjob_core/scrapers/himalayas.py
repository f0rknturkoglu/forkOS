"""Himalayas (himalayas.app) — remote job board with public API.

    GET https://himalayas.app/jobs/api

No key required. Public job fields include location/timezone restrictions and compensation; missing sponsorship remains unknown.
"""

from __future__ import annotations

import contextlib
from datetime import datetime
from typing import Any

from ..geo import country_from_name, region_for
from ..models import Job, Layer, Region, WorkMode, date_source_for
from ..normalize import format_salary, html_to_text, parse_epoch_ms
from ..rich_text import enrich
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError

API_URL = "https://himalayas.app/jobs/api"


class HimalayasScraper(ScraperBase):
    source_key = "himalayas"
    label = "Himalayas"
    base_url = "https://himalayas.app"

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        payload = await client.get_json(API_URL)
        jobs = self.parse(payload)
        total = payload.get("totalCount") if isinstance(payload, dict) else None
        cap = isinstance(total, int) and total > len(jobs)
        self.record_telemetry(items_seen=len(jobs), items_returned=len(jobs), pages_fetched=1, cap_hit=cap, stop_reason="upstream_window" if cap else "exhausted", partial_reason="upstream_window" if cap else None, metadata={"upstream_total": total})
        return jobs

    def parse(self, payload: Any) -> list[Job]:
        # Himalayas returns a list of jobs directly
        entries = payload
        if isinstance(payload, dict):
            if not any(isinstance(payload.get(k), list) for k in ("jobs", "results")):
                raise ScraperPermanentError("himalayas: missing recognized jobs envelope")
            entries = payload["jobs"] if "jobs" in payload else payload["results"]
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

        if not url:
            return None
        description = html_to_text(entry.get("description") or entry.get("descriptionHtml"))
        company = (entry.get("companyName") or entry.get("company") or "?").strip()

        # Location restrictions — Himalayas lists where candidates must be
        location_raw = entry.get("locationRestrictions") or entry.get("locationRestriction") or entry.get("location") or ""
        location = ", ".join(location_raw) if isinstance(location_raw, list) else str(location_raw).strip() if location_raw else None
        country = country_from_name(location) if location else None

        posted_str = entry.get("createdAt") or entry.get("postedAt") or entry.get("date")
        posted_at = None
        if isinstance(posted_str, str):
            with contextlib.suppress(ValueError):
                posted_at = datetime.fromisoformat(posted_str.replace("Z", "+00:00"))

        posted_at = parse_epoch_ms(entry.get("pubDate")) or posted_at
        salary = format_salary(entry.get("minSalary"), entry.get("maxSalary"), entry.get("currency"), suffix="/" + entry["salaryPeriod"] if entry.get("salaryPeriod") else "")
        description = enrich(description, self.source, {
            "Remote scope": location, "Timezone requirements": ", ".join(str(x) for x in entry.get("timezoneRestrictions") or []),
            "Category": ", ".join(entry.get("categories") or []), "Experience level": ", ".join(entry.get("seniority") or []),
            "Employment type": entry.get("employmentType"), "Expiry": parse_epoch_ms(entry.get("expiryDate")),
            "Application URL": entry.get("applicationLink"), "Company URL": "https://himalayas.app/companies/" + entry["companySlug"] if entry.get("companySlug") else None,
        })
        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=company,
            title=title,
            external_id=str(entry.get("id") or entry.get("guid") or url),
            location=location,
            country=country,
            region=region_for(country) if country else Region.UNKNOWN,
            work_mode=WorkMode.REMOTE,
            remote=True,
            description=description,
            salary=salary,
            posted_at=posted_at,
            date_source=date_source_for(None, posted_at)[1],
        )
