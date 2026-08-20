"""JustJoin.it (justjoin.it) — Poland's largest tech job board, public JSON API.

    GET https://justjoin.it/api/offers

No key, no auth. Returns all active tech jobs in Poland with salary bands,
work mode, and skill tags.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..geo import country_from_name, region_for
from ..models import DateSource, Job, Layer, Region, WorkMode
from ..normalize import html_to_text
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError

API_URL = "https://justjoin.it/api/offers"


class JustJoinItScraper(ScraperBase):
    source_key = "justjoinit"
    label = "JustJoin.it"
    base_url = "https://justjoin.it"

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        payload = await client.get_json(API_URL)
        return self.parse(payload)

    def parse(self, payload: Any) -> list[Job]:
        """API returns a list of offer objects."""
        entries = payload
        if isinstance(payload, dict):
            entries = payload.get("data") or payload.get("offers") or []
        if not isinstance(entries, list):
            raise ScraperPermanentError(
                f"justjoinit: expected list, got {type(payload).__name__}"
            )
        jobs: list[Job] = []
        for entry in entries:
            if isinstance(entry, dict):
                job = self._parse_one(entry)
                if job is not None:
                    jobs.append(job)
        return jobs

    def _parse_one(self, entry: dict[str, Any]) -> Job | None:
        title = (entry.get("title") or "").strip()
        if not title:
            return None

        offer_id = entry.get("id") or entry.get("slug")
        url = f"https://justjoin.it/job-offer/{offer_id}" if offer_id else None

        company = (entry.get("companyName") or entry.get("company_name") or "?").strip()

        # Location: city + country, e.g. "Warsaw, Poland"
        city = (entry.get("city") or "").strip()
        country_code = (entry.get("countryCode") or entry.get("country_code") or "").strip().upper()
        location = f"{city}, {country_code}" if city and country_code else (city or country_code or None)
        country = country_code if country_code else country_from_name(location)

        # Work mode
        workplace = (entry.get("workplace") or entry.get("workplaceType") or "").lower()
        if workplace in ("remote", "fully_remote"):
            work_mode = WorkMode.REMOTE
            remote = True
        elif workplace in ("hybrid", "partly_remote"):
            work_mode = WorkMode.HYBRID
            remote = None
        elif workplace == "office":
            work_mode = WorkMode.ONSITE
            remote = False
        else:
            work_mode = WorkMode.UNKNOWN
            remote = None

        # Description from body/skills
        body = entry.get("body") or entry.get("description") or ""
        description = html_to_text(body)

        skills = []
        for skill in entry.get("skills") or []:
            if isinstance(skill, dict) and skill.get("name"):
                skills.append(skill["name"])
        if skills:
            description = f"Skills: {', '.join(skills)}\n\n{description}"

        # Salary
        salary = None
        employment_types = entry.get("employmentTypes") or []
        if employment_types:
            for et in employment_types:
                if isinstance(et, dict):
                    frm = et.get("from")
                    to = et.get("to")
                    cur = et.get("currency", "PLN")
                    if frm and to:
                        salary = f"{int(frm):,} - {int(to):,} {cur}"
                        break

        posted_str = entry.get("publishedAt") or entry.get("createdAt")
        posted_at = None
        if isinstance(posted_str, str):
            try:
                posted_at = datetime.fromisoformat(posted_str.replace("Z", "+00:00"))
            except ValueError:
                pass

        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=company,
            title=title,
            external_id=str(offer_id) if offer_id else None,
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
