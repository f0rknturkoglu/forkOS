"""freelancermap (freelancermap.com) — DACH/Europe B2B IT contracts.

    GET https://www.freelancermap.com/projects?pagenr=N

SSR listing, verified 2026-08-18: HTTP 200 with an honest UA, ~1.3 MB HTML
with the project list embedded as real JSON objects
(`{"id":3037109,"slug":"...","title":"...","company":"WA Consultants",
"created":"2026-08-18T19:26:12+02:00","locations":[...],"country":{...}}`).
robots.txt is fully open (`Disallow:` empty). The old RSS feed paths are dead
and `/freelance-jobs` is a 404 — `/projects` is the live listing.

Why it matters for the B2B case: this is the biggest German/European board of
hourly/daily-rate IT contracts. The rate shows up as free text inside the
description ("£500-600/day"), which is exactly the signal the earning rules
read. Company, location and publish date come structured.

Field notes from the live response:
- Each project is a complete JSON object in the page; the parser finds
  `"id":N,"slug":...` starts and balances braces to extract them properly
  rather than regexing individual fields (the `company` key also appears
  inside the `poster` sub-object).
- `created` is a real publish timestamp → date_source is `employer`.
- The numeric id is the external_id; the apply URL is `/project/<slug>-<id>`.
- `country.iso2` is the ISO code; `locations[].name` is the city.
"""

from __future__ import annotations

import contextlib
import json
import re
from typing import Any

from ..geo import region_for
from ..models import DateSource, Job, Layer, Region, WorkMode
from ..normalize import html_to_text, parse_datetime
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError

LISTING_URL = "https://www.freelancermap.com/projects"
DEFAULT_MAX_PAGES = 5

#: Every project object starts with its id and slug.
_OBJECT_START_RE = re.compile(r'"id":\d+,"slug":')


def _extract_objects(html: str) -> list[dict[str, Any]]:
    """Balanced-brace extraction of every embedded JSON object on the page."""
    out: list[dict[str, Any]] = []
    for match in _OBJECT_START_RE.finditer(html):
        open_brace = html.rfind("{", 0, match.start())
        if open_brace < 0:
            continue
        depth = 0
        in_str = False
        esc = False
        for i in range(open_brace, len(html)):
            ch = html[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        with contextlib.suppress(json.JSONDecodeError, ValueError):
                            out.append(json.loads(html[open_brace : i + 1]))
                        break
    return out


class FreelancermapScraper(ScraperBase):
    source_key = "freelancermap"
    label = "Freelancermap"
    base_url = "https://www.freelancermap.com"

    def __init__(self, config: Any = None, *, max_pages: int = DEFAULT_MAX_PAGES) -> None:
        super().__init__(config)
        self.max_pages = max_pages

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()
        for page in range(1, self.max_pages + 1):
            url = LISTING_URL if page == 1 else f"{LISTING_URL}?pagenr={page}"
            try:
                html = await client.get_html(url)
            except ScraperPermanentError:
                break
            page_jobs = self.parse(html)
            if not page_jobs:
                break
            fresh = [j for j in page_jobs if j.external_id not in seen]
            seen.update(j.external_id for j in fresh if j.external_id)
            jobs.extend(fresh)
            if not fresh:
                break  # paged past the end
        return jobs

    def parse(self, html: str) -> list[Job]:
        """Pure: listing HTML in, Jobs out."""
        jobs: list[Job] = []
        for obj in _extract_objects(html or ""):
            job = self.build_job(obj)
            if job is not None:
                jobs.append(job)
        return jobs

    def build_job(self, obj: dict[str, Any]) -> Job | None:
        title = (obj.get("title") or "").strip()
        project_id = obj.get("id")
        if not title or project_id is None:
            return None

        slug = (obj.get("slug") or "").strip()
        url = f"{self.base_url}/project/{slug}" if slug else f"{self.base_url}/project/{project_id}"

        company = (obj.get("company") or "").strip() or "?"

        locations = obj.get("locations") or []
        city = None
        if isinstance(locations, list) and locations:
            first = locations[0]
            city = first.get("name") if isinstance(first, dict) else None
        country_block = obj.get("country")
        country = None
        if isinstance(country_block, dict):
            country = (country_block.get("iso2") or "").upper()[:2] or None

        description = html_to_text(obj.get("description"))
        work_mode = WorkMode.UNKNOWN
        if description:
            lowered = description.lower()
            if "hybrid" in lowered:
                work_mode = WorkMode.HYBRID
            elif "remote" in lowered:
                work_mode = WorkMode.REMOTE

        posted_at = parse_datetime(obj.get("created"))

        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=company,
            title=title,
            external_id=str(project_id),
            location=", ".join(p for p in (city, country) if p) or None,
            city=city,
            country=country,
            region=region_for(country) if country else Region.UNKNOWN,
            work_mode=work_mode,
            remote=True if work_mode is WorkMode.REMOTE else None,
            description=description,
            posted_at=posted_at,
            date_source=DateSource.EMPLOYER if posted_at else DateSource.DISCOVERED,
        )
