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

from ..geo import region_for
from ..models import Job, Layer, Region, WorkMode, date_source_for
from ..normalize import html_to_text, parse_datetime, parse_single_country
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
        pages_fetched = 0
        items_seen = 0
        cap_hit = False
        keywords = self.keywords or ("",)
        page_limit = len(keywords) * self.max_pages

        for keyword in keywords:
            for page in range(1, self.max_pages + 1):
                try:
                    payload = await client.get_json(self.query_url(keyword, page))
                except ScraperPermanentError:
                    break  # a rejected filter must not sink the rest

                pages_fetched += 1
                page_jobs = self.parse(payload)
                items_seen += len(page_jobs)
                fresh = [j for j in page_jobs if (j.external_id or j.url) not in seen]
                seen.update((j.external_id or j.url) for j in fresh)
                jobs.extend(fresh)

                # `pagination.hasMore` is authoritative — the docs say so.
                pagination = payload.get("pagination") if isinstance(payload, dict) else None
                has_more = isinstance(pagination, dict) and bool(pagination.get("hasMore"))
                if page == self.max_pages and has_more:
                    cap_hit = True

                if not page_jobs or not has_more:
                    break

        stop_reason = "max_pages_reached" if cap_hit else "exhausted"
        self.record_telemetry(
            items_seen=items_seen,
            items_returned=len(jobs),
            pages_fetched=pages_fetched,
            page_limit=page_limit,
            result_limit=None,
            cap_hit=cap_hit,
            stop_reason=stop_reason,
            partial_reason="max_pages_reached" if cap_hit else None,
        )
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
        country = parse_single_country(location)

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
            date_source=date_source_for(posted_at)[1],
        )
