"""Web3.career (web3.career) — the largest Web3/blockchain job board.

    GET https://web3.career/remote-jobs?page=N

SSR table listing, verified 2026-08-18: HTTP 200 with an honest UA. Each row
is `tr.table_row[data-jobid]` carrying the title (`h2`), company (`h3`),
location, a **mutual `<time datetime="2026-08-18 19:08:41+07:00">`**, and a
salary range. robots.txt allows everything except `/metrics*`. Detail pages
also carry a schema.org JobPosting in ld+json, but the listing table already
has everything the scorer needs — reading it avoids one request per posting.

Why it matters for the earning case: Web3 companies almost never put staff on
a local payroll — they pay contractors through Deel/Remote.com or in crypto —
so the board is a dense source of the "employer of record" and crypto wording
the scoring rules look for. The salary column also states USD ranges outright.

Field notes from the live response:
- `data-jobid` on the row is the external_id; the detail URL is
  `/<slug>/<jobid>`.
- The `<time datetime>` is a real publish timestamp → date_source is
  `employer`.
- The salary cell holds text like "$70k - $90k".
- The title h2 is a link to the detail page.
"""

from __future__ import annotations

from typing import Any

from selectolax.parser import HTMLParser, Node

from ..models import DateSource, Job, Layer, Region, WorkMode
from ..normalize import parse_datetime
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError

LISTING_URL = "https://web3.career/remote-jobs"
DEFAULT_MAX_PAGES = 3

ROW = "tr.table_row"


class Web3CareerScraper(ScraperBase):
    source_key = "web3career"
    label = "Web3.career"
    base_url = "https://web3.career"

    def __init__(self, config: Any = None, *, max_pages: int = DEFAULT_MAX_PAGES) -> None:
        super().__init__(config)
        self.max_pages = max_pages

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()
        for page in range(1, self.max_pages + 1):
            url = LISTING_URL if page == 1 else f"{LISTING_URL}?page={page}"
            try:
                html = await client.get_html(url)
            except ScraperPermanentError:
                break
            page_jobs = self.parse(html)
            if not page_jobs:
                break
            fresh = [j for j in page_jobs if j.external_id not in seen]
            seen.update(j.external_id for j in fresh if j.external_id)
            jobs.extend(fresh)
            if not fresh:
                break
        return jobs

    def parse(self, html: str) -> list[Job]:
        """Pure: listing HTML in, Jobs out."""
        jobs: list[Job] = []
        for row in HTMLParser(html or "").css(ROW):
            job = self.build_job(row)
            if job is not None:
                jobs.append(job)
        return jobs

    def build_job(self, row: Node) -> Job | None:
        job_id = (row.attributes.get("data-jobid") or "").strip()
        if not job_id:
            return None

        link = row.css_first("a[href]")
        href = (link.attributes.get("href") if link else None) or ""
        if not href:
            return None
        url = href if href.startswith("http") else f"{self.base_url}{href}"

        h2 = row.css_first("h2")
        title = h2.text(strip=True) if h2 else ""
        if not title:
            return None

        h3 = row.css_first("h3")
        company = h3.text(strip=True) if h3 else "?"

        # Location: the row's location span, else the "Remote" badge.
        loc_node = row.css_first(".job-location-mobile span:last-child")
        location = loc_node.text(strip=True) if loc_node else None

        # The <time datetime> is a real publish timestamp.
        time_node = row.css_first("time[datetime]")
        posted_at = None
        if time_node is not None:
            posted_at = parse_datetime(time_node.attributes.get("datetime"))

        salary_node = row.css_first(".cell-salary p")
        salary = salary_node.text(strip=True) if salary_node else None

        work_mode = WorkMode.UNKNOWN
        if location and "remote" in location.lower() or "remote" in (title or "").lower():
            work_mode = WorkMode.REMOTE

        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=company,
            title=title,
            external_id=job_id,
            location=location,
            country=None,  # "Remote" or a city without a resolvable country
            region=Region.UNKNOWN,
            work_mode=work_mode,
            remote=True if work_mode is WorkMode.REMOTE else None,
            salary=salary,
            posted_at=posted_at,
            date_source=DateSource.EMPLOYER if posted_at else DateSource.DISCOVERED,
        )
