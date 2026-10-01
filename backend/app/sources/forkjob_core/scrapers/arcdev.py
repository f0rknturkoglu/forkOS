"""Arc.dev (arc.dev) — global remote contractor platform.

    GET https://arc.dev/remote-jobs

SSR Next.js page: the entire first page of jobs is embedded in the initial
HTML as `__NEXT_DATA__` → `props.pageProps`, verified 2026-08-18 (HTTP 200
with an honest UA). robots.txt allows `/` apart from `/resume/builder/`, and
ClaudeBot/AhrefsBot get a Crawl-delay of 10 which this tool honours via the
Layer B spacing.

Two job families come back on one page:
- `arcJobs` — Arc's own vetted contractor roles; carry `jobType: "contract"`
  and real hourly rates.
- `externalJobs` — employer postings; carry the company name.

Why it matters for the B2B case: Arc is explicitly a contractor marketplace —
`jobType: "contract"` and `minHourlyRate`/`maxHourlyRate` in USD per hour are
on the record rather than inferred.

Field notes from the live response:
- `postedAt` is a board Unix timestamp → date_source is `updated`.
- Explicit `requiredCountries: []` and `timeZone: "no-preference"` mean open to
  anyone; missing fields do not. a populated list is a geographic lock.
- `randomKey` is the stable id; `urlString` builds the job URL.
- The listing is shallow on purpose: the rest is client-side infinite scroll,
  so this reads the SSR page only.
"""

from __future__ import annotations

import re
from typing import Any

from ..models import Job, Layer, WorkMode, date_source_for
from ..normalize import parse_epoch_ms
from ..rich_text import enrich
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError

LISTING_URL = "https://arc.dev/remote-jobs"

_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json"[^>]*>(.*?)</script>',
    re.S,
)


class ArcDevScraper(ScraperBase):
    source_key = "arcdev"
    label = "Arc.dev"
    base_url = "https://arc.dev"

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        html = await client.get_html(LISTING_URL)
        return self.parse(html)

    def parse(self, html: str) -> list[Job]:
        """Pure: page HTML in, Jobs out."""
        match = _NEXT_DATA_RE.search(html or "")
        if match is None:
            raise ScraperPermanentError("arcdev: __NEXT_DATA__ not found on the page")
        try:
            data = _load_json(match.group(1))
        except ValueError as exc:
            raise ScraperPermanentError(f"arcdev: __NEXT_DATA__ is not JSON: {exc}") from exc

        page_props = (data.get("props") or {}).get("pageProps") or {}
        jobs: list[Job] = []
        seen: set[str] = set()
        entries = [(entry, "native") for entry in page_props.get("arcJobs") or []] + [(entry, "meta") for entry in page_props.get("externalJobs") or []]
        for entry, authority in entries:
            if not isinstance(entry, dict):
                continue
            job = self.build_job(entry)
            if job is None:
                continue
            job.description = enrich(job.description, self.source, {"Source authority": authority})
            key = job.external_id or job.url
            if key in seen:
                continue
            seen.add(key)
            jobs.append(job)
        return jobs

    def build_job(self, entry: dict[str, Any]) -> Job | None:
        title = (entry.get("title") or "").strip()
        random_key = entry.get("randomKey")
        if not title or not random_key:
            return None

        url_string = (entry.get("urlString") or "").strip()
        url = f"{self.base_url}/remote-jobs/{url_string}" if url_string else None

        company_block = entry.get("company")
        if isinstance(company_block, dict):
            company = (company_block.get("name") or "").strip() or "?"
        else:
            company = "?"  # Arc's own roles hide the client until you apply

        # Geographic openness is the whole point here.
        required = entry.get("requiredCountries") or []
        geo_locked = bool(required)
        if geo_locked and isinstance(required, list):
            geo_text = ", ".join(str(c) for c in required)
        else:
            geo_text = None

        description_parts: list[str] = []
        job_type = (entry.get("jobType") or "").strip()
        if job_type:
            description_parts.append(f"Engagement: {job_type}")
        level = entry.get("experienceLevel")
        if level:
            description_parts.append(f"Level: {level}")
        hourly = _hourly(entry)
        if hourly:
            description_parts.append(f"Rate: {hourly}")
        if geo_text:
            description_parts.append(f"Residency required: {geo_text}")
        elif "requiredCountries" in entry and not required and entry.get("timeZone") == "no-preference":
            description_parts.append("Open to candidates worldwide")
        categories = entry.get("categories")
        if isinstance(categories, list) and categories:
            description_parts.append("Skills: " + ", ".join(str(c) for c in categories))
        description = enrich("\n".join(description_parts), self.source, {"Remote scope": geo_text or ("Anywhere" if "requiredCountries" in entry and not required and entry.get("timeZone") == "no-preference" else None), "Timezone requirements": entry.get("timeZone"), "Timezone offset": entry.get("timeZoneOffset"), "Overlap hours": entry.get("overlapHours"), "Client timezone restriction": entry.get("clientTimeZoneRestriction"), "Annual salary minimum (currency unspecified)": entry.get("minAnnualSalary"), "Annual salary maximum (currency unspecified)": entry.get("maxAnnualSalary"), "Technologies": ", ".join(str(c) for c in categories) if isinstance(categories, list) else None})

        posted_at = parse_epoch_ms(entry.get("postedAt"))

        return Job.build(
            url=url or "",
            source=self.source,
            layer=Layer.B,
            company=company,
            title=title,
            external_id=str(random_key),
            work_mode=WorkMode.REMOTE,
            remote=True,
            description=description,
            salary=hourly,
            posted_at=posted_at,
            date_source=date_source_for(None, posted_at)[1],
        )


def _hourly(entry: dict[str, Any]) -> str | None:
    low, high = entry.get("minHourlyRate"), entry.get("maxHourlyRate")
    if low is None and high is None:
        return None
    if low is not None and high is not None and low != high:
        return f"${low:g}-{high:g}/hr"
    return f"${(low if low is not None else high):g}/hr"


def _load_json(raw: str) -> Any:
    import json

    return json.loads(raw)
