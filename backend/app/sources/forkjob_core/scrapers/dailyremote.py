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

from selectolax.parser import HTMLParser

from ..models import Job, Layer, WorkMode, date_source_for
from ..normalize import format_salary, html_to_text, parse_datetime, parse_location
from ..rich_text import enrich, merge_descriptions
from .base import ScraperBase, ScraperError, ScraperHttpClient, ScraperPermanentError
from .schemaorg import job_posting_nodes, organisation_name, schema_job, text

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

    def __init__(self, config: Any = None, *, max_pages: int = DEFAULT_MAX_PAGES, detail_budget: int = 20) -> None:
        super().__init__(config)
        self.max_pages = max_pages
        self.detail_budget = max(0, int(detail_budget))

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        jobs, seen = [], set()
        pages = details = requests = 0
        cap = False
        for page in range(1, self.max_pages + 1):
            url = LISTING_URL if page == 1 else f"{LISTING_URL}?page={page}"
            try:
                requests += 1
                html = await client.get_html(url)
                cards = self.parse_listing(html)
            except ScraperError as exc:
                self.errors.append(str(exc))
                break
            pages += 1
            fresh = self.dedup_seen(seen, cards)
            if cards and not fresh:
                self.errors.append("dailyremote: repeated listing identities")
                break
            jobs.extend(fresh)
            if not cards:
                break
            if page == self.max_pages:
                cap = True
        for job in jobs[:self.detail_budget]:
            try:
                requests += 1
                body = await client.get_html(job.url)
                detail = self.parse_offer(body, job.url)
                if detail is None or detail.external_id != job.external_id:
                    raise ScraperPermanentError("dailyremote: invalid job-specific detail")
                job.description = merge_descriptions(job.description, detail.description, prefer_incoming=True)
                job.salary = detail.salary or job.salary
                if job.company == "?" and detail.company != "?":
                    job.company = detail.company
                details += 1
            except ScraperError as exc:
                self.errors.append("detail: " + str(exc))
        richness_partial = len(jobs) > details
        self.record_telemetry(items_seen=len(jobs), items_returned=len(jobs), pages_fetched=pages,
            page_limit=self.max_pages, cap_hit=cap or richness_partial,
            partial_reason="page_limit_reached" if cap else "detail_budget_or_failure" if richness_partial else None,
            stop_reason="page_limit_reached" if cap else "detail_budget_or_failure" if richness_partial else "exhausted",
            metadata={"requests": requests, "listing_pages": pages, "detail_requests": min(len(jobs), self.detail_budget), "details_succeeded": details, "detail_budget": self.detail_budget, "listing_complete": not cap and not any(not e.startswith("detail:") for e in self.errors), "richness_partial": richness_partial})
        return jobs

    def parse_listing(self, html: str) -> list[Job]:
        parser = HTMLParser(html)
        structured = {}
        for posting in job_posting_nodes(html):
            url = text(posting.get("url"))
            if url and url.startswith(BASE_URL + "/remote-job/"):
                structured[url] = self._posting(posting, url)
        jobs = []
        for card in parser.css(".lst-card__content"):
            link = card.css_first('.lst-card__title a[href^="/remote-job/"]')
            company = card.css_first(".lst-card__company")
            if link is None:
                continue
            url = BASE_URL + link.attributes["href"]
            match = _ID_RE.search(url)
            if not match:
                continue
            job = structured.get(url)
            if job is None:
                scope = card.css_first(".lst-pill[title]")
                location = scope.attributes.get("title") if scope else None
                info = parse_location(location)
                summary = card.css_first(".lst-card__summary")
                job = Job.build(url=url, source=self.source, layer=Layer.B,
                    company=company.text(strip=True) if company else "?", title=link.text(strip=True),
                    external_id=match.group(1), location=location, country=info.country,
                    work_mode=WorkMode.REMOTE, remote=True,
                    description=summary.text(separator=" ", strip=True) if summary else None)
            tags = [node.text(strip=True) for node in card.css(".lst-card__tags .lst-tag")]
            scope = card.css_first(".lst-pill[title]")
            pills = [node.text(separator=" ", strip=True).strip() for node in card.css(".lst-pill")]
            salary = next((v for v in pills if re.match(r"^[€$£]\s*\d", v)), None)
            job.salary = job.salary or salary  # Preserve rendered currency; no invented period.
            job.description = enrich(job.description, self.source, {"Technologies": ", ".join(tags), "Remote scope": scope.attributes.get("title") if scope else None, "Description coverage": "listing preview"})
            jobs.append(job)
        if not jobs and not parser.css_first("[data-empty-results], .jobs-search__no-results"):
            raise ScraperPermanentError("dailyremote: unrecognized listing schema")
        return jobs

    def parse_offer(self, html: str, url: str) -> Job | None:
        posting = next(iter(job_posting_nodes(html)), None)
        if posting is None:
            return None
        return self._posting(posting, url)

    def _posting(self, posting, url):
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

        return schema_job(posting,
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
