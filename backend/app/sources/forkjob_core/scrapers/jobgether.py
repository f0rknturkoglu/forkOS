"""Jobgether (jobgether.com) — remote and flexible roles across Europe.

Verified 2026-08-08.

    GET https://jobgether.com/astroapi/ai/jobs?experience=entry-level-graduate

Unusually, the site **invites this**. Its robots.txt closes query strings
generally and then opens this one endpoint by name:

    Content-Signal: search=yes, ai-input=yes, ai-train=no
    Allow: /astroapi/ai/jobs
    Allow: /astroapi/ai/jobs?*
    Disallow: /*?*
    Crawl-delay: 2

And the endpoint documents itself at `/astroapi/ai/jobs/docs`, describing
itself as "intended for AI agents/assistants answering user job-search
queries". Nothing here is inferred: every parameter below is from that
document, and the allowed values come from the API's own 400 responses, which
return the offending field with its permitted values so a caller can
self-correct.

That makes it the second source after EURES where the seniority filter is a
*fact stated by the poster* rather than something read out of a job title:

    entry-level-graduate, junior-1-2-years, mid-level-2-5-years,
    senior-5-10-years, expert-10-years

`postedAt` is ISO 8601 and a real publish date, so `date_source` is
`employer`. `salaryRange` comes through as prose ("82500-102500 EUR").
"""

from __future__ import annotations

from typing import Any

from ..geo import country_from_name, region_for
from ..models import DateSource, Job, Layer, Region, WorkMode
from ..normalize import html_to_text, parse_datetime
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError

BASE_URL = "https://jobgether.com"
API_URL = "https://jobgether.com/astroapi/ai/jobs"

#: From the API's own 400 response. The first two are the target profile.
EXPERIENCE_LEVELS = (
    "entry-level-graduate",
    "junior-1-2-years",
    "mid-level-2-5-years",
    "senior-5-10-years",
    "expert-10-years",
)
CONTRACT_TYPES = ("full-time", "part-time", "fixed-term", "freelance", "internships")
REMOTE_TYPES = ("full-remote", "remote-first", "hybrid")

#: Ask for the levels that fit, not the whole board.
DEFAULT_EXPERIENCE = ("entry-level-graduate", "junior-1-2-years")
DEFAULT_LOCATIONS = ("europe",)
DEFAULT_KEYWORDS = ("developer", "software engineer")
#: The endpoint caps at 25 per page.
DEFAULT_LIMIT = 25
DEFAULT_MAX_PAGES = 4


class JobgetherScraper(ScraperBase):
    source_key = "jobgether"
    label = "Jobgether"
    base_url = BASE_URL

    def __init__(
        self,
        config: Any = None,
        *,
        experience: tuple[str, ...] | list[str] = DEFAULT_EXPERIENCE,
        locations: tuple[str, ...] | list[str] = DEFAULT_LOCATIONS,
        keywords: tuple[str, ...] | list[str] = DEFAULT_KEYWORDS,
        limit: int = DEFAULT_LIMIT,
        max_pages: int = DEFAULT_MAX_PAGES,
    ) -> None:
        super().__init__(config)
        self.experience = tuple(experience)
        self.locations = tuple(locations)
        self.keywords = tuple(keywords)
        self.limit = min(limit, DEFAULT_LIMIT)
        self.max_pages = max_pages

    @property
    def scope(self) -> str:
        """Which slice this run asks for — see ScraperBase.scope."""
        return "|".join(
            (
                ",".join(sorted(self.experience)),
                ",".join(sorted(self.locations)),
                ",".join(sorted(self.keywords)),
            )
        )

    def query_url(self, keyword: str, page: int) -> str:
        params = [
            f"page={page}",
            f"limit={self.limit}",
            "sort=date",
        ]
        if keyword:
            params.append(f"keyword={keyword.replace(' ', '+')}")
        if self.experience:
            params.append(f"experience={','.join(self.experience)}")
        if self.locations:
            params.append(f"locations={','.join(self.locations)}")
        return f"{API_URL}?{'&'.join(params)}"

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()

        for keyword in self.keywords or ("",):
            for page in range(1, self.max_pages + 1):
                try:
                    payload = await client.get_json(self.query_url(keyword, page))
                except ScraperPermanentError:
                    break  # a rejected filter must not sink the rest

                page_jobs = self.parse(payload)
                fresh = [j for j in page_jobs if (j.external_id or j.url) not in seen]
                seen.update((j.external_id or j.url) for j in fresh)
                jobs.extend(fresh)

                # `pagination.hasMore` is authoritative — the docs say so.
                pagination = payload.get("pagination") if isinstance(payload, dict) else None
                if not page_jobs or not (
                    isinstance(pagination, dict) and pagination.get("hasMore")
                ):
                    break
        return jobs

    # -- pure parsing -------------------------------------------------------

    def parse(self, payload: Any) -> list[Job]:
        """Pure: API payload in, Jobs out."""
        if not isinstance(payload, dict) or "jobs" not in payload:
            raise ScraperPermanentError(
                f"jobgether: unexpected payload shape {type(payload).__name__}; "
                "expected an object with a 'jobs' list"
            )
        jobs: list[Job] = []
        for entry in payload.get("jobs") or []:
            if isinstance(entry, dict):
                job = self.build_job(entry)
                if job is not None:
                    jobs.append(job)
        return jobs

    def build_job(self, entry: dict[str, Any]) -> Job | None:
        title = (entry.get("title") or "").strip()
        url = (entry.get("url") or "").strip()
        if not title or not url:
            return None

        location = (entry.get("location") or "").strip() or None
        country = _single_country(location)

        remote = (entry.get("remote") or "").strip().lower()
        work_mode = WorkMode.UNKNOWN
        if "full remote" in remote or "remote" in remote:
            work_mode = WorkMode.REMOTE
        if "hybrid" in remote:
            work_mode = WorkMode.HYBRID

        description = html_to_text(entry.get("description"))
        experience = (entry.get("experience") or "").strip()
        if experience:
            # Stated by the poster, so it goes where the scorer will read it.
            description = f"Experience level: {experience}\n\n{description or ''}".strip()

        functions = entry.get("jobFunctions")
        posted_at = parse_datetime(entry.get("postedAt"))

        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=(entry.get("company") or "").strip() or "?",
            title=title,
            external_id=str(entry.get("id")) if entry.get("id") else None,
            location=location,
            country=country,
            region=region_for(country) if country else Region.UNKNOWN,
            work_mode=work_mode,
            remote=work_mode is WorkMode.REMOTE or None,
            department=", ".join(functions[:2]) if isinstance(functions, list) else None,
            description=description,
            salary=(entry.get("salaryRange") or "").strip() or None,
            posted_at=posted_at,
            date_source=DateSource.EMPLOYER if posted_at else DateSource.DISCOVERED,
        )


def _single_country(location: Any) -> str | None:
    """Resolve only when the location names exactly one known country.

    "Germany" resolves; "Spain, France" does not, and neither does "Europe".
    """
    if not isinstance(location, str) or not location.strip():
        return None
    parts = [p.strip() for p in location.split(",") if p.strip()]
    if len(parts) != 1:
        return None
    return country_from_name(parts[0])
