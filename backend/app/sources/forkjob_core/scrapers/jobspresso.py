"""Jobspresso — curated remote job board.

    GET https://jobspresso.co/jobs/feed/

A WP Job Manager RSS feed. robots.txt allows it: the only broad rule is
`Disallow: /*?`, which covers query strings, and this path has none. Crawl-delay
is 3s.

The site's main /feed/ is the blog and carries no postings — the job feed is a
separate path. Company and location are not their own elements; both are packed
into `dc:creator` as `Company<br>⚲&nbsp;Location, Location`.

Verified 2026-08-09: 20 postings, all remote.
"""

from __future__ import annotations

import html
import re
from xml.etree import ElementTree as ET

from ..geo import country_from_name, region_for
from ..models import Job, Layer, Region, WorkMode, date_source_for
from ..normalize import html_to_text, parse_rfc822
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError

FEED_URL = "https://jobspresso.co/jobs/feed/"
DC = "{http://purl.org/dc/elements/1.1/}creator"

#: dc:creator is "Company<br>⚲&nbsp;Where". The pin marks where location starts.
CREATOR_SPLIT = re.compile(r"<br\s*/?>", re.I)
PIN = "⚲"


class JobspressoScraper(ScraperBase):
    source_key = "jobspresso"
    label = "Jobspresso"
    base_url = "https://jobspresso.co"

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        xml = await client.get_html(FEED_URL)
        return self.parse(xml)

    def parse(self, xml: str) -> list[Job]:
        try:
            root = ET.fromstring(xml or "")
        except ET.ParseError as exc:
            raise ScraperPermanentError(
                f"jobspresso: feed is not valid XML: {exc}"
            ) from exc
        jobs: list[Job] = []
        for item in root.iter("item"):
            job = self._parse_item(item)
            if job is not None:
                jobs.append(job)
        return jobs

    def _parse_item(self, item: ET.Element) -> Job | None:
        title = (item.findtext("title") or "").strip()
        url = (item.findtext("link") or "").strip()
        if not title or not url:
            return None

        company, location = self._creator(item.findtext(DC) or "")

        posted_at = parse_rfc822(item.findtext("pubDate"))

        country = self._country_of(location)

        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=company or "?",
            title=html.unescape(title),
            external_id=self._post_id(item.findtext("guid") or "") or url,
            location=location,
            country=country,
            region=region_for(country) if country else Region.UNKNOWN,
            # The board only lists remote work; that is its whole premise.
            work_mode=WorkMode.REMOTE,
            remote=True,
            description=html_to_text(item.findtext("description") or ""),
            posted_at=posted_at,
            date_source=date_source_for(posted_at)[1],
        )

    @staticmethod
    def _country_of(location: str | None) -> str | None:
        """Take the first resolvable country out of a multi-country location.

        Postings routinely list every country they will hire from —
        "United Kingdom, Spain, Dubai" — and the whole string resolves to
        nothing. The first entry is the one the employer led with.
        """
        if not location:
            return None
        direct = country_from_name(location)
        if direct:
            return direct
        for part in re.split(r"[,/()]", location):
            found = country_from_name(part.strip())
            if found:
                return found
        return None

    @staticmethod
    def _creator(creator: str) -> tuple[str, str | None]:
        """Split `Company<br>⚲&nbsp;Cities` into its two halves."""
        parts = CREATOR_SPLIT.split(html.unescape(creator or ""))
        company = parts[0].strip() if parts else ""
        location = None
        if len(parts) > 1:
            location = parts[1].replace(PIN, " ").replace("\xa0", " ").strip(" ,")
        return company, location or None

    @staticmethod
    def _post_id(guid: str) -> str | None:
        """guid is `…/?post_type=job_listing&p=163372`; keep the numeric id."""
        match = re.search(r"[?&]p=(\d+)", html.unescape(guid))
        return match.group(1) if match else None
