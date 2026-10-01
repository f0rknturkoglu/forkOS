"""Shared bounded collection of the public surfaces verified for Batch 2."""

from dataclasses import replace
from functools import wraps
from urllib.parse import urlsplit

from ..models import Job, Layer, WorkMode, canonical_url, date_source_for
from ..normalize import html_to_text, parse_datetime, parse_location
from ..rich_text import enrich, merge_descriptions
from .detail_evidence import richness_metadata
from .base import ScrapeBatch, ScraperBase, ScraperConfig, ScraperError, ScraperPermanentError
from .remotecom import flight_records, walk


def public_config(config, url):
    host = urlsplit(url).hostname
    base = config or ScraperConfig()
    return replace(
        base,
        allowed_hosts=(host, "www." + host),
        max_response_bytes=base.max_response_bytes or 8 * 1024 * 1024,
    )


def state_nodes(html):
    records = flight_records(html)
    for root in records.values():
        yield from walk(root)


def resolve_text(value, records):
    if isinstance(value, str) and value.startswith("$"):
        replacement = records.get(value[1:])
        return replacement if isinstance(replacement, str) else None
    return value if isinstance(value, str) else None


def safe_record(fn):
    """A corrupt optional field must not discard other valid source records."""

    @wraps(fn)
    def guarded(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (TypeError, ValueError, AttributeError):
            return None

    return guarded


@safe_record
def build(
    source,
    row,
    *,
    url,
    title,
    company,
    location=None,
    country=None,
    description=None,
    posted=None,
    updated=None,
    mode=None,
    salary=None,
    language=None,
    facts=None,
    external_id=None,
):
    if (
        not isinstance(title, str)
        or not title.strip()
        or not isinstance(company, str)
        or not company.strip()
    ):
        return None
    if urlsplit(url or "").scheme not in {"http", "https"} or not urlsplit(url or "").hostname:
        return None
    info = parse_location(location, description=description)
    posted, provenance = date_source_for(parse_datetime(posted), parse_datetime(updated))
    return Job.build(
        url=canonical_url(url),
        source=source,
        layer=Layer.B,
        title=title,
        company=company,
        external_id=str(external_id) if external_id else None,
        location=location,
        city=info.city,
        country=country or info.country,
        region=parse_location(country).region if country else info.region,
        work_mode=mode or info.work_mode,
        salary=salary,
        language=language,
        posted_at=posted,
        date_source=provenance,
        description=enrich(html_to_text(description), source, facts or {}),
    )


class PublicPagedScraper(ScraperBase):
    """Source-specific parsers; one transport/partial/dedup/budget contract."""

    def __init__(self, config=None, *, max_pages=3, max_offers=150, detail_budget=10):
        super().__init__(public_config(config, self.base_url))
        self.max_pages = max(1, int(max_pages))
        self.max_offers = max(1, int(max_offers))
        self.detail_budget = max(0, int(detail_budget))

    async def read_listing(self, client, url):
        return self.listing(await client.get_html(url), url)

    async def scrape(self, client):
        jobs, errors, seen, visited, bounds = [], [], set(), set(), []
        pages = attempts = successes = items_seen = listing_pages = details = 0
        for start in self.listing_urls:
            window_seen = set()
            url = start
            for page in range(self.max_pages):
                if url in visited:
                    errors.append("repeated_pagination_url")
                    break
                visited.add(url)
                attempts += 1
                try:
                    parsed, count, next_url = await self.read_listing(client, url)
                    pages += 1
                    listing_pages += 1
                    successes += 1
                except (ScraperError, ValueError, TypeError) as exc:
                    errors.append(f"{self.source}: {type(exc).__name__}: {exc}")
                    break
                if count and not parsed:
                    errors.append("nonempty_listing_without_valid_jobs")
                    break
                items_seen += count
                page_ids = {job.external_id or canonical_url(job.url) for job in parsed}
                if page and page_ids and page_ids <= window_seen:
                    errors.append("repeated_pagination_items")
                    break
                window_seen.update(page_ids)
                for job in parsed:
                    identity = job.external_id or canonical_url(job.url)
                    if identity in seen:
                        continue
                    seen.add(identity)
                    if len(jobs) < self.max_offers:
                        jobs.append(job)
                    else:
                        bounds.append("result_limit_reached")
                if len(jobs) >= self.max_offers and (next_url or start != self.listing_urls[-1]):
                    bounds.append("result_limit_reached")
                    break
                if not next_url:
                    break
                # Public pagination is source-owned; never follow arbitrary outbound URLs.
                if urlsplit(next_url).netloc != urlsplit(start).netloc:
                    errors.append("foreign_pagination_url")
                    break
                if page + 1 == self.max_pages:
                    bounds.append("page_limit_reached")
                url = next_url
            if len(jobs) >= self.max_offers:
                break
        listing_errors = list(errors)
        candidates = [i for i, j in enumerate(jobs) if self.needs_detail(j)]
        for i in candidates[: self.detail_budget]:
            attempts += 1
            try:
                html = await client.get_html(jobs[i].url)
                pages += 1
                detail = self.detail(html, jobs[i].url)
                if not detail:
                    raise ScraperPermanentError(
                        "missing detail schema (challenge/login/layout drift)"
                    )
                detail.description = merge_descriptions(jobs[i].description, detail.description)
                for field in ("location", "city", "country", "salary", "language"):
                    if not getattr(detail, field):
                        setattr(detail, field, getattr(jobs[i], field))
                if detail.work_mode is WorkMode.UNKNOWN:
                    detail.work_mode = jobs[i].work_mode
                jobs[i] = detail
                details += 1
                successes += 1
            except (ScraperError, ValueError, TypeError) as exc:
                errors.append(f"detail: {type(exc).__name__}: {exc}")
        bounds = list(dict.fromkeys(bounds))
        telemetry = self.record_telemetry(
            items_seen=items_seen,
            items_returned=len(jobs),
            pages_fetched=pages,
            page_limit=self.max_pages * len(self.listing_urls),
            result_limit=self.max_offers,
            cap_hit=bool(bounds),
            stop_reason=bounds[0] if bounds else "listing_request_failed" if listing_errors else "exhausted",
            partial_reason="; ".join([*bounds, *listing_errors]) or None,
            metadata={
                "transport": self.transport,
                "listing_pages": listing_pages,
                "details_succeeded": details,
                "detail_budget": self.detail_budget,
                "bounds": bounds,
                "listing_complete": not bounds and not listing_errors,
                **richness_metadata(len(candidates), details, self.detail_budget, errors[len(listing_errors):]),
            },
        )
        return ScrapeBatch(jobs, errors, attempts, successes, telemetry)

    def needs_detail(self, job):
        return True

    @property
    def listing_urls(self):
        return [self.base_url]
