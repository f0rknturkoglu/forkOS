"""WeAreDevelopers (wearedevelopers.com) — European developer jobs.

Verified 2026-08-08 against the remote listing page.

robots.txt disallows only `devjobsatBot` and advertises three sitemaps, so this
is about as permissive as a site gets.

**The sitemap is a trap and was checked first.** `sitemap-jobs.xml` sounds like
the answer; it holds 66,335 URLs and not one is a posting. Every entry is a
category or location facet — `/jobs/ls/austria/vienna`, `/jobs/s/php`. So the
listing page is parsed instead, with selectors taken from a captured page:

    article.wad4-job-card
      .wad4-job-card__title        title
      .wad4-job-card__link         /companies/<cid>/<company>/<jid>/<slug>
      .wad4-job-card__info         company + location together
      .wad4-job-card__info--light  location on its own
      .wad4-common-chip__label     "Remote", "€70-100K", "Senior", "TypeScript"

The chips are the reason this source is worth having. One card carried
work mode, a salary band, a seniority level and the tech stack, all as
discrete labels rather than buried in prose. Seniority and salary are pulled
out into their own fields; the rest goes to the description where the scorer's
skill rules read it.

The card carries no date at all, so `date_source` is `discovered` and the
posting never looks stale on evidence that does not exist.
"""

from __future__ import annotations

import re
from typing import Any

from selectolax.parser import HTMLParser, Node

from ..geo import country_from_name, region_for
from ..models import DateSource, Job, Layer, Region, WorkMode
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError

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
    ) -> None:
        super().__init__(config)
        self.queries = tuple(queries)

    @property
    def scope(self) -> str:
        """Which slice this run asks for — see ScraperBase.scope."""
        return ",".join(sorted(q or "all" for q in self.queries))

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()

        for query in self.queries:
            url = f"{LISTING_URL}?{query}" if query else LISTING_URL
            try:
                html = await client.get_html(url)
            except ScraperPermanentError:
                continue

            for job in self.parse(html):
                if job.url in seen:
                    continue
                seen.add(job.url)
                jobs.append(job)
        return jobs

    # -- pure parsing -------------------------------------------------------

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
