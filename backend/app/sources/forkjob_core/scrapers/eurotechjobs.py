"""EuroTechJobs (eurotechjobs.com) — tech roles across Europe.

Verified 2026-08-08 against the Spain listing page.

robots.txt names ClaudeBot, GPTBot, Bytespider and meta-externalagent with
`Disallow: /` — those are bulk AI crawlers — while leaving `User-agent: *`
completely open (`Disallow:` with no path). Same shape as JobFluent, which is
already enabled. This tool identifies honestly and is neither of those agents.

There is no structured data here: no `__NEXT_DATA__`, no ld+json, no
microdata, and the sitemap holds only articles and static pages. So this one
does need selectors, taken from a captured page rather than guessed:

    li.highlightedJobContainer   "Top Job" placements
    li.standardJobContainer      ordinary listings
      h3                         title
      a[href^="/job_display/"]   /job_display/<id>/<slug>
      .companyName               "Tesla"
      .location                  "Barcelona, Spain"
      .postedDate                "Posted 10 days ago"
      .badge                     role tags

Both container classes must be read. Taking only the standard ones would drop
every promoted posting, and taking only the highlighted ones would drop nearly
everything.

`postedDate` is relative prose ("Posted 10 days ago"), and the site gives no
absolute timestamp — so `date_source` is `updated`, not `employer`. It is a
real signal about age but not a publish date, and the tiered decay treats it
at half weight accordingly.
"""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Any

from selectolax.parser import HTMLParser, Node

from ..geo import country_from_name, region_for
from ..models import Job, Layer, Region, WorkMode, date_source_for, utcnow
from ..normalize import html_to_text
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError

BASE_URL = "https://www.eurotechjobs.com"
LISTING_URL = "https://www.eurotechjobs.com/jobs/{country}"

#: Target markets that the site actually has sections for.
DEFAULT_COUNTRIES = ("spain", "netherlands", "germany", "sweden", "ireland", "portugal")

CARDS = "li.highlightedJobContainer, li.standardJobContainer"
LINK = 'a[href^="/job_display/"]'

_ID_RE = re.compile(r"/job_display/(\d+)/")
#: "Posted 10 days ago", "Posted 3 hours ago", "Posted a month ago"
_AGE_RE = re.compile(r"(\d+|a|an)\s+(hour|day|week|month|year)s?\s+ago", re.IGNORECASE)
_AGE_UNITS = {
    "hour": timedelta(hours=1),
    "day": timedelta(days=1),
    "week": timedelta(weeks=1),
    "month": timedelta(days=30),
    "year": timedelta(days=365),
}


class EuroTechJobsScraper(ScraperBase):
    source_key = "eurotechjobs"
    label = "EuroTechJobs"
    base_url = BASE_URL

    def __init__(
        self,
        config: Any = None,
        *,
        countries: tuple[str, ...] | list[str] = DEFAULT_COUNTRIES,
    ) -> None:
        super().__init__(config)
        self.countries = tuple(c.lower() for c in countries)

    @property
    def scope(self) -> str:
        """Which slice this run asks for — see ScraperBase.scope."""
        return ",".join(sorted(self.countries))

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()

        for country in self.countries:
            try:
                html = await client.get_html(LISTING_URL.format(country=country))
            except ScraperPermanentError:
                continue  # one country page missing must not stop the rest

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
        for card in HTMLParser(html or "").css(CARDS):
            job = self.build_job(card)
            if job is not None:
                jobs.append(job)
        return jobs

    def build_job(self, card: Node) -> Job | None:
        heading = card.css_first("h3")
        title = heading.text(strip=True) if heading else ""
        link = card.css_first(LINK)
        href = (link.attributes.get("href") if link else None) or ""
        if not title or not href:
            return None

        url = href if href.startswith("http") else f"{BASE_URL}{href}"
        match = _ID_RE.search(href)

        location = _text(card, ".location")
        country = _country(location)

        badges = [b.text(strip=True) for b in card.css(".badge") if b.text(strip=True)]
        posted_at = _relative_date(_text(card, ".postedDate"))

        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=_text(card, ".companyName") or "?",
            title=title,
            external_id=match.group(1) if match else None,
            location=location,
            city=_city(location),
            country=country,
            region=region_for(country) if country else Region.UNKNOWN,
            # The card says nothing about remote work; the tags occasionally
            # do, and normalize.py reads those conservatively.
            work_mode=WorkMode.UNKNOWN,
            department=", ".join(badges[:3]) or None,
            description=html_to_text(card.text(separator=" ", deep=True)),
            posted_at=posted_at,
            # Relative prose, never an absolute publish date — so this decays
            # at half weight rather than being trusted as `employer`.
            date_source=date_source_for(None, posted_at)[1],
        )


def _text(card: Node, selector: str) -> str | None:
    node = card.css_first(selector)
    if node is None:
        return None
    return node.text(strip=True) or None


def _country(location: Any) -> str | None:
    """ "Barcelona, Spain" -> ES. The country is the last comma-separated part."""
    if not isinstance(location, str) or not location.strip():
        return None
    return country_from_name(location.split(",")[-1].strip())


def _city(location: Any) -> str | None:
    if not isinstance(location, str) or "," not in location:
        return None
    return location.split(",")[0].strip() or None


def _relative_date(value: Any) -> Any:
    """ "Posted 10 days ago" -> a timestamp. Returns None when unparseable."""
    if not isinstance(value, str):
        return None
    match = _AGE_RE.search(value)
    if not match:
        return None
    amount = 1 if match.group(1).lower() in ("a", "an") else int(match.group(1))
    unit = _AGE_UNITS.get(match.group(2).lower())
    return utcnow() - unit * amount if unit else None
