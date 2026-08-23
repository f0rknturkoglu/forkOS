"""GulfTalent (gulftalent.com) — Middle East job board.

Verified 2026-08-09.

Listing pages are server-rendered HTML with job cards at
``https://www.gulftalent.com/jobs/search?keyword=developer&sort=d``.
Each card links to a detail page that carries a ld+json schema.org
JobPosting with ``datePosted`` (real publish date → ``date_source`` is
``employer``), ``hiringOrganization``, ``jobLocation`` with structured
``PostalAddress``, ``description``, ``employmentType``, ``industry``,
``validThrough``, ``directApply`` and ``identifier``.

robots.txt: ``User-agent: * / Allow: /``. Only AI crawlers are blocked.
Sitemap at ``/sitemap.xml`` indexes 30000 category URLs across 7 listing
sitemaps — detail page URLs are not in the sitemap, so this scraper
walks the search page instead, capped at ``max_offers`` newest-first.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urljoin

from ..geo import country_from_name, region_for
from ..models import DateSource, Job, Layer, Region, WorkMode
from ..normalize import html_to_text, parse_datetime
from .base import ScraperBase, ScraperConfig, ScraperHttpClient
from .schemaorg import find_type, ld_blocks, organisation_name, place, text

BASE_URL = "https://www.gulftalent.com"
SEARCH_URL = f"{BASE_URL}/jobs/search"

DEFAULT_KEYWORDS = ("developer", "software engineer")
DEFAULT_MAX_OFFERS = 60
#: The listing page has no age filter; we filter by lastmod in the parser.
DEFAULT_MAX_AGE_DAYS = 60
#: 30 cards per listing page.
CARDS_PER_PAGE = 30

#: A job card on the search page. Extract the URL and skip the rest —
#: the detail page ld+json has everything.
_JOB_HREF_RE = re.compile(r'href="(/mobile/[^"]+/jobs/[^"]+-\d+)"')


@dataclass(slots=True)
class _Card:
    url: str = ""
    job_id: str = ""


class GulfTalentScraper(ScraperBase):
    source_key = "gulftalent"
    label = "GulfTalent"
    base_url = BASE_URL

    def __init__(
        self,
        config: ScraperConfig | None = None,
        *,
        keywords: tuple[str, ...] | list[str] = DEFAULT_KEYWORDS,
        max_offers: int = DEFAULT_MAX_OFFERS,
        max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    ) -> None:
        super().__init__(config)
        self.keywords = tuple(keywords)
        self.max_offers = max_offers
        self.max_age_days = max_age_days

    @property
    def scope(self) -> str:
        return ",".join(sorted(self.keywords))

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()
        cutoff = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

        for keyword in self.keywords:
            cards = await self._fetch_listing(client, keyword)
            for card in cards:
                if card.job_id in seen:
                    continue
                if len(jobs) >= self.max_offers:
                    break
                seen.add(card.job_id)

                try:
                    html = await client.get_html(card.url)
                except Exception:
                    continue  # One dead detail page must not sink the whole run.

                for job in self._parse_detail(html, card.url, cutoff):
                    jobs.append(job)
                    if len(jobs) >= self.max_offers:
                        break

                # Be polite between detail pages — robots.txt has no Crawl-delay,
                # but the host's listing is heavy enough to warrant a gentle pace.
                await asyncio.sleep(1.0)

            if len(jobs) >= self.max_offers:
                break

        return jobs

    # -- listing ---------------------------------------------------------------

    async def _fetch_listing(self, client: ScraperHttpClient, keyword: str) -> list[_Card]:
        """Walk the search page and collect job card URLs."""
        cards: list[_Card] = []
        page = 1
        max_pages = (self.max_offers // CARDS_PER_PAGE) + 2

        while page <= max_pages:
            url = f"{SEARCH_URL}?keyword={keyword.replace(' ', '+')}&sort=d&page={page}"
            try:
                html = await client.get_html(url)
            except Exception:
                break

            page_cards = self._parse_listing(html, BASE_URL)
            if not page_cards:
                break

            seen_on_page: set[str] = {c.job_id for c in cards}
            new_cards = [c for c in page_cards if c.job_id not in seen_on_page]
            if not new_cards:
                break

            cards.extend(new_cards)
            page += 1

        return cards

    @staticmethod
    def _parse_listing(html: str, base_url: str) -> list[_Card]:
        cards: list[_Card] = []
        for m in _JOB_HREF_RE.finditer(html):
            href = m.group(1)
            # ID is the trailing number before the closing quote.
            job_id = href.rsplit("-", 1)[-1]
            if job_id.isdigit():
                cards.append(
                    _Card(
                        url=urljoin(base_url, href),
                        job_id=job_id,
                    )
                )
        return cards

    # -- detail ----------------------------------------------------------------

    def _parse_detail(self, html: str, url: str, cutoff: datetime) -> list[Job]:
        """Parse a detail page for schema.org JobPosting blocks."""
        posting = find_type(ld_blocks(html), "JobPosting")
        if posting is None:
            return []
        job = self._build_job(posting, url, cutoff)
        return [job] if job is not None else []

    def _build_job(self, posting: dict[str, Any], url: str, cutoff: datetime) -> Job | None:
        title = text(posting.get("title"))
        if not title:
            return None

        # Company — use the schema.org helper that unescapes HTML entities.
        company = organisation_name(posting.get("hiringOrganization")) or "?"

        # Location via the shared helper: returns (city, ISO country).
        city, country_code = place(posting.get("jobLocation"))
        # `place()` does naive [:2] on the country name, which is wrong for
        # multi-letter codes (e.g. Bahrain → BA instead of BH). Resolve properly.
        country = country_code
        if city and not country:
            # Fall back: resolve country from the city name.
            country = country_from_name(city)
        loc_str = ", ".join(p for p in (city, country) if p) or None

        # Work mode: GulfTalent is mostly onsite postings.
        work_mode = WorkMode.ONSITE if loc_str else WorkMode.UNKNOWN

        # Description
        raw_desc = posting.get("description")
        desc_html = str(raw_desc) if isinstance(raw_desc, str) else None
        description = html_to_text(desc_html)

        # Date
        posted_raw = posting.get("datePosted")
        posted_at = parse_datetime(str(posted_raw)) if posted_raw else None

        # Age filter: newer postings first.
        if posted_at and posted_at < cutoff - timedelta(days=self.max_age_days):
            return None

        # ID
        identifier = posting.get("identifier") or {}
        external_id: str | None = None
        if isinstance(identifier, dict):
            external_id = text(identifier.get("value"))

        # Employment type
        emp_type = posting.get("employmentType")
        if isinstance(emp_type, list):
            emp_types = [str(t).strip() for t in emp_type if t]
        elif isinstance(emp_type, str):
            emp_types = [emp_type.strip()]
        else:
            emp_types = []

        # Enrich description with extras the scorer can read.
        extra_parts: list[str] = []
        if emp_types:
            extra_parts.append(f"Employment: {', '.join(emp_types)}")
        industry = posting.get("industry")
        if isinstance(industry, str) and industry.strip():
            extra_parts.append(f"Industry: {industry.strip()}")

        if extra_parts and description:
            description = description + "\n" + "\n".join(extra_parts)
        elif extra_parts:
            description = "\n".join(extra_parts)

        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=company,
            title=title,
            external_id=external_id,
            location=loc_str,
            city=city,
            country=country,
            region=region_for(country) if country else Region.UNKNOWN,
            work_mode=work_mode,
            description=description,
            posted_at=posted_at,
            date_source=DateSource.EMPLOYER if posted_at else DateSource.DISCOVERED,
        )
