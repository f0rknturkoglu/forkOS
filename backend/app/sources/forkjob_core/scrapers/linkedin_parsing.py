"""Native guest contracts. Synthetic fixtures, not claimed live DOM captures."""

import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlsplit

from selectolax.parser import HTMLParser

from ..models import DateSource, Job, Layer
from ..normalize import format_salary, html_to_text, parse_datetime, parse_location
from ..rich_text import enrich, merge_descriptions
from .schemaorg import job_posting_nodes, schema_job
from .schemaorg import text as schema_text


class LinkedInResponseError(Exception):
    def __init__(self, kind, *, eligible=False):
        self.kind, self.eligible = kind, eligible
        super().__init__(kind)


def linkedin_identity(url):
    if not isinstance(url, str):
        return None, None
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in {"linkedin.com", "www.linkedin.com"}
        or parsed.username
        or parsed.password
    ):
        return None, None
    match = re.fullmatch(r"/jobs/view/(?:[^/]*-)?(\d+)/?", parsed.path)
    if match:
        return match.group(1), "https://www.linkedin.com/jobs/view/" + match.group(1)
    if re.fullmatch(r"/jobs/view/[A-Za-z0-9_-]{1,200}/?", parsed.path):
        return None, "https://www.linkedin.com" + parsed.path.rstrip("/")
    return None, None


def text(node, selector):
    n = node.css_first(selector)
    return n.text(separator=" ", strip=True) if n else None


def fingerprint(html):
    tree = HTMLParser(html)
    if tree.css_first('form[action*="checkpoint"], #challenge, .challenge, iframe[src*="captcha"]'):
        raise LinkedInResponseError("challenge")
    if tree.css_first(
        'form[action*="login"], form[action*="uas"], input[name="session_key"], input[name="session_password"]'
    ):
        raise LinkedInResponseError("login")
    return tree


@dataclass(frozen=True)
class LinkedInCard:
    job_id: str | None
    title: str
    company: str
    location: str | None
    url: str
    posted_text: str | None = None
    posted_at: datetime | None = None
    company_url: str | None = None

    def to_job(self):
        info = parse_location(self.location)
        reposted = bool(self.posted_text and "repost" in self.posted_text.lower())
        return Job.build(
            source="linkedin",
            layer=Layer.B,
            external_id=self.job_id or self.url,
            title=self.title,
            company=self.company,
            url=self.url,
            location=self.location,
            city=info.city,
            country=info.country,
            region=info.region,
            work_mode=info.work_mode,
            posted_at=None if reposted else self.posted_at,
            date_source=DateSource.DISCOVERED
            if reposted or not self.posted_at
            else DateSource.EMPLOYER,
            description=enrich(
                None,
                "linkedin",
                {
                    "Observed recency": self.posted_text,
                    "Listing state": "Reposted" if reposted else None,
                    "Company URL": self.company_url,
                },
            ),
        )


def parse_cards(html):
    tree = fingerprint(html)
    containers = tree.css(".base-search-card, li:has(.base-card)")
    # Avoid double counting outer li plus its .base-search-card child.
    containers = [n for n in containers if n.tag != "li" or not n.css_first(".base-search-card")]
    if not containers:
        if tree.css_first(
            ".jobs-search__no-results, .jobs-search-results__no-results, ul.jobs-search__results-list"
        ):
            return [], 0
        if tree.css_first("#guest-jobs-content"):
            raise LinkedInResponseError("shell", eligible=True)
        raise LinkedInResponseError("schema", eligible=True)
    cards = []
    for node in containers:
        link = node.css_first('a.base-card__full-link, a[href*="/jobs/view/"]')
        if not link:
            continue
        identifier, url = linkedin_identity(link.attributes.get("href"))
        urn = re.fullmatch(r"urn:li:jobPosting:(\d+)", node.attributes.get("data-entity-urn", ""))
        if urn and identifier and urn.group(1) != identifier:
            continue
        title = text(node, ".base-search-card__title")
        company = text(node, ".base-search-card__subtitle")
        if urn and url:
            identifier = urn.group(1)
            url = "https://www.linkedin.com/jobs/view/" + identifier
        if not url or not title or not company:
            continue
        stamp = node.css_first("time")
        company_link = node.css_first(".base-search-card__subtitle a")
        cards.append(
            LinkedInCard(
                identifier,
                title,
                company,
                text(node, ".job-search-card__location"),
                url,
                stamp.text(strip=True) if stamp else None,
                parse_datetime(stamp.attributes.get("datetime")) if stamp else None,
                company_link.attributes.get("href") if company_link else None,
            )
        )
    if not cards:
        raise LinkedInResponseError("malformed_cards", eligible=True)
    return cards, len(containers)


def detail_job(html, card):
    tree = fingerprint(html)
    posts = list(job_posting_nodes(html))
    post = posts[0] if posts else {}
    if post:
        declared_url = post.get("url") or post.get("@id")
        declared_id = linkedin_identity(declared_url)[0] if isinstance(declared_url, str) else None
        if (declared_id and card.job_id and declared_id != card.job_id) or (post.get("title") and schema_text(post["title"]).casefold() != card.title.casefold()):
            raise LinkedInResponseError("detail_identity", eligible=False)
    body = html_to_text(post.get("description")) or text(tree, ".show-more-less-html__markup")
    if not body:
        raise LinkedInResponseError("detail_schema", eligible=True)
    job = card.to_job()
    facts = {
        "Employment type": post.get("employmentType")
        if isinstance(post.get("employmentType"), str)
        else None
    }
    salary_data = post.get("baseSalary")
    if isinstance(salary_data, dict) and isinstance(salary_data.get("value"), dict):
        value = salary_data["value"]
        try:
            job.salary = format_salary(
                value.get("minValue") or value.get("value"),
                value.get("maxValue"),
                salary_data.get("currency"),
            )
            if job.salary and value.get("unitText"):
                job.salary += "/" + str(value["unitText"])
        except (TypeError, ValueError):
            pass
    for item in tree.css(".description__job-criteria-item"):
        key = text(item, ".description__job-criteria-subheader")
        value = text(item, ".description__job-criteria-text")
        if key and value:
            normalized = {
                "Seniority level": "Seniority",
                "Employment type": "Employment type",
                "Job function": "Job function",
                "Industries": "Industry",
            }.get(key)
            if normalized:
                facts[normalized] = value
    apply = tree.css_first('a.apply-button, a[data-tracking-control-name*="apply-link-offsite"]')
    if apply:
        url = apply.attributes.get("href", "")
        parts = urlsplit(url)
        if (
            parts.scheme in {"https", "http"}
            and parts.hostname
            and not parts.username
            and not parts.password
        ):
            facts["Application URL"] = url
    salary = text(tree, ".salary")
    if salary:
        job.salary = salary
    posted = parse_datetime(post.get("datePosted"))
    reposted = "repost" in (card.posted_text or "").lower()
    if posted and not reposted:
        job.posted_at, job.date_source = posted, DateSource.EMPLOYER
    detail = schema_job(post, url=job.url, source="linkedin", layer=Layer.B, company=job.company,
        title=job.title, external_id=job.external_id, location=job.location, country=job.country,
        region=job.region, work_mode=job.work_mode, description=body)
    job.description = merge_descriptions(job.description, enrich(detail.description, "linkedin", facts), prefer_incoming=True)
    return job
