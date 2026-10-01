"""JobTech / Platsbanken — the Swedish Public Employment Service's open API.

    GET https://jobsearch.api.jobtechdev.se/search?q=<terms>&limit=100&offset=N

Run by Arbetsförmedlingen, a government agency, and published as open data: no
key, no bot protection, and every Swedish employer is legally required to post
here. That makes it the most complete single view of one country's market in
this whole registry.

Queries use English role names because the public API supports both Swedish
and English text. Page/prose language is not a working-language requirement.
Batch 3 retains only explicit must_have.languages, including the original
labels, and preserves application, workload, expiry and skill evidence.

Verified 2026-08-09: 673 hits for "developer".
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from ..geo import country_from_name, region_for
from ..models import Job, Layer, Region, WorkMode, date_source_for
from ..normalize import html_to_text
from ..rich_text import enrich
from ..sources.evidence import labels
from .base import ScraperBase, ScraperError, ScraperHttpClient, ScraperPermanentError

API_URL = "https://jobsearch.api.jobtechdev.se/search"

#: English role names. See the module docstring for why they are not Swedish.
DEFAULT_SEARCHES = [
    "software developer",
    "backend developer",
    "frontend developer",
    "junior developer",
    "software engineer",
]

#: The API caps a page at 100.
PAGE_SIZE = 100

#: Letters and function words that only appear in Swedish postings. Cheap, and
#: it only has to separate "readable" from "not readable".
SWEDISH = re.compile(r"[åäöÅÄÖ]|\b(och|som|för|med|vi söker|du är|arbeta)\b", re.I)

REMOTE_WORDS = re.compile(r"\bdistans\b|\bremote\b|\bhemifrån\b", re.I)
HYBRID_WORDS = re.compile(r"\bhybrid\b", re.I)


class JobTechScraper(ScraperBase):
    source_key = "jobtech"
    label = "JobTech (Platsbanken)"
    base_url = "https://arbetsformedlingen.se"

    def __init__(
        self,
        config: Any = None,
        *,
        searches: list[str] | None = None,
        max_pages: int = 2,
    ) -> None:
        super().__init__(config)
        self.searches = list(searches or DEFAULT_SEARCHES)
        self.max_pages = max_pages

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        jobs: dict[str, Job] = {}
        pages_fetched = 0
        items_seen = 0
        cap_hit = False

        for term in self.searches:
            identities = set()
            for page in range(self.max_pages):
                url = (
                    f"{API_URL}?q={term.replace(' ', '%20')}"
                    f"&limit={PAGE_SIZE}&offset={page * PAGE_SIZE}"
                )
                try:
                    payload = await client.get_json(url)
                except ScraperError as exc:
                    self.errors.append(str(exc))
                    break
                pages_fetched += 1
                page_jobs = self.parse(payload)
                items_seen += len(page_jobs)
                if not page_jobs:
                    break
                keys = {job.external_id or job.url for job in page_jobs}
                if page and not (keys - identities):
                    self.errors.append("jobtech: repeated page identities")
                    break
                identities.update(keys)
                # The searches overlap heavily — "software developer" and
                # "software engineer" return much of the same set.
                for job in page_jobs:
                    jobs.setdefault(job.url, job)
                total = payload.get("total", {}).get("value") if isinstance(payload, dict) else None
                if page == self.max_pages - 1 and isinstance(total, int) and (page + 1) * PAGE_SIZE < total:
                    cap_hit = True
                if isinstance(total, int) and (page + 1) * PAGE_SIZE >= total:
                    break

        stop_reason = "max_pages_reached" if cap_hit else "exhausted"
        self.record_telemetry(
            items_seen=items_seen,
            items_returned=len(jobs),
            pages_fetched=pages_fetched,
            page_limit=len(self.searches) * self.max_pages,
            result_limit=None,
            cap_hit=cap_hit,
            stop_reason=stop_reason,
            partial_reason="max_pages_reached" if cap_hit else None,
        )
        return list(jobs.values())

    def parse(self, payload: Any) -> list[Job]:
        hits = payload.get("hits") if isinstance(payload, dict) else None
        if not isinstance(hits, list):
            raise ScraperPermanentError("jobtech: missing hits schema")
        jobs: list[Job] = []
        for hit in hits:
            if isinstance(hit, dict):
                job = self._parse_one(hit)
                if job is not None:
                    jobs.append(job)
        return jobs

    def _parse_one(self, entry: dict[str, Any]) -> Job | None:
        if entry.get("removed") is True:
            return None
        title = (entry.get("headline") or "").strip()
        url = (entry.get("webpage_url") or "").strip()
        if not title or not url:
            return None

        employer = entry.get("employer")
        company = ""
        if isinstance(employer, dict):
            company = (employer.get("name") or employer.get("workplace") or "").strip()

        location, country = self._where(entry.get("workplace_address"))

        description_block = entry.get("description")
        text = ""
        if isinstance(description_block, dict):
            text = description_block.get("text") or ""
            formatted = description_block.get("text_formatted")
            if not text and formatted:
                text = html_to_text(formatted)

        occupation = entry.get("occupation")
        if isinstance(occupation, dict) and occupation.get("label"):
            text = f"{occupation['label']}\n\n{text}"

        work_mode = WorkMode.UNKNOWN
        haystack = f"{title}\n{text[:2000]}"
        if HYBRID_WORDS.search(haystack):
            work_mode = WorkMode.HYBRID
        elif entry.get("remote_work") or REMOTE_WORDS.search(haystack):
            work_mode = WorkMode.REMOTE

        posted_at = self._date(entry.get("publication_date"))

        must = entry.get("must_have") or {}
        language = labels(must.get("languages"))
        text = enrich(text, self.source, {
            "Application URL": (entry.get("application_details") or {}).get("url"),
            "Application deadline": entry.get("application_deadline"),
            "Employment type": labels(entry.get("employment_type")), "Workload": labels(entry.get("working_hours_type")),
            "Workload percentage": str(entry.get("scope_of_work")) if entry.get("scope_of_work") else None,
            "Contract duration": labels(entry.get("duration")), "Language": language,
            "Technologies": labels(must.get("skills")), "Nice-to-have skills": labels((entry.get("nice_to_have") or {}).get("skills")),
            "Company URL": (entry.get("employer") or {}).get("url"), "Requisition ID": (entry.get("application_details") or {}).get("reference"),
        })
        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=company or "?",
            title=title,
            external_id=str(entry.get("id") or "") or None,
            location=location,
            country=country,
            region=region_for(country) if country else Region.EU,
            work_mode=work_mode,
            remote=True if work_mode is WorkMode.REMOTE else None,
            description=text,
            salary=(entry.get("salary_description") or None),
            language=language,
            posted_at=posted_at,
            # publication_date is when the employer published the ad.
            date_source=date_source_for(posted_at)[1],
        )

    @staticmethod
    def _where(address: Any) -> tuple[str | None, str | None]:
        if not isinstance(address, dict):
            return None, "SE"
        city = (address.get("municipality") or "").strip()
        country_name = (address.get("country") or "").strip()
        # The agency writes country names in Swedish; "Sverige" is the common case.
        country = "SE" if country_name.lower() == "sverige" else country_from_name(country_name)
        location = ", ".join(part for part in (city, country_name) if part) or None
        return location, country or "SE"

    @staticmethod
    def _language(text: str) -> str | None:
        if not text.strip():
            return None
        return "sv" if SWEDISH.search(text) else "en"

    @staticmethod
    def _date(value: Any) -> datetime | None:
        if not isinstance(value, str) or not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
