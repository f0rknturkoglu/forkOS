"""RemoteOK (remoteok.com) — remote board with a free public JSON API.

Verified 2026-08-08. No key, no auth.

    GET https://remoteok.com/api

Their API terms, returned as the **first element of the array**:

    "Please link back (with follow, and without nofollow!) to the URL on
     Remote OK and mention Remote OK as a source... If you do not we'll have
     to suspend API access."

The stored `url` is that link, which satisfies it. That first element is a
legal notice rather than a posting and must be skipped — parsing it as a job
would produce a titleless row.

Field notes:

- `epoch` / `date` is a real publish timestamp -> `date_source` is `updated`.
- `location` is frequently empty, and `tags` carry the useful signal instead
  ("dev", "engineer", "senior", "python", "react"). They are surfaced into the
  description so the scorer's skill and seniority rules can read them.
- `salary_min` / `salary_max` are real numbers when present, which is rare
  among these sources.
- Everything here is remote by definition of the site.
"""

from __future__ import annotations

from typing import Any

from ..geo import country_from_name, region_for
from ..models import Job, Layer, Region, WorkMode, date_source_for
from ..normalize import format_salary, html_to_text, parse_datetime, parse_epoch_ms
from ..rich_text import enrich
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError

BASE_URL = "https://remoteok.com"
API_URL = "https://remoteok.com/api"


class RemoteOkScraper(ScraperBase):
    source_key = "remoteok"
    label = "RemoteOK"
    base_url = BASE_URL

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        payload = await client.get_json(API_URL)
        raw_entries = (
            [e for e in payload if isinstance(e, dict) and "legal" not in e]
            if isinstance(payload, list)
            else []
        )
        jobs = self.parse(payload)
        self.record_telemetry(
            items_seen=len(raw_entries),
            items_returned=len(jobs),
            pages_fetched=1,
            cap_hit=True,
            partial_reason="upstream_recent_window",
            stop_reason="upstream_recent_window",
        )
        return jobs

    def parse(self, payload: Any) -> list[Job]:
        """Pure: API payload in, Jobs out."""
        if not isinstance(payload, list):
            raise ScraperPermanentError(f"remoteok: expected a list, got {type(payload).__name__}")
        jobs: list[Job] = []
        for entry in payload:
            if not isinstance(entry, dict) or "legal" in entry:
                continue  # the first element is the API terms, not a posting
            job = self.build_job(entry)
            if job is not None:
                jobs.append(job)
        return jobs

    def build_job(self, entry: dict[str, Any]) -> Job | None:
        title = (entry.get("position") or "").strip()
        url = entry.get("url")
        if not title or not url:
            return None

        description = html_to_text(entry.get("description"))

        tags = [t for t in (entry.get("tags") or []) if isinstance(t, str)]
        if tags:
            # `location` is usually empty here and the tags carry the signal,
            # so they go where the scorer's skill rules will see them.
            description = f"Tags: {', '.join(tags)}\n\n{description or ''}".strip()

        location = (entry.get("location") or "").strip() or None
        country = country_from_name(location) if location else None

        posted_at = parse_datetime(entry.get("date")) or parse_epoch_ms(entry.get("epoch"))

        description = enrich(description, self.source, {"Technologies": ", ".join(tags), "Remote scope": location, "Application URL": entry.get("apply_url")})
        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=(entry.get("company") or "").strip() or "?",
            title=title,
            external_id=str(entry.get("id")) if entry.get("id") is not None else None,
            location=location,
            country=country,
            region=region_for(country) if country else Region.UNKNOWN,
            work_mode=WorkMode.REMOTE,
            remote=True,
            department=", ".join(tags[:3]) or None,
            description=description,
            salary=_salary(entry),
            posted_at=posted_at,
            date_source=date_source_for(None, posted_at)[1],
        )


def _salary(entry: dict[str, Any]) -> str | None:
    low, high = entry.get("salary_min"), entry.get("salary_max")
    low = low if isinstance(low, (int, float)) and low > 0 else None
    high = high if isinstance(high, (int, float)) and high > 0 else None
    return format_salary(low, high, entry.get("salary_currency"), suffix="/" + entry["salary_period"] if isinstance(entry.get("salary_period"), str) else "")
