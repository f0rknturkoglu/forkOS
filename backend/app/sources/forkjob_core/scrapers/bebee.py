"""beBee (bebee.com) — multi-country aggregator, schema.org all the way down.

Verified 2026-08-08 against live TR pages.

robots.txt is `Allow: /` **but disallows every search parameter**: `?q=`,
`?page=`, `?location=`, `?remote=`, `?salary=`, `?jobType=` and a dozen more.
So search and pagination are off the table. What is left, and what this uses:

  - country listing pages, no query string:  /{cc}/jobs  and  /{cc}/jobs/remote
  - individual posting pages, no query string

The sitemap is no help — all 2394 entries are category or salary pages, with
zero individual postings. So listings come from the page's own
`application/ld+json` `ItemList`, which carries 20 posting URLs per page.

That 20-per-page ceiling is the real constraint here: without `?page=` there is
no way to reach the 21st posting, and this scraper does not try. It is a
shallow, frequently-refreshed skim rather than a deep crawl.

Each posting page then carries a full schema.org `JobPosting`:

    title, datePosted, validThrough, employmentType, hiringOrganization.name,
    jobLocation.address.{addressLocality,addressCountry}, identifier.value,
    description

`datePosted` is a real publish date, so `date_source` is `employer`.
`addressCountry` is an ISO code, so the country needs no prose parsing at all.
"""

from __future__ import annotations

from typing import Any

from ..geo import country_code, region_for
from ..models import Job, Layer, Region, WorkMode, date_source_for
from ..normalize import html_to_text, parse_datetime, parse_location
from .base import ScraperBase, ScraperHttpClient
from .schemaorg import ld_blocks

BASE_URL = "https://bebee.com"
#: No query string on either — anything with `?` is disallowed by robots.
LISTING_PATHS = ("jobs", "jobs/remote")

DEFAULT_COUNTRIES = ("tr", "es")
DEFAULT_MAX_OFFERS = 40

#: Kept as a thin alias: the implementation is shared with Ticjob, which needs
#: `strict=False` for its raw newlines, and beBee benefits from the same
#: tolerance.
_ld_blocks = ld_blocks


class BebeeScraper(ScraperBase):
    source_key = "bebee"
    label = "beBee"
    base_url = BASE_URL

    def __init__(
        self,
        config: Any = None,
        *,
        countries: tuple[str, ...] | list[str] = DEFAULT_COUNTRIES,
        max_offers: int = DEFAULT_MAX_OFFERS,
    ) -> None:
        super().__init__(config)
        self.countries = tuple(c.lower() for c in countries)
        self.max_offers = max_offers

    @property
    def scope(self) -> str:
        """Which slice this run asks for — see ScraperBase.scope."""
        return ",".join(sorted(self.countries))

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()

        for country in self.countries:
            for path in LISTING_PATHS:
                if len(jobs) >= self.max_offers:
                    return jobs

                listing_url = f"{BASE_URL}/{country}/{path}"
                listing = await self.isolate(listing_url, lambda: client.get_html(listing_url))
                if listing is None:
                    continue  # one country blocked must not sink the rest

                remote_hint = path.endswith("remote")
                for url in self.parse_listing(listing):
                    if len(jobs) >= self.max_offers:
                        return jobs
                    if url in seen:
                        continue
                    seen.add(url)

                    page = await self.isolate(url, lambda: client.get_html(url))
                    if page is None:
                        continue
                    job = self.parse_offer(page, url, remote_hint=remote_hint)
                    if job is not None:
                        jobs.append(job)
        return jobs

    # -- pure parsing -------------------------------------------------------

    def parse_listing(self, html: str) -> list[str]:
        """Posting URLs from the page's ld+json ItemList (20 per page)."""
        urls: list[str] = []
        for block in _ld_blocks(html):
            if block.get("@type") != "ItemList":
                continue
            for item in block.get("itemListElement") or []:
                url = item.get("url") if isinstance(item, dict) else None
                if isinstance(url, str) and "/jobs/" in url:
                    urls.append(url)
        return urls

    def parse_offer(self, html: str, url: str, *, remote_hint: bool = False) -> Job | None:
        """Build a Job from a posting page's schema.org JobPosting."""
        posting = next((b for b in _ld_blocks(html) if b.get("@type") == "JobPosting"), None)
        if posting is None:
            return None
        return self.build_job(posting, url, remote_hint=remote_hint)

    def build_job(
        self, posting: dict[str, Any], url: str, *, remote_hint: bool = False
    ) -> Job | None:
        title = (posting.get("title") or "").strip()
        if not title:
            return None

        org = posting.get("hiringOrganization")
        company = (org.get("name") if isinstance(org, dict) else None) or "?"

        city, country = _place(posting.get("jobLocation"))
        description = html_to_text(posting.get("description"))

        region = region_for(country) if country else Region.UNKNOWN
        if country is None:
            # Fall back to prose only when the structured field was absent.
            info = parse_location(city, description=description)
            city, country, region = info.city or city, info.country, info.region

        work_mode = WorkMode.UNKNOWN
        if remote_hint or str(posting.get("jobLocationType", "")).upper() == "TELECOMMUTE":
            work_mode = WorkMode.REMOTE
        elif city or country:
            work_mode = WorkMode.ONSITE

        posted_at = parse_datetime(posting.get("datePosted"))

        identifier = posting.get("identifier")
        external_id = None
        if isinstance(identifier, dict):
            value = identifier.get("value")
            external_id = str(value) if value else None

        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=company.strip(),
            title=title,
            external_id=external_id,
            location=city,
            city=city,
            country=country,
            region=region,
            work_mode=work_mode,
            department=posting.get("employmentType") or None,
            description=description,
            posted_at=posted_at,
            date_source=date_source_for(posted_at)[1],
        )


def _place(node: Any) -> tuple[str | None, str | None]:
    """(city, ISO country) from a schema.org Place, or (None, None)."""
    if isinstance(node, list):
        node = node[0] if node else None
    if not isinstance(node, dict):
        return None, None
    address = node.get("address")
    if not isinstance(address, dict):
        return None, None
    city = address.get("addressLocality")
    country = address.get("addressCountry")
    if isinstance(country, dict):
        country = country.get("name")
    country = country_code(country) if isinstance(country, str) else None
    return (city.strip() if isinstance(city, str) else None), country
