"""No Fluff Jobs (nofluffjobs.com) — CEE tech job board.

    POST https://nofluffjobs.com/api/search/posting
        ?page=1&salaryCurrency=PLN&salaryPeriod=month&region=pl
        {"rawSearch": "", "criteriaSearch": {"seniority": [...]}}

Salary transparency is mandatory. Visa sponsorship and B2B remote common.

Three details the endpoint does not forgive, all found by calling it:

* `salaryCurrency`, `salaryPeriod` and `region` are required *query* params.
  Without them the API answers 400 "Required parameter 'salaryCurrency' is not
  present" — which the scraper used to swallow as an empty page.
* The body key is `criteriaSearch`, not `criteria`. A body of `{}` is a 500,
  and `{"criteriaSearch": {"country": ["pl"]}}` parses as the literal keyword
  `country=pl` and matches nothing. Only `rawSearch` + `criteriaSearch` works.
* `page` is a query param. Sending it in the body does nothing, so every page
  used to be page one.

Verified 2026-08-09: 692 junior postings across 7 pages.
"""

from __future__ import annotations

from typing import Any

from ..geo import country_from_name, region_for
from ..models import Job, Layer, Region, WorkMode, date_source_for
from ..normalize import parse_epoch_ms
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError

API_URL = "https://nofluffjobs.com/api/search/posting"

#: The board serves one currency per region; `pl` is the full catalogue.
QUERY = "salaryCurrency=PLN&salaryPeriod=month&region=pl"

#: Server-side filter. The board's own vocabulary — anything else is ignored
#: silently rather than rejected, so these strings are worth keeping exact.
SENIORITY = ["trainee", "junior"]


class NoFluffJobsScraper(ScraperBase):
    source_key = "nofluffjobs"
    label = "No Fluff Jobs"
    base_url = "https://nofluffjobs.com"

    def __init__(self, config: Any = None, *, max_pages: int = 8) -> None:
        super().__init__(config)
        self.max_pages = max_pages

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        jobs: list[Job] = []
        pages_fetched = 0
        items_seen = 0
        cap_hit = False
        total_pages: int | None = None

        for page in range(1, self.max_pages + 1):
            try:
                payload = await client.post_json(
                    f"{API_URL}?page={page}&{QUERY}",
                    payload={"rawSearch": "", "criteriaSearch": {"seniority": SENIORITY}},
                )
            except ScraperPermanentError:
                break
            pages_fetched += 1
            page_jobs = self.parse(payload)
            items_seen += len(page_jobs)
            if not page_jobs:
                break
            jobs.extend(page_jobs)
            # The response knows how long the result set is; asking for page 8
            # of 7 returns an empty list, so stop before spending the request.
            total_pages = payload.get("totalPages") if isinstance(payload, dict) else None
            if page == self.max_pages and isinstance(total_pages, int) and page < total_pages:
                cap_hit = True
            if isinstance(total_pages, int) and page >= total_pages:
                break

        stop_reason = "max_pages_reached" if cap_hit else "exhausted"
        self.record_telemetry(
            items_seen=items_seen,
            items_returned=len(jobs),
            pages_fetched=pages_fetched,
            page_limit=self.max_pages,
            result_limit=None,
            cap_hit=cap_hit,
            stop_reason=stop_reason,
            partial_reason="max_pages_reached" if cap_hit else None,
        )
        return jobs

    def parse(self, payload: Any) -> list[Job]:
        entries = payload
        if isinstance(payload, dict):
            entries = payload.get("postings") or []
        if not isinstance(entries, list):
            return []
        jobs: list[Job] = []
        for entry in entries:
            if isinstance(entry, dict):
                job = self._parse_one(entry)
                if job is not None:
                    jobs.append(job)
        return self._dedupe(jobs)

    @staticmethod
    def _dedupe(jobs: list[Job]) -> list[Job]:
        """Collapse the one-posting-per-province copies of a single job.

        A posting open to the whole country is republished under every
        voivodeship it accepts — one Upvanta opening came back as six postings
        with six ids, six URLs and the identical "Remote, PL" location. They
        differ only in the province slug, so nothing downstream separates them
        and the list fills up with the same job.

        Keep the shortest URL of each group: that is the unqualified one.
        """
        best: dict[tuple[str, str, str | None], Job] = {}
        for job in jobs:
            key = (job.company.casefold(), job.title.casefold(), job.location)
            current = best.get(key)
            if current is None or len(job.url) < len(current.url):
                best[key] = job
        return list(best.values())

    def _parse_one(self, entry: dict[str, Any]) -> Job | None:
        title = (entry.get("title") or "").strip()
        if not title:
            return None

        job_id = entry.get("id")
        slug = entry.get("url") or job_id
        if not slug:
            return None
        url = f"{self.base_url}/job/{slug}"

        company = (entry.get("name") or "?").strip()

        # There are two `fullyRemote` flags and only the nested one is filled
        # in: the top-level copy was False on all 118 postings of a live page
        # while location.fullyRemote was True on 106 of them.
        location_block = entry.get("location")
        location, country = self._place(location_block)
        remote = bool(entry.get("fullyRemote")) or bool(
            isinstance(location_block, dict) and location_block.get("fullyRemote")
        )
        work_mode = WorkMode.REMOTE if remote else WorkMode.ONSITE

        salary = self._salary(entry.get("salary"))

        # The search response carries no description; what it does carry is the
        # board's own taxonomy, which is what scoring reads.
        details = []
        seniority = entry.get("seniority")
        if isinstance(seniority, list) and seniority:
            details.append(f"Seniority: {', '.join(str(s) for s in seniority)}")
        if entry.get("category"):
            details.append(f"Category: {entry['category']}")
        tiles = entry.get("tiles")
        if isinstance(tiles, list) and tiles:
            names = [str(t.get("value") or t.get("name")) for t in tiles if isinstance(t, dict)]
            names = [n for n in names if n and n != "None"]
            if names:
                details.append(f"Skills: {', '.join(names)}")

        posted_at = parse_epoch_ms(entry.get("posted"))
        renewed_at = parse_epoch_ms(entry.get("renewed"))
        posted_at, date_source = date_source_for(posted_at, renewed_at)

        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=company,
            title=title,
            external_id=str(job_id) if job_id else str(slug),
            location=location,
            country=country,
            region=region_for(country) if country else Region.EU,
            work_mode=work_mode,
            remote=True if remote else None,
            description="\n".join(details),
            salary=salary,
            posted_at=posted_at,
            date_source=date_source,
        )

    def _place(self, location: Any) -> tuple[str | None, str | None]:
        """Pick a city out of `location.places`.

        Postings list every province they are open to, each as its own entry
        flagged `provinceOnly`. Only the entries with a real city say where the
        work actually is.
        """
        if not isinstance(location, dict):
            return None, None
        places = location.get("places")
        if not isinstance(places, list):
            return None, None

        # Any entry can carry the country, and the "Remote" one never does —
        # so resolve it across the whole list before picking a city.
        country = None
        for place in places:
            if isinstance(place, dict):
                country = self._country(place.get("country"))
                if country:
                    break

        for place in places:
            if not isinstance(place, dict) or place.get("provinceOnly"):
                continue
            city = (place.get("city") or "").strip()
            if not city:
                continue
            if city.lower() == "remote":
                # "Remote" is not a place; the country is still worth keeping.
                return (f"Remote, {country}" if country else "Remote"), country
            return (f"{city}, {country}" if country else city), country

        # Province-only postings still tell us the country.
        return (country, country) if country else (None, None)

    @staticmethod
    def _country(block: Any) -> str | None:
        """Resolve an ISO-3166 alpha-2 code out of a `country` block.

        The board emits two shapes: `{"code": "POL", "name": "Poland"}` and
        `{"code": "pl", "name": "Polish"}` — the second names the *language*,
        so the name is only trustworthy when the code is not already alpha-2.
        """
        if not isinstance(block, dict):
            return None
        code = (block.get("code") or "").strip()
        if len(code) == 2:
            return code.upper()
        name = (block.get("name") or "").strip()
        return country_from_name(name) if name else None

    @staticmethod
    def _salary(sal: Any) -> str | None:
        if not isinstance(sal, dict):
            return None
        frm, to = sal.get("from"), sal.get("to")
        currency = (sal.get("currency") or "PLN").upper()
        if frm and to:
            return f"{int(frm):,} - {int(to):,} {currency}"
        if frm:
            return f"{int(frm):,}+ {currency}"
        return None