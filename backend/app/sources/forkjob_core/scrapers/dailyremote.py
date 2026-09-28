"""DailyRemote (dailyremote.com) — worldwide remote jobs across categories.

    GET https://dailyremote.com/remote-jobs[?page=N]

SSR listing + SSR detail, verified 2026-08-18: HTTP 200 with an honest UA.
robots.txt disallows only `/apply/`. Each detail page carries a schema.org
JobPosting in ld+json with a real `datePosted` and a stable `identifier`
(`{"name": "<company>", "value": "<id>-<slug>"}`); the numeric part of the
URL is the external id.

Why it matters: a generalist worldwide-remote board with software, DevOps and
QA categories — a wide, cheap complement to the stack-specific sources.

Field notes:
- The detail page JSON-LD is the source of truth (title, company, datePosted,
  jobLocationType TELECOMMUTE, baseSalary when present).
- Salary is frequently zero/absent — do not invent one.
"""

from __future__ import annotations

import re
from typing import Any

from ..models import Job, Layer, WorkMode, date_source_for
from ..normalize import format_salary, html_to_text, parse_datetime
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError
from .schemaorg import find_type, ld_blocks, organisation_name, text

LISTING_URL = "https://dailyremote.com/remote-jobs"
BASE_URL = "https://dailyremote.com"
DEFAULT_MAX_PAGES = 2

#: Numeric id in /remote-job/<slug>-<id>
_ID_RE = re.compile(r"-(\d+)/?$")
_LINK_RE = re.compile(r'href="(/remote-job/[^"]+)"')


class DailyRemoteScraper(ScraperBase):
    source_key = "dailyremote"
    label = "DailyRemote"
    base_url = BASE_URL

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
            url = LISTING_URL if page == 1 else f"{LISTING_URL}?page={page}"
            try:
                html = await client.get_html(url)
            except ScraperPermanentError:
                break
            pages_fetched += 1
            urls = list(dict.fromkeys(_LINK_RE.findall(html)))
            if not urls:
                break
            items_seen += len(urls)
            for u in urls:
                detail_url = f"{BASE_URL}{u}"
                if detail_url in seen:
                    continue
                seen.add(detail_url)
                try:
                    detail_page = await client.get_html(detail_url)
                    pages_fetched += 1
                except ScraperPermanentError:
                    continue
                job = self.parse_offer(detail_page, detail_url)
                if job is not None:
                    jobs.append(job)
            if page == self.max_pages:
                cap_hit = True

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

    def parse_offer(self, html: str, url: str) -> Job | None:
        posting = find_type(ld_blocks(html), "JobPosting")
        if posting is None:
            return None
        title = text(posting.get("title"))
        if not title:
            return None
        company = organisation_name(posting.get("hiringOrganization")) or "?"

        location = _location_text(posting)
        work_mode = WorkMode.REMOTE
        if str(posting.get("jobLocationType") or "").upper() == "TELECOMMUTE":
            work_mode = WorkMode.REMOTE

        posted_at = parse_datetime(text(posting.get("datePosted")))
        salary = _salary(posting.get("baseSalary"))

        match = _ID_RE.search(url)
        external_id = match.group(1) if match else None

        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=company,
            title=title,
            external_id=external_id,
            location=location,
            work_mode=work_mode,
            remote=True,
            description=html_to_text(posting.get("description")),
            salary=salary,
            posted_at=posted_at,
            date_source=date_source_for(posted_at)[1],
        )


def _location_text(posting: dict[str, Any]) -> str | None:
    req = posting.get("applicantLocationRequirements")
    if isinstance(req, list):
        names = [c.get("name") for c in req if isinstance(c, dict) and c.get("name")]
        if names:
            return ", ".join(str(n) for n in names[:4])
    if isinstance(req, dict) and req.get("name"):
        return str(req["name"])
    return None


def _salary(sal: Any) -> str | None:
    if not isinstance(sal, dict):
        return None
    value = sal.get("value") or {}
    if isinstance(value, dict):
        low, high = value.get("minValue"), value.get("maxValue")
    else:
        low = high = None
    return format_salary(low, high, (sal.get("currency") or "").upper())
