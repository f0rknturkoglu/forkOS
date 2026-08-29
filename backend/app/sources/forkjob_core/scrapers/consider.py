"""VC portfolio boards (consider.co) — Sequoia, a16z and similar.

Verified 2026-08-09.

The board calls::

    POST https://jobs.sequoiacap.com/api-boards/search-jobs

with a JSON body that selects the parent ``sequoia-capital`` board, requests
50 results and groups jobs by company.

Two fields nothing else in this project carries: ``minYearsExp`` (a number, not
a prose guess) and a structured salary range (``minValue``/``maxValue``/``currency``).
That makes it the best junior filter in the registry.

Per-job fields: ``applyUrl``, ``companyName``, ``locations``,
``normalizedLocations``, ``salary``, ``skills``, ``requiredSkills``,
``preferredSkills``, ``minYearsExp``, ``considerLevels``, ``departments``,
``jobFunctions``, ``remote``, ``hybrid``, ``timeStamp`` (ISO 8601, real publish
date → ``date_source`` is ``employer``), ``jobId``.

Per-company fields: ``investors``, ``investorSlugs``, ``markets``, ``stages``,
``numRemoteJobs``, ``fractionRemote``, ``website``.
"""

from __future__ import annotations

import json
from typing import Any

from ..geo import region_for
from ..models import DateSource, Job, Layer, Region, WorkMode
from ..normalize import parse_datetime, parse_location
from .base import ScraperBase, ScraperConfig, ScraperHttpClient, ScraperPermanentError

PAGE_SIZE = 50


class ConsiderScraper(ScraperBase):
    """One VC portfolio board running on consider.co."""

    source_key = "consider"
    label = "Consider"

    def __init__(
        self,
        config: ScraperConfig | None = None,
        *,
        board_id: str = "",
        board_label: str = "",
        base_url: str = "",
    ) -> None:
        super().__init__(config)
        self.board_id: str = board_id
        self.board_label: str = board_label
        self.base_url: str = base_url.rstrip("/")

    @property
    def source(self) -> str:
        return f"consider:{self.board_id}"

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()
        meta: dict[str, Any] = {"size": PAGE_SIZE}
        page = 0
        jobs_url = f"{self.base_url}/jobs"
        csrf_token = _csrf_token(await client.get_html(jobs_url))
        request_headers = {
            "x-csrf-token": csrf_token,
            "origin": self.base_url,
            "referer": jobs_url,
        }

        while True:
            body: dict[str, Any] = {
                # Copied, not shared: `meta` is mutated below to carry the next
                # page token, so passing the live dict means the body of a
                # request already sent keeps changing underneath it.
                "meta": dict(meta),
                "board": {"id": self.board_id, "isParent": True},
                "query": {},
                "grouped": True,
            }
            payload = await client.post_json(
                f"{self.base_url}/api-boards/search-jobs", body, headers=request_headers
            )
            page += 1

            groups = self._parse_groups(payload)
            if not groups:
                break

            for group in groups:
                company_info = group.get("company", {}) if isinstance(group, dict) else {}
                for entry in group.get("jobs") or []:
                    if not isinstance(entry, dict):
                        continue
                    job = self._build_job(entry, company_info)
                    if job is None:
                        continue
                    dedup_key = job.external_id or job.url
                    if dedup_key in seen:
                        continue
                    seen.add(dedup_key)
                    jobs.append(job)

            # Pagination: the server returns a `sequence` token in meta.
            new_meta = payload.get("meta") if isinstance(payload, dict) else None
            seq = new_meta.get("sequence") if isinstance(new_meta, dict) else None
            if not seq:
                break
            meta["sequence"] = seq

            # Safety valve: a buggy pagination loop must not run forever.
            if page > 200:
                break

        return jobs

    # -- parsing ---------------------------------------------------------------

    @staticmethod
    def _parse_groups(payload: Any) -> list[dict[str, Any]]:
        if not isinstance(payload, dict):
            raise ScraperPermanentError(
                f"consider: unexpected payload shape {type(payload).__name__}; "
                "expected an object with a 'jobs' list"
            )
        groups = payload.get("jobs")
        if not isinstance(groups, list):
            return []
        return [g for g in groups if isinstance(g, dict)]

    def _build_job(self, entry: dict[str, Any], company_info: dict[str, Any]) -> Job | None:
        title = (entry.get("title") or "").strip()
        url = (entry.get("applyUrl") or entry.get("url") or "").strip()
        if not title or not url:
            return None

        company = (entry.get("companyName") or company_info.get("name") or "").strip() or "?"

        # Location: prefer the first free-text entry.
        locations = entry.get("locations")
        location: str | None = None
        if isinstance(locations, list) and locations:
            location = str(locations[0]).strip() or None

        # Resolve country and work mode from the location prose.
        loc_info = parse_location(location)
        country = loc_info.country
        city = loc_info.city

        # Work mode
        work_mode = WorkMode.UNKNOWN
        if entry.get("remote"):
            work_mode = WorkMode.REMOTE
        elif entry.get("hybrid"):
            work_mode = WorkMode.HYBRID
        elif loc_info.work_mode is not WorkMode.UNKNOWN:
            work_mode = loc_info.work_mode
        elif location:
            work_mode = WorkMode.ONSITE

        # Description: enrich with structured fields the scorer can read.
        description_parts: list[str] = []

        # Seniority signal — this is the unique value of this source.
        min_years = entry.get("minYearsExp")
        if isinstance(min_years, (int, float)):
            description_parts.append(f"Min experience: {min_years} years")
        levels = entry.get("considerLevels")
        if isinstance(levels, list) and levels:
            # Each entry is [min, max] or a label object — normalise to text.
            level_texts: list[str] = []
            for lv in levels:
                if isinstance(lv, list) and len(lv) == 2:
                    level_texts.append(f"{lv[0]}-{lv[1]}")
                elif isinstance(lv, dict):
                    level_texts.append(str(lv.get("label", lv.get("value", ""))))
                elif lv is not None:
                    level_texts.append(str(lv))
            if level_texts:
                description_parts.append(f"Levels: {', '.join(level_texts)}")

        # Skills — structured, curated by the poster.
        skills_all: list[str] = []
        for key in ("skills", "requiredSkills", "preferredSkills"):
            skills_list = entry.get(key)
            if isinstance(skills_list, list):
                for s in skills_list:
                    if isinstance(s, dict):
                        label = s.get("label") or s.get("value") or ""
                        if label:
                            skills_all.append(str(label))
                    elif isinstance(s, str):
                        skills_all.append(s)
        if skills_all:
            # Deduplicate while preserving order.
            seen_skills: set[str] = set()
            unique: list[str] = []
            for s in skills_all:
                if s.lower() not in seen_skills:
                    seen_skills.add(s.lower())
                    unique.append(s)
            description_parts.append(f"Skills: {', '.join(unique)}")

        # Salary
        salary = entry.get("salary")
        salary_text: str | None = None
        if isinstance(salary, dict):
            parts: list[str] = []
            min_v = salary.get("minValue")
            max_v = salary.get("maxValue")
            currency = salary.get("currency")
            curr_label = (
                currency.get("label") or currency.get("value") or ""
                if isinstance(currency, dict)
                else ""
            )
            if min_v is not None and max_v is not None:
                parts.append(f"{min_v}-{max_v}")
            elif min_v is not None:
                parts.append(str(min_v))
            elif max_v is not None:
                parts.append(str(max_v))
            if curr_label:
                parts.append(str(curr_label))
            salary_text = " ".join(parts) or None
            if salary_text:
                description_parts.append(f"Salary: {salary_text}")

        # Departments / job functions
        functions = entry.get("jobFunctions")
        if isinstance(functions, list):
            func_labels = [
                str(f.get("label", f.get("value", ""))) for f in functions if isinstance(f, dict)
            ]
            func_labels = [label for label in func_labels if label]
            if func_labels:
                description_parts.append(f"Functions: {', '.join(func_labels)}")

        # Company context — investors, markets, stages.
        if isinstance(company_info, dict):
            investors = company_info.get("investors")
            if isinstance(investors, list) and investors:
                description_parts.append(f"Investors: {', '.join(str(i) for i in investors)}")
            stages = company_info.get("stages")
            if isinstance(stages, list) and stages:
                description_parts.append(f"Stages: {', '.join(str(s) for s in stages)}")

        description = "\n".join(description_parts) or None

        department: str | None = None
        depts = entry.get("departments")
        if isinstance(depts, list):
            dept_labels: list[str] = []
            for d in depts:
                if isinstance(d, dict):
                    label = str(d.get("label", d.get("value", "")))
                    if label:
                        dept_labels.append(label)
                elif isinstance(d, str):
                    dept_labels.append(d)
            department = ", ".join(dept_labels[:2]) or None

        posted_at = parse_datetime(entry.get("timeStamp"))

        external_id = str(entry.get("jobId")) if entry.get("jobId") else None

        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=company,
            title=title,
            external_id=external_id,
            location=location,
            city=city,
            country=country,
            region=region_for(country) if country else Region.UNKNOWN,
            work_mode=work_mode,
            remote=entry.get("remote") or None,
            department=department,
            description=description,
            salary=salary_text,
            posted_at=posted_at,
            date_source=DateSource.EMPLOYER if posted_at else DateSource.DISCOVERED,
        )


def _csrf_token(body: str) -> str:
    marker = "window.serverInitialData"
    start = body.find(marker)
    if start < 0:
        raise ScraperPermanentError("consider: serverInitialData bulunamadı")
    assignment = body.find("=", start + len(marker))
    if assignment < 0:
        raise ScraperPermanentError("consider: serverInitialData ataması bulunamadı")
    try:
        payload, _ = json.JSONDecoder().raw_decode(body[assignment + 1 :].lstrip())
    except json.JSONDecodeError as exc:
        raise ScraperPermanentError("consider: serverInitialData JSON bozuk") from exc
    token = payload.get("csrfToken") if isinstance(payload, dict) else None
    if not isinstance(token, str) or not token:
        raise ScraperPermanentError("consider: csrfToken bulunamadı")
    return token
