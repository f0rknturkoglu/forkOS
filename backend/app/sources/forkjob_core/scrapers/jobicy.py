"""Jobicy (jobicy.com) — remote-first board, read through its RSS feed.

Verified 2026-08-08.

    GET https://jobicy.com/jobs/feed?industry=engineering&geo=europe

**Why RSS and not the JSON API.** The documented API at `/api/v2/remote-jobs`
is forbidden by the site's own robots.txt (line 48: `Disallow: /api/`), which
the scraper obeys — the first live attempt returned zero postings and no error.
The RSS feed is a different path and is permitted: `Disallow: /feed$` pins to
the bare `/feed`, and nothing covers `/jobs/feed`. Same publisher, same data,
a route they leave open.

The feed turned out to be *richer* than the API response, not poorer. Items
carry a Jobicy-specific namespace (`https://jobicy.com`) with:

    <jobicy:company>   <jobicy:location>   <jobicy:job_type>   <jobicy:category>

plus `title`, `id`, `link`, `pubDate` and a full `content:encoded` body.

The one thing lost against the API is `jobLevel` ("Entry-Level, Junior" /
"Midweight" / "Senior"), which the feed does not carry. The title-based
seniority rules cover it, less precisely.

`pubDate` is RFC 822 and a real publish date, so `date_source` is `employer`.

Their terms ask that Jobicy be credited with a direct link and that
applications go to the original URL; the stored `url` is that link.
"""

from __future__ import annotations

from typing import Any
from xml.etree import ElementTree as ET

from ..geo import region_for
from ..models import Job, Layer, Region, WorkMode, date_source_for
from ..normalize import html_to_text, parse_rfc822, parse_single_country
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError

BASE_URL = "https://jobicy.com"
FEED_URL = "https://jobicy.com/jobs/feed"

#: Jobicy's own RSS namespace, where the useful fields live.
NS = {"jobicy": "https://jobicy.com", "content": "http://purl.org/rss/1.0/modules/content/"}

#: `geo` values worth asking for. "anywhere" is not one — the API rejects it
#: outright and asks that geo simply be omitted, which the bare feed does.
DEFAULT_GEOS = ("europe", "emea", "")
#: `industry` filter. Engineering is the closest thing to a software bucket.
DEFAULT_INDUSTRIES = ("engineering",)


class JobicyScraper(ScraperBase):
    source_key = "jobicy"
    label = "Jobicy"
    base_url = BASE_URL

    def __init__(
        self,
        config: Any = None,
        *,
        geos: tuple[str, ...] | list[str] = DEFAULT_GEOS,
        industries: tuple[str, ...] | list[str] = DEFAULT_INDUSTRIES,
    ) -> None:
        super().__init__(config)
        self.geos = tuple(geos)
        self.industries = tuple(industries)

    @property
    def scope(self) -> str:
        """Which slice this run asks for — see ScraperBase.scope."""
        return ",".join(sorted(f"{g}/{i}" for g in self.geos for i in self.industries))

    def feed_url(self, geo: str, industry: str) -> str:
        params = [f"industry={industry}"] if industry else []
        if geo:
            params.append(f"geo={geo}")
        return f"{FEED_URL}?{'&'.join(params)}" if params else FEED_URL

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()

        for geo in self.geos:
            for industry in self.industries:
                url = self.feed_url(geo, industry)
                xml = await self.isolate(url, lambda: client.get_html(url))
                if xml is None:
                    continue  # one slice failing must not stop the rest
                jobs.extend(self.dedup_seen(seen, self.parse(xml)))
        return jobs

    # -- pure parsing -------------------------------------------------------

    def parse(self, xml: str) -> list[Job]:
        """Pure: feed XML in, Jobs out. Drives `--mock` and the offline tests."""
        try:
            root = ET.fromstring(xml or "")
        except ET.ParseError as exc:
            raise ScraperPermanentError(f"jobicy: feed is not valid XML: {exc}") from exc

        jobs: list[Job] = []
        for item in root.findall(".//item"):
            job = self.build_job(item)
            if job is not None:
                jobs.append(job)
        return jobs

    def build_job(self, item: ET.Element) -> Job | None:
        title = (item.findtext("title") or "").strip()
        url = (item.findtext("link") or "").strip()
        if not title or not url:
            return None

        location = (item.findtext("jobicy:location", namespaces=NS) or "").strip() or None
        country = parse_single_country(location)

        body = item.findtext("content:encoded", namespaces=NS) or item.findtext("description")
        description = html_to_text(body)

        category = item.findtext("jobicy:category", namespaces=NS)
        job_type = item.findtext("jobicy:job_type", namespaces=NS)

        posted_at = parse_rfc822(item.findtext("pubDate"))

        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=(item.findtext("jobicy:company", namespaces=NS) or "").strip() or "?",
            title=title,
            external_id=(item.findtext("id") or "").strip() or None,
            location=location,
            country=country,
            region=region_for(country) if country else Region.UNKNOWN,
            # Every posting on Jobicy is remote — that is the premise of the
            # site, so this is a fact about the source, not an inference.
            work_mode=WorkMode.REMOTE,
            remote=True,
            department=", ".join(p for p in (category, job_type) if p) or None,
            description=description,
            posted_at=posted_at,
            date_source=date_source_for(posted_at)[1],
        )


