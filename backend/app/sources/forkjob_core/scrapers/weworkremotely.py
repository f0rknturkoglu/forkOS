"""We Work Remotely (weworkremotely.com) — public RSS feeds.

Verified 2026-08-08.

WWR publishes these feeds for exactly this purpose. Their own wording: "Anyone
can use the feed, all we ask is that you attribute the links back to We Work
Remotely." The stored `url` is that link.

robots.txt is `Allow: /` with only account, profile and admin paths disallowed
— none of which this touches.

**The category feeds do not nest.** "All Programming" is not a superset: it
returned 25 postings that appeared in none of the others, while Full-Stack
returned 123, DevOps 51, Back-End 29 and Front-End 16, all disjoint. Fetching
only the "all" feed would have collected 25 of 219 available postings. So every
relevant category is fetched and the results merged.

Feed shape, per item:

    title      "Gusto, Inc.: Retirement Implementation Specialist"
    region     "Anywhere in the World"
    category   "Full-Stack Programming"
    pubDate    RFC 822
    link       the WWR listing page

`title` packs the company and the role into one string separated by ": ", so it
is split rather than stored whole — otherwise every company name would end up
inside the job title and cluster matching across sources would never fire.

`pubDate` is a real publish date, so `date_source` is `employer`.
"""

from __future__ import annotations

from typing import Any
from xml.etree import ElementTree as ET

from ..geo import country_from_name, region_for
from ..models import Job, Layer, Region, WorkMode, date_source_for
from ..normalize import html_to_text, parse_rfc822
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError

BASE_URL = "https://weworkremotely.com"
FEED_URL = "https://weworkremotely.com/categories/{category}.rss"

#: Only the engineering categories. Design, sales, support and management are
#: published too and are deliberately left out.
DEFAULT_CATEGORIES = (
    "remote-programming-jobs",
    "remote-full-stack-programming-jobs",
    "remote-back-end-programming-jobs",
    "remote-front-end-programming-jobs",
    "remote-devops-sysadmin-jobs",
)

#: "Anywhere in the World" and friends are not countries.
_GLOBAL_REGIONS = {"anywhere in the world", "worldwide", "anywhere"}


class WeWorkRemotelyScraper(ScraperBase):
    source_key = "weworkremotely"
    label = "We Work Remotely"
    base_url = BASE_URL

    def __init__(
        self,
        config: Any = None,
        *,
        categories: tuple[str, ...] | list[str] = DEFAULT_CATEGORIES,
    ) -> None:
        super().__init__(config)
        self.categories = tuple(categories)

    @property
    def scope(self) -> str:
        """Which slice this run asks for — see ScraperBase.scope."""
        return ",".join(sorted(self.categories))

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()

        for category in self.categories:
            url = FEED_URL.format(category=category)
            xml = await self.isolate(url, lambda: client.get_html(url))
            if xml is None:
                continue  # one dead category must not stop the rest
            jobs.extend(self.dedup_seen(seen, self.parse(xml)))
        return jobs

    # -- pure parsing -------------------------------------------------------

    def parse(self, xml: str) -> list[Job]:
        """Pure: feed XML in, Jobs out. Drives `--mock` and the offline tests."""
        try:
            root = ET.fromstring(xml or "")
        except ET.ParseError as exc:
            raise ScraperPermanentError(f"weworkremotely: feed is not valid XML: {exc}") from exc

        jobs: list[Job] = []
        for item in root.findall(".//item"):
            job = self.build_job(item)
            if job is not None:
                jobs.append(job)
        return jobs

    def build_job(self, item: ET.Element) -> Job | None:
        raw_title = (item.findtext("title") or "").strip()
        url = (item.findtext("link") or "").strip()
        if not raw_title or not url:
            return None

        company, title = split_title(raw_title)
        region_text = (item.findtext("region") or "").strip() or None
        country = _country(region_text)

        posted_at = parse_rfc822(item.findtext("pubDate"))

        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=company,
            title=title,
            # The feed has no id of its own; the listing URL is stable and
            # unique, and `guid` is the same string.
            external_id=url.rstrip("/").rsplit("/", 1)[-1] or None,
            location=region_text,
            country=country,
            region=region_for(country) if country else Region.UNKNOWN,
            # Every posting on WWR is remote — that is the premise of the site.
            work_mode=WorkMode.REMOTE,
            remote=True,
            department=(item.findtext("category") or "").strip() or None,
            description=html_to_text(item.findtext("description")),
            posted_at=posted_at,
            date_source=date_source_for(posted_at)[1],
        )


def split_title(raw: str) -> tuple[str, str]:
    """ "Gusto, Inc.: Retirement Specialist" -> ("Gusto, Inc.", "Retirement…").

    Only the first ": " separates them; role titles contain colons too
    ("Engineer: Platform"), so splitting on the last one would take the company
    name with it. Falls back to the whole string as the title when there is no
    separator, rather than inventing a company.
    """
    company, sep, title = raw.partition(": ")
    if not sep or not title.strip():
        return "?", raw.strip()
    return company.strip() or "?", title.strip()


def _country(region_text: Any) -> str | None:
    """Resolve the region line only when it names one recognisable country.

    "Anywhere in the World" is not a place, and "USA or Canada" is two.
    """
    if not isinstance(region_text, str) or not region_text.strip():
        return None
    if region_text.strip().lower() in _GLOBAL_REGIONS:
        return None
    parts = [p.strip() for p in region_text.replace(" or ", ",").split(",") if p.strip()]
    if len(parts) != 1:
        return None
    return country_from_name(parts[0])
