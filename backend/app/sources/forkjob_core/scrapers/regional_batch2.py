"""Verified Austrian/Swiss/German public listing and JobPosting surfaces."""

import re
from urllib.parse import urljoin, urlsplit

from selectolax.parser import HTMLParser

from ..models import WorkMode
from ..normalize import format_salary, html_to_text
from .base import ScraperPermanentError
from .batch2_public import PublicPagedScraper, build
from .schemaorg import job_posting_nodes, organisation_name, place


def content(node, selector):
    child = node.css_first(selector)
    return child.text(separator=" ", strip=True) if child else None


def next_link(tree, url):
    for n in tree.css("a[href]"):
        if n.attributes.get("rel") == "next" or n.text(strip=True).lower() in {
            "next →",
            "next",
            "next page",
            "»",
            "weiter",
        }:
            href = n.attributes.get("href")
            if href:
                return urljoin(url, href)
    return None


class RegionalDetailScraper(PublicPagedScraper):
    transport = "ssr_html_jsonld"

    def detail(self, html, url):
        nodes = job_posting_nodes(html)
        if not nodes:
            return None
        row = nodes[0]
        city, country = place(row.get("jobLocation"))
        salary = None
        sal = row.get("baseSalary")
        if isinstance(sal, dict) and isinstance(sal.get("value"), dict):
            value = sal["value"]
            salary = format_salary(
                value.get("minValue") or value.get("value"),
                value.get("maxValue"),
                sal.get("currency"),
            )
            if salary and value.get("unitText"):
                salary += f"/{value['unitText']}"
        identifier = row.get("identifier")
        identifier = identifier.get("value") if isinstance(identifier, dict) else identifier
        body = html_to_text(row.get("description"))
        # schema TELECOMMUTE means remote possible here, not unrestricted worldwide.
        remote_possible = row.get("jobLocationType") == "TELECOMMUTE"
        tree = HTMLParser(html)
        labels = {}
        for dl in tree.css("main dl"):
            label, value = content(dl, "dt"), content(dl, "dd")
            if label and value:
                labels.setdefault(label, value)
        explicit_mode = {
            "Onsite": WorkMode.ONSITE,
            "Hybrid": WorkMode.HYBRID,
            "Remote": WorkMode.REMOTE,
        }.get(labels.get("Arbeitsmodell"))
        application = next(
            (
                link.attributes.get("href")
                for link in tree.css("a[href]")
                if re.search(r"apply now|jetzt bewerben", link.text(), re.I)
                and urlsplit(link.attributes.get("href") or "").scheme in {"http", "https"}
                and urlsplit(link.attributes["href"]).hostname != urlsplit(url).hostname
            ),
            None,
        )
        facts = {
            "Employment type": row.get("employmentType"),
            "Technologies": row.get("skills"),
            "Application deadline": row.get("validThrough"),
            "Application URL": application,
            "Experience level": labels.get("Level"),
            "Contract type": labels.get("Vertragsart"),
            "Work model (explicit job label)": labels.get("Arbeitsmodell"),
            "Work model": "Remote possible; eligibility unspecified" if remote_possible else None,
        }
        return build(
            self.source,
            row,
            url=url,
            title=row.get("title"),
            company=organisation_name(row.get("hiringOrganization")),
            external_id=identifier or url.rstrip("/").rsplit("/", 1)[-1],
            country=country,
            location=", ".join(x for x in [city, country] if x),
            description=body,
            posted=row.get("datePosted"),
            salary=salary,
            mode=explicit_mode or WorkMode.UNKNOWN if remote_possible else explicit_mode,
            facts=facts,
        )


class DevJobsAtScraper(RegionalDetailScraper):
    source_key = "devjobsat"
    label = "DEVjobs.at"
    base_url = "https://devjobs.at/jobs/search"

    def listing(self, html, url):
        tree = HTMLParser(html)
        cards = tree.css('a[data-cy="jobSearchResultLink"]')
        jobs = []
        if not cards:
            raise ScraperPermanentError("DEVjobs missing public result cards")
        for card in cards:
            href = card.attributes.get("href")
            title = content(card, "h2")
            company = content(card, "p.font-semibold")
            tech = [
                n.text(strip=True)
                for n in card.css("li")
                if n.css_first('img[alt^="Logo Technology"]')
            ]
            pills = [n.text(strip=True) for n in card.css("li") if not n.css_first("img")]
            job = build(
                self.source,
                {},
                url=urljoin(url, href or ""),
                title=title,
                company=company,
                external_id=(href or "").rsplit("/", 1)[-1],
                country="AT",
                location=content(card, "div.flex.truncate"),
                description=content(card, "p.line-clamp-2"),
                salary=next((p for p in pills if "€" in p), None),
                facts={"Technologies": ", ".join(tech), "Listing tags": ", ".join(pills)},
            )
            if job:
                jobs.append(job)
        return jobs, len(cards), None

    async def scrape(self, client):
        result = await super().scrape(client)
        # Site's search-query pagination is disallowed by robots. The allowed
        # first listing is useful, but can never certify catalogue exhaustion.
        if result.succeeded:
            result.telemetry.cap_hit = True
            result.telemetry.stop_reason = "robots_limited_listing_window"
            result.telemetry.metadata["bounds"].append("robots_limited_listing_window")
            result.telemetry.partial_reason = "robots_limited_listing_window; " + (
                result.telemetry.partial_reason or ""
            )
        return result


class DeveloperJobsChScraper(RegionalDetailScraper):
    source_key = "developerjobsch"
    label = "developerjobs.ch"
    base_url = "https://developerjobs.ch/en/"

    def listing(self, html, url):
        tree = HTMLParser(html)
        links = tree.css('h2 a[href^="/en/jobs/"]')
        jobs = []
        if not links:
            raise ScraperPermanentError("developerjobs missing public cards")
        for link in links:
            card = link.parent.parent.parent.parent.parent
            company = content(card, 'a[href^="/en/company/"]')
            tags = [n.text(strip=True) for n in card.css('div[class*="mt-1.5"] span')]
            href = link.attributes["href"]
            labels = [n.text(strip=True).lstrip("· ") for n in card.css("p.mt-2 span")]
            located = next((label for label in labels if " · " in label), None)
            location = located.split(" · ")[0] if located else None
            workload = next(
                (label for label in labels if re.fullmatch(r"[0-9–—%-]+%", label)), None
            )
            salary = next((label for label in labels if "CHF" in label), None)
            preview = content(card, "p.mt-2.text-sm")
            job = build(
                self.source,
                {},
                url=urljoin(url, href),
                title=link.text(strip=True),
                company=company,
                external_id=href.rsplit("/", 1)[-1],
                country="CH",
                location=location,
                salary=salary,
                description=preview,
                facts={
                    "Technologies": ", ".join(tags),
                    "Workload": workload,
                    "Employment type": content(card, "div.flex.items-start span"),
                    "Listing evidence": card.text(separator=" ", strip=True),
                },
            )
            if job:
                jobs.append(job)
        return jobs, len(links), next_link(tree, url)


class EnglishJobsDeScraper(PublicPagedScraper):
    source_key = "englishjobsde"
    label = "English Jobs Germany"
    base_url = "https://englishjobs.de"
    transport = "public_ssr_listing"
    states = (
        "bayern",
        "brandenburg",
        "berlin",
        "schleswig-holstein",
        "niedersachsen",
        "mecklenburg-vorpommern",
        "sachsen",
        "baden-wuerttemberg",
        "sachsen-anhalt",
        "rheinland-pfalz",
        "hamburg",
        "saarland",
        "bremen",
        "hessen",
        "nordrhein-westfalen",
        "thueringen",
    )

    @property
    def listing_urls(self):
        return [self.base_url + "/in/" + s for s in self.states]

    def listing(self, html, url):
        tree = HTMLParser(html)
        cards = tree.css(".job.js-job")
        jobs = []
        if not cards and not re.search(r"0 (?:jobs|job offers)|no jobs found", tree.text(), re.I):
            raise ScraperPermanentError("EnglishJobs missing result structure")
        for card in cards:
            link = card.css_first("a.js-joblink")
            identifier = card.attributes.get("id")
            fields = [n.text(strip=True) for n in card.css("ul li")]
            if not link or len(fields) < 2 or not identifier:
                continue
            # Clickout is an explicitly disallowed crawl route: store the public
            # user application link, never request it. Its signature must remain.
            job = build(
                self.source,
                {},
                url=urljoin(url, link.attributes.get("href") or ""),
                title=content(card, '[itemprop="title"]'),
                company=fields[0],
                external_id=identifier,
                country="DE",
                location=fields[1],
                description=card.text(separator=" ", strip=True),
                facts={
                    "Original source": link.attributes.get("source"),
                    "Listed date (year unspecified)": fields[2] if len(fields) > 2 else None,
                    "Board context": "English-oriented search; posting language requirements are not inferred",
                },
            )
            if job:
                jobs.append(job)
        return jobs, len(cards), next_link(tree, url)

    def needs_detail(self, job):
        return False
