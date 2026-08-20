"""Kariyer.net — Turkey's largest white-collar job portal.

Verified 2026-08-08 against a live listing page.

robots.txt (checked 2026-08-08): `User-agent: *` disallows CV, profile,
application and settings paths — `/ozgecmis/*`, `/profil`, `/hesabim`,
`/basvuru-*`, `/filtre*` — none of which this scraper touches. Listing pages
under `/is-ilanlari/` are permitted, and the file advertises a sitemap. There
is no Claude- or AI-specific rule. Nothing here needs a login.

Why this one is unusually sturdy for an HTML source: each card carries its data
in **HTML attributes**, not in nested markup, so there is almost no selector
surface to break:

    <div data-test="ad-card"
         positionname="Kurumsal Satış Uzmanı"
         cityname="İstanbul(Asya)"  countryname="Türkiye"
         workmodeltext="İş Yerinde" worktypetext="Tam zamanlı"
         jobdatestatus="Updated"    time="1 gün"
         jobcode="RF-PA66130"       positionid="1127" companyid="5643"
         sectorname="Bilişim">
      <a data-test="ad-card-item" href="/is-ilani/…-4522282">
      <img data-test="company-image" alt="FULL COMPANY NAME">

All 25 attributes were present on 53/53 cards. `data-test` hooks are used
rather than styling classes because they survive redesigns.

The site states its own date provenance in `jobdatestatus`, which maps
directly onto our `date_source`: "Updated" means an edit timestamp and must not
be trusted as a publish date.
"""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Any

from selectolax.parser import HTMLParser, Node

from ..models import DateSource, Job, Layer, Region, WorkMode, utcnow
from ..normalize import html_to_text
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError

BASE_URL = "https://www.kariyer.net"
#: Listing path. Robots permits /is-ilanlari/; the keyword is a path segment.
SEARCH_URL = "https://www.kariyer.net/is-ilanlari/{keyword}"

DEFAULT_KEYWORDS = ("yazilim", "yazilim-muhendisi", "backend-developer", "frontend-developer")
DEFAULT_MAX_PAGES = 5

CARD = 'div[data-test="ad-card"]'
LINK = 'a[data-test="ad-card-item"]'
LOGO = 'img[data-test="company-image"]'

#: Trailing job id in /is-ilani/<slug>-<id>
_ID_RE = re.compile(r"-(\d+)/?$")

#: "1 gün", "10 saat", "3 hafta", "2 ay" — the card's own age label.
_AGE_RE = re.compile(r"(\d+)\s*(saniye|dakika|saat|gün|gun|hafta|ay|yıl|yil)", re.IGNORECASE)
_AGE_UNITS = {
    "saniye": timedelta(seconds=1),
    "dakika": timedelta(minutes=1),
    "saat": timedelta(hours=1),
    "gün": timedelta(days=1),
    "gun": timedelta(days=1),
    "hafta": timedelta(weeks=1),
    "ay": timedelta(days=30),
    "yıl": timedelta(days=365),
    "yil": timedelta(days=365),
}

_WORK_MODES = {
    "uzaktan / remote": WorkMode.REMOTE,
    "uzaktan": WorkMode.REMOTE,
    "remote": WorkMode.REMOTE,
    "hibrit": WorkMode.HYBRID,
    "i̇ş yerinde": WorkMode.ONSITE,
    "iş yerinde": WorkMode.ONSITE,
    "is yerinde": WorkMode.ONSITE,
}

#: "İstanbul(Asya)" / "İstanbul(Avr.)" are one city as far as commuting goes.
_CITY_SUFFIX_RE = re.compile(r"\s*\([^)]*\)\s*$")


class KariyerNetScraper(ScraperBase):
    source_key = "kariyernet"
    label = "Kariyer.net"
    base_url = BASE_URL

    def __init__(
        self,
        config: Any = None,
        *,
        keywords: tuple[str, ...] | list[str] = DEFAULT_KEYWORDS,
        max_pages: int = DEFAULT_MAX_PAGES,
    ) -> None:
        super().__init__(config)
        self.keywords = tuple(keywords)
        self.max_pages = max_pages

    @property
    def scope(self) -> str:
        """Which slice this run asks for — see ScraperBase.scope."""
        return ",".join(sorted(self.keywords))

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()

        for keyword in self.keywords:
            for page in range(1, self.max_pages + 1):
                url = SEARCH_URL.format(keyword=keyword)
                if page > 1:
                    url = f"{url}?sayfa={page}"
                try:
                    html = await client.get_html(url)
                except ScraperPermanentError:
                    break  # blocked or gone — drop this keyword, keep the rest

                page_jobs = self.parse(html)
                if not page_jobs:
                    break  # ran past the last page

                fresh = [j for j in page_jobs if j.url not in seen]
                seen.update(j.url for j in fresh)
                jobs.extend(fresh)

                # A keyword search returns the same postings under several
                # terms; stop early once a page adds nothing new.
                if not fresh:
                    break
        return jobs

    def parse(self, html: str) -> list[Job]:
        """Pure: HTML in, Jobs out. Drives the offline tests and `--mock`."""
        tree = HTMLParser(html or "")
        jobs: list[Job] = []
        for card in tree.css(CARD):
            job = self._parse_card(card)
            if job is not None:
                jobs.append(job)
        return jobs

    def _parse_card(self, card: Node) -> Job | None:
        attrs = card.attributes
        title = (attrs.get("positionname") or "").strip()
        if not title:
            return None

        link = card.css_first(LINK)
        href = (link.attributes.get("href") if link else None) or ""
        if not href:
            return None
        url = href if href.startswith("http") else f"{BASE_URL}{href}"

        logo = card.css_first(LOGO)
        company = (logo.attributes.get("alt") if logo else None) or ""

        city_raw = (attrs.get("cityname") or "").strip()
        city = _CITY_SUFFIX_RE.sub("", city_raw) or None

        posted_at, date_source = _card_date(attrs)

        work_mode = _WORK_MODES.get((attrs.get("workmodeltext") or "").strip().lower(),
                                    WorkMode.UNKNOWN)

        # The card shows no description; the detail page is a second request
        # per posting and is deliberately not fetched. Scoring signals that
        # need prose (visa, language) simply stay silent for this source.
        summary = html_to_text(card.text(separator=" ", deep=True))

        match = _ID_RE.search(href)
        external_id = match.group(1) if match else (attrs.get("jobcode") or None)

        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=company.strip() or "?",
            title=title,
            external_id=external_id,
            location=city_raw or attrs.get("countryname"),
            city=city,
            country="TR" if (attrs.get("countryname") or "").lower().startswith("tür") else None,
            region=Region.TR if (attrs.get("countryname") or "").lower().startswith("tür")
            else Region.UNKNOWN,
            work_mode=work_mode,
            department=attrs.get("sectorname") or None,
            description=summary,
            language="tr",
            posted_at=posted_at,
            date_source=date_source,
        )


def _card_date(attrs: dict[str, str]) -> tuple[Any, DateSource]:
    """Turn the card's own age label into a timestamp and a provenance.

    `jobdatestatus` is the site telling us which it is: "Updated" means the
    posting was edited, not published, so it decays at half rate. Anything else
    ("Default") is treated as a publish date.
    """
    age = _parse_age(attrs.get("time"))
    if age is None:
        return None, DateSource.DISCOVERED

    status = (attrs.get("jobdatestatus") or "").strip().lower()
    source = DateSource.UPDATED if status == "updated" else DateSource.EMPLOYER
    return utcnow() - age, source


def _parse_age(label: str | None) -> timedelta | None:
    """"1 gün" -> 1 day. Returns None when the label says nothing usable."""
    if not label:
        return None
    match = _AGE_RE.search(label)
    if not match:
        return None
    amount = int(match.group(1))
    unit = _AGE_UNITS.get(match.group(2).lower())
    return unit * amount if unit else None
