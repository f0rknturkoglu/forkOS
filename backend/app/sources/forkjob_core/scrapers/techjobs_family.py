"""Current TechJobs frontend JSON contract, verified 2026-10-01.

/api/jobsLight is independent of the retired /api/jobs. Full prose costs
one sequential request to /api/jobWithUrl/<slug>.
"""

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote
from xml.etree import ElementTree

from ..geo import region_for
from ..models import Job, Layer, WorkMode, canonical_url, date_source_for
from ..normalize import html_to_text, parse_datetime
from ..rich_text import enrich, merge_descriptions
from .base import ScrapeBatch, ScraperBase, ScraperError, ScraperHttpClient, ScraperPermanentError


@dataclass(frozen=True)
class TechJobsSiteSpec:
    key: str
    label: str
    domain: str
    country: str
    country_name: str
    currency: str


class TechJobsFamilyScraper(ScraperBase):
    spec: TechJobsSiteSpec

    def __init__(self, config=None, *, max_offers: int = 1000, detail_budget: int = 20):
        super().__init__(config)
        self.source_key, self.label = self.spec.key, self.spec.label
        self.base_url = f"https://{self.spec.domain}"
        self.max_offers = max(1, int(max_offers))
        self.detail_budget = max(0, int(detail_budget))

    def entries(self, payload: Any) -> list[dict]:
        if not isinstance(payload, list):
            raise ScraperPermanentError(f"{self.source}: unexpected jobsLight schema")
        if payload and not any(isinstance(row, dict) and row.get("jobUrl") for row in payload):
            raise ScraperPermanentError(f"{self.source}: no recognized job entries")
        return [row for row in payload if isinstance(row, dict)]

    def parse(self, payload: Any) -> list[Job]:
        rows = self.entries(payload)
        jobs = self.dedup_seen(set(), [job for row in rows if (job := self.build_job(row))])
        if (
            rows
            and not jobs
            and not all(row.get("isPaused") or row.get("isDisabledOrOutdated") for row in rows)
        ):
            raise ScraperPermanentError(f"{self.source}: no valid jobs in nonempty response")
        return jobs

    def build_job(self, row: dict) -> Job | None:
        try:
            return self._build_job(row)
        except (TypeError, ValueError, AttributeError):
            return None  # A malformed record must not discard the other jobs.

    def _build_job(self, row: dict) -> Job | None:
        title, slug, company = row.get("name"), row.get("jobUrl"), row.get("company")
        if not all(isinstance(value, str) and value.strip() for value in (title, slug, company)):
            return None
        if row.get("isDisabledOrOutdated") or row.get("isPaused"):
            return None
        mode = {
            "office": WorkMode.ONSITE,
            "remote": WorkMode.REMOTE,
            "hybrid": WorkMode.HYBRID,
        }.get(row.get("workplace"), WorkMode.UNKNOWN)
        scope = {
            "anywhere": "Anywhere",
            "onlycountry": f"{self.spec.country_name} only",
            "countryandeu": f"{self.spec.country_name} and EU only",
        }.get(row.get("remoteType"))
        tech = (
            [x.strip() for x in row.get("technologies", []) if isinstance(x, str) and x.strip()]
            if isinstance(row.get("technologies"), list)
            else []
        )
        visa = row.get("hasVisaSponsorship")
        visa = visa if visa in ("Yes", "No") else None
        parts = [
            html_to_text(row.get(key))
            for key in (
                "description",
                "requirementsMustTextArea",
                "requirementsNiceTextArea",
                "responsibilitiesTextArea",
            )
        ]
        salary = self.salary(row)
        description = enrich(
            "\n\n".join(x for x in parts if x) or None,
            self.source,
            {
                "Visa sponsorship": visa,
                "Experience level": row.get("expLevel"),
                "Language": row.get("language"),
                "Technologies": ", ".join(dict.fromkeys(tech)),
                "Remote scope": scope,
                "Employment type": row.get("jobType"),
                "Salary": salary,
                "Application URL": row.get("redirectJobUrl"),
            },
        )
        city = row.get("actualCity") or row.get("cityCategory")
        location = ", ".join(str(x) for x in (city, self.spec.country_name) if x)
        # activeFrom is the source's current activation date, not necessarily original publication.
        posted, provenance = date_source_for(
            None, parse_datetime(row.get("activeFrom")) or parse_datetime(row.get("updatedAt"))
        )
        return Job.build(
            url=canonical_url(f"{self.base_url}/jobs/{quote(slug, safe='-_')}"),
            source=self.source,
            layer=Layer.B,
            company=company.strip(),
            title=title.strip(),
            external_id=str(row["_id"]) if row.get("_id") else None,
            location=location,
            city=city,
            country=self.spec.country,
            region=region_for(self.spec.country),
            work_mode=mode,
            salary=salary,
            language=row.get("language"),
            department=row.get("techCategory"),
            description=description,
            posted_at=posted,
            date_source=provenance,
        )

    def salary(self, row: dict) -> str | None:
        low, high = row.get("annualSalaryFrom"), row.get("annualSalaryTo")
        period = "year"
        if low is None and high is None:
            low, high = row.get("contractRateFrom"), row.get("contractRateTo")
            period = row.get("contractRateType") or "source period unspecified"
        if not any(isinstance(x, (int, float)) for x in (low, high)):
            return None
        values = [f"{x:,}" for x in (low, high) if isinstance(x, (int, float))]
        return f"{self.spec.currency} {' - '.join(values)} per {period}"

    async def scrape(self, client: ScraperHttpClient) -> ScrapeBatch:
        payload = await client.get_json(f"{self.base_url}/api/jobsLight")
        rows = self.entries(payload)
        jobs = self.parse(payload)
        total = len(jobs)
        jobs = jobs[: self.max_offers]
        errors, pages, attempted, succeeded = [], 1, 1, 1
        feed_bodies = {}
        if jobs:
            attempted += 1
            try:
                xml = await client.get_html(f"{self.base_url}/rss")
                pages += 1
                feed_bodies = self.parse_feed(xml)
                succeeded += 1
            except (ScraperError, ValueError) as exc:
                errors.append(f"RSS enrichment: {exc}")
        pending = []
        for index, job in enumerate(jobs):
            if body := feed_bodies.get(job.url):
                job.description = merge_descriptions(job.description, body)
            else:
                pending.append(index)
        by_url = {job.url: row for row in rows if (job := self.build_job(row))}
        detail_success = 0
        for index in pending[: self.detail_budget]:
            job = jobs[index]
            row = by_url[job.url]
            attempted += 1
            try:
                detail = await client.get_json(
                    f"{self.base_url}/api/jobWithUrl/{quote(row.get('jobUrl', ''), safe='-_')}"
                )
                pages += 1
                if not isinstance(detail, dict) or detail.get("_id") != row.get("_id"):
                    raise ScraperPermanentError("unrecognized/mismatched detail schema")
                richer = self.build_job({**row, **detail})
                if richer is None:
                    raise ScraperPermanentError("detail became inactive or malformed")
                jobs[index] = richer
                succeeded += 1
                detail_success += 1
            except (ScraperError, ValueError) as exc:
                errors.append(f"{job.url}: {exc}")
        stop = (
            "max_offers_reached"
            if total > self.max_offers
            else "detail_budget_reached"
            if len(pending) > self.detail_budget
            else "exhausted"
        )
        cap = stop != "exhausted"
        telemetry = self.record_telemetry(
            items_seen=len(rows),
            items_returned=len(jobs),
            pages_fetched=pages,
            result_limit=self.max_offers,
            cap_hit=cap,
            stop_reason=stop,
            partial_reason=stop if cap else "; ".join(errors) or None,
            metadata={
                "transport": "public_frontend_json_rss",
                "detail_budget": self.detail_budget,
                "details_attempted": min(len(pending), self.detail_budget),
                "details_succeeded": detail_success,
                "rss_enriched": len(jobs) - len(pending),
                "listing_jobs": total,
            },
        )
        return ScrapeBatch(jobs, errors, attempted, succeeded, telemetry)

    def parse_feed(self, xml: str) -> dict[str, str]:
        try:
            root = ElementTree.fromstring(xml)
        except ElementTree.ParseError as exc:
            raise ScraperPermanentError(f"{self.source}: unrecognized RSS schema") from exc
        if root.tag != "rss" or root.find("channel") is None:
            raise ScraperPermanentError(f"{self.source}: unrecognized RSS schema")
        bodies = {}
        for item in root.findall("./channel/item"):
            url = item.findtext("link")
            raw = item.findtext(
                "{http://purl.org/rss/1.0/modules/content/}encoded"
            ) or item.findtext("description")
            if url and url.startswith(self.base_url + "/jobs/") and raw:
                body = html_to_text(raw)
                if body:
                    bodies[canonical_url(url)] = body
        return bodies


class GermanTechJobsScraper(TechJobsFamilyScraper):
    source_key = "germantechjobs"
    spec = TechJobsSiteSpec(
        source_key, "GermanTechJobs", "germantechjobs.de", "DE", "Germany", "EUR"
    )


class SwissDevJobsScraper(TechJobsFamilyScraper):
    source_key = "swissdevjobs"
    spec = TechJobsSiteSpec(
        source_key, "SwissDevJobs", "swissdevjobs.ch", "CH", "Switzerland", "CHF"
    )
