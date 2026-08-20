"""4dayweek.io — jobs at companies with a shorter work week.

    GET https://4dayweek.io/api/v2/jobs?page=N&limit=N

Public JSON API, verified 2026-08-18: HTTP 200 with an honest UA, no key, no
auth, `total` reported up front so paging stops exactly. robots.txt allows
`/api/v2` and `/api/v1` explicitly.

The API answers one question the rest of the registry cannot: which companies
have already committed to a 4-day (or shorter) week. Those are exactly the
employers whose hiring process is small and fast, and the schedule itself is a
real signal about the role.

Field notes from the live response:
- `id` is a UUID and `slug` a URL component — the UUID is the external_id.
- `work_arrangement` is "remote" / "hybrid" / "onsite" (no guessing needed).
- `company.hires_worldwide` tells us whether they hire outside their country.
- `salary_min/max/currency/period` are structured when present.
- `posted_at` is a real publish timestamp → date_source is `employer`.
"""

from __future__ import annotations

from typing import Any

from ..models import DateSource, Job, Layer, Region, WorkMode
from ..normalize import html_to_text, parse_datetime
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError

API_URL = "https://4dayweek.io/api/v2/jobs"

#: The API caps a page somewhere; 50 is safe and cheap.
PAGE_SIZE = 50
DEFAULT_MAX_PAGES = 4


class FourDayWeekScraper(ScraperBase):
    source_key = "fourdayweek"
    label = "4dayweek.io"
    base_url = "https://4dayweek.io"

    def __init__(self, config: Any = None, *, max_pages: int = DEFAULT_MAX_PAGES) -> None:
        super().__init__(config)
        self.max_pages = max_pages

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()
        for page in range(1, self.max_pages + 1):
            try:
                payload = await client.get_json(
                    f"{API_URL}?page={page}&limit={PAGE_SIZE}"
                )
            except ScraperPermanentError:
                break
            if not isinstance(payload, dict):
                break
            page_jobs = self.parse(payload)
            if not page_jobs:
                break
            fresh = [j for j in page_jobs if j.external_id not in seen]
            seen.update(j.external_id for j in fresh if j.external_id)
            jobs.extend(fresh)
            # The API says whether there is more; asking past the end would
            # just burn a request.
            if not payload.get("has_more"):
                break
        return jobs

    def parse(self, payload: Any) -> list[Job]:
        """Pure: API payload in, Jobs out."""
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            raise ScraperPermanentError(
                f"{self.source}: unexpected payload shape {type(payload).__name__}; "
                "expected an object with a 'data' list"
            )
        jobs: list[Job] = []
        for entry in data:
            if isinstance(entry, dict):
                job = self.build_job(entry)
                if job is not None:
                    jobs.append(job)
        return jobs

    def build_job(self, entry: dict[str, Any]) -> Job | None:
        title = (entry.get("title") or "").strip()
        if not title:
            return None

        url = (entry.get("url") or "").strip()
        if not url and entry.get("slug"):
            url = f"{self.base_url}/job/{entry['slug']}"

        company = (entry.get("company") or {}).get("name") or "?"

        # Structured work arrangement — no prose guessing.
        arrangement = (entry.get("work_arrangement") or "").lower()
        if arrangement == "remote":
            work_mode = WorkMode.REMOTE
        elif arrangement == "hybrid":
            work_mode = WorkMode.HYBRID
        elif arrangement == "onsite":
            work_mode = WorkMode.ONSITE
        else:
            work_mode = WorkMode.UNKNOWN

        locations = entry.get("locations") or []
        city: str | None = None
        country: str | None = None
        for loc in locations:
            if not isinstance(loc, dict):
                continue
            if loc.get("is_primary") is False:
                continue
            city = (loc.get("city") or "").strip() or city
            country = _country_code(loc.get("country")) or country
            break

        # The schedule is the point of this board: surface it for the scorer.
        description_parts: list[str] = []
        schedule = entry.get("schedule_type")
        if isinstance(schedule, str) and schedule:
            description_parts.append(f"Schedule: {schedule}")
        hires_ww = (entry.get("company") or {}).get("hires_worldwide")
        if hires_ww:
            description_parts.append("Hires worldwide")
        skills = entry.get("skills")
        if isinstance(skills, list) and skills:
            description_parts.append("Skills: " + ", ".join(str(s) for s in skills))
        description = "\n".join(description_parts) or None

        salary = _salary(entry)

        posted_at = parse_datetime(entry.get("posted_at"))

        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=company,
            title=title,
            external_id=str(entry.get("id")) if entry.get("id") else None,
            location=", ".join(p for p in (city, country) if p) or None,
            city=city,
            country=country,
            region=_region(country),
            work_mode=work_mode,
            remote=True if work_mode is WorkMode.REMOTE else None,
            department=entry.get("category") or None,
            description=description,
            salary=salary,
            posted_at=posted_at,
            date_source=DateSource.EMPLOYER if posted_at else DateSource.DISCOVERED,
        )


def _country_code(value: Any) -> str | None:
    """The API writes full country names ("United Kingdom"), not codes."""
    from ..geo import country_from_name

    if not isinstance(value, str) or not value.strip():
        return None
    return country_from_name(value.strip())


def _region(country: str | None):
    from ..geo import region_for

    return region_for(country)


def _salary(entry: dict[str, Any]) -> str | None:
    low, high = entry.get("salary_min"), entry.get("salary_max")
    if low is None and high is None:
        return None
    currency = (entry.get("salary_currency") or "").upper()
    period = entry.get("salary_period") or ""
    parts = []
    if low is not None and high is not None and low != high:
        parts.append(f"{low:g}-{high:g}")
    else:
        parts.append(f"{(low if low is not None else high):g}")
    if currency:
        parts.append(currency)
    if period:
        parts.append(f"/{period}")
    return " ".join(parts) or None
