"""DevITjobs network — GermanTechJobs, SwissDevJobs, UKTechJobs.

    GET https://germantechjobs.de/api/jobs
    GET https://swissdevjobs.ch/api/jobs
    GET https://uktechjobs.co.uk/api/jobs

Public JSON API, no key. Returns salary bands, visa sponsorship status,
remote ratio, and tech stack tags explicitly per posting.
"""

from __future__ import annotations

import contextlib
from datetime import datetime
from typing import Any

from ..geo import country_from_name, region_for
from ..models import DateSource, Job, Layer, Region, WorkMode
from ..normalize import html_to_text
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError

API_URLS = {
    "de": "https://germantechjobs.de/api/jobs",
    "ch": "https://swissdevjobs.ch/api/jobs",
    "uk": "https://uktechjobs.co.uk/api/jobs",
}
COUNTRY_MAP = {"de": "DE", "ch": "CH", "uk": "GB"}


class DevITJobsScraper(ScraperBase):
    source_key = "devitjobs"
    label = "DevITjobs"
    base_url = "https://germantechjobs.de"

    def __init__(self, config: Any = None, *, countries: list[str] | None = None) -> None:
        super().__init__(config)
        self.countries = countries or ["de", "ch", "uk"]

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        jobs: list[Job] = []
        for cc in self.countries:
            url = API_URLS.get(cc)
            if not url:
                continue
            try:
                payload = await client.get_json(url)
                country_code = COUNTRY_MAP.get(cc, cc.upper())
                jobs.extend(self.parse(payload, country_code))
            except ScraperPermanentError:
                continue
        return jobs

    def parse(self, payload: Any, country_code: str = "DE") -> list[Job]:
        entries = payload
        if isinstance(payload, dict):
            entries = payload.get("jobs") or payload.get("data") or []
        if not isinstance(entries, list):
            raise ScraperPermanentError(f"devitjobs: expected list, got {type(payload).__name__}")
        jobs: list[Job] = []
        for entry in entries:
            if isinstance(entry, dict):
                job = self._parse_one(entry, country_code)
                if job is not None:
                    jobs.append(job)
        return jobs

    def _parse_one(self, entry: dict[str, Any], country_code: str) -> Job | None:
        title = (entry.get("title") or entry.get("jobTitle") or "").strip()
        if not title:
            return None

        slug = entry.get("slug") or entry.get("id") or entry.get("url")
        url = entry.get("url") or entry.get("jobUrl") or entry.get("link")
        if not url and slug:
            url = f"https://germantechjobs.de/jobs/{slug}"

        company = (entry.get("company") or entry.get("companyName") or "?").strip()

        location = (entry.get("location") or entry.get("city") or "").strip() or None
        country = country_from_name(location) if location else country_code

        # Salary
        salary = None
        salary_from = entry.get("salaryFrom") or entry.get("salary_from")
        salary_to = entry.get("salaryTo") or entry.get("salary_to")
        currency = entry.get("currency") or "EUR"
        if salary_from and salary_to:
            salary = f"{int(salary_from):,} - {int(salary_to):,} {currency}"

        # Remote
        remote_ratio = entry.get("remoteRatio") or entry.get("remote")
        if (
            isinstance(remote_ratio, (int, float))
            and remote_ratio >= 80
            or entry.get("remote") is True
        ):
            work_mode = WorkMode.REMOTE
            remote = True
        else:
            work_mode = WorkMode.UNKNOWN
            remote = None

        # Description from body + tech stack
        body = entry.get("body") or entry.get("description") or ""
        description = html_to_text(body)

        skills = entry.get("skills") or entry.get("techStack") or []
        if isinstance(skills, list) and skills:
            description = f"Skills: {', '.join(str(s) for s in skills)}\n\n{description}"

        posted_str = entry.get("publishedAt") or entry.get("createdAt") or entry.get("date")
        posted_at = None
        if isinstance(posted_str, str):
            with contextlib.suppress(ValueError):
                posted_at = datetime.fromisoformat(posted_str.replace("Z", "+00:00"))

        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=company,
            title=title,
            external_id=str(slug) if slug else None,
            location=location,
            country=country,
            region=region_for(country) if country else Region.EU,
            work_mode=work_mode,
            remote=remote,
            description=description,
            salary=salary,
            posted_at=posted_at,
            date_source=DateSource.EMPLOYER if posted_at else DateSource.DISCOVERED,
        )
