"""WeAreDevelopers (wearedevelopers.com) — European developer jobs.

Batch 3 (2026-10-01): legacy HTML selectors no longer match the public listing.
The site's advertised public Markdown mirrors provide listing identities,
absolute board dates, specific apply links and bounded job-specific details.
Historical HTML parsing remains only for offline replay of old fixtures.
Publication is a board timestamp; remote availability alone is not global scope.
"""

from __future__ import annotations

import html as html_lib
import re
from contextlib import suppress
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit

from selectolax.parser import HTMLParser, Node

from ..geo import country_from_name, region_for
from ..models import DateSource, Job, Layer, Region, WorkMode, canonical_url
from ..normalize import parse_location
from ..rich_text import enrich, merge_descriptions
from .detail_evidence import richness_metadata
from .base import ScrapeBatch, ScraperBase, ScraperError, ScraperHttpClient, ScraperPermanentError

BASE_URL = "https://www.wearedevelopers.com"
LISTING_URL = "https://www.wearedevelopers.com/jobs"

CARD = "article.wad4-job-card"
TITLE = ".wad4-job-card__title"
LINK = ".wad4-job-card__link"
INFO = ".wad4-job-card__info"
INFO_LIGHT = ".wad4-job-card__info--light"
CHIP = ".wad4-common-chip__label"

#: The site lists postings under two URL shapes: its own companies' pages and
#: externally-sourced ones. Matching only the first left every external
#: posting without an id, which would have made them collide on the URL hash
#: instead of their real identifier.
#:   /companies/<company_id>/<company-slug>/<job_id>/<job-slug>
#:   /jobs/ext/<job_id>/<job-slug>
_ID_RE = re.compile(r"/companies/\d+/[^/]+/(\d+)/|/jobs/ext/(\d+)/")

#: Chip vocabularies. Anything unrecognised is kept as a skill tag.
_WORK_MODES = {
    "remote": WorkMode.REMOTE,
    "fully remote": WorkMode.REMOTE,
    "hybrid": WorkMode.HYBRID,
    "on-site": WorkMode.ONSITE,
    "onsite": WorkMode.ONSITE,
    "office": WorkMode.ONSITE,
}
_SENIORITY = {"junior", "medior", "mid", "senior", "lead", "principal", "intern", "entry"}
_SALARY_RE = re.compile(r"^[€$£]\s?\d")


class WeAreDevelopersScraper(ScraperBase):
    source_key = "wearedevelopers"
    label = "WeAreDevelopers"
    base_url = BASE_URL

    def __init__(
        self,
        config: Any = None,
        *,
        queries: tuple[str, ...] | list[str] = ("remote=true", ""),
        max_pages: int = 2,
        detail_budget: int = 10,
    ) -> None:
        super().__init__(config)
        normalized = []
        for query in queries:
            params = dict(parse_qsl(query))
            if params.pop("remote", None) == "true":
                params.setdefault("q", "remote")  # advertised search, not an unsupported strict filter
            params.setdefault("country", "all")  # avoid IP-derived country defaults
            normalized.append(urlencode(params))
        self.queries = tuple(dict.fromkeys(normalized))
        self.max_pages = max(1, int(max_pages))
        self.detail_budget = max(0, int(detail_budget))

    @property
    def scope(self) -> str:
        """Which slice this run asks for — see ScraperBase.scope."""
        return ",".join(sorted(q or "all" for q in self.queries))

    async def scrape(self, client: ScraperHttpClient) -> ScrapeBatch:
        jobs, errors, seen, visited = [], [], set(), set()
        requests = pages = details = 0
        cap = False
        for query in self.queries:
            url = LISTING_URL + ".md" + ("?" + query if query else "?country=all")
            for page in range(self.max_pages):
                requests += 1
                try:
                    if url in visited:
                        raise ScraperPermanentError("wearedevelopers: repeated cursor")
                    visited.add(url)
                    body = await client.get_html(url)
                    parsed = self.parse_markdown(body)
                    fresh = self.dedup_seen(seen, parsed)
                    if parsed and not fresh and page:
                        raise ScraperPermanentError("wearedevelopers: repeated page identities")
                    jobs.extend(fresh)
                    pages += 1
                    next_match = re.search(r"\[Next page\]\((https://[^)]+)\)", body)
                    if not next_match:
                        break
                    next_url = html_lib.unescape(next_match.group(1))
                    if urlsplit(next_url).netloc != urlsplit(BASE_URL).netloc or urlsplit(next_url).path != "/jobs":
                        raise ScraperPermanentError("wearedevelopers: foreign pagination")
                    url = next_url.replace("/jobs?", "/jobs.md?", 1)
                    if page + 1 == self.max_pages:
                        cap = True
                except ScraperError as exc:
                    errors.append(str(exc))
                    break
        listing_errors = list(errors)
        for job in jobs[:self.detail_budget]:
            requests += 1
            try:
                body = await client.get_html(job.url + ".md")
                mirror = re.search(r"^> Markdown version of .*?\]\((https://[^)]+)\)", body)
                if not mirror or canonical_url(mirror.group(1)) != canonical_url(job.url):
                    raise ScraperPermanentError("wearedevelopers: mismatched detail identity")
                if "## About the Role" not in body and "## Description" not in body:
                    raise ScraperPermanentError("wearedevelopers: unrecognized detail")
                prose = re.split(r"\n## Related (?:Videos|Articles)", body, maxsplit=1)[0]
                prose = prose[prose.find("\n## ") + 1:]
                fields = dict(re.findall(r"^- \*\*([^*]+):\*\* (.+)$", body, re.M))
                job.description = merge_descriptions(job.description, enrich(prose, self.source, {"Technologies": fields.get("Skills"), "Application URL": fields.get("Apply")}))
                details += 1
            except ScraperError as exc:
                errors.append("detail: " + str(exc))
        richness = richness_metadata(len(jobs), details, self.detail_budget, errors[len(listing_errors):])
        telemetry = self.record_telemetry(items_seen=len(jobs), items_returned=len(jobs), pages_fetched=pages,
            page_limit=self.max_pages * len(self.queries), cap_hit=cap,
            stop_reason="page_limit_reached" if cap else "listing_request_failed" if listing_errors else "exhausted",
            partial_reason="; ".join(listing_errors + (["page_limit_reached"] if cap else [])) or None,
            metadata={"transport": "public_markdown", "requests": requests, "listing_pages": pages, "details_succeeded": details, "detail_budget": self.detail_budget, "listing_complete": not cap and not listing_errors, **richness})
        return ScrapeBatch(jobs, errors, requests, pages + details, telemetry)

    def parse_markdown(self, body):
        if "# Developer Jobs" not in body or not re.search(r"\d+ jobs found", body):
            raise ScraperPermanentError("wearedevelopers: missing public markdown schema")
        jobs = []
        for section in re.split(r"^## ", body, flags=re.M)[1:]:
            title = section.splitlines()[0].strip()
            fields = dict(re.findall(r"^- \*\*([^*]+):\*\* (.+)$", section, re.M))
            link = re.search(r"\[View job\]\((https://[^)]+)\)", section)
            apply = re.search(r"\[Apply\]\((https://[^)]+)\)", section)
            if not link or not fields.get("Company"):
                continue
            url = html_lib.unescape(link.group(1))
            identity = re.fullmatch(r"/jobs/(ext/)?(\d+)-[^/]+", urlsplit(url).path)
            if not identity or urlsplit(url).netloc != urlsplit(BASE_URL).netloc:
                continue
            location = fields.get("Location")
            info = parse_location((location or "").replace(" (Remote available)", ""))
            if location and "Remote available" in location:
                info.work_mode = WorkMode.UNKNOWN  # flexibility is not guaranteed fully remote
            posted = None
            with suppress(ValueError):
                posted = datetime.strptime(fields.get("Published", ""), "%B %d, %Y").replace(tzinfo=UTC)
            jobs.append(Job.build(url=url, source=self.source, layer=Layer.B,
                company=fields["Company"], title=title, external_id=identity.group(2),
                location=location, country=info.country, city=info.city, region=info.region, work_mode=info.work_mode,
                salary=fields.get("Salary"), posted_at=posted, date_source=DateSource.UPDATED if posted else DateSource.DISCOVERED,
                description=enrich(None, self.source, {"Experience level": fields.get("Experience"), "Employment type": fields.get("Contract"), "Remote scope": location if location and "Remote" in location else None, "Application URL": html_lib.unescape(apply.group(1)) if apply else None, "Source authority": "meta" if identity.group(1) else "native"})))
        if not jobs and not re.search(r"\b0 jobs found\b", body):
            raise ScraperPermanentError("wearedevelopers: malformed nonempty markdown listing")
        return jobs

    def parse(self, html: str) -> list[Job]:
        """Pure: listing HTML in, Jobs out. Drives `--mock` and the tests."""
        jobs: list[Job] = []
        for card in HTMLParser(html or "").css(CARD):
            job = self.build_job(card)
            if job is not None:
                jobs.append(job)
        return jobs

    def build_job(self, card: Node) -> Job | None:
        title_node = card.css_first(TITLE)
        title = title_node.text(strip=True) if title_node else ""
        link = card.css_first(LINK)
        href = (link.attributes.get("href") if link else None) or ""
        if not title or not href:
            return None

        url = href if href.startswith("http") else f"{BASE_URL}{href}"
        match = _ID_RE.search(href)
        external_id = next((g for g in match.groups() if g), None) if match else None

        company, location = _company_and_location(card)
        country = _country(location)

        work_mode, seniority, salary, skills = _read_chips(card)

        parts = []
        if seniority:
            parts.append(f"Seniority: {seniority}")
        if skills:
            parts.append("Skills: " + ", ".join(skills))
        description = "\n\n".join(parts) or None

        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=company or "?",
            title=title,
            external_id=external_id,
            location=location,
            city=_city(location),
            country=country,
            region=region_for(country) if country else Region.UNKNOWN,
            work_mode=work_mode,
            remote=True if work_mode is WorkMode.REMOTE else None,
            department=", ".join(skills[:3]) or None,
            description=description,
            salary=salary,
            # The card carries no date, and inventing one would make every
            # posting look fresh forever.
            posted_at=None,
            date_source=DateSource.DISCOVERED,
        )


def _company_and_location(card: Node) -> tuple[str | None, str | None]:
    """Split the info block, which runs company and location together.

    `.wad4-job-card__info` reads "SunhatKöln, Germany" while
    `.wad4-job-card__info--light` holds just "Köln, Germany", so the company is
    what remains once the location is removed.
    """
    info_node = card.css_first(INFO)
    light_node = card.css_first(INFO_LIGHT)
    info = info_node.text(strip=True) if info_node else ""
    location = light_node.text(strip=True) if light_node else ""

    company = info[: -len(location)] if location and info.endswith(location) else info
    return (company.strip() or None), (location.strip() or None)


def _read_chips(card: Node) -> tuple[WorkMode, str | None, str | None, list[str]]:
    """Sort the chips into work mode, seniority, salary and skills."""
    work_mode = WorkMode.UNKNOWN
    seniority: str | None = None
    salary: str | None = None
    skills: list[str] = []

    for chip in card.css(CHIP):
        label = chip.text(strip=True)
        if not label:
            continue
        low = label.lower()
        if low in _WORK_MODES:
            work_mode = _WORK_MODES[low]
        elif low in _SENIORITY:
            seniority = label
        elif _SALARY_RE.match(label):
            salary = label
        else:
            skills.append(label)
    return work_mode, seniority, salary, skills


def _country(location: Any) -> str | None:
    if not isinstance(location, str) or not location.strip():
        return None
    return country_from_name(location.split(",")[-1].strip())


def _city(location: Any) -> str | None:
    if not isinstance(location, str) or "," not in location:
        return None
    return location.split(",")[0].strip() or None
