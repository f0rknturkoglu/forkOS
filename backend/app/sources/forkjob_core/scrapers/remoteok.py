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

- `epoch` / `date` is a real publish timestamp -> `date_source` is `employer`.
- `location` is frequently empty, and `tags` carry the useful signal instead
  ("dev", "engineer", "senior", "python", "react"). They are surfaced into the
  description so the scorer's skill and seniority rules can read them.
- `salary_min` / `salary_max` are real numbers when present, which is rare
  among these sources.
- Everything here is remote by definition of the site.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ..geo import country_from_name, region_for
from ..models import DateSource, Job, Layer, Region, WorkMode
from ..normalize import html_to_text, parse_datetime
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError

BASE_URL = "https://remoteok.com"
API_URL = "https://remoteok.com/api"


class RemoteOkScraper(ScraperBase):
    source_key = "remoteok"
    label = "RemoteOK"
    base_url = BASE_URL

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        return self.parse(await client.get_json(API_URL))

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

        posted_at = parse_datetime(entry.get("date")) or _epoch(entry.get("epoch"))

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
            date_source=DateSource.EMPLOYER if posted_at else DateSource.DISCOVERED,
        )


def _salary(entry: dict[str, Any]) -> str | None:
    low, high = entry.get("salary_min"), entry.get("salary_max")
    if isinstance(low, (int, float)) and isinstance(high, (int, float)) and low > 0:
        return f"${int(low):,}-${int(high):,}"
    return None


def _epoch(value: Any) -> datetime | None:
    if isinstance(value, (int, float)) and value > 0:
        return datetime.fromtimestamp(value, tz=UTC)
    return None
