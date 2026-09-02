"""Real Work From Anywhere (realworkfromanywhere.com) — 100% location-free jobs.

    GET https://www.realworkfromanywhere.com/rss.xml

Public RSS feed, verified 2026-08-18: HTTP 200 with an honest UA, 149 items,
`ttl=60`. robots.txt is empty (no rules at all). The site only publishes jobs
that can genuinely be done from anywhere in the world, and the feed carries
the salary range — the board's whole premise is "we pay contractors wherever
they live".

Field notes from the live response:
- `guid` is the posting URL; the numeric id at the end of the URL is the
  external_id.
- `pubDate` (RFC 822) is a real publish date → date_source is `employer`.
- `title` is the raw role title; the company appears inside the description's
  first line and in the JSON-LD on the detail page, so it is best-effort.
- Location prose in the item is minimal; the description mentions the salary
  band ("$190,000 - $220,000 USD").
"""

from __future__ import annotations

import re
from xml.etree import ElementTree as ET

from ..models import date_source_for, Job, Layer, WorkMode
from ..normalize import html_to_text, parse_rfc822
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError

FEED_URL = "https://www.realworkfromanywhere.com/rss.xml"
BASE_URL = "https://www.realworkfromanywhere.com"

#: Numeric id at the end of /jobs/<slug>-<id>
_ID_RE = re.compile(r"-(\d+)/?$")
#: The company is often the first line of the description.
_COMPANY_RE = re.compile(r"^(?:Company:\s*)?([^\n|,]+)")


class RealWorkFromAnywhereScraper(ScraperBase):
    source_key = "realworkfromanywhere"
    label = "Real Work From Anywhere"
    base_url = BASE_URL

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        try:
            xml = await client.get_html(FEED_URL)
        except ScraperPermanentError:
            return []
        return self.parse(xml)

    def parse(self, xml: str) -> list[Job]:
        """Pure: feed XML in, Jobs out.

        The feed is technically malformed XML: 500+ unescaped `&` characters
        (e.g. `<enclosure url="...&v=4">`), which makes ElementTree throw
        rather than parse. Escape the loose ampersands first, so a broken
        feed cannot silently become zero jobs — the failure mode this project
        keeps being bitten by.
        """
        xml = _escape_loose_ampersands(xml or "")
        try:
            root = ET.fromstring(xml)
        except ET.ParseError:
            return []
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

        description = html_to_text(item.findtext("description") or "") or ""
        company = _company(description)

        match = _ID_RE.search(url)
        external_id = match.group(1) if match else None

        posted_at = parse_rfc822(item.findtext("pubDate"))

        work_mode = WorkMode.REMOTE  # the board's premise
        salary = _salary(description)

        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=company or "?",
            title=title,
            external_id=external_id,
            work_mode=work_mode,
            remote=True,
            description=description,
            salary=salary,
            posted_at=posted_at,
            date_source=date_source_for(posted_at)[1],
        )


def _escape_loose_ampersands(xml: str) -> str:
    """Turn bare `&` into `&amp;`, leaving valid entities alone.

    The feed emits `<enclosure url="...&v=4">` and similar; without this the
    whole feed fails to parse and the source silently reports zero jobs.
    """
    return re.sub(r"&(?!(?:amp|lt|gt|quot|apos|#\d+);)", "&amp;", xml)


def _company(description: str) -> str | None:
    """Company is often the first line of the description, e.g.
    "Circle is a US-based fintech company..." — take the first words."""
    match = _COMPANY_RE.match(description)
    if not match:
        return None
    name = match.group(1).strip(" .:")
    if len(name) < 2 or " " not in name and len(name) > 40:
        return None
    return name[:40] or None


def _salary(description: str) -> str | None:
    """Find a "$190,000 - $220,000 USD" style band in the prose."""
    match = re.search(r"(\$[\d,]{4,})\s*(?:-|to|–)\s*(\$[\d,]{4,})\s*([A-Z]{3})?", description)
    if not match:
        return None
    parts = [match.group(1), "-", match.group(2)]
    if match.group(3):
        parts.append(match.group(3))
    return " ".join(parts)
