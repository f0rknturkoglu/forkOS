"""Remote/relocation/meta board public SSR evidence, no private API reads."""

import re
from urllib.parse import urljoin, urlsplit

from selectolax.parser import HTMLParser

from ..models import WorkMode, canonical_url
from ..normalize import format_salary
from .base import ScraperPermanentError
from .batch2_public import build, resolve_text, state_nodes
from .regional_batch2 import RegionalDetailScraper, content, next_link
from .remotecom import flight_records, walk


class WorkationBaseScraper(RegionalDetailScraper):
    source_key = "workationbase"
    label = "WorkationBase"
    base_url = "https://workationbase.com/jobs"
    transport = "public_ssr_state_jsonld"

    def listing(self, html, url):
        rows = [
            n
            for n in state_nodes(html)
            if isinstance(n.get("slug"), str) and "remoteScope" in n and "companyName" in n
        ]
        if not rows:
            raise ScraperPermanentError("WorkationBase missing job card state")
        jobs = []
        for r in rows:
            scope = {
                "anywhere": "Anywhere",
                "region-required": r.get("region"),
                "unclear": "Unclear",
            }.get(r.get("remoteScope"), r.get("remoteScope"))
            job = build(
                self.source,
                r,
                url=self.base_url + "/" + r["slug"],
                title=r.get("title"),
                company=r.get("companyName"),
                external_id=r["slug"],
                mode=WorkMode.REMOTE,
                salary=r.get("salaryRaw"),
                language=r.get("language"),
                facts={
                    "Remote scope": scope,
                    "Timezone requirements": r.get("timezoneOverlap"),
                    "Async/distributed": str(r.get("asyncFriendly"))
                    if isinstance(r.get("asyncFriendly"), bool)
                    else None,
                    "Technologies/topics": ", ".join(r.get("tags") or []),
                    # false on this curated board means absence of a sponsoring flag,
                    # not an explicit employer refusal. Keep both as board labels.
                    "Board sponsorship flag": str(r.get("visaSponsorship"))
                    if isinstance(r.get("visaSponsorship"), bool)
                    else None,
                    "Board region": r.get("region"),
                    "Board language tag": r.get("language"),
                    "Listed relative age": r.get("postedDaysAgo"),
                },
            )
            if job:
                jobs.append(job)
        return jobs, len(rows), next_link(HTMLParser(html), url)


class JumpIntoEuScraper(RegionalDetailScraper):
    source_key = "jumpintoeu"
    label = "JumpInto.eu"
    base_url = "https://jumpinto.eu/"
    transport = "public_ssr_full_state"

    def listing(self, html, url):
        records = flight_records(html)
        rows = None
        for root in records.values():
            for n in walk(root):
                if isinstance(n.get("initialJobs"), list):
                    rows = n["initialJobs"]
                    break
        if rows is None:
            raise ScraperPermanentError("JumpInto missing initialJobs state")
        jobs = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            salary = format_salary(r.get("salaryMin"), r.get("salaryMax"), r.get("currency"))
            mode = {
                "Remote": WorkMode.REMOTE,
                "Hybrid": WorkMode.HYBRID,
                "On-site": WorkMode.ONSITE,
            }.get(r.get("locationType"))
            # createdAt is board insertion, not employer publication.
            job = build(
                self.source,
                r,
                url=urljoin(url, "/jobs/" + str(r.get("slug") or "")),
                title=r.get("title"),
                company=r.get("company"),
                external_id=r.get("id"),
                location=r.get("location"),
                mode=mode,
                salary=salary,
                description=resolve_text(r.get("description"), records),
                updated=r.get("createdAt"),
                facts={
                    "Technologies": ", ".join(r.get("techStack") or []),
                    "Experience level": r.get("seniority"),
                    "Board sponsorship claim": str(r.get("visaSponsorship"))
                    if isinstance(r.get("visaSponsorship"), bool)
                    else None,
                    "Board requirements": "; ".join(r.get("requirements") or []),
                    "Board benefits": "; ".join(r.get("benefits") or []),
                    "Application URL": r.get("applyUrl"),
                    "Work model": r.get("locationType"),
                    "Evidence provenance": "Board-curated tags/requirements/benefits; not independently employer-confirmed",
                },
            )
            if job:
                jobs.append(job)
        if rows and not jobs:
            raise ScraperPermanentError("JumpInto nonempty malformed records")
        return jobs, len(rows), None

    def needs_detail(self, job):
        return False


class WorkcaminoScraper(RegionalDetailScraper):
    source_key = "workcamino"

    async def scrape(self, client):
        raise ScraperPermanentError(
            "workcamino terms prohibit automated scraping; disabled 2026-10-01"
        )

    label = "Workcamino"
    base_url = "https://workcamino.com/en/jobs"
    transport = "public_ssr_full_state"

    def listing(self, html, url):
        records = flight_records(html)
        data = None
        for root in records.values():
            for n in walk(root):
                if isinstance(n.get("jobs"), list) and "pagination" in n:
                    data = n
                    break
        if data is None:
            raise ScraperPermanentError("Workcamino missing public jobs state")
        rows = data["jobs"]
        jobs = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            job = build(
                self.source,
                r,
                url=r.get("url"),
                title=r.get("title"),
                company=r.get("company"),
                external_id=r.get("id"),
                location=r.get("location_raw"),
                description=resolve_text(r.get("description"), records),
                updated=r.get("posted_at"),
                mode=WorkMode.REMOTE if r.get("remote") is True else WorkMode.UNKNOWN,
                facts={
                    "Original source": r.get("source"),
                    "Original URL": r.get("url"),
                    "Meta source": "workcamino",
                    "Source authority": "meta",
                    "Experience level (board inference)": r.get("seniority"),
                    "Experience years (board inference)": r.get("min_years"),
                    "Sponsorship hint (Workcamino text inference)": str(r.get("visa_hint"))
                    if isinstance(r.get("visa_hint"), bool)
                    else None,
                    "English-friendly (Workcamino text inference)": str(r.get("english_ok"))
                    if isinstance(r.get("english_ok"), bool)
                    else None,
                    "Category": r.get("category"),
                    "Application URL": r.get("url"),
                },
            )
            if job:
                jobs.append(job)
        # robots forbids /en/jobs? query pagination. We use only its allowed
        # public window; do not try its disallowed /api/ or paid filters.
        if rows and not jobs:
            raise ScraperPermanentError("Workcamino nonempty malformed records")
        return jobs, len(rows), None

    def needs_detail(self, job):
        return False


class RelocantlyScraper(RegionalDetailScraper):
    source_key = "relocantly"

    async def scrape(self, client):
        raise ScraperPermanentError(
            "relocantly terms prohibit automated scraping; disabled 2026-10-01"
        )

    label = "Relocantly"
    base_url = "https://relocantly.com/jobs"
    transport = "public_ssr_html_jsonld"

    def listing(self, html, url):
        tree = HTMLParser(html)
        cards = [n for n in tree.css('a[href^="/jobs/"]') if n.css_first("h3")]
        jobs = []
        if not cards and not re.search(r"0 live jobs", tree.text()):
            raise ScraperPermanentError("Relocantly missing public cards")
        flags = {
            "🇩🇪": "DE",
            "🇫🇷": "FR",
            "🇪🇸": "ES",
            "🇵🇱": "PL",
            "🇦🇹": "AT",
            "🇳🇱": "NL",
            "🇮🇹": "IT",
            "🇨🇿": "CZ",
            "🇸🇰": "SK",
        }
        for card in cards:
            line = content(card, "p") or ""
            company = line.split("·")[0].strip()
            country = next((v for k, v in flags.items() if k in line), None)
            tags = [n.text(strip=True) for n in card.css("div.flex.flex-wrap span")]
            publisher = next(
                (
                    tag
                    for tag in tags
                    if tag.lower()
                    in {
                        "linkedin",
                        "indeed",
                        "stepstone",
                        "infojobs",
                        "pracuj",
                        "nofluffjobs",
                        "justjoin",
                        "profesia",
                        "karriere.at",
                        "tecnoempleo",
                    }
                ),
                None,
            )
            href = card.attributes["href"]
            job = build(
                self.source,
                {},
                url=urljoin(url, href),
                title=content(card, "h3"),
                company=company,
                external_id=href.rsplit("/", 1)[-1],
                location=line.split("·")[-1].strip(),
                country=country,
                facts={
                    "Meta source": "relocantly",
                    "Source authority": "meta",
                    "Original source": publisher,
                    "Board discovery tags": ", ".join(tags),
                    "Evidence provenance": "Relocantly inferred eligibility labels; not employer-confirmed",
                },
            )
            if job:
                jobs.append(job)
        return jobs, len(cards), next_link(tree, url)

    def detail(self, html, url):
        job = super().detail(html, url)
        if not job:
            return None
        tree = HTMLParser(html)
        for link in tree.css("a[href]"):
            href = link.attributes.get("href") or ""
            if (
                urlsplit(href).scheme in {"http", "https"}
                and urlsplit(href).hostname != "relocantly.com"
                and re.search(r"apply|original|view job", link.text(), re.I)
            ):
                from ..rich_text import enrich

                # The public detail exposes the upstream posting itself. Use
                # that URL for strongest cross-source identity, keep meta ID.
                job.url = canonical_url(href)
                job.description = enrich(
                    job.description,
                    self.source,
                    {"Original URL": href, "Application URL": href, "Meta source": "relocantly"},
                )
                break
        return job
