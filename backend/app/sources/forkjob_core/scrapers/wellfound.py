"""Wellfound (wellfound.com, formerly AngelList Talent) — startup roles.

Verified 2026-08-08 against the Spain / software-engineer role page.

robots.txt permits the role pages under `User-agent: *`. The page is Next.js
and ships its Apollo GraphQL cache inside `__NEXT_DATA__`, so no selectors are
needed:

    props.pageProps.apolloState.data
      StartupResult:<id>          name, slug, highlightedJobListings[]
      JobListingSearchResult:<id> title, slug, description, locationNames,
                                  remoteConfig, compensation, jobType,
                                  liveStartAt, yearsExperienceMin/Max

Jobs hang off companies rather than the other way round: a `StartupResult`
lists its postings by `__ref`, and that is the only place the company name
exists. A posting whose company cannot be resolved is still kept, with "?" —
losing a real posting over a broken reference would be worse.

Two fields no other source provides:

- **`yearsExperienceMin`** is a number stated by the poster. Together with
  EURES and Jobgether that makes three sources where seniority is a fact
  rather than a guess from the title.
- **`compensation`** is real pay data ("$70k – $150k • 0.01% – 0.05%"),
  equity included.

`liveStartAt` is a Unix timestamp and a real publish date, so `date_source` is
`employer`.

**Caveat worth keeping in view.** The page also carries Cloudflare and captcha
machinery. It served us fine at one request per 2s with an honest UA, but this
is the most likely source here to start refusing — if it does, it will show up
as an `error` run rather than as silence, and it should be left refused rather
than worked around.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from ..geo import country_from_name, region_for
from ..models import DateSource, Job, Layer, Region, WorkMode
from ..normalize import html_to_text
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError

BASE_URL = "https://wellfound.com"
#: Role/location landing pages, which is what robots permits.
ROLE_URL = "https://wellfound.com/role/l/{role}/{location}"
JOB_URL = "https://wellfound.com/jobs/{id}-{slug}"

DEFAULT_ROLES = ("software-engineer", "backend-engineer", "frontend-engineer")
DEFAULT_LOCATIONS = ("spain", "netherlands", "germany", "sweden", "portugal", "ireland")

_NEXT_DATA_RE = re.compile(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


class WellfoundScraper(ScraperBase):
    source_key = "wellfound"
    label = "Wellfound"
    base_url = BASE_URL

    def __init__(
        self,
        config: Any = None,
        *,
        roles: tuple[str, ...] | list[str] = DEFAULT_ROLES,
        locations: tuple[str, ...] | list[str] = DEFAULT_LOCATIONS,
    ) -> None:
        super().__init__(config)
        self.roles = tuple(roles)
        self.locations = tuple(locations)

    @property
    def scope(self) -> str:
        """Which slice this run asks for — see ScraperBase.scope."""
        return ",".join(sorted(f"{r}@{loc}" for r in self.roles for loc in self.locations))

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()

        for role in self.roles:
            for location in self.locations:
                url = ROLE_URL.format(role=role, location=location)
                try:
                    html = await client.get_html(url)
                except ScraperPermanentError:
                    continue  # one role/location refused must not stop the rest

                for job in self.parse(html):
                    if job.external_id in seen:
                        continue
                    seen.add(job.external_id or job.url)
                    jobs.append(job)
        return jobs

    # -- pure parsing -------------------------------------------------------

    def parse(self, html: str) -> list[Job]:
        """Pure: page HTML in, Jobs out. Drives `--mock` and the tests."""
        match = _NEXT_DATA_RE.search(html or "")
        if match is None:
            return []
        try:
            payload = json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError) as exc:
            raise ScraperPermanentError(f"wellfound: __NEXT_DATA__ is not JSON: {exc}") from exc

        data = (
            payload.get("props", {})
            .get("pageProps", {})
            .get("apolloState", {})
            .get("data")
        )
        if not isinstance(data, dict):
            return []

        company_by_job = _company_index(data)

        jobs: list[Job] = []
        for key, entry in data.items():
            if not isinstance(entry, dict):
                continue
            if entry.get("__typename") != "JobListingSearchResult":
                continue
            job = self.build_job(entry, company_by_job.get(key))
            if job is not None:
                jobs.append(job)
        return jobs

    def build_job(self, entry: dict[str, Any], company: str | None) -> Job | None:
        title = (entry.get("title") or "").strip()
        job_id = entry.get("id")
        if not title or not job_id:
            return None

        slug = entry.get("slug") or ""
        url = JOB_URL.format(id=job_id, slug=slug) if slug else f"{BASE_URL}/jobs/{job_id}"

        locations = entry.get("locationNames")
        location = ", ".join(locations) if isinstance(locations, list) and locations else None
        country = _single_country(locations)

        work_mode, remote = _work_mode(entry)

        description = html_to_text(entry.get("description"))
        years = entry.get("yearsExperienceMin")
        if isinstance(years, int):
            # Stated by the poster as a number — surfaced where the scorer's
            # experience rules will read it.
            description = f"Experience required: {years}+ years\n\n{description or ''}".strip()

        posted_at = _epoch(entry.get("liveStartAt"))

        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=company or "?",
            title=title,
            external_id=str(job_id),
            location=location,
            country=country,
            region=region_for(country) if country else Region.UNKNOWN,
            work_mode=work_mode,
            remote=remote,
            department=entry.get("primaryRoleTitle") or entry.get("jobType") or None,
            description=description,
            salary=(entry.get("compensation") or "").strip() or None,
            posted_at=posted_at,
            date_source=DateSource.EMPLOYER if posted_at else DateSource.DISCOVERED,
        )


def _company_index(data: dict[str, Any]) -> dict[str, str]:
    """Map each job cache key to its company name.

    The relationship only exists in this direction: a `StartupResult` lists its
    postings by `__ref`, and the posting itself carries no company at all.
    """
    index: dict[str, str] = {}
    for entry in data.values():
        if not isinstance(entry, dict) or entry.get("__typename") != "StartupResult":
            continue
        name = (entry.get("name") or "").strip()
        if not name:
            continue
        for ref in entry.get("highlightedJobListings") or []:
            if isinstance(ref, dict) and isinstance(ref.get("__ref"), str):
                index[ref["__ref"]] = name
    return index


def _work_mode(entry: dict[str, Any]) -> tuple[WorkMode, bool | None]:
    """`remoteConfig.kind` is authoritative; `remote` is the coarse fallback."""
    config = entry.get("remoteConfig")
    kind = (config.get("kind") if isinstance(config, dict) else "") or ""
    kind = kind.upper()
    if kind == "REMOTE":
        return WorkMode.REMOTE, True
    if kind == "HYBRID":
        return WorkMode.HYBRID, False
    if kind == "ONSITE":
        return WorkMode.ONSITE, False
    if entry.get("remote") is True:
        return WorkMode.REMOTE, True
    return WorkMode.UNKNOWN, None


def _single_country(locations: Any) -> str | None:
    """Resolve only when exactly one location is given and it is recognised."""
    if not isinstance(locations, list) or len(locations) != 1:
        return None
    return country_from_name(locations[0]) if isinstance(locations[0], str) else None


def _epoch(value: Any) -> datetime | None:
    if isinstance(value, (int, float)) and value > 0:
        return datetime.fromtimestamp(value, tz=timezone.utc)
    return None
