"""Manfred (getmanfred.com) — developer-focused Spanish job platform.

Verified 2026-08-08 against the live site.

**There is no public REST API.** `api.getmanfred.com/v1/jobs` returns 404, as
does `/api/offers`. An earlier version of this file claimed one existed and
documented a `/developers` page; both were invented. What follows was read off
real responses.

What actually works, and why this shape:

1. `robots.txt` allows everything and advertises `sitemap-offers.xml`. That
   sitemap is the offer index — one request, every live posting, with a
   `lastmod` per entry. Far cleaner than paginating a listing page, and the
   listing page would not help anyway: `/ofertas-empleo` ships filter
   vocabularies in `__NEXT_DATA__` and loads the offers client-side.
2. Each offer page is Next.js and carries `__NEXT_DATA__` with a fully
   structured `props.pageProps.offer`, plus a schema.org JobPosting blob in
   `offer.jsonld` that includes a real `datePosted` — so `date_source` is
   `employer`, not `updated`.

Detail pages cost one request each at 2s spacing, so the run is capped
(`max_offers`) and the newest `lastmod` entries go first.

Note on the cap: the sitemap keeps closed offers listed — 5 of the 7 most
recently modified entries were `status: CLOSED` when this was written, because
closing an offer *is* a modification and bumps it to the top of the lastmod
ordering. Those are skipped, so a run yields noticeably fewer jobs than
`max_offers` suggests.
"""

from __future__ import annotations

import json
import re
from typing import Any
from xml.etree import ElementTree

from ..models import DateSource, Job, Layer, Region, WorkMode
from ..normalize import html_to_text, parse_datetime, parse_location
from .base import ScraperBase, ScraperConfig, ScraperHttpClient, ScraperPermanentError

SITEMAP_URL = "https://www.getmanfred.com/sitemap-offers.xml"
SITE_BASE = "https://www.getmanfred.com"

#: Offer detail pages fetched per run. Each is a separate request at the
#: configured 2s spacing, so this is a time budget as much as a politeness one.
DEFAULT_MAX_OFFERS = 40

_NEXT_DATA_RE = re.compile(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
_SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


class ManfredScraper(ScraperBase):
    """Manfred offer scraper, driven by the sitemap and `__NEXT_DATA__`."""

    source_key = "manfred"
    label = "Manfred"
    base_url = SITE_BASE

    def __init__(
        self,
        config: ScraperConfig | None = None,
        *,
        max_offers: int = DEFAULT_MAX_OFFERS,
    ) -> None:
        super().__init__(config)
        self.max_offers = max_offers

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        entries = parse_sitemap(await client.get_html(SITEMAP_URL))
        if not entries:
            raise ScraperPermanentError(f"{self.source}: sitemap held no offer URLs")

        # Newest first, so a capped run still sees what changed.
        entries.sort(key=lambda e: e[1] or "", reverse=True)

        jobs: list[Job] = []
        for url, _lastmod in entries[: self.max_offers]:
            try:
                html = await client.get_html(url)
            except ScraperPermanentError:
                continue  # one dead offer must not end the run
            job = self.parse_offer(html, url)
            if job is not None:
                jobs.append(job)
        return jobs

    def parse_offer(self, html: str, url: str) -> Job | None:
        """Pure: HTML in, Job out. Drives the offline tests and `--mock`."""
        data = extract_next_data(html)
        if data is None:
            return None
        offer = (data.get("props") or {}).get("pageProps", {}).get("offer")
        return self.build_job(offer, url) if isinstance(offer, dict) else None

    def build_job(self, offer: dict[str, Any], url: str) -> Job | None:
        title = offer.get("title")
        if not title:
            return None
        if offer.get("status") and offer["status"] != "ACTIVE":
            return None

        jsonld = _load_jsonld(offer.get("jsonld"))

        # A real publish date, not an edit timestamp.
        posted_at = parse_datetime(jsonld.get("datePosted"))
        date_source = DateSource.EMPLOYER
        if posted_at is None:
            posted_at = parse_datetime(offer.get("updatedAt"))
            date_source = DateSource.UPDATED if posted_at else DateSource.DISCOVERED

        work_mode, remote = _work_mode(offer, jsonld)
        location_text = _location_text(offer, jsonld)
        info = parse_location(location_text)
        # Manfred is a Spanish platform; a remote posting with no named country
        # is Spain-based unless it says otherwise.
        country = info.country or ("ES" if work_mode is WorkMode.REMOTE else None)
        region = info.region if info.country else (Region.EU if country else info.region)

        # The jsonld description is a short summary; the page's own sections and
        # FAQs carry the requirements. The FAQs matter most: Manfred asks every
        # employer "¿Puedo aplicar si vivo fuera de España?" and the answer is
        # the clearest relocation signal any source in this project provides.
        description = _compose_description(jsonld, offer)

        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=offer.get("company")
            or (jsonld.get("hiringOrganization") or {}).get("name")
            or "",
            title=str(title).strip(),
            external_id=str(offer["id"]) if offer.get("id") is not None else None,
            location=location_text,
            city=info.city,
            country=country,
            region=region,
            work_mode=work_mode,
            remote=remote,
            description=description,
            salary=_salary(offer),
            language=_language(offer),
            posted_at=posted_at,
            date_source=date_source,
        )


# ---------------------------------------------------------------------------
# Parsing helpers — pure, so fixtures can drive them
# ---------------------------------------------------------------------------


def parse_sitemap(xml: str) -> list[tuple[str, str | None]]:
    """Return [(offer url, lastmod)] from sitemap-offers.xml."""
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        return []

    entries: list[tuple[str, str | None]] = []
    for node in root.findall("sm:url", _SITEMAP_NS) or root.findall("url"):
        loc = _child(node, "loc")
        if loc is None or not (loc.text or "").strip():
            continue
        lastmod = _child(node, "lastmod")
        entries.append(
            (loc.text.strip(), (lastmod.text or "").strip() if lastmod is not None else None)
        )
    return entries


def _child(node: ElementTree.Element, tag: str) -> ElementTree.Element | None:
    """Find a child with or without the sitemap namespace.

    Written out rather than chained with `or`: an ElementTree element with no
    children is falsy, so `find(ns) or find(plain)` discards every match that
    has no sub-elements — which is every <lastmod> there is.
    """
    found = node.find(f"sm:{tag}", _SITEMAP_NS)
    return found if found is not None else node.find(tag)


def extract_next_data(html: str) -> dict[str, Any] | None:
    """Pull the `__NEXT_DATA__` payload out of a Next.js page."""
    match = _NEXT_DATA_RE.search(html or "")
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _load_jsonld(raw: Any) -> dict[str, Any]:
    """`offer.jsonld` is a JSON *string* holding a schema.org JobPosting."""
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str) or not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _work_mode(offer: dict[str, Any], jsonld: dict[str, Any]) -> tuple[WorkMode, bool | None]:
    """`offer.remote` is a percentage: 100 fully remote, 0 fully on-site."""
    remote_pct = offer.get("remote")
    if isinstance(remote_pct, (int, float)):
        if remote_pct >= 100:
            return WorkMode.REMOTE, True
        if remote_pct <= 0:
            return WorkMode.ONSITE, False
        return WorkMode.HYBRID, False

    if jsonld.get("jobLocationType") == "TELECOMMUTE":
        return WorkMode.REMOTE, True
    return WorkMode.UNKNOWN, None


def _location_text(offer: dict[str, Any], jsonld: dict[str, Any]) -> str | None:
    summary = offer.get("locationsSummary") or {}
    cities = summary.get("trimmedCities") or summary.get("extraCities") or []
    names = [c.get("name") if isinstance(c, dict) else str(c) for c in cities]
    names = [n for n in names if n]
    if names:
        return ", ".join(names)

    requirement = jsonld.get("applicantLocationRequirements")
    if isinstance(requirement, dict) and requirement.get("name"):
        return str(requirement["name"])

    location = jsonld.get("jobLocation")
    if isinstance(location, dict):
        address = location.get("address") or {}
        parts = [address.get("addressLocality"), address.get("addressCountry")]
        joined = ", ".join(p for p in parts if p)
        if joined:
            return joined
    return None


def _salary(offer: dict[str, Any]) -> str | None:
    """Salary bands are in thousands, per Manfred's own display ("€32-35K")."""
    low, high = offer.get("salaryMin"), offer.get("salaryMax")
    currency = offer.get("currency") or "€"
    if not low and not high:
        return None
    if low and high and low != high:
        return f"{currency}{low:g}-{high:g}K"
    return f"{currency}{(low or high):g}K"


def _language(offer: dict[str, Any]) -> str | None:
    languages = offer.get("languages") or []
    if languages and isinstance(languages[0], dict):
        code = languages[0].get("code") or languages[0].get("name")
        return str(code).lower() if code else None
    return None


#: Prose sections, in the order they read on the page.
_SECTION_KEYS = (
    "requirementsSectionData",
    "skillsSectionData",
    "howSectionData",
    "teamSectionData",
)


def _section_text(offer: dict[str, Any]) -> str | None:
    """Fallback description assembled from the page's markdown sections."""
    chunks: list[str] = []
    for key in _SECTION_KEYS:
        section = offer.get(key)
        if not isinstance(section, dict):
            continue
        for value in section.values():
            if isinstance(value, str) and len(value) > 40:
                chunks.append(value)
    return html_to_text("\n\n".join(chunks)) if chunks else None


def faq_text(offer: dict[str, Any]) -> str | None:
    """Flatten the FAQ block into "Q A" lines.

    Verified across 7 offers on 2026-08-08: every one carried the templated
    question "¿Puedo aplicar si vivo fuera de España?" with a real answer —
    "No … permiso de trabajo", "Sí, siempre y cuando tengas pasaporte de la
    Unión Europea", "Sí, pero … timezone". There is no structured visa field
    on the offer, so this prose is the signal, and it has to reach the
    description for the scorer to read it.
    """
    faqs = (offer.get("faqsSectionData") or {}).get("faqs")
    if not isinstance(faqs, list):
        return None
    lines = [
        f"{entry.get('q', '').strip()} {entry.get('a', '').strip()}".strip()
        for entry in faqs
        if isinstance(entry, dict) and (entry.get("q") or entry.get("a"))
    ]
    return "\n".join(line for line in lines if line) or None


def _compose_description(jsonld: dict[str, Any], offer: dict[str, Any]) -> str | None:
    parts = [
        html_to_text(jsonld.get("description")),
        _section_text(offer),
        html_to_text(faq_text(offer)),
    ]
    joined = "\n\n".join(part for part in parts if part)
    return joined or None
