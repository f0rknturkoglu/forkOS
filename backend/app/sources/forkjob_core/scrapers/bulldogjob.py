"""BulldogJob (bulldogjob.com) — Polish/CEE tech jobs, often B2B.

    POST https://bulldogjob.com/graphql
    GraphQL searchJobs query with country PL, English language and 50 results.

Public GraphQL endpoint, verified 2026-08-18: HTTP 200 with an honest UA, no
auth, no key. robots.txt leaves the listing paths open (only /auth, /account,
/feeds and friends are disallowed). The query was found by reading the page's
own Apollo state rather than by guessing field names — `position` is the
title, `publishedAt` a real ISO publish timestamp, `contractB2b` an explicit
boolean.

Why it matters for the B2B case: `contractB2b` tells us directly whether the
employer offers B2B billing, and the Polish IT market runs almost entirely on
contracts — a company that does that at home is set up to pay a contractor
abroad too.

Field notes from the live response:
- `id` is `<numeric>-<slug>` — stable, unique, used as external_id.
- `publishedAt` is a board publication date → date_source is `updated`.
- `city` is a prose list ("Gdansk, Krakow, Warsaw, Wroclaw").
- `experienceLevel` is stated by the poster ("lead", "regular", …).
"""

from __future__ import annotations

from typing import Any

from ..models import Job, Layer, Region, WorkMode, date_source_for
from ..normalize import parse_datetime
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError
from .detail_evidence import enrich_job_details

GRAPHQL_URL = "https://bulldogjob.com/graphql"
PAGE_SIZE = 50
DEFAULT_MAX_PAGES = 6

_QUERY = """\
query {{
  searchJobs(country: "PL", language: en, page: {page}, perPage: {per_page}) {{
    totalCount
    nodes {{
      id
      position
      city
      publishedAt
      remote
      contractB2b
      experienceLevel
    }}
  }}
}}
"""


class BulldogjobScraper(ScraperBase):
    source_key = "bulldogjob"
    label = "BulldogJob"
    base_url = "https://bulldogjob.com"

    def __init__(self, config: Any = None, *, max_pages: int = DEFAULT_MAX_PAGES, detail_budget: int = 20) -> None:
        super().__init__(config)
        self.max_pages = max_pages
        self.detail_budget = max(0, int(detail_budget))

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()
        pages_fetched = 0
        items_seen = 0
        cap_hit = False
        total: int | None = None
        for page in range(1, self.max_pages + 1):
            query = {"query": _QUERY.format(page=page, per_page=PAGE_SIZE)}
            payload = await self.isolate(f"page {page}", lambda query=query: client.post_json(GRAPHQL_URL, query))
            if payload is None:
                break
            if not isinstance(payload, dict):
                self.errors.append("bulldogjob: unrecognized listing schema")
                break
            errors = payload.get("errors")
            if isinstance(errors, list) and errors:
                first = errors[0]
                message = first.get("message") if isinstance(first, dict) else str(first)
                self.errors.append(f"{self.source}: GraphQL: {message}")
                break
            result = payload.get("data", {}).get("searchJobs") or {}
            pages_fetched += 1
            try:
                page_jobs = self.parse(result)
            except ScraperPermanentError as exc:
                self.errors.append(str(exc))
                break
            items_seen += len(page_jobs)
            if not page_jobs:
                break
            fresh = self.dedup_seen(seen, page_jobs)
            if not fresh:
                self.errors.append("bulldogjob: repeated page identities")
                break
            jobs.extend(fresh)
            total = result.get("totalCount")
            if page == self.max_pages and (not isinstance(total, int) or page * PAGE_SIZE < total):
                cap_hit = True
            if isinstance(total, int) and page * PAGE_SIZE >= total:
                break

        listing_errors = list(self.errors)
        metadata = await enrich_job_details(self, client, jobs, self.detail_budget)
        metadata["listing_pages"] = pages_fetched
        metadata["listing_complete"] = not cap_hit and not listing_errors
        stop_reason = "max_pages_reached" if cap_hit else "listing_request_failed" if listing_errors else "exhausted"
        self.record_telemetry(
            items_seen=items_seen,
            items_returned=len(jobs),
            pages_fetched=pages_fetched,
            page_limit=self.max_pages,
            result_limit=None,
            cap_hit=cap_hit,
            stop_reason=stop_reason,
            partial_reason="; ".join(listing_errors + (["max_pages_reached"] if cap_hit else [])) or None,
            metadata=metadata,
        )
        return jobs

    def parse(self, result: Any) -> list[Job]:
        """Pure: the searchJobs result in, Jobs out."""
        nodes = result.get("nodes") if isinstance(result, dict) else None
        if not isinstance(nodes, list):
            raise ScraperPermanentError(
                f"{self.source}: unexpected payload shape; expected searchJobs.nodes"
            )
        jobs: list[Job] = []
        for entry in nodes:
            if isinstance(entry, dict):
                job = self.build_job(entry)
                if job is not None:
                    jobs.append(job)
        return jobs

    def build_job(self, entry: dict[str, Any]) -> Job | None:
        title = (entry.get("position") or "").strip()
        job_id = entry.get("id")
        if not title or not job_id:
            return None

        # The public posting URL is derived from the id slug; the GraphQL
        # response carries no direct apply URL.
        url = f"https://bulldogjob.com/companies/jobs/{job_id}"

        city_text = (entry.get("city") or "").strip() or None
        # "Gdansk, Krakow, Warsaw" — keep the first as the anchor city.
        city = city_text.split(",")[0].strip() if city_text else None

        description_parts: list[str] = []
        if entry.get("contractB2b"):
            description_parts.append("B2B contract available")
        level = entry.get("experienceLevel")
        if level:
            description_parts.append(f"Level: {level}")
        salary = None
        description = "\n".join(description_parts) or None

        work_mode = WorkMode.REMOTE if entry.get("remote") else WorkMode.UNKNOWN
        posted_at = parse_datetime(entry.get("publishedAt"))

        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company="?",
            title=title,
            external_id=str(job_id),
            location=city_text,
            city=city,
            country="PL",
            region=Region.EU,
            work_mode=work_mode,
            remote=True if work_mode is WorkMode.REMOTE else None,
            description=description,
            salary=salary,
            posted_at=posted_at,
            date_source=date_source_for(None, posted_at)[1],
        )
