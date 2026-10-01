"""FreeHire documented unauthenticated REST, bounded recent geographic slices."""

from contextlib import suppress
from urllib.parse import urlencode

from ..models import WorkMode, canonical_url
from ..normalize import format_salary
from .base import ScrapeBatch, ScraperBase, ScraperError, ScraperPermanentError
from .batch2_public import build, public_config, safe_record


class FreeHireScraper(ScraperBase):
    source_key = "freehire"
    label = "FreeHire"
    base_url = "https://freehire.me"

    def __init__(
        self, config=None, *, max_pages=3, max_offers=300, page_size=50, recent_days=7, slices=None
    ):
        super().__init__(public_config(config, self.base_url))
        self.max_pages = max(1, int(max_pages))
        self.max_offers = max(1, int(max_offers))
        self.page_size = min(100, max(1, int(page_size)))
        self.recent_days = min(36500, max(1, int(recent_days)))
        self.slices = slices or [
            {"regions": ["eu", "uk"], "countries": ["TR", "NO", "CH"]},
            {"work_mode": ["remote"]},
        ]
        self.rate_remaining = None
        self.rate_limit = None
        self.rate_reset = None

    @safe_record
    def parse_record(self, row):
        if not isinstance(row, dict):
            return None
        e = row.get("enrichment") or {}
        e = e if isinstance(e, dict) else {}
        # Agent shape retains rich values in enrichment; ordinary search can
        # project them onto the row. Missing and explicit false remain distinct.
        values = {**e, **{k: v for k, v in row.items() if v is not None}}
        countries = row.get("countries") or []
        regions = row.get("regions") or []
        salary = format_salary(
            values.get("salary_min"), values.get("salary_max"), values.get("salary_currency")
        )
        if salary and values.get("salary_period"):
            salary += "/" + str(values["salary_period"])
        mode = {m.value: m for m in WorkMode}.get(values.get("work_mode"), WorkMode.UNKNOWN)
        visa = values.get("visa_sponsorship")
        language = values.get("posting_language")
        return build(
            self.source,
            row,
            url=row.get("url"),
            title=row.get("title"),
            company=row.get("company"),
            external_id=row.get("public_slug")
            or (
                f"{row['source']}:{row['external_id']}"
                if row.get("source") and row.get("external_id")
                else None
            ),
            location=row.get("location"),
            country=countries[0] if len(countries) == 1 else None,
            mode=mode,
            description=row.get("description"),
            salary=salary,
            language=None,
            posted=None,
            updated=row.get("posted_at") or row.get("updated_at"),
            facts={
                "Meta source": "freehire",
                "Source authority": "meta",
                "Original source": row.get("source"),
                "Original external ID": row.get("external_id"),
                "Original URL": row.get("url"),
                "Application URL": row.get("url"),
                "Countries": ", ".join(countries),
                "Regions": ", ".join(regions),
                "Cities": ", ".join(row.get("cities") or []),
                "Remote scope": ", ".join(countries or regions)
                if mode is WorkMode.REMOTE
                else None,
                "Technologies": ", ".join(row.get("skills") or []),
                "Experience level": values.get("seniority"),
                "Employment type": values.get("employment_type"),
                "Posting language": language,
                "Board English level": values.get("english_level"),
                "Board sponsorship claim": "Yes" if visa is True else "No" if visa is False else None,
                "Relocation (board normalization)": values.get("relocation"),
                "Board repost count": (row.get("reality") or {}).get("repost_count"),
                "Board fake freshness flag": (row.get("reality") or {}).get("fake_freshness"),
                "Original posted date (upstream claim)": row.get("posted_at"),
                "Experience years": values.get("experience_years_min"),
                "Category": values.get("category"),
                "Evidence provenance": "FreeHire normalization of upstream posting; original URL retained",
            },
        )

    def listing(self, data):
        if (
            not isinstance(data, dict)
            or not isinstance(data.get("data"), list)
            or not isinstance(data.get("meta"), dict)
        ):
            raise ScraperPermanentError("FreeHire missing public collection envelope")
        meta = data["meta"]
        if any(
            not isinstance(meta.get(k), int) or meta[k] < 0 for k in ["total", "offset", "limit"]
        ):
            raise ScraperPermanentError("FreeHire invalid pagination metadata")
        jobs = [j for row in data["data"] if (j := self.parse_record(row))]
        if data["data"] and not jobs:
            raise ScraperPermanentError("FreeHire nonempty malformed records")
        return jobs, len(data["data"]), meta

    async def scrape(self, client):
        jobs = []
        seen = set()
        errors = []
        bounds = []
        totals = []
        requests = pages = success = items_seen = 0
        for scope in self.slices:
            offset = 0
            for page in range(self.max_pages):
                size = min(self.page_size, self.max_offers - len(jobs))
                if size <= 0:
                    bounds.append("result_limit_reached")
                    break
                if offset + size > 10000:
                    bounds.append("api_depth_limit_reached")
                    break
                if self.rate_remaining is not None and self.rate_remaining <= 1:
                    bounds.append("rate_budget_reached")
                    break
                params = {
                    **scope,
                    "posted_within_days": self.recent_days,
                    "sort": "posted_at",
                    "order": "desc",
                    "description_format": "text",
                    "limit": size,
                    "offset": offset,
                }
                url = self.base_url + "/api/v1/agent/jobs/search?" + urlencode(params, doseq=True)
                requests += 1
                try:
                    # Batch full descriptions prevent N+1 detail calls. No token,
                    # CLI, account state, proxy credential or personal payload.
                    response = await client._request("GET", url)
                    for header, attr in [
                        ("X-RateLimit-Remaining", "rate_remaining"),
                        ("X-RateLimit-Limit", "rate_limit"),
                        ("X-RateLimit-Reset", "rate_reset"),
                    ]:
                        value = response.headers.get(header)
                        if value is not None:
                            with suppress(ValueError):
                                setattr(self, attr, int(value))
                    parsed, count, meta = self.listing(response.json())
                    pages += 1
                    success += 1
                    items_seen += count
                    totals.append(
                        {
                            "scope": scope,
                            "offset": offset,
                            "total": meta["total"],
                            "limit": meta["limit"],
                        }
                    )
                    if meta["offset"] != offset:
                        raise ScraperPermanentError("FreeHire server changed requested offset")
                    for job in parsed:
                        identity = job.external_id or canonical_url(job.url)
                        if identity not in seen:
                            seen.add(identity)
                            jobs.append(job)
                    if not count:
                        if offset < meta["total"]:
                            raise ScraperPermanentError(
                                "FreeHire unexpected empty page before total"
                            )
                        break
                    offset += count
                    if offset >= meta["total"]:
                        break
                    if len(jobs) >= self.max_offers:
                        bounds.append("result_limit_reached")
                        break
                    if page + 1 == self.max_pages:
                        bounds.append("page_limit_reached")
                except (ScraperError, ValueError, TypeError) as exc:
                    errors.append(f"FreeHire: {type(exc).__name__}: {exc}")
                    break
            if len(jobs) >= self.max_offers:
                break
        bounds = list(dict.fromkeys(bounds))
        telemetry = self.record_telemetry(
            items_seen=items_seen,
            items_returned=len(jobs),
            pages_fetched=pages,
            page_limit=self.max_pages * len(self.slices),
            result_limit=self.max_offers,
            cap_hit=bool(bounds),
            stop_reason=bounds[0] if bounds else "request_failed" if errors else "exhausted",
            partial_reason="; ".join([*bounds, *errors]) or None,
            metadata={
                "transport": "public_rest_agent_batch",
                "requests": requests,
                "slices": totals,
                "recent_days": self.recent_days,
                "api_depth_limit": 10000,
                "rate_limit": self.rate_limit,
                "rate_remaining": self.rate_remaining,
                "rate_reset": self.rate_reset,
                "freehire_seen": items_seen,
                "freehire_unique": len(jobs),
                "freehire_overlap": None,
                "freehire_new_canonical": None,
                "freehire_not_new_canonical": None,
            },
        )
        return ScrapeBatch(jobs, errors, requests, success, telemetry)
