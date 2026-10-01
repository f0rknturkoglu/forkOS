"""SOLID.Jobs (solid.jobs) — Polish jobs with fully disclosed salaries.

    GET https://solid.jobs/public-api/offers/IT?pageIndex=N&pageSize=N

The site publishes a keyless public REST API for job boards, verified
2026-08-18: HTTP 200 with an honest UA, no auth, 300 requests/min/IP, and the
response is cached for an hour. robots.txt allows everything except
`/management/` and `/admin/`. There is also an RSS feed at
`https://solid.jobs/rss/job-offers` that carries the same postings.

Why this source matters for the B2B case: the API returns **two salary
brackets per posting** — the primary (usually `employmentType: "B2B"`) and a
secondary (usually UoP, a Polish employment contract). A company that already
offers B2B billing is set up to pay a contractor in another country.

Field notes from the live response:
- `jobOfferKey` is a UUID — the external_id.
- `validFrom` is the listing's start date and matches the RSS pubDate
  exactly; this is board validity, so date_source is `updated`.
- `isRemote` / `isHybrid` are explicit booleans.
- `locations` is a list of Polish city names.
- `experienceLevel` ("Regular", "Senior"…) is stated by the poster.
"""

from __future__ import annotations

from typing import Any

from ..models import Job, Layer, Region, WorkMode, date_source_for
from ..normalize import format_salary, html_to_text, parse_datetime
from ..rich_text import enrich
from .base import ScraperBase, ScraperError, ScraperHttpClient, ScraperPermanentError

API_URL = "https://solid.jobs/public-api/offers/IT"

#: The API allows 10–500 per page. 100 is a good balance.
PAGE_SIZE = 100
DEFAULT_MAX_PAGES = 5
#: The API asks callers to identify themselves; any string works.
CAMPAIGN = "forkjob"


class SolidJobsScraper(ScraperBase):
    source_key = "solidjobs"
    label = "SOLID.Jobs"
    base_url = "https://solid.jobs"

    def __init__(self, config: Any = None, *, max_pages: int = DEFAULT_MAX_PAGES) -> None:
        super().__init__(config)
        self.max_pages = max_pages

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()
        pages_fetched = 0
        items_seen = 0
        cap_hit = False

        for page in range(1, self.max_pages + 1):
            try:
                payload = await client.get_json(
                    f"{API_URL}?campaign={CAMPAIGN}&pageIndex={page}&pageSize={PAGE_SIZE}"
                )
            except ScraperError as exc:
                self.errors.append(str(exc))
                break
            if not isinstance(payload, dict):
                self.errors.append("solidjobs: invalid response schema")
                break
            pages_fetched += 1
            page_jobs = self.parse(payload)
            items_seen += len(page_jobs)
            if not page_jobs:
                break
            fresh = [j for j in page_jobs if j.external_id not in seen]
            if not fresh:
                self.errors.append("solidjobs: repeated page identities")
                break
            seen.update(j.external_id for j in fresh if j.external_id)
            jobs.extend(fresh)
            # Stop when we have seen everything the API reports.
            total = payload.get("totalCount")
            if page == self.max_pages and isinstance(total, int) and page * PAGE_SIZE < total:
                cap_hit = True
            if isinstance(total, int) and page * PAGE_SIZE >= total:
                break

        stop_reason = "max_pages_reached" if cap_hit else "exhausted"
        self.record_telemetry(
            items_seen=items_seen,
            items_returned=len(jobs),
            pages_fetched=pages_fetched,
            page_limit=self.max_pages,
            result_limit=None,
            cap_hit=cap_hit,
            stop_reason=stop_reason,
            partial_reason="max_pages_reached" if cap_hit else None,
        )
        return jobs

    def parse(self, payload: Any) -> list[Job]:
        """Pure: API payload in, Jobs out."""
        jobs = payload.get("jobs") if isinstance(payload, dict) else None
        if not isinstance(jobs, list):
            raise ScraperPermanentError(
                f"{self.source}: unexpected payload shape {type(payload).__name__}; "
                "expected an object with a 'jobs' list"
            )
        out: list[Job] = []
        for entry in jobs:
            if isinstance(entry, dict):
                job = self.build_job(entry)
                if job is not None:
                    out.append(job)
        return out

    def build_job(self, entry: dict[str, Any]) -> Job | None:
        title = (entry.get("title") or "").strip()
        if not title:
            return None
        url = (entry.get("url") or "").strip()
        if not url:
            return None

        company = entry.get("company") or "?"
        locations = entry.get("locations") or []
        city = locations[0] if isinstance(locations, list) and locations else None

        # Both salary brackets go to the description so the scorer and the
        # list's salary column can see the B2B rate explicitly.
        description_parts: list[str] = []
        primary = _salary_text(entry.get("salary"))
        secondary = _salary_text(entry.get("secondarySalary"))
        if primary:
            description_parts.append(f"Salary: {primary}")
        if secondary:
            description_parts.append(f"Salary (secondary): {secondary}")
        skills = entry.get("skills") or []
        if isinstance(skills, list) and skills:
            names = [s.get("name") if isinstance(s, dict) else str(s) for s in skills]
            names = [n for n in names if n]
            if names:
                description_parts.append("Skills: " + ", ".join(names))
        level = entry.get("experienceLevel")
        if level:
            description_parts.append(f"Level: {level}")
        description = "\n\n".join(p for p in [html_to_text(entry.get("description")), "\n".join(description_parts)] if p) or None
        languages = entry.get("languages") or []
        language = ", ".join(str(x["name"]) for x in languages if isinstance(x, dict) and x.get("name")) or None
        description = enrich(description, self.source, {"Technologies": ", ".join(names) if isinstance(skills, list) and skills else None, "Experience level": level, "Language": ", ".join(str(x["name"]) + ": " + str(x.get("level") or "unspecified level") for x in languages if isinstance(x, dict) and x.get("name")), "Expiry": entry.get("validTo"), "Benefits": ", ".join(entry.get("benefits") or []), "Employment type": (entry.get("salary") or {}).get("employmentType"), "Workload": entry.get("contractTime"), "Remote scope": ", ".join(locations) if entry.get("isRemote") else None})

        work_mode = WorkMode.UNKNOWN
        if entry.get("isRemote"):
            work_mode = WorkMode.REMOTE
        elif entry.get("isHybrid"):
            work_mode = WorkMode.HYBRID

        # validFrom matches the RSS pubDate exactly — a real listing date.
        posted_at = parse_datetime(entry.get("validFrom"))

        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=company,
            title=title,
            external_id=str(entry.get("jobOfferKey")) if entry.get("jobOfferKey") else None,
            location=city,
            city=city,
            # Polish board; postings without a location are PL by default.
            country="PL",
            region=Region.EU,
            work_mode=work_mode,
            remote=True if work_mode is WorkMode.REMOTE else None,
            department=entry.get("category") or None,
            description=description,
            salary=primary or None,
            language=language,
            posted_at=posted_at,
            date_source=date_source_for(None, posted_at)[1],
        )


def _salary_text(sal: Any) -> str | None:
    """Format a salary bracket: {"from": 8500, "to": 12000, "currency": "PLN",
    "period": "Month", "employmentType": "B2B"}."""
    if not isinstance(sal, dict):
        return None
    low, high = sal.get("from"), sal.get("to")
    if low is None and high is None:
        return None
    parts = [format_salary(low, high, (sal.get("currency") or "").upper())]
    emp = sal.get("employmentType")
    if emp:
        parts.append(str(emp))
    period = sal.get("period")
    if period:
        parts.append(f"/{period}")
    return " ".join(part for part in parts if part) or None
