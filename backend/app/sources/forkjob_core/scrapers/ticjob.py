"""Ticjob (ticjob.es) — independent Spanish IT portal.

Verified 2026-08-08.

robots.txt disallows only `/*/legal`, `/*/disclaimer`, `/*/privacy` and
`/*/online-cv` — none of which this touches — and advertises the sitemap.

The sitemap route worked, as it did for Manfred and beBee: three per-language
sitemaps (`cat`, `eng`, `esp`), and posting URLs sit under `/{lang}/job/`.
Each posting page carries a full schema.org `JobPosting` in ld+json, so there
are no selectors here at all.

Two quirks, both already paid for elsewhere:

- **The JSON is technically invalid.** Ticjob emits raw newlines inside its
  JSON strings. Browsers accept it; a strict parse throws the posting away
  over a line break. `schemaorg.ld_blocks` parses with `strict=False`.
- **`identifier` is the company, not the posting** — the same trap JobFluent
  set: `{name: "S&M Services", value: "4501"}` is the employer and its id, so
  every posting from one company would collide on
  `UNIQUE(source, external_id)`. The id comes from the URL instead.

`datePosted` is a real publish date, so `date_source` is `employer`.
`addressCountry` is absent — the site is Spain-only, so ES is assumed and the
assumption is stated rather than hidden.
"""

from __future__ import annotations

import re
from typing import Any

from ..models import Job, Layer, Region, WorkMode, date_source_for
from ..normalize import html_to_text, parse_datetime, sitemap_locations
from .base import ScraperBase, ScraperError, ScraperHttpClient
from .schemaorg import find_type, ld_blocks, organisation_name, place, schema_job, text

BASE_URL = "https://ticjob.es"
SITEMAP_URL = "https://www.ticjob.es/{lang}/sitemap.xml"

#: English first — the postings themselves are mostly Spanish either way, but
#: the English sitemap is the one that was verified.
DEFAULT_LANGUAGES = ("eng",)
DEFAULT_MAX_OFFERS = 40

#: Posting URLs look like /{lang}/job/{slug}/{id}
_JOB_URL_RE = re.compile(r"/(?:eng|esp|cat)/job/[^/]+/(\d+)/?$")


class TicjobScraper(ScraperBase):
    source_key = "ticjob"
    label = "Ticjob"
    base_url = BASE_URL

    def __init__(
        self,
        config: Any = None,
        *,
        languages: tuple[str, ...] | list[str] = DEFAULT_LANGUAGES,
        max_offers: int = DEFAULT_MAX_OFFERS,
    ) -> None:
        super().__init__(config)
        self.languages = tuple(languages)
        self.max_offers = max_offers

    @property
    def scope(self) -> str:
        """Which slice this run asks for — see ScraperBase.scope."""
        return ",".join(sorted(self.languages))

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()
        pages_fetched = 0
        items_seen = 0
        cap_hit = False

        for lang in self.languages:
            if len(jobs) >= self.max_offers:
                cap_hit = True
                break
            try:
                xml = await client.get_html(SITEMAP_URL.format(lang=lang))
                pages_fetched += 1
            except ScraperError as exc:
                self.errors.append(str(exc))
                continue

            for url in parse_sitemap(xml):
                items_seen += 1
                if len(jobs) >= self.max_offers:
                    cap_hit = True
                    break
                if url in seen:
                    continue
                seen.add(url)
                try:
                    page = await client.get_html(url)
                    pages_fetched += 1
                except ScraperError as exc:
                    self.errors.append(str(exc))
                    continue
                job = self.parse_offer(page, url)
                if job is not None:
                    jobs.append(job)

        if len(jobs) >= self.max_offers:
            cap_hit = True

        stop_reason = "max_offers_reached" if cap_hit else "exhausted"
        self.record_telemetry(
            items_seen=items_seen,
            items_returned=len(jobs),
            pages_fetched=pages_fetched,
            page_limit=None,
            result_limit=self.max_offers,
            cap_hit=cap_hit,
            stop_reason=stop_reason,
            partial_reason="max_offers_reached" if cap_hit else None,
        )
        return jobs

    # -- pure parsing -------------------------------------------------------

    def parse(self, html: str) -> list[Job]:
        """Every JobPosting on a page. Drives `--mock` and the offline tests."""
        job = self.parse_offer(html, BASE_URL)
        return [job] if job is not None else []

    def parse_offer(self, html: str, url: str) -> Job | None:
        posting = find_type(ld_blocks(html), "JobPosting")
        if posting is None:
            return None
        return self.build_job(posting, url)

    def build_job(self, posting: dict[str, Any], url: str) -> Job | None:
        title = text(posting.get("title"))
        if not title:
            return None

        city, country = place(posting.get("jobLocation"))
        # The site is Spain-only and never sets addressCountry; saying so here
        # beats leaving every posting regionless.
        country = country or "ES"

        posted_at = parse_datetime(posting.get("datePosted"))
        description = html_to_text(posting.get("description"))

        return schema_job(posting,
            url=url,
            source=self.source,
            layer=Layer.B,
            company=organisation_name(posting.get("hiringOrganization")) or "?",
            title=title,
            external_id=external_id_from_url(url),
            location=city,
            city=city,
            country=country,
            region=Region.EU,
            # The feed carries no remote flag; the description is the only hint
            # and normalize.py already reads it conservatively.
            work_mode=WorkMode.UNKNOWN,
            department=posting.get("employmentType") or None,
            description=description,
            language=None,
            posted_at=posted_at,
            date_source=date_source_for(posted_at)[1],
        )


def parse_sitemap(xml: str) -> list[str]:
    """Posting URLs from a language sitemap, ignoring category pages."""
    return [u for u in sitemap_locations(xml) if _JOB_URL_RE.search(u)]


def external_id_from_url(url: str) -> str | None:
    """Posting id from the URL.

    Deliberately not the ld+json `identifier`, which is the *company* id — the
    same trap JobFluent set, where trusting it collided every posting from one
    employer onto a single row.
    """
    match = _JOB_URL_RE.search(url or "")
    return match.group(1) if match else None
