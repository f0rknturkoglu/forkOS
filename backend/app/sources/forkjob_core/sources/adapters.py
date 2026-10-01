"""Layer A: ATS board adapters.

Every endpoint here was probed against a real company board before its parser
was written; the field notes on each class record what the payload actually
contained, not what the documentation claims.

Verified against live boards:
  greenhouse       2026-08-07, 5 boards, 507 postings
  lever            2026-08-08, 5 boards
  ashby            2026-08-08, 6 boards
  smartrecruiters  2026-08-08, wise (100 postings)
  recruitee        2026-08-08, holded (8 postings)

Still unverified — written but never run against a real board:
  workable, factorial, workday

A note on Personio, which looks verifiable and is not. Tokens like `fever` and
`payhawk` answer 200 with three postings — "SEO Marketing Manager", "Social
Media (Working Student)", "General Application" — and they are the *same three*
for every such token. Those are Personio's starter templates on accounts that
have published nothing. A non-empty response is therefore not evidence the
board is real, which is exactly the gap the discover confirmation prompt cannot
see.
"""

from __future__ import annotations

from typing import Any, ClassVar
from urllib.parse import urlencode, urljoin, urlsplit

from app.sources.base import ScrapeTelemetry

from ..geo import country_from_name, region_for
from ..models import Company, DateSource, Job, Layer, WorkMode
from ..normalize import detect_language, html_to_text, parse_datetime, parse_location
from .base import ATSAdapter, HttpClient, PermanentError, SourceError
from .evidence import ats_job

# ---------------------------------------------------------------------------
# Greenhouse — verified
# ---------------------------------------------------------------------------


class GreenhouseAdapter(ATSAdapter):
    """Greenhouse job boards.

    GET https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true

    Verified 2026-08-07 against cabify (52), gitlab (191), elastic (241),
    typeform (12), wallapop (11).

    Field notes:
    - `first_published` was present on 507/507 postings across those five
      boards, so `date_source` is `employer`. `updated_at` is only the
      fallback, and it downgrades to `updated` — it is an edit timestamp, and
      a stale posting touched yesterday would otherwise look brand new.
    - `content` is double-escaped HTML (`&lt;p&gt;`).
    - `language` is reported per posting ("es"/"en"), so no guessing needed.
    - `offices[].location` carries the country ("Madrid, Madrid, Spain") but is
      often empty — 0/12 on typeform, 19/241 on elastic. `location.name` is
      always present, so it leads and offices only fill a missing country.
    """

    ats: ClassVar[str] = "greenhouse"
    BASE_URL: ClassVar[str] = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"

    async def fetch_raw(self, client: HttpClient) -> Any:
        return await client.get_json(
            self.BASE_URL.format(token=self.token), params={"content": "true"}
        )

    def parse(self, raw: Any) -> list[Job]:
        if not isinstance(raw, dict) or not isinstance(raw.get("jobs"), list):
            raise PermanentError(f"{self.source}: unexpected payload shape {type(raw).__name__}")

        jobs: list[Job] = []
        for entry in raw.get("jobs") or []:
            job = self.parse_record(entry)
            if job is not None:
                jobs.append(job)
        return jobs

    def _parse_one(self, entry: dict[str, Any]) -> Job | None:
        url = entry.get("absolute_url")
        title = entry.get("title")
        if not url or not title:
            return None

        description = html_to_text(entry.get("content"))
        location_name = (entry.get("location") or {}).get("name")
        info = parse_location(location_name, description=description)

        if info.country is None:
            offices = "; ".join(
                office.get("location") or office.get("name") or ""
                for office in entry.get("offices") or []
            ).strip("; ")
            if offices:
                from_offices = parse_location(offices, description=description)
                info.country = from_offices.country
                info.city = info.city or from_offices.city
                info.region = from_offices.region

        posted_at = parse_datetime(entry.get("first_published"))
        date_source = DateSource.EMPLOYER
        if posted_at is None:
            posted_at = parse_datetime(entry.get("updated_at"))
            date_source = DateSource.UPDATED if posted_at else DateSource.DISCOVERED

        departments = [d.get("name") for d in entry.get("departments") or [] if d.get("name")]

        # Greenhouse lets a board define arbitrary `metadata` fields, and some
        # of them are worth more than anything in the prose. Elastic publishes
        # a "Seniority" field ("Entry Level" / "Associate" / "Mid-Senior
        # Level"), which is the employer stating the level outright rather
        # than us reading it off a title.
        description = _prepend_metadata(entry, description)

        return ats_job(entry,
            url=url,
            source=self.source,
            layer=Layer.A,
            company=entry.get("company_name") or self.company.name,
            title=title.strip(),
            external_id=str(entry.get("id")) if entry.get("id") is not None else None,
            location=location_name,
            city=info.city,
            country=info.country,
            region=info.region,
            work_mode=info.work_mode,
            department=" / ".join(departments) or None,
            description=description,
            language=detect_language(description, declared=entry.get("workingLanguage")),
            posted_at=posted_at,
            date_source=date_source,
        )


# ---------------------------------------------------------------------------
# Lever — structural, unverified
# ---------------------------------------------------------------------------


class LeverAdapter(ATSAdapter):
    """Lever job boards.

    GET https://api.lever.co/v0/postings/{token}?mode=json

    Payload shape (from Lever's public docs):
      [
        {
          "id": "...",
          "text": "Senior Backend Engineer",
          "categories": {
            "department": "Engineering",
            "team": "Platform",
            "location": "Madrid, Spain",
            "commitment": "Full-time"
          },
          "hostedUrl": "https://jobs.lever.co/company/...",
          "applyUrl": "https://jobs.lever.co/company/.../apply",
          "descriptionPlain": "...",
          "description": "<div>...</div>",
          "createdAt": 1714000000000,
          "lists": [...],
          "workplaceType": "remote"
        }
      ]

    `createdAt` is ATS record creation, not proven original publication; date_source = updated.
    `workplaceType` is "remote" / "onsite" / "hybrid" / unspecified.
    """

    ats: ClassVar[str] = "lever"
    BASE_URL: ClassVar[str] = "https://api.lever.co/v0/postings/{token}"

    async def fetch_raw(self, client: HttpClient) -> Any:
        return await client.get_json(
            self.BASE_URL.format(token=self.token), params={"mode": "json"}
        )

    def parse(self, raw: Any) -> list[Job]:
        if not isinstance(raw, list):
            raise PermanentError(f"{self.source}: expected a list, got {type(raw).__name__}")

        jobs: list[Job] = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            job = self.parse_record(entry)
            if job is not None:
                jobs.append(job)
        return jobs

    def _parse_one(self, entry: dict[str, Any]) -> Job | None:
        title = entry.get("text")
        url = entry.get("hostedUrl") or entry.get("applyUrl")
        if not title or not url:
            return None

        categories = entry.get("categories") or {}
        location_name = _lever_location(categories)
        info = parse_location(location_name)

        # `country` is an ISO code straight from Lever and beats anything
        # inferred from prose — Trendyol's Riyadh postings carry "SA".
        country = entry.get("country")
        if isinstance(country, str) and len(country) == 2:
            info.country = country.upper()
            info.region = region_for(info.country)

        posted_at = parse_datetime(_lever_ts(entry.get("createdAt")))
        date_source = DateSource.UPDATED if posted_at else DateSource.DISCOVERED

        workplace = (entry.get("workplaceType") or "").lower()
        if workplace in ("remote", "hybrid", "onsite", "on-site"):
            info.work_mode = WorkMode(workplace.replace("on-site", "onsite"))

        description = html_to_text(entry.get("description"))
        if description is None:
            description = html_to_text(entry.get("descriptionPlain"))

        return ats_job(entry,
            url=url,
            source=self.source,
            layer=Layer.A,
            company=self.company.name,
            title=title.strip(),
            external_id=entry.get("id"),
            location=location_name,
            city=info.city,
            country=info.country,
            region=info.region,
            work_mode=info.work_mode,
            department=categories.get("department") or categories.get("team"),
            description=description,
            language=detect_language(description, declared=entry.get("workingLanguage")),
            posted_at=posted_at,
            date_source=date_source,
        )


#: Greenhouse `metadata` names worth surfacing, lowercased. Boards invent
#: their own field names, so this is a small allowlist rather than a dump of
#: everything — "FADV_Package" and "Integration is ready (DO NOT USE)" are
#: real examples of what the rest looks like.
_USEFUL_METADATA = {
    "seniority": "Seniority",
    "level": "Level",
    "visa sponsorship": "Visa sponsorship",
    "relocation": "Relocation",
    "working language": "Working language",
    "employment type": "Employment type",
    "remote scope": "Remote scope",
    "salary": "Salary",
    "skills": "Skills",
    "target remote countries / states locations [for job wrapping]": "Remote countries",
}


def _prepend_metadata(entry: dict[str, Any], description: str | None) -> str | None:
    """Surface useful board metadata where the scorer will read it.

    Kept at the top of the description rather than added as new columns: the
    field names differ per board, so a column would be empty for most sources,
    while the scorer's existing level and location rules already read prose.
    """
    lines: list[str] = []
    for item in entry.get("metadata") or []:
        if not isinstance(item, dict):
            continue
        label = _USEFUL_METADATA.get(str(item.get("name") or "").strip().lower())
        value = item.get("value")
        if not label or value in (None, "", []):
            continue
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value if v)
        if isinstance(value, bool) and label in {"Visa sponsorship", "Relocation"}:
            value = "Yes" if value else "No"
        if value is not None and value != "":
            lines.append(f"{label}: {value}")
    if not lines:
        return description
    return "\n".join(lines) + "\n\n" + (description or "")


#: Employment types that turn up in Lever's `location` field when a company
#: has filled its board in wrong. Peak Games' entire board reports its location
#: as "Full-time"; treating that as a place would invent a country.
_LEVER_NON_LOCATIONS = {
    "full-time",
    "part-time",
    "fulltime",
    "parttime",
    "full time",
    "part time",
    "contract",
    "internship",
    "temporary",
    "freelance",
    "permanent",
}


def _lever_location(categories: dict[str, Any]) -> str | None:
    """Best location string from a Lever posting, or None if it is junk."""
    candidates = categories.get("allLocations") or []
    if isinstance(candidates, list) and candidates:
        usable = [str(c) for c in candidates if str(c).strip().lower() not in _LEVER_NON_LOCATIONS]
        if usable:
            return "; ".join(usable)

    location = categories.get("location")
    if isinstance(location, str) and location.strip().lower() not in _LEVER_NON_LOCATIONS:
        return location
    return None


def _lever_ts(value: Any) -> str | None:
    """Lever timestamps are millisecond epoch integers."""
    if isinstance(value, (int, float)) and value > 0:

        from ..normalize import parse_epoch_ms

        parsed = parse_epoch_ms(value)
        return parsed.isoformat() if parsed else None
    return str(value) if value else None


# ---------------------------------------------------------------------------
# Ashby — structural, unverified
# ---------------------------------------------------------------------------


class AshbyAdapter(ATSAdapter):
    """Ashby job boards.

    GET https://api.ashbyhq.com/posting-api/job-board/{token}

    Payload shape (from Ashby's public API):
      {
        "jobBoard": {"name": "Company Name", ...},
        "jobs": [
          {
            "id": "...",
            "title": "Senior Backend Engineer",
            "location": "Madrid, Spain",
            "departmentName": "Engineering",
            "descriptionPlain": "...",
            "descriptionHtml": "<div>...</div>",
            "publishedAt": "2024-03-01T00:00:00.000Z",
            "updatedAt": "2024-03-15T00:00:00.000Z",
            "isRemote": false,
            "employmentType": "Full-time",
            "applyUrl": "https://jobs.ashbyhq.com/company/..."
          }
        ]
      }

    `publishedAt` is the last-published date → date_source = updated.
    `isRemote` is a boolean, no need to guess.
    """

    ats: ClassVar[str] = "ashby"
    BASE_URL: ClassVar[str] = "https://api.ashbyhq.com/posting-api/job-board/{token}"

    async def fetch_raw(self, client: HttpClient) -> Any:
        return await client.get_json(self.BASE_URL.format(token=self.token), params={"includeCompensation": "true"})

    def parse(self, raw: Any) -> list[Job]:
        if not isinstance(raw, dict) or not isinstance(raw.get("jobs"), list):
            raise PermanentError(f"{self.source}: unexpected payload shape {type(raw).__name__}")

        board_name = raw.get("jobBoard", {}).get("name") or self.company.name
        jobs: list[Job] = []
        for entry in raw.get("jobs") or []:
            job = self.parse_record(entry, board_name)
            if job is not None:
                jobs.append(job)
        return jobs

    def _parse_one(self, entry: dict[str, Any], board_name: str) -> Job | None:
        title = entry.get("title")
        url = entry.get("applyUrl")
        if not title or not url:
            return None

        location_name = entry.get("location")
        info = parse_location(location_name)

        # Ashby gives an explicit isRemote boolean.
        if entry.get("isRemote") is True and info.work_mode is not None:
            info.work_mode = WorkMode.REMOTE

        posted_at = parse_datetime(entry.get("publishedAt"))
        date_source = DateSource.UPDATED
        if posted_at is None:
            posted_at = parse_datetime(entry.get("updatedAt"))
            date_source = DateSource.UPDATED if posted_at else DateSource.DISCOVERED

        description = html_to_text(entry.get("descriptionHtml"))
        if description is None:
            description = html_to_text(entry.get("descriptionPlain"))

        return ats_job(entry,
            url=url,
            source=self.source,
            layer=Layer.A,
            company=board_name,
            title=title.strip(),
            external_id=entry.get("id"),
            location=location_name,
            city=info.city,
            country=info.country,
            region=info.region,
            work_mode=info.work_mode,
            department=entry.get("department") or entry.get("departmentName"),
            description=description,
            language=detect_language(description, declared=entry.get("workingLanguage")),
            posted_at=posted_at,
            date_source=date_source,
        )


# ---------------------------------------------------------------------------
# Workable — structural, unverified
# ---------------------------------------------------------------------------


class WorkableAdapter(ATSAdapter):
    """Workable job boards.

    GET https://{token}.workable.com/spi/v3/jobs?state=published

    Payload shape (from Workable's public API):
      {
        "jobs": [
          {
            "shortcode": "ABC123",
            "title": "Senior Backend Engineer",
            "full_title": "Senior Backend Engineer — Madrid",
            "url": "https://company.workable.com/j/ABC123",
            "location": {
              "city": "Madrid",
              "country": "Spain",
              "region": "Community of Madrid"
            },
            "department": "Engineering",
            "description": "<div>...</div>",
            "published": "2024-03-01T00:00:00Z",
            "remote": false,
            "employment_type": "Full-time"
          }
        ]
      }

    `published` is the publish date → date_source = employer.
    `remote` is a boolean.
    """

    ats: ClassVar[str] = "workable"
    BASE_URL: ClassVar[str] = "https://{token}.workable.com/spi/v3/jobs"

    async def fetch_raw(self, client: HttpClient) -> Any:
        return await client.get_json(
            self.BASE_URL.format(token=self.token), params={"state": "published"}
        )

    def parse(self, raw: Any) -> list[Job]:
        if not isinstance(raw, dict) or not isinstance(raw.get("jobs"), list):
            raise PermanentError(f"{self.source}: unexpected payload shape {type(raw).__name__}")

        jobs: list[Job] = []
        for entry in raw.get("jobs") or []:
            job = self.parse_record(entry)
            if job is not None:
                jobs.append(job)
        return jobs

    def _parse_one(self, entry: dict[str, Any]) -> Job | None:
        title = entry.get("title")
        url = entry.get("url")
        if not title or not url:
            return None

        loc = entry.get("location") or {}
        if isinstance(loc, dict):
            city = loc.get("city")
            country = loc.get("country")
            location_name = (
                ", ".join(v for v in (loc.get("city"), loc.get("region"), loc.get("country")) if v)
                or None
            )
        else:
            city = None
            country = None
            location_name = str(loc) if loc else None

        info = parse_location(location_name)
        info.city = info.city or city
        if info.country is None and country:
            info.country = country_from_name(country)
            info.region = region_for(info.country)

        if entry.get("remote") is True:
            info.work_mode = WorkMode.REMOTE

        posted_at = parse_datetime(entry.get("published"))
        date_source = DateSource.EMPLOYER if posted_at else DateSource.DISCOVERED

        description = html_to_text(entry.get("description"))

        return ats_job(entry,
            url=url,
            source=self.source,
            layer=Layer.A,
            company=self.company.name,
            title=title.strip(),
            external_id=entry.get("shortcode"),
            location=location_name,
            city=info.city,
            country=info.country,
            region=info.region,
            work_mode=info.work_mode,
            department=entry.get("department"),
            description=description,
            language=detect_language(description, declared=entry.get("workingLanguage")),
            posted_at=posted_at,
            date_source=date_source,
        )


# ---------------------------------------------------------------------------
# SmartRecruiters — structural, unverified
# ---------------------------------------------------------------------------


class SmartRecruitersAdapter(ATSAdapter):
    """SmartRecruiters job boards.

    GET https://api.smartrecruiters.com/v1/companies/{token}/postings

    Payload is paginated:
      {
        "content": [
          {
            "id": "...",
            "name": "Senior Backend Engineer",
            "ref": "abc-123",
            "location": {"city": "Madrid", "country": "Spain", "region": "..."},
            "department": {"label": "Engineering"},
            "releasedDate": "2024-03-01T00:00:00.000Z",
            "company": {"name": "Company"},
            "url": "https://jobs.smartrecruiters.com/Company/...",
            "typeOfEmployment": {"label": "Full-time"},
            "industry": {"label": "..."}
          }
        ],
        "totalFound": 52,
        "totalPages": 1,
        ...
      }

    `releasedDate` is the publish date → date_source = employer.
    Pagination handled by following `next` links up to a safety cap.
    """

    ats: ClassVar[str] = "smartrecruiters"
    BASE_URL: ClassVar[str] = "https://api.smartrecruiters.com/v1/companies/{token}/postings"
    MAX_PAGES: ClassVar[int] = 20  # safety cap — real boards rarely exceed this

    async def fetch_raw(self, client: HttpClient) -> Any:
        rows, seen, visited, errors = [], set(), set(), []
        base = self.BASE_URL.format(token=self.token)
        url, pages, more = base, 0, True
        for _ in range(self.MAX_PAGES):
            if url in visited:
                errors.append("repeated_pagination_url")
                break
            visited.add(url)
            try:
                page = await client.get_json(url)
                if not isinstance(page, dict) or not isinstance(page.get("content"), list):
                    raise PermanentError("SmartRecruiters missing content schema")
                content = page["content"]
                ids = {str(r.get("id")) for r in content if isinstance(r, dict) and r.get("id")}
                if content and (not ids or ids <= seen):
                    raise PermanentError("SmartRecruiters repeated/malformed posting page")
                total = page.get("totalFound")
                if not content and isinstance(total, int) and len(rows) < total:
                    raise PermanentError("SmartRecruiters empty page before total")
                rows.extend(r for r in content if isinstance(r, dict) and str(r.get("id")) not in seen)
                seen.update(ids)
                pages += 1
                next_url = next((r.get("href") for r in page.get("links") or [] if isinstance(r, dict) and r.get("rel") == "next"), None)
                if not next_url and content and isinstance(total, int) and len(rows) < total:
                    next_url = base + "?" + urlencode({"offset": len(rows), "limit": 100})
                more = bool(next_url)
                if not more:
                    break
                if urlsplit(next_url).netloc != urlsplit(base).netloc or not urlsplit(next_url).path.startswith(urlsplit(base).path):
                    raise PermanentError("SmartRecruiters foreign pagination route")
                url = next_url
            except SourceError as exc:
                if not rows:
                    raise
                errors.append(type(exc).__name__ + ": " + str(exc))
                break
        cap = more and pages == self.MAX_PAGES
        self.telemetry = ScrapeTelemetry(
            items_seen=len(rows), pages_fetched=pages, page_limit=self.MAX_PAGES,
            cap_hit=cap, partial_reason="; ".join(errors) or ("page_limit_reached" if cap else None),
            stop_reason="request_failed" if errors else "page_limit_reached" if cap else "exhausted",
            metadata={"listing_pages": pages, "detail_requests": 0},
        )
        return rows

    def parse(self, raw: Any) -> list[Job]:
        if not isinstance(raw, list):
            raise PermanentError(f"{self.source}: unexpected payload shape {type(raw).__name__}")

        jobs: list[Job] = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            job = self.parse_record(entry)
            if job is not None:
                jobs.append(job)
        return jobs

    def _parse_one(self, entry: dict[str, Any]) -> Job | None:
        title = entry.get("name")
        posting_id = entry.get("id")
        if not title or not posting_id:
            return None

        # There is no `url` field in the payload. `ref` is the API endpoint,
        # not something a human can apply through, so the public posting URL is
        # built from the company token and id. Looking for `url` silently
        # dropped every posting: verify saw 100 and sync stored 0.
        url = entry.get("postingUrl") or (
            f"https://jobs.smartrecruiters.com/{self.token}/{posting_id}"
        )

        loc = entry.get("location") or {}
        if isinstance(loc, dict):
            location_name = (
                ", ".join(v for v in (loc.get("city"), loc.get("region"), loc.get("country")) if v)
                or None
            )
        else:
            location_name = str(loc) if loc else None

        info = parse_location(location_name)

        # `location.country` is a lowercase ISO code and beats prose parsing.
        country = loc.get("country") if isinstance(loc, dict) else None
        if isinstance(country, str) and len(country) == 2:
            info.country = country.upper()
            info.region = region_for(info.country)
        if isinstance(loc, dict) and loc.get("remote") is True:
            info.work_mode = WorkMode.REMOTE

        posted_at = parse_datetime(entry.get("releasedDate"))
        date_source = DateSource.EMPLOYER if posted_at else DateSource.DISCOVERED

        department = entry.get("department") or {}
        dep_label = department.get("label") if isinstance(department, dict) else None

        company_name = (entry.get("company") or {}).get("name") or self.company.name

        return ats_job(entry,
            url=url,
            source=self.source,
            layer=Layer.A,
            company=company_name,
            title=title.strip(),
            external_id=entry.get("id"),
            location=location_name,
            city=info.city,
            country=info.country,
            region=info.region,
            work_mode=info.work_mode,
            department=dep_label,
            description=None,  # descriptions require a separate API call
            language=None,
            posted_at=posted_at,
            date_source=date_source,
        )


# ---------------------------------------------------------------------------
# Recruitee — structural, unverified
# ---------------------------------------------------------------------------


class RecruiteeAdapter(ATSAdapter):
    """Recruitee job boards.

    GET https://{token}.recruitee.com/api/offers/

    Payload shape:
      {
        "offers": [
          {
            "id": 12345,
            "title": "Senior Backend Engineer",
            "slug": "senior-backend-engineer",
            "location": "Madrid, Spain",
            "department": "Engineering",
            "description": "<div>...</div>",
            "description_html": "<div>...</div>",
            "remote": true,
            "published_at": "2024-03-01T00:00:00.000Z",
            "created_at": "2024-02-15T00:00:00.000Z",
            "updated_at": "2024-03-15T00:00:00.000Z",
            "company_name": "Company",
            "careers_url": "https://company.recruitee.com",
            "tags": ["engineering", "backend"]
          }
        ]
      }

    `published_at` is the real publish date → date_source = employer.
    `created_at` / `updated_at` are never used as primary — only fallbacks.

    Recruitee sometimes moves posting URLs — `external_id` is critical here.
    """

    ats: ClassVar[str] = "recruitee"
    BASE_URL: ClassVar[str] = "https://{token}.recruitee.com/api/offers/"

    async def fetch_raw(self, client: HttpClient) -> Any:
        return await client.get_json(self.BASE_URL.format(token=self.token))

    def parse(self, raw: Any) -> list[Job]:
        if not isinstance(raw, dict) or not isinstance(raw.get("offers"), list):
            raise PermanentError(f"{self.source}: unexpected payload shape {type(raw).__name__}")

        jobs: list[Job] = []
        for entry in raw.get("offers") or []:
            job = self.parse_record(entry)
            if job is not None:
                jobs.append(job)
        return jobs

    def _parse_one(self, entry: dict[str, Any]) -> Job | None:
        title = entry.get("title")
        slug = entry.get("slug")
        careers_url = entry.get("careers_url")
        if not title or not careers_url:
            return None
        url = entry.get("offer_url") or f"{careers_url.rstrip('/')}/o/{slug or entry.get('id', '')}"

        location_name = entry.get("location")
        info = parse_location(location_name)

        if entry.get("remote") is True:
            info.work_mode = WorkMode.REMOTE

        posted_at = parse_datetime(entry.get("published_at"))
        date_source = DateSource.EMPLOYER
        if posted_at is None:
            posted_at = parse_datetime(entry.get("created_at"))
            date_source = DateSource.UPDATED if posted_at else DateSource.DISCOVERED

        description = html_to_text(entry.get("description_html"))
        if description is None:
            description = html_to_text(entry.get("description"))

        return ats_job(entry,
            url=url,
            source=self.source,
            layer=Layer.A,
            company=entry.get("company_name") or self.company.name,
            title=title.strip(),
            external_id=str(entry.get("id")) if entry.get("id") is not None else None,
            location=location_name,
            city=info.city,
            country=info.country,
            region=info.region,
            work_mode=info.work_mode,
            department=entry.get("department"),
            description=description,
            language=detect_language(description, declared=entry.get("workingLanguage")),
            posted_at=posted_at,
            date_source=date_source,
        )


# ---------------------------------------------------------------------------
# Personio — structural, unverified
# ---------------------------------------------------------------------------


class PersonioAdapter(ATSAdapter):
    """Personio job boards.

    GET https://{token}.jobs.personio.com/search.json

    Payload shape (varies — Personio has evolved their API):
      {
        "jobs": [
          {
            "id": 12345,
            "title": "Senior Backend Engineer",
            "location": "Madrid, Spain",
            "department": "Engineering",
            "description": "<div>...</div>",
            "published_at": "2024-03-01T00:00:00.000Z",
            "url": "https://company.jobs.personio.com/job/12345",
            "employment_type": "Full-time",
            "remote": false
          }
        ]
      }

    Older Personio boards return an array directly. Both shapes are handled.
    `published_at` → date_source = employer.
    """

    ats: ClassVar[str] = "personio"
    BASE_URL: ClassVar[str] = "https://{token}.jobs.personio.com/search.json"

    async def fetch_raw(self, client: HttpClient) -> Any:
        return await client.get_json(self.BASE_URL.format(token=self.token))

    def parse(self, raw: Any) -> list[Job]:
        # Personio returns either {"jobs": [...]} or [...] depending on version.
        if isinstance(raw, dict):
            entries = next((raw[k] for k in ("jobs", "data") if isinstance(raw.get(k), list)), None)
        elif isinstance(raw, list):
            entries = raw
        else:
            raise PermanentError(f"{self.source}: unexpected payload shape {type(raw).__name__}")

        if not isinstance(entries, list):
            raise PermanentError(f"{self.source}: expected a list of jobs")

        jobs: list[Job] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            job = self.parse_record(entry)
            if job is not None:
                jobs.append(job)
        return jobs

    def _parse_one(self, entry: dict[str, Any]) -> Job | None:
        title = entry.get("title") or entry.get("name")
        url = entry.get("url") or entry.get("link")
        if not title or not url:
            return None

        location_name = entry.get("location")
        info = parse_location(location_name)

        if entry.get("remote") is True:
            info.work_mode = WorkMode.REMOTE

        posted_at = parse_datetime(entry.get("published_at") or entry.get("publishedAt"))
        date_source = DateSource.EMPLOYER
        if posted_at is None:
            posted_at = parse_datetime(entry.get("created_at") or entry.get("createdAt"))
            date_source = DateSource.UPDATED if posted_at else DateSource.DISCOVERED

        description = html_to_text(entry.get("description"))

        return ats_job(entry,
            url=url,
            source=self.source,
            layer=Layer.A,
            company=entry.get("company_name") or entry.get("companyName") or self.company.name,
            title=title.strip(),
            external_id=str(entry.get("id")) if entry.get("id") is not None else None,
            location=location_name,
            city=info.city,
            country=info.country,
            region=info.region,
            work_mode=info.work_mode,
            department=entry.get("department") or entry.get("departmentName"),
            description=description,
            language=detect_language(description, declared=entry.get("workingLanguage")),
            posted_at=posted_at,
            date_source=date_source,
        )


# ---------------------------------------------------------------------------
# Factorial — structural, unverified
# ---------------------------------------------------------------------------


class FactorialAdapter(ATSAdapter):
    """Factorial HR job boards.

    GET https://{token}.factorialhr.com/api/v1/jobs

    Payload shape (from Factorial's public careers API):
      [
        {
          "id": 12345,
          "title": "Senior Backend Engineer",
          "location": "Madrid, Spain",
          "department": "Engineering",
          "description": "<div>...</div>",
          "published_at": "2024-03-01T00:00:00.000Z",
          "url": "https://company.factorialhr.com/job/12345",
          "remote": false,
          "employment_type": "Full-time"
        }
      ]

    `published_at` → date_source = employer.
    """

    ats: ClassVar[str] = "factorial"
    BASE_URL: ClassVar[str] = "https://{token}.factorialhr.com/api/v1/jobs"

    async def fetch_raw(self, client: HttpClient) -> Any:
        return await client.get_json(self.BASE_URL.format(token=self.token))

    def parse(self, raw: Any) -> list[Job]:
        if isinstance(raw, dict):
            entries = next((raw[k] for k in ("jobs", "data") if isinstance(raw.get(k), list)), None)
        elif isinstance(raw, list):
            entries = raw
        else:
            raise PermanentError(f"{self.source}: unexpected payload shape {type(raw).__name__}")

        if not isinstance(entries, list):
            raise PermanentError(f"{self.source}: expected a list of jobs")

        jobs: list[Job] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            job = self.parse_record(entry)
            if job is not None:
                jobs.append(job)
        return jobs

    def _parse_one(self, entry: dict[str, Any]) -> Job | None:
        title = entry.get("title")
        url = entry.get("url") or entry.get("link") or entry.get("apply_url")
        if not title or not url:
            return None

        location_name = entry.get("location")
        info = parse_location(location_name)

        if entry.get("remote") is True:
            info.work_mode = WorkMode.REMOTE

        posted_at = parse_datetime(entry.get("published_at") or entry.get("publishedAt"))
        date_source = DateSource.EMPLOYER if posted_at else DateSource.DISCOVERED

        description = html_to_text(entry.get("description"))

        return ats_job(entry,
            url=url,
            source=self.source,
            layer=Layer.A,
            company=self.company.name,
            title=title.strip(),
            external_id=str(entry.get("id")) if entry.get("id") is not None else None,
            location=location_name,
            city=info.city,
            country=info.country,
            region=info.region,
            work_mode=info.work_mode,
            department=entry.get("department"),
            description=description,
            language=detect_language(description, declared=entry.get("workingLanguage")),
            posted_at=posted_at,
            date_source=date_source,
        )


# ---------------------------------------------------------------------------
# Workday — structural, unverified
# ---------------------------------------------------------------------------

# Workday's public REST API follows this pattern:
#   POST https://{tenant}.wd3.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
#   Body: {"limit": 20, "offset": 0, "searchText": ""}
#
# Returns a deeply nested JSON structure. The canonical external_id is
# `bulletFields[0]` (the requisition ID). Without it a URL move orphans the row.
#
# Workday cannot be discovered from a name alone — the tenant and site are
# subdomain components that only appear in a direct careers-page URL.
# Registry entries for Workday must be added by hand with `--extra`:
#
#   forkjob registry add "Company" --ats workday \
#       --extra '{"host": "company.wd3.myworkdayjobs.com", "tenant": "company", "site": "External"}'


class WorkdayAdapter(ATSAdapter):
    """Workday external career sites.

    POST https://{host}/wday/cxs/{tenant}/{site}/jobs

    Workday URLs move aggressively — without the requisition ID as external_id,
    every schema refresh produces a fresh job_id and loses first_seen.

    `postedDate` is only present on some tenants. When absent, date_source is
    `discovered` — a Workday posting with no date is not old by default.
    """

    ats: ClassVar[str] = "workday"
    POST_PATH: ClassVar[str] = "/wday/cxs/{tenant}/{site}/jobs"
    MAX_OFFSET: ClassVar[int] = 5000  # safety cap
    PAGE_SIZE: ClassVar[int] = 20

    def __init__(self, company: Company) -> None:
        super().__init__(company)
        self.host = company.extra.get("host", "")
        self.site = company.extra.get("site", "External")

    @property
    def token(self) -> str:
        # Workday uses host/site from extra, not a plain token.
        return ""

    @property
    def source(self) -> str:
        return f"workday:{self.company.extra.get('tenant', self.company.name.lower())}"

    def _base_url(self) -> str:
        host = self.host.rstrip("/")
        if not host.startswith("https://"):
            host = f"https://{host}"
        if not self.host or not self.company.extra.get("tenant"):
            raise PermanentError("Workday requires registry host, tenant and site")
        return f"{host}{self.POST_PATH.format(tenant=self.company.extra["tenant"], site=self.site)}"

    async def fetch_raw(self, client: HttpClient) -> Any:
        rows, seen, errors = [], set(), []
        url, pages, more = self._base_url(), 0, True
        for offset in range(0, self.MAX_OFFSET, self.PAGE_SIZE):
            try:
                response = await client.request("POST", url, json={"limit": self.PAGE_SIZE, "offset": offset, "searchText": ""})
                data = response.json()
                if not isinstance(data, dict) or not isinstance(data.get("jobPostings"), list):
                    raise PermanentError("Workday missing jobPostings schema")
                postings = data["jobPostings"]
                ids = {str(r.get("externalPath")) for r in postings if isinstance(r, dict) and r.get("externalPath")}
                if postings and (not ids or ids <= seen):
                    raise PermanentError("Workday repeated/malformed page")
                if not postings and isinstance(data.get("total"), int) and len(rows) < data["total"]:
                    raise PermanentError("Workday empty page before total")
                rows.extend(r for r in postings if isinstance(r, dict) and str(r.get("externalPath")) not in seen)
                seen.update(ids)
                pages += 1
                more = len(rows) < data["total"] if isinstance(data.get("total"), int) else len(postings) >= self.PAGE_SIZE
                if not more:
                    break
            except (SourceError, ValueError) as exc:
                if not rows:
                    raise PermanentError("Workday invalid first response") from exc
                errors.append(type(exc).__name__ + ": " + str(exc))
                break
        cap = more and pages * self.PAGE_SIZE >= self.MAX_OFFSET
        self.telemetry = ScrapeTelemetry(items_seen=len(rows), pages_fetched=pages,
            page_limit=self.MAX_OFFSET // self.PAGE_SIZE, cap_hit=cap,
            partial_reason="; ".join(errors) or ("page_limit_reached" if cap else None),
            stop_reason="request_failed" if errors else "page_limit_reached" if cap else "exhausted")
        return rows

    def parse(self, raw: Any) -> list[Job]:
        if not isinstance(raw, list):
            raise PermanentError(f"{self.source}: unexpected payload shape {type(raw).__name__}")

        jobs: list[Job] = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            job = self.parse_record(entry)
            if job is not None:
                jobs.append(job)
        return jobs

    def _parse_one(self, entry: dict[str, Any]) -> Job | None:
        title = entry.get("title")
        url = entry.get("url")
        if not url and entry.get("externalPath") and self.host:
            url = urljoin("https://" + self.host.removeprefix("https://") + "/" + self.site + "/", entry["externalPath"].lstrip("/"))
        if not title or not url:
            return None

        location_name = entry.get("locationsText") or entry.get("location")
        info = parse_location(location_name)

        external_id = None
        bullet_fields = entry.get("bulletFields") or []
        if isinstance(bullet_fields, list) and len(bullet_fields) > 0:
            external_id = str(bullet_fields[0]) if bullet_fields[0] else None

        posted_at = parse_datetime(entry.get("postedDate"))
        # Workday's postedDate is not always present — do not guess employer.
        date_source = DateSource.EMPLOYER if posted_at else DateSource.DISCOVERED

        return ats_job(entry,
            url=url or "",
            source=self.source,
            layer=Layer.A,
            company=self.company.name,
            title=title.strip(),
            external_id=external_id,
            location=location_name,
            city=info.city,
            country=info.country,
            region=info.region,
            work_mode=info.work_mode,
            department=entry.get("department"),
            description=None,
            language=None,
            posted_at=posted_at,
            date_source=date_source,
        )


def _extract_workday_jobs(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Walk Workday's deeply nested JSON to find job postings.

    The exact path varies by tenant version; this probes known shapes.
    """
    # Most common: data.jobPostings
    if isinstance(data.get("jobPostings"), list):
        return data["jobPostings"]

    # Some versions: data.body.children[0].children[0].jobPostings
    body = data.get("body")
    if isinstance(body, dict):
        children = body.get("children", [])
        for child in children:
            if isinstance(child, dict):
                for inner in child.get("children", []):
                    if isinstance(inner, dict) and isinstance(inner.get("jobPostings"), list):
                        return inner["jobPostings"]

    # Unrecognized shell/navigation records are not jobs.
    raise PermanentError("Workday missing recognized jobPostings contract")


def _find_job_list(node: Any, depth: int = 0) -> list[dict[str, Any]]:
    if depth > 6 or not isinstance(node, (dict, list)):
        return []
    if (
        isinstance(node, list)
        and len(node) > 0
        and isinstance(node[0], dict)
        and any("title" in (item or {}) for item in node if isinstance(item, dict))
    ):
        return [item for item in node if isinstance(item, dict)]
    if isinstance(node, dict):
        for value in node.values():
            result = _find_job_list(value, depth + 1)
            if result:
                return result
    return []


class TeamtailorAdapter(ATSAdapter):
    """Teamtailor job boards.

    GET https://{token}.teamtailor.com/jobs.json

    Teamtailor hosts career pages for ~8,000 companies, heavily concentrated
    in Nordics (Sweden, Finland) and DACH region. The public /jobs.json
    endpoint returns all published postings without auth.
    """

    ats: ClassVar[str] = "teamtailor"
    BASE_URL: ClassVar[str] = "https://{token}.teamtailor.com/jobs.json"

    async def fetch_raw(self, client: HttpClient) -> Any:
        return await client.get_json(self.BASE_URL.format(token=self.token))

    def parse(self, raw: Any) -> list[Job]:
        if isinstance(raw, dict):
            entries = next((raw[k] for k in ("jobs", "data") if isinstance(raw.get(k), list)), None)
        elif isinstance(raw, list):
            entries = raw
        else:
            raise PermanentError(f"{self.source}: unexpected payload shape {type(raw).__name__}")

        if not isinstance(entries, list):
            raise PermanentError(f"{self.source}: expected a list of jobs")

        jobs: list[Job] = []
        for entry in entries:
            if isinstance(entry, dict):
                job = self.parse_record(entry)
                if job is not None:
                    jobs.append(job)
        return jobs

    def _parse_one(self, entry: dict[str, Any]) -> Job | None:
        title = entry.get("title") or entry.get("name")
        if not title:
            return None

        job_id = entry.get("id") or entry.get("slug")
        url = entry.get("url") or entry.get("applyUrl")
        if not url and job_id:
            url = f"https://{self.token}.teamtailor.com/jobs/{job_id}"

        location_name = entry.get("location") or entry.get("city")
        info = parse_location(location_name)

        if entry.get("remote") is True:
            info.work_mode = WorkMode.REMOTE

        posted_at = parse_datetime(entry.get("published_at"))
        date_source = DateSource.EMPLOYER if posted_at else DateSource.DISCOVERED
        if posted_at is None:
            posted_at = parse_datetime(entry.get("created_at"))
            date_source = DateSource.UPDATED if posted_at else DateSource.DISCOVERED

        description = html_to_text(entry.get("description") or entry.get("body"))

        return ats_job(entry,
            url=url,
            source=self.source,
            layer=Layer.A,
            company=entry.get("company_name") or self.company.name,
            title=title.strip(),
            external_id=str(job_id) if job_id else None,
            location=location_name,
            city=info.city,
            country=info.country,
            region=info.region,
            work_mode=info.work_mode,
            department=entry.get("department") or entry.get("departmentName"),
            description=description,
            language=detect_language(description, declared=entry.get("workingLanguage")),
            posted_at=posted_at,
            date_source=date_source,
        )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

#: ATS name -> adapter class.
ADAPTERS: dict[str, type[ATSAdapter]] = {
    GreenhouseAdapter.ats: GreenhouseAdapter,
    LeverAdapter.ats: LeverAdapter,
    AshbyAdapter.ats: AshbyAdapter,
    WorkableAdapter.ats: WorkableAdapter,
    SmartRecruitersAdapter.ats: SmartRecruitersAdapter,
    RecruiteeAdapter.ats: RecruiteeAdapter,
    PersonioAdapter.ats: PersonioAdapter,
    FactorialAdapter.ats: FactorialAdapter,
    WorkdayAdapter.ats: WorkdayAdapter,
    TeamtailorAdapter.ats: TeamtailorAdapter,
}


def build_adapter(company: Company) -> ATSAdapter | None:
    """Return an adapter for a registry entry, or None if none is implemented."""
    adapter_cls = ADAPTERS.get(company.ats)
    return adapter_cls(company) if adapter_cls else None
