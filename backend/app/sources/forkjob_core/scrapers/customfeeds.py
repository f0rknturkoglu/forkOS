"""User-added RSS feeds — one Layer B source covering all of them.

Reads data/feeds.yaml, which the web UI at /feeds writes. Adding a feed in the
browser is enough for the next sync to collect it; nothing here is hard-coded.

This is the generic path. A board with a real API or its own quirks deserves its
own scraper — this one only assumes RSS 2.0 or Atom, so what it can extract is
the intersection of every feed: title, link, date, and whatever the description
holds. Anything richer is a reason to write a dedicated scraper instead.

One feed failing must not take the others down: each is caught separately and
reported, because a source that returns nothing is indistinguishable from one
that was never reachable.
"""

from __future__ import annotations

import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urljoin, urlsplit
from xml.etree import ElementTree as ET

from selectolax.parser import HTMLParser

from ..feeds import Feed, Feeds
from ..geo import country_from_location, region_for
from ..models import DateSource, Job, Layer, Region, WorkMode, date_source_for
from ..normalize import html_to_text, parse_datetime
from .base import ScrapeBatch, ScraperBase, ScraperError, ScraperHttpClient, ScraperPermanentError
from .schemaorg import job_posting_nodes, organisation_name
from .schemaorg import place as schema_place
from .schemaorg import text as schema_text

ATOM = "{http://www.w3.org/2005/Atom}"
DC_CREATOR = "{http://purl.org/dc/elements/1.1/}creator"

REMOTE_WORDS = re.compile(r"\bremote\b|\bwork from home\b|\banywhere\b", re.I)
HYBRID_WORDS = re.compile(r"\bhybrid\b", re.I)

#: "Backend Engineer at Acme" and "Acme: Backend Engineer" are both common ways
#: for a feed to pack the employer into the title.
TITLE_AT = re.compile(r"^(?P<title>.+?)\s+(?:at|@)\s+(?P<company>[^|]+)$", re.I)
TITLE_COLON = re.compile(r"^(?P<company>[^:]{2,40}):\s+(?P<title>.+)$")


class CustomFeedsScraper(ScraperBase):
    source_key = "customfeeds"
    label = "Custom RSS feeds"
    base_url = ""

    def __init__(self, config: Any = None, *, feeds_path: str = "") -> None:
        super().__init__(config)
        self.feeds_path = feeds_path

    async def scrape(self, client: ScraperHttpClient) -> ScrapeBatch:
        feeds = (Feeds.load(self.feeds_path) if self.feeds_path else Feeds.load()).enabled()
        if not feeds:
            return ScrapeBatch(jobs=[], errors=[], attempted=0, succeeded=0)

        jobs: list[Job] = []
        errors: list[str] = []
        succeeded = 0
        for feed in feeds:
            try:
                xml = await client.get_html(feed.url)
            except ScraperError as exc:
                errors.append(f"{feed.label}: {type(exc).__name__}: {exc}")
                continue
            except Exception as exc:  # a user-supplied URL can be anything
                errors.append(f"{feed.label}: {type(exc).__name__}: {exc}")
                continue

            try:
                parsed = self.parse_page(xml, feed) if feed.is_page else self.parse(xml, feed)
            except ScraperError as exc:
                errors.append(f"{feed.label}: {exc}")
                continue
            if not parsed and not feed.is_page:
                root = ET.fromstring(xml)
                entries = [n for n in root.iter() if n.tag.rsplit("}", 1)[-1] in {"item", "entry"}]
                if not entries:
                    succeeded += 1
                    continue
            if not parsed:
                what = "page" if feed.is_page else "feed"
                errors.append(f"{feed.label}: no postings found in the {what}")
                continue
            jobs.extend(parsed)
            succeeded += 1

        return ScrapeBatch(jobs=jobs, errors=errors, attempted=len(feeds), succeeded=succeeded)

    def parse_page(self, html: str, feed: Feed) -> list[Job]:
        """Read a company's own careers page.

        Two routes, in order of how much they can be trusted:

        1. schema.org `JobPosting` in ld+json. Rare on listing pages — zero of
           six own-site careers pages measured had it — but when it is there it
           is the employer's own structured data, so nothing is guessed.
        2. The `item` selector the user pointed at, with optional title/link
           selectors inside it. This is the fallback that makes non-ATS
           companies reachable at all.
        """
        jobs = [
            j
            for j in (self._from_ld(node, feed) for node in job_posting_nodes(html))
            if j is not None
        ]
        if jobs:
            return jobs

        item_selector = feed.selectors.get("item")
        if not item_selector:
            return []

        parser = HTMLParser(html)
        out: list[Job] = []
        seen: set[str] = set()
        for node in parser.css(item_selector):
            job = self._from_node(node, feed)
            if job is None or job.url in seen:
                continue
            seen.add(job.url)
            out.append(job)
        return out

    def _from_ld(self, node: dict[str, Any], feed: Feed) -> Job | None:
        title = schema_text(node.get("title"))
        if not title:
            return None
        url = schema_text(node.get("url")) or feed.url
        location, country = schema_place(node.get("jobLocation"))
        company = organisation_name(node.get("hiringOrganization")) or feed.label
        posted = parse_datetime(schema_text(node.get("datePosted")))
        description = html_to_text(schema_text(node.get("description")) or "") or ""
        return self._build(
            feed,
            url=url,
            title=title,
            company=company,
            location=location,
            country=country or feed.country or None,
            description=description,
            posted_at=posted,
            # datePosted is the employer's own field, unlike a feed's pubDate.
            date_source=date_source_for(posted)[1],
        )

    def _from_node(self, node: Any, feed: Feed) -> Job | None:
        sel = feed.selectors

        link_node = node.css_first(sel["link"]) if sel.get("link") else None
        if link_node is None:
            link_node = node if node.tag == "a" else node.css_first("a")
        href = (link_node.attributes.get("href") or "") if link_node is not None else ""
        if not href:
            return None
        url = href if href.startswith("http") else urljoin(feed.url, href)

        title = self._pick(node, sel.get("title")) or (
            link_node.text(strip=True) if link_node is not None else ""
        )
        title = " ".join(title.split())
        if not title:
            return None

        location = self._pick(node, sel.get("location"))
        department = self._pick(node, sel.get("department"))
        details = [d for d in (department,) if d]

        return self._build(
            feed,
            url=url,
            title=title,
            company=feed.label,
            location=location or None,
            country=feed.country or None,
            description="\n".join(details),
            posted_at=None,
            # A listing page carries no date, and inventing one would let a
            # stale posting look fresh.
            date_source=DateSource.DISCOVERED,
        )

    @staticmethod
    def _pick(node: Any, selector: str | None) -> str:
        if not selector:
            return ""
        found = node.css_first(selector)
        return " ".join(found.text(strip=True).split()) if found is not None else ""

    def _build(
        self,
        feed: Feed,
        *,
        url: str,
        title: str,
        company: str,
        location: str | None,
        country: str | None,
        description: str,
        posted_at: Any,
        date_source: DateSource,
    ) -> Job:
        haystack = f"{title}\n{location or ''}\n{description[:1500]}"
        if HYBRID_WORDS.search(haystack):
            work_mode = WorkMode.HYBRID
        elif feed.remote or REMOTE_WORDS.search(haystack):
            work_mode = WorkMode.REMOTE
        else:
            work_mode = WorkMode.UNKNOWN

        resolved = country or country_from_location(location)
        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=company or feed.label,
            title=title,
            external_id=url,
            location=location,
            country=resolved,
            region=region_for(resolved) if resolved else Region.UNKNOWN,
            work_mode=work_mode,
            remote=True if work_mode is WorkMode.REMOTE else None,
            description=f"[{feed.label}]\n\n{description}".strip(),
            posted_at=posted_at,
            date_source=date_source,
        )

    def parse(self, xml: str, feed: Feed) -> list[Job]:
        try:
            root = ET.fromstring(xml or "")
        except ET.ParseError as exc:
            # Reported per-feed by scrape()'s isolation; a malformed feed must
            # not come back as the misleading "no postings found".
            raise ScraperPermanentError(
                f"customfeeds: {feed.label} is not valid XML: {exc}"
            ) from exc

        if root.tag not in {"rss", f"{ATOM}feed", "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF"}:
            raise ScraperPermanentError("customfeeds: unknown feed root")
        items = list(root.iter("item")) or list(root.iter(f"{ATOM}entry"))
        jobs: list[Job] = []
        for item in items:
            job = self._parse_item(item, feed)
            if job is not None:
                jobs.append(job)
        return jobs

    def _parse_item(self, item: ET.Element, feed: Feed) -> Job | None:
        raw_title = (self._text(item, "title", f"{ATOM}title") or "").strip()
        url = self._link(item)
        if not raw_title or not url:
            return None

        company, title = self._split_title(raw_title, item)

        # html_to_text returns None for empty input, and plenty of feeds carry
        # a title and a link with nothing else.
        description = (
            html_to_text(self._text(item, "{http://purl.org/rss/1.0/modules/content/}encoded", f"{ATOM}content", "description", f"{ATOM}summary") or "")
            or ""
        )

        haystack = f"{raw_title}\n{description[:1500]}"
        if HYBRID_WORDS.search(haystack):
            work_mode = WorkMode.HYBRID
        elif feed.remote or REMOTE_WORDS.search(haystack):
            work_mode = WorkMode.REMOTE
        else:
            work_mode = WorkMode.UNKNOWN

        country = feed.country or country_from_location(description[:200]) or None
        posted_at = self._date(item)

        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=company or feed.label,
            title=title,
            external_id=self._guid(item) or url,
            location=None,
            country=country,
            region=region_for(country) if country else Region.UNKNOWN,
            work_mode=work_mode,
            remote=True if work_mode is WorkMode.REMOTE else None,
            # Which feed a posting came from is the only provenance there is.
            description=f"[{feed.label}]\n\n{description}".strip(),
            posted_at=posted_at,
            # A feed's date is when the feed published it, which for a job board
            # is the listing date, not an employer-stated one.
            date_source=date_source_for(None, posted_at)[1],
        )

    # -- element helpers -----------------------------------------------------

    @staticmethod
    def _text(item: ET.Element, *tags: str) -> str | None:
        """First non-empty match. Atom namespaces every element, RSS none."""
        for tag in tags:
            found = item.find(tag)
            if found is not None:
                value = " ".join(found.itertext()).strip()
                if value:
                    return value
        return None

    @staticmethod
    def _link(item: ET.Element) -> str | None:
        link = item.find("link")
        if link is not None and link.text and link.text.strip():
            return link.text.strip()
        # Atom puts it in an attribute.
        for candidate in item.iter(f"{ATOM}link"):
            href = candidate.attrib.get("href")
            if href and candidate.attrib.get("rel", "alternate") == "alternate":
                return href
        return None

    @staticmethod
    def _guid(item: ET.Element) -> str | None:
        for tag in ("guid", f"{ATOM}id"):
            found = item.find(tag)
            if found is not None and found.text:
                return found.text.strip()
        return None

    @staticmethod
    def _date(item: ET.Element) -> datetime | None:
        raw = None
        for tag in ("pubDate", f"{ATOM}published", f"{ATOM}updated"):
            found = item.find(tag)
            if found is not None and found.text:
                raw = found.text.strip()
                break
        if not raw:
            return None
        try:
            return parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            pass
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None

    @staticmethod
    def _split_title(raw_title: str, item: ET.Element) -> tuple[str | None, str]:
        """Pull the employer out of the title, or take it from dc:creator."""
        creator = item.findtext(DC_CREATOR)
        if creator and creator.strip():
            return creator.strip().split("\n")[0].strip(), raw_title

        match = TITLE_AT.match(raw_title)
        if match:
            return match.group("company").strip(), match.group("title").strip()
        match = TITLE_COLON.match(raw_title)
        if match:
            return match.group("company").strip(), match.group("title").strip()
        return None, raw_title


def feed_host(url: str) -> str:
    host = urlsplit(url).netloc
    return host[4:] if host.startswith("www.") else host
