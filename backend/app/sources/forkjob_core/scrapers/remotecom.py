"""Remote.com public SSR listings and detail Flight state (2026-10-01).

No private GraphQL/auth dependency. Monetary values are minor units, verified
against the rendered salary; page totals come from jobsData.
"""

import json
import re
from typing import Any

from ..geo import country_code, region_for
from ..models import Job, Layer, Region, WorkMode, canonical_url, date_source_for
from ..normalize import html_to_text, parse_datetime
from ..rich_text import enrich
from .detail_evidence import richness_metadata
from .base import ScrapeBatch, ScraperBase, ScraperError, ScraperPermanentError

BASE = "https://remote.com"
_PUSH = re.compile(r"self\.__next_f\.push\((.*?)\)</script>", re.S)
_RECORD = re.compile(r"(?:^|\n)([0-9a-f]+):")


def flight_records(html: str) -> dict[str, Any]:
    """Decode inert JSON/text records, never execute the site's JavaScript."""
    chunks = []
    for match in _PUSH.finditer(html):
        try:
            payload = json.loads(match.group(1))
        except (ValueError, TypeError):
            continue
        if (
            isinstance(payload, list)
            and len(payload) > 1
            and payload[0] == 1
            and isinstance(payload[1], str)
        ):
            chunks.append(payload[1])
    stream = "".join(chunks).encode("utf-8")
    records = {}
    decoder = json.JSONDecoder()
    cursor = 0
    while cursor < len(stream):
        if stream[cursor : cursor + 1] == b"\n":
            cursor += 1
            continue
        header = re.match(rb"([0-9a-f]+):", stream[cursor:])
        if not header:
            end = stream.find(b"\n", cursor)
            cursor = end + 1 if end >= 0 else len(stream)
            continue
        key = header.group(1).decode()
        cursor += header.end()
        tail = stream[cursor:]
        try:
            if tail.startswith(b"T"):
                text_header = re.match(rb"T([0-9a-f]+),", tail)
                if not text_header:
                    raise ValueError("invalid text record")
                start = cursor + text_header.end()
                end = start + int(text_header.group(1), 16)
                records[key] = stream[start:end].decode("utf-8")
                cursor = end
            else:
                value, length = decoder.raw_decode(tail.decode("utf-8"))
                records[key] = value
                cursor += len(tail.decode("utf-8")[:length].encode("utf-8"))
        except (ValueError, UnicodeError):
            end = stream.find(b"\n", cursor)
            cursor = end + 1 if end >= 0 else len(stream)
    return records


def walk(value):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)


class RemoteComScraper(ScraperBase):
    source_key = "remotecom"
    label = "Remote.com Jobs"
    base_url = BASE

    def __init__(
        self, config=None, *, max_pages: int = 5, max_offers: int = 100, detail_budget: int = 20
    ):
        super().__init__(config)
        self.max_pages, self.max_offers = max(1, int(max_pages)), max(1, int(max_offers))
        self.detail_budget = max(0, int(detail_budget))

    def listing(self, html: str) -> dict:
        records = flight_records(html)
        for root in records.values():
            for node in walk(root):
                if isinstance(node.get("jobsData"), dict):
                    data = node["jobsData"]
                    if isinstance(data.get("jobs"), list) and isinstance(
                        data.get("totalPages"), int
                    ):
                        return data
        raise ScraperPermanentError(
            "remotecom: missing public jobsData schema (challenge/login/layout change)"
        )

    def parse_offer(self, html: str) -> Job | None:
        records = flight_records(html)
        for root in records.values():
            for node in walk(root):
                if (
                    node.get("title")
                    and node.get("slug")
                    and "hiringLocation" in node
                    and "description" in node
                ):
                    row = dict(node)
                    description = row.get("description")
                    if isinstance(description, str) and description.startswith("$"):
                        row["description"] = records.get(description[1:])
                    return self.build_job(row)
        return None

    def build_job(self, row: dict) -> Job | None:
        try:
            return self._build_job(row)
        except (TypeError, ValueError, AttributeError):
            return None  # A malformed record must not discard the other jobs.

    def _build_job(self, row: dict) -> Job | None:
        company = row.get("companyProfile")
        if not isinstance(company, dict) or not all(
            isinstance(x, str) and x
            for x in (row.get("title"), row.get("slug"), company.get("slug"), company.get("name"))
        ):
            return None
        if row.get("status") != "published":
            return None
        hiring = row.get("hiringLocation") or {}
        locations = hiring.get("includedLocations") or []
        names = [
            x["value"]["name"]
            for x in locations
            if isinstance(x, dict) and isinstance(x.get("value"), dict) and x["value"].get("name")
        ]
        scope = (
            "Anywhere"
            if hiring.get("type") == "global"
            else ", ".join(names) + " only"
            if names
            else None
        )
        if hiring.get("type") == "timezone":
            zone = hiring.get("timezone") or {}
            if zone.get("name"):
                scope = (
                    f"{zone['name']} timezone ±{hiring.get('timezoneRange')} hours"
                    if hiring.get("timezoneRange") is not None
                    else f"{zone['name']} timezone"
                )
        country = None
        if len(locations) == 1 and locations[0].get("type") == "country":
            value = locations[0].get("value") or {}
            country = country_code(value.get("alpha2Code") or value.get("name"))
        workplace = row.get("workplaceLocation") or {}
        mode = {
            "remote": WorkMode.REMOTE,
            "hybrid": WorkMode.HYBRID,
            "onsite": WorkMode.ONSITE,
            "office": WorkMode.ONSITE,
        }.get(workplace.get("type"), WorkMode.UNKNOWN)
        compensation = row.get("compensation")
        salary = None
        if isinstance(compensation, dict):
            values = [
                f"{compensation[k] / 100:,.2f}".rstrip("0").rstrip(".")
                for k in ("minimum", "maximum")
                if isinstance(compensation.get(k), (int, float))
            ]
            currency = (compensation.get("currency") or {}).get("code")
            if values and currency:
                salary = f"{' - '.join(values)} {currency}/{compensation.get('frequency') or 'unspecified period'}"
        visa = row.get("visaSponsorshipOffered")
        facts = {
            "Visa sponsorship": "Yes" if visa is True else "No" if visa is False else None,
            "Experience level": ", ".join(row.get("seniority") or []),
            "Remote scope": scope,
            "Employment type": row.get("employmentType"),
            "Travel requirement": row.get("travelFrequency"),
            "Salary": salary,
            "Application URL": row.get("applyUrl"),
        }
        description = row.get("description")
        description = (
            None
            if isinstance(description, str) and description.startswith("$")
            else html_to_text(description)
        )
        posted, provenance = date_source_for(
            parse_datetime(row.get("publishedAt")), parse_datetime(row.get("updatedAt"))
        )
        return Job.build(
            url=canonical_url(f"{BASE}/jobs/{company['slug']}/{row['slug']}"),
            source=self.source,
            layer=Layer.B,
            company=company["name"],
            title=row["title"],
            external_id=row["slug"].rsplit("-", 1)[-1],
            location=scope,
            country=country,
            region=region_for(country)
            if country
            else Region.EU
            if names == ["Europe"]
            else Region.UNKNOWN,
            work_mode=mode,
            department=(row.get("department") or {}).get("name"),
            salary=salary,
            description=enrich(description, self.source, facts),
            posted_at=posted,
            date_source=provenance,
        )

    async def scrape(self, client) -> ScrapeBatch:
        jobs, errors, seen = [], [], set()
        pages = items_seen = attempted = succeeded = 0
        stop, more, total = "exhausted", False, None
        for page in range(1, self.max_pages + 1):
            attempted += 1
            try:
                html = await client.get_html(f"{BASE}/jobs/all?page={page}")
                pages += 1
                data = self.listing(html)
                if data.get("currentPage") != page:
                    raise ScraperPermanentError("remotecom: pagination repeated/wrong page")
                succeeded += 1
            except (ScraperError, ValueError) as exc:
                errors.append(f"page {page}: {exc}")
                stop = "page_failed"
                break
            rows = data["jobs"]
            items_seen += len(rows)
            total = data.get("totalCount")
            fresh = self.dedup_seen(
                seen,
                [job for row in rows if isinstance(row, dict) and (job := self.build_job(row))],
            )
            if rows and not fresh:
                errors.append(f"page {page}: no new valid job identities")
                stop = "unexpected_page"
                break
            remaining = self.max_offers - len(jobs)
            jobs.extend(fresh[:remaining])
            more = page < data["totalPages"]
            if len(fresh) > remaining or len(jobs) >= self.max_offers and more:
                stop = "max_offers_reached"
                break
            if not more:
                break
            if page == self.max_pages:
                stop = "max_pages_reached"
        listing_errors = list(errors)
        detail_success = 0
        for index, job in enumerate(jobs[: self.detail_budget]):
            attempted += 1
            try:
                html = await client.get_html(job.url)
                pages += 1
                detail = self.parse_offer(html)
                if (
                    detail is None
                    or detail.external_id != job.external_id
                    or not detail.description
                ):
                    raise ScraperPermanentError("missing/mismatched detail schema")
                jobs[index] = detail
                succeeded += 1
                detail_success += 1
            except (ScraperError, ValueError) as exc:
                errors.append(f"{job.url}: {exc}")
        cap = stop in ("max_offers_reached", "max_pages_reached")
        telemetry = self.record_telemetry(
            items_seen=items_seen,
            items_returned=len(jobs),
            pages_fetched=pages,
            page_limit=self.max_pages,
            result_limit=self.max_offers,
            cap_hit=cap,
            stop_reason=stop,
            partial_reason=stop if cap else "; ".join(listing_errors) or None,
            metadata={
                "transport": "ssr_flight",
                "total_count": total,
                "detail_budget": self.detail_budget,
                "details_succeeded": detail_success,
                "listing_complete": not cap and not listing_errors,
                **richness_metadata(len(jobs), detail_success, self.detail_budget, errors[len(listing_errors):]),
            },
        )
        return ScrapeBatch(jobs, errors, attempted, succeeded, telemetry)
