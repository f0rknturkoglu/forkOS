"""Public WordPress startup boards: listing discovery + bounded JSON-LD details."""

import re
from urllib.parse import urljoin, urlsplit

from selectolax.parser import HTMLParser

from ..models import Job, Layer, WorkMode, canonical_url, date_source_for
from ..normalize import format_salary, html_to_text, parse_datetime, parse_location
from ..rich_text import enrich, merge_descriptions
from .detail_evidence import richness_metadata
from .base import ScrapeBatch, ScraperBase, ScraperError, ScraperPermanentError
from .schemaorg import job_posting_nodes, organisation_name, place, text


def node_text(node, selector):
    child = node.css_first(selector)
    return child.text(separator=" ", strip=True) if child else None


def next_page(html: str, url: str) -> str | None:
    parser = HTMLParser(html)
    for selector in ("a[rel=next]", "a.next", ".wpjb-paginate-next a", ".wpjb-pagination a"):
        for node in parser.css(selector):
            href = node.attributes.get("href", "")
            if href and (
                "next" in node.text(strip=True).lower() or selector != ".wpjb-pagination a"
            ):
                target = urljoin(url, href)
                if urlsplit(target).netloc == urlsplit(url).netloc:
                    return target
    # WPJobBoard displays a numeric next page, sometimes without rel/class.
    current = re.search(r"/page/(\d+)/", url)
    number = int(current.group(1)) + 1 if current else 2
    for node in parser.css("a[href]"):
        href = node.attributes.get("href") or ""
        if (
            f"/page/{number}/" in href
            and urlsplit(urljoin(url, href)).netloc == urlsplit(url).netloc
        ):
            return urljoin(url, href)
    return None


class StartupBoardScraper(ScraperBase):
    def __init__(
        self, config=None, *, max_pages: int = 2, max_offers: int = 500, detail_budget: int = 20
    ):
        super().__init__(config)
        self.max_pages, self.max_offers = max(1, int(max_pages)), max(1, int(max_offers))
        self.detail_budget = max(0, int(detail_budget))

    def parse_offer(self, html: str, url: str) -> Job | None:
        postings = job_posting_nodes(html)
        if not postings:
            return None
        row = postings[0]
        title, company = text(row.get("title")), organisation_name(row.get("hiringOrganization"))
        if not title or not company:
            return None
        if self.source == "eustartups" and re.search(r"\bcomparison guide\b", title, re.I):
            return None  # Promotional articles incorrectly published as JobPosting, not roles.
        city, country = place(row.get("jobLocation"))
        location = ", ".join(x for x in (city, country) if x) or None
        info = parse_location(location)
        remote = row.get("jobLocationType") == "TELECOMMUTE"
        scope = city if city and re.search(r"worldwide|anywhere|remote", city, re.I) else None
        req = row.get("applicantLocationRequirements")
        if isinstance(req, dict) and req.get("name"):
            scope = str(req["name"])
        mode = (
            WorkMode.REMOTE
            if remote or scope and re.search(r"worldwide|anywhere|remote", scope, re.I)
            else WorkMode.UNKNOWN
        )
        salary = None
        sal = row.get("baseSalary")
        if isinstance(sal, dict) and isinstance(sal.get("value"), dict):
            value = sal["value"]
            salary = format_salary(
                value.get("minValue"), value.get("maxValue"), sal.get("currency")
            )
            if salary and value.get("unitText"):
                salary += f"/{value['unitText']}"
        body = html_to_text(row.get("description"))
        if not salary and body:
            match = re.search(r"(?:Salary|Pay Rate)\s*:\s*([^\n]{1,80})", body, re.I)
            salary = match.group(1).strip() if match else None
        parser = HTMLParser(html)
        tags = [node.text(strip=True) for node in parser.css('.bsj-tags a[href*="/skill-areas/"]')]
        employment = text(row.get("employmentType"))
        if self.source == "eustartups":
            # WPJobBoard's JSON-LD often maps Part-Time to OTHER; retain actual UI label.
            for node in parser.css(".wpjb-grid-row"):
                label = node_text(node, ".wpjb-col-title")
                if label and "Job Type" in label:
                    employment = node_text(node, ".wpjb-col-value") or employment
        identifier = row.get("identifier")
        external_id = (
            str(identifier["value"])
            if isinstance(identifier, dict) and identifier.get("value") is not None
            else None
        )
        posted, provenance = date_source_for(parse_datetime(row.get("datePosted")))
        return Job.build(
            url=canonical_url(url),
            source=self.source,
            layer=Layer.B,
            company=company,
            title=title.split(" // ")[0],
            external_id=external_id,
            location=location,
            city=city,
            country=country,
            region=info.region,
            work_mode=mode,
            salary=salary,
            posted_at=posted,
            date_source=provenance,
            description=enrich(
                body,
                self.source,
                {
                    "Technologies/topics": ", ".join(dict.fromkeys(tags)),
                    "Employment type": employment,
                    "Remote scope": scope,
                },
            ),
        )

    async def scrape(self, client) -> ScrapeBatch:
        jobs, errors, seen = [], [], set()
        attempted = succeeded = pages = items_seen = 0
        cap_reasons = []
        listing_pages = 0
        for start in self.listing_urls:
            url = start
            for page in range(1, self.max_pages + 1):
                attempted += 1
                try:
                    html = await client.get_html(url)
                    pages += 1
                    listing_pages += 1
                    parsed, count = self.parse_listing(html, url)
                    succeeded += 1
                except (ScraperError, ValueError) as exc:
                    errors.append(f"{url}: {exc}")
                    break
                items_seen += count
                fresh = self.dedup_seen(seen, parsed)
                remaining = self.max_offers - len(jobs)
                jobs.extend(fresh[:remaining])
                next_url = next_page(html, url)
                if len(fresh) > remaining or len(jobs) >= self.max_offers:
                    if len(fresh) > remaining or next_url or start != self.listing_urls[-1]:
                        cap_reasons.append("max_offers_reached")
                    break
                if not next_url:
                    break
                if page == self.max_pages:
                    cap_reasons.append("max_pages_reached")
                url = next_url
            if len(jobs) >= self.max_offers:
                break
        listing_errors = list(errors)
        details = 0
        for index, job in enumerate(jobs[: self.detail_budget]):
            attempted += 1
            try:
                html = await client.get_html(job.url)
                pages += 1
                detail = self.parse_offer(html, job.url)
                if not detail:
                    raise ScraperPermanentError(
                        "missing JobPosting schema (challenge/login/layout change)"
                    )
                detail.description = merge_descriptions(job.description, detail.description)
                jobs[index] = detail
                succeeded += 1
                details += 1
            except (ScraperError, ValueError) as exc:
                errors.append(f"{job.url}: {exc}")
        reasons = list(dict.fromkeys(cap_reasons))
        stop = reasons[0] if reasons else "listing_request_failed" if listing_errors else "exhausted"
        telemetry = self.record_telemetry(
            items_seen=items_seen,
            items_returned=len(jobs),
            pages_fetched=pages,
            page_limit=self.max_pages * len(self.listing_urls),
            result_limit=self.max_offers,
            cap_hit=bool(reasons),
            stop_reason=stop,
            partial_reason="; ".join([*reasons, *listing_errors]) or None,
            metadata={
                "transport": "ssr_html_jsonld",
                "listing_pages": listing_pages,
                "detail_budget": self.detail_budget,
                "details_succeeded": details,
                "bounds": reasons,
                "listing_complete": not reasons and not listing_errors,
                **richness_metadata(len(jobs), details, self.detail_budget, errors[len(listing_errors):]),
            },
        )
        return ScrapeBatch(jobs, errors, attempted, succeeded, telemetry)


class BerlinStartupJobsScraper(StartupBoardScraper):
    source_key = "berlinstartupjobs"
    label = "Berlin Startup Jobs"
    base_url = "https://berlinstartupjobs.com"
    categories = (
        "engineering",
        "marketing",
        "design-ux",
        "operations",
        "sales",
        "product-management",
        "hr-recruiting",
        "finance",
        "internships",
        "contracting-positions",
        "seeking-co-founders",
        "other",
    )

    @property
    def listing_urls(self):
        return [f"{self.base_url}/{category}/" for category in self.categories]

    def parse_listing(self, html, url):
        parser = HTMLParser(html)
        cards = parser.css("li.bjs-jlid")
        if not cards and not parser.css(".jobs-list-items"):
            raise ScraperPermanentError("berlinstartupjobs: unexpected listing schema")
        jobs = []
        for card in cards:
            link = card.css_first(".bjs-jlid__h a")
            title = node_text(card, ".bjs-jlid__h")
            company = node_text(card, ".bjs-jlid__b")
            if not link or not title or not company:
                continue
            href = urljoin(url, link.attributes.get("href", ""))
            if (
                urlsplit(href).netloc != urlsplit(self.base_url).netloc
                or len(urlsplit(href).path.strip("/").split("/")) != 2
            ):
                continue
            tags = [node.text(strip=True) for node in card.css('a[href*="/skill-areas/"]')]
            description = node_text(card, ".bjs-jlid__description")
            category = urlsplit(url).path.strip("/").split("/")[0]
            jobs.append(
                Job.build(
                    url=canonical_url(href),
                    source=self.source,
                    layer=Layer.B,
                    company=company,
                    title=title,
                    description=enrich(
                        description,
                        self.source,
                        {
                            "Category": category,
                            "Technologies/topics": ", ".join(dict.fromkeys(tags)),
                        },
                    ),
                )
            )
        return jobs, len(cards)


class EUStartupsScraper(StartupBoardScraper):
    source_key = "eustartups"
    label = "EU-Startups Jobs"
    base_url = "https://www.eu-startups.com"
    listing_urls = ["https://www.eu-startups.com/startup-jobs/"]

    def parse_listing(self, html, url):
        parser = HTMLParser(html)
        cards = parser.css(".wpjb-grid-row.wpjb-click-area")
        if not cards and not parser.css(".wpjb-grid"):
            raise ScraperPermanentError("eustartups: unexpected WPJobBoard schema")
        jobs = []
        for card in cards:
            link = card.css_first(".wpjb-col-title a")
            title = link.text(strip=True) if link else None
            company = node_text(card, ".wpjb-col-title .wpjb-sub")
            if not title or not company or not link:
                continue
            if re.search(r"\bcomparison guide\b", title, re.I):
                continue
            href = urljoin(url, link.attributes.get("href", ""))
            if not href.startswith(self.base_url + "/job/"):
                continue
            location = node_text(card, ".wpjb-col-location .wpjb-line-major")
            employment = node_text(card, ".wpjb-col-location .wpjb-sub")
            info = parse_location(location)
            remote = bool(location and re.search(r"worldwide|anywhere|remote", location, re.I))
            jobs.append(
                Job.build(
                    url=canonical_url(href),
                    source=self.source,
                    layer=Layer.B,
                    company=company,
                    title=title,
                    location=location,
                    city=info.city,
                    country=info.country,
                    region=info.region,
                    work_mode=WorkMode.REMOTE if remote else WorkMode.UNKNOWN,
                    description=enrich(
                        None,
                        self.source,
                        {
                            "Employment type": employment,
                            "Remote scope": location if remote else None,
                        },
                    ),
                )
            )
        return jobs, len(cards)
