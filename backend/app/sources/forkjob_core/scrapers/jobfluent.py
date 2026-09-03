"""JobFluent (jobfluent.com) — startup and scale-up tech jobs in Spain.

Verified 2026-08-08 against live pages.

robots.txt: `GPTBot`, `ChatGPT-User`, `ClaudeBot`, `CCBot` and `Bytespider`
each get a blanket `Disallow: /`. Those are AI *crawlers* — bulk indexers. The
`User-agent: *` block that covers this tool disallows only `/login`,
`/subscriptions*`, `/sessions*`, `/api/*`, `/track`, `/log_search` and the
`/*/external*` apply-redirect paths. None of those are touched here: listings
come from the advertised sitemap and postings from their own public pages, with
an honest `forkjob/0.1 (personal job search bot)` UA. `/api/*` is off limits
and is not used.

`__NEXT_DATA__` was the first thing tried, per the usual reflex — it is not a
Next.js site and there is no ld+json either. What it does have is schema.org
**microdata**, which is just as structured:

    <div itemscope itemtype="http://schema.org/JobPosting">
      <meta itemprop="datePosted" content="2026-07-27" />
      <span itemprop="title">Product Manager Junior</span>
      <span itemprop="addressLocality">Barcelona</span>
      <span itemprop="addressCountry">ES</span>
      <span itemprop="hiringOrganization">Deale</span>
      <span itemprop="skills">UX/UI, Product Management, Jira</span>

So no invented selectors: every field is addressed by its schema.org property
name.

`skills` is unusual and worth having — a curated, comma-separated list rather
than prose to be mined, which the scorer reads alongside the description.

One trap: the microdata `identifier` is **not** the posting id. It is the
company id (`{name: "Typeform", value: "9"}`), so every posting from one
company shares it. `external_id` comes from the URL hash instead — see
`_external_id`.

The sitemap splits by region: barcelona, madrid, valencia and **remote**.
"""

from __future__ import annotations

import re
from typing import Any

from selectolax.parser import HTMLParser, Node

from ..geo import region_for
from ..models import Job, Layer, Region, WorkMode, date_source_for
from ..normalize import html_to_text, parse_datetime, sitemap_locations
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError

BASE_URL = "https://www.jobfluent.com"
SITEMAP_URL = "https://www.jobfluent.com/sitemaps/jobs-{region}/offers-list.xml"

#: Sitemap regions. "remote" is a region in their scheme, not a filter.
DEFAULT_REGIONS = ("remote", "barcelona", "madrid", "valencia")
DEFAULT_MAX_OFFERS = 40

POSTING = '[itemtype*="JobPosting"]'


class JobFluentScraper(ScraperBase):
    source_key = "jobfluent"
    label = "JobFluent"
    base_url = BASE_URL

    def __init__(
        self,
        config: Any = None,
        *,
        regions: tuple[str, ...] | list[str] = DEFAULT_REGIONS,
        max_offers: int = DEFAULT_MAX_OFFERS,
    ) -> None:
        super().__init__(config)
        self.regions = tuple(regions)
        self.max_offers = max_offers

    @property
    def scope(self) -> str:
        """Which slice this run asks for — see ScraperBase.scope."""
        return ",".join(sorted(self.regions))

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()

        for region in self.regions:
            if len(jobs) >= self.max_offers:
                break
            try:
                xml = await client.get_html(SITEMAP_URL.format(region=region))
            except ScraperPermanentError:
                continue  # one region missing must not sink the rest

            for url in parse_offer_sitemap(xml):
                if len(jobs) >= self.max_offers:
                    break
                if url in seen:
                    continue
                seen.add(url)
                try:
                    page = await client.get_html(url)
                except ScraperPermanentError:
                    continue
                job = self.parse_offer(page, url, remote_hint=region == "remote")
                if job is not None:
                    jobs.append(job)
        return jobs

    # -- pure parsing -------------------------------------------------------

    def parse(self, html: str) -> list[Job]:
        """Every JobPosting on a page. Drives `--mock` and the offline tests."""
        tree = HTMLParser(html or "")
        jobs = []
        for card in tree.css(POSTING):
            job = self.build_job(card, BASE_URL)
            if job is not None:
                jobs.append(job)
        return jobs

    def parse_offer(self, html: str, url: str, *, remote_hint: bool = False) -> Job | None:
        card = HTMLParser(html or "").css_first(POSTING)
        if card is None:
            return None
        return self.build_job(card, url, remote_hint=remote_hint)

    def build_job(self, card: Node, url: str, *, remote_hint: bool = False) -> Job | None:
        title = _prop(card, "title")
        if not title:
            return None

        company = _prop(card, "hiringOrganization") or "?"
        city = _prop(card, "addressLocality")
        country = (_prop(card, "addressCountry") or "").upper()[:2] or None

        description = html_to_text(_prop_html(card, "description"))
        skills = _prop(card, "skills")
        if skills:
            # Keep the curated list next to the prose so the scorer sees both.
            description = f"Skills: {skills}\n\n{description or ''}".strip()

        posted_at = parse_datetime(_prop(card, "datePosted"))

        work_mode = WorkMode.UNKNOWN
        if remote_hint:
            work_mode = WorkMode.REMOTE
        elif city or country:
            work_mode = WorkMode.ONSITE

        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=company,
            title=title,
            external_id=_external_id(url),
            location=city,
            city=city,
            country=country,
            region=region_for(country) if country else Region.UNKNOWN,
            work_mode=work_mode,
            department=_prop(card, "occupationalCategory") or _prop(card, "industry"),
            description=description,
            posted_at=posted_at,
            date_source=date_source_for(posted_at)[1],
        )


def parse_offer_sitemap(xml: str) -> list[str]:
    """Posting URLs from an offers-list.xml."""
    return [u for u in sitemap_locations(xml) if "/jobs/" in u]


def _prop(node: Node, name: str) -> str | None:
    """Microdata value: @content wins, then the element's text."""
    found = node.css_first(f'[itemprop="{name}"]')
    if found is None:
        return None
    value = found.attributes.get("content") or found.attributes.get("datetime")
    if value:
        return value.strip() or None
    return found.text(strip=True) or None


def _prop_html(node: Node, name: str) -> str | None:
    found = node.css_first(f'[itemprop="{name}"]')
    return found.html if found is not None else None


#: Trailing hash in /jobs/<slug>-<hash>, e.g. ...-barcelona-cd010e
_URL_ID_RE = re.compile(r"-([0-9a-f]{6,})/?$", re.IGNORECASE)


def _external_id(url: str) -> str | None:
    """Stable posting id, taken from the URL.

    **Not** from the microdata `identifier`, which looks like a posting id but
    is the *company* id: Typeform's postings all report
    `{name: "Typeform", value: "9"}`. Using it made every posting from one
    company collide on `UNIQUE(source, external_id)` and overwrite each other —
    17 of 40 postings vanished on the first live run before this was caught.

    The URL hash is unique per posting and survives slug rewrites.
    """
    match = _URL_ID_RE.search(url or "")
    return match.group(1).lower() if match else None
