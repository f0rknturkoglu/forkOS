"""Relocate.me — relocation & visa sponsorship job board.

    GET https://relocate.me/international-jobs[?page=N]

Every posting on this board comes with relocation support; that is the board's
entire premise, so the visa signal is stated at the source rather than guessed.

Two things the original selectors got wrong, both found against the live page:

* `/search` is a 301 to `/international-jobs`. The scraper followed it, landed
  on real HTML, and then matched nothing.
* The markup uses BEM (`jobs-list__job`, `job__title`, `job__company`), not the
  `.job-card` / `.listing-item` family that was being guessed at. There is no
  schema.org JobPosting on the listing page either.

Verified 2026-08-09: 20 cards per page.
"""

from __future__ import annotations

import re
from typing import Any

from selectolax.parser import HTMLParser

from ..geo import country_from_name, region_for
from ..models import DateSource, Job, Layer, Region, WorkMode
from .base import ScraperBase, ScraperError, ScraperHttpClient

BASE_URL = "https://relocate.me"
SEARCH_URL = "https://relocate.me/international-jobs"

#: Job URLs are /<country>/<city>/<company>/<title-slug>-<id>.
ID_SUFFIX = re.compile(r"-(\d+)$")


class RelocateMeScraper(ScraperBase):
    source_key = "relocateme"
    label = "Relocate.me"
    base_url = BASE_URL

    def __init__(self, config: Any = None, *, max_pages: int = 5) -> None:
        super().__init__(config)
        self.max_pages = max_pages

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()
        pages_fetched = 0
        items_seen = 0
        cap_hit = False

        for page in range(1, self.max_pages + 1):
            url = f"{SEARCH_URL}?page={page}" if page > 1 else SEARCH_URL
            try:
                html = await client.get_html(url)
            except ScraperError as exc:
                self.errors.append(str(exc))
                break
            pages_fetched += 1
            page_jobs = self.parse(html)
            items_seen += len(page_jobs)
            if not page_jobs:
                break
            fresh = self.dedup_seen(seen, page_jobs)
            jobs.extend(fresh)
            # Paging past the end re-serves the last page rather than an empty
            # one, so a page that adds nothing new is the real stop condition.
            if not fresh:
                break
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

    def parse(self, html: str) -> list[Job]:
        """Parse one listing page. Separate from fetching so it can be frozen."""
        jobs: list[Job] = []
        for card in HTMLParser(html).css(".jobs-list__job"):
            job = self._parse_card(card)
            if job is not None:
                jobs.append(job)
        return jobs

    def _parse_card(self, card) -> Job | None:
        link = card.css_first(".job__title a")
        if link is None:
            return None
        href = link.attributes.get("href") or ""
        if not href:
            return None
        url = href if href.startswith("http") else f"{BASE_URL}{href}"

        # The <b> holds the title; the text after it is "in <city>".
        bold = link.css_first("b")
        title = (bold.text(strip=True) if bold else link.text(strip=True)).strip()
        if not title:
            return None

        # Two .job__company blocks per card: the first is the country (or
        # "Remote"), the second is the employer.
        blocks = [b.text(strip=True) for b in card.css(".job__company")]
        blocks = [b for b in blocks if b]
        place = blocks[0] if blocks else ""
        company = blocks[1] if len(blocks) > 1 else "?"

        country_slug, city_slug = self._path_parts(href)
        remote = place.lower() == "remote" or country_slug == "remote"

        country = None if remote else country_from_name(place or country_slug)
        location = (
            "Remote"
            if remote
            else ", ".join(part for part in (self._titleise(city_slug), place) if part)
        )

        preview = card.css_first(".job__preview")
        description = preview.text(strip=True) if preview else ""
        if not remote:
            # Stated by the board, not inferred from the posting text.
            description = (
                "Relocation package and visa sponsorship offered (Relocate.me listing).\n\n"
                + description
            )

        external_id = None
        match = ID_SUFFIX.search(href)
        if match:
            external_id = match.group(1)

        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=company,
            title=title,
            external_id=external_id,
            location=location or None,
            country=country,
            region=region_for(country) if country else Region.UNKNOWN,
            work_mode=WorkMode.REMOTE if remote else WorkMode.ONSITE,
            remote=True if remote else None,
            description=description,
            date_source=DateSource.DISCOVERED,
        )

    @staticmethod
    def _path_parts(href: str) -> tuple[str, str]:
        parts = [p for p in href.split("/") if p]
        country = parts[0] if parts else ""
        city = parts[1] if len(parts) > 1 else ""
        return country, city

    @staticmethod
    def _titleise(slug: str) -> str:
        if not slug or slug == "remote":
            return ""
        return slug.replace("-", " ").title()
