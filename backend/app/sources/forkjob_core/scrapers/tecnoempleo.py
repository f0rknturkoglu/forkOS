"""Tecnoempleo (tecnoempleo.com) — Spain's largest IT-only job portal.

Verified 2026-08-08 against a live posting, frozen as a fixture.

**There is no listing API and the search page's query parameters are
undocumented.** What works, and why this shape:

1. `robots.txt` advertises `sitemap.xml`, and the sitemap is the offer index:
   2,008 offer URLs (`/<slug>/<skills>/rf-<hex>`) all carrying a real
   `lastmod` and priority 1.0. It also holds the full site history back to
   2017, so offers are filtered to the last `max_age_days` and fetched
   newest-first, capped at `max_offers` (each detail page is one request at
   the configured 2 s spacing — a time budget as much as a politeness one).
2. Each offer page is server-rendered HTML with a schema.org `JobPosting` in
   ld+json carrying a real `datePosted` — so `date_source` is `employer`,
   not `updated`. The ld+json `identifier` is the *company* id (the JobFluent
   trap), so `external_id` comes from the `rf-<hex>` URL tail.
3. The right-hand detail box (`ul.list-unstyled li.list-item`, label/value
   pairs) holds Experiencia, Jornada, Tipo contrato — facts the scorer reads
   — and is appended to the description. A closed offer resolves to a 200
   search page with no JobPosting and is skipped.

robots.txt note (checked 2026-08-08): `User-agent: *` does not disallow the
listings, but `AnthropicBot`, `Claude*` and `GPTBot` are named with a blanket
`Disallow: /`. This tool is none of those agents and identifies honestly;
the owner's stated intent is on record and the decision is deliberate.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any
from xml.etree import ElementTree

from selectolax.parser import HTMLParser

from ..models import Job, Layer, Region, WorkMode, date_source_for
from ..normalize import html_to_text, parse_datetime, sitemap_child
from .base import ScraperBase, ScraperConfig, ScraperHttpClient, ScraperPermanentError
from .schemaorg import find_type, ld_blocks, organisation_name, place, text

SITEMAP_URL = "https://www.tecnoempleo.com/sitemap.xml"
SITE_BASE = "https://www.tecnoempleo.com"

#: Offer pages fetched per run — one request each at 2 s spacing.
DEFAULT_MAX_OFFERS = 40
#: The sitemap holds the whole site history back to 2017; only offers with a
#: lastmod inside this window are treated as live.
DEFAULT_MAX_AGE_DAYS = 30

#: Offer URLs end in /rf-<hex>; everything else in the sitemap is a category,
#: company or article page.
_RF_URL_RE = re.compile(r"/rf-([0-9a-f]+)/?$")
#: "Nivel Profesional: Empleado" lives outside the detail box, in the
#: "Otros detalles" section — a regex beats a fragile selector chain there.
_NIVEL_RE = re.compile(r"Nivel Profesional:\s*([^<]+)")
_SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

#: Detail-box rows worth surfacing to the scorer; the rest (Ubicación,
#: Funciones, skills buttons) is noise or already structured elsewhere.
_DETAIL_KEYS = ("Experiencia", "Jornada", "Tipo contrato")

_REMOTO_RE = re.compile(r"\bremot[oa]s?\b", re.IGNORECASE)
_HIBRIDO_RE = re.compile(r"\b(h[ií]brid[oa]|semipresencial)\b", re.IGNORECASE)
_PRESENCIAL_RE = re.compile(r"\bpresencial\b", re.IGNORECASE)


class TecnoempleoScraper(ScraperBase):
    source_key = "tecnoempleo"
    label = "Tecnoempleo"
    base_url = SITE_BASE

    def __init__(
        self,
        config: ScraperConfig | None = None,
        *,
        max_offers: int = DEFAULT_MAX_OFFERS,
        max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    ) -> None:
        super().__init__(config)
        self.max_offers = max_offers
        self.max_age_days = max_age_days

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        xml = await client.get_html(SITEMAP_URL)
        entries = offer_entries(xml, max_age_days=self.max_age_days)
        if not entries:
            raise ScraperPermanentError(f"{self.source}: sitemap held no live offer URLs")

        jobs: list[Job] = []
        for url, _lastmod in entries[: self.max_offers]:
            try:
                page = await client.get_html(url)
            except ScraperPermanentError:
                continue  # one dead offer must not end the run
            job = self.parse_offer(page, url)
            if job is not None:
                jobs.append(job)
        return jobs

    def parse(self, html: str) -> list[Job]:
        """Every JobPosting on a page. Drives `--mock` and the offline tests."""
        job = self.parse_offer(html, SITE_BASE)
        return [job] if job is not None else []

    def parse_offer(self, html: str, url: str) -> Job | None:
        """Pure: HTML in, Job out. Drives the offline tests and `--mock`."""
        posting = find_type(ld_blocks(html), "JobPosting")
        if posting is None:
            return None  # closed offers resolve to a search page without one
        title = text(posting.get("title"))
        if not title:
            return None
        return self.build_job(posting, html, url, title)

    def build_job(self, posting: dict[str, Any], html: str, url: str, title: str) -> Job:
        city, country = place(posting.get("jobLocation"))
        # Spain-only portal; a posting without an addressCountry is ES.
        country = country or "ES"

        posted_at = parse_datetime(posting.get("datePosted"))
        if posted_at is None:
            posted_at = _badge_date(html)  # same day, shown as DD/MM/YYYY
        date_source = date_source_for(posted_at)[1]

        detail = _detail_map(html)
        location = detail.get("Ubicación") or ", ".join(p for p in (city, country) if p) or None
        work_mode = _work_mode(posting, title, url, detail)

        description = _compose_description(posting, html, detail)

        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company=organisation_name(posting.get("hiringOrganization")) or "?",
            title=title,
            external_id=_external_id(url),
            location=location,
            city=city,
            country=country,
            region=Region.EU,
            work_mode=work_mode,
            department=posting.get("employmentType") or None,
            description=description,
            salary=detail.get("Salario"),
            language="es",
            posted_at=posted_at,
            date_source=date_source,
        )


# ---------------------------------------------------------------------------
# Parsing helpers — pure, so fixtures can drive them
# ---------------------------------------------------------------------------


def offer_entries(
    xml: str, *, today: date | None = None, max_age_days: int = DEFAULT_MAX_AGE_DAYS
) -> list[tuple[str, date]]:
    """Return [(offer url, lastmod)] from sitemap.xml, newest first.

    Only offer URLs (`/rf-<hex>`) with a `lastmod` inside the age window
    survive — the sitemap also lists categories and the site's full history
    back to 2017.
    """
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        return []

    today = today or date.today()
    cutoff = today - timedelta(days=max_age_days)
    entries: list[tuple[str, date]] = []
    for node in root.findall("sm:url", _SITEMAP_NS) or root.findall("url"):
        loc = sitemap_child(node, "loc")
        if loc is None or not (loc.text or "").strip():
            continue
        url = loc.text.strip()
        if _RF_URL_RE.search(url) is None:
            continue
        lastmod = sitemap_child(node, "lastmod")
        if lastmod is None or not (lastmod.text or "").strip():
            continue
        try:
            modified = date.fromisoformat(lastmod.text.strip()[:10])
        except ValueError:
            continue
        if modified >= cutoff:
            entries.append((url, modified))

    entries.sort(key=lambda e: e[1], reverse=True)
    return entries


def _external_id(url: str) -> str | None:
    """Posting id from the `rf-<hex>` URL tail.

    Deliberately not the ld+json `identifier`, which is the *company* id —
    the same trap JobFluent set, where trusting it collided every posting
    from one employer onto a single row.
    """
    match = _RF_URL_RE.search(url or "")
    return match.group(1) if match else None


def _badge_date(html: str) -> datetime | None:
    """Fallback: the `DD/MM/YYYY` badge next to the location badge.

    Verified to show the same day as ld+json `datePosted`, so it is a real
    publish date, not an edit timestamp.
    """
    for badge in HTMLParser(html).css("span.badge"):
        value = badge.text(deep=True, separator=" ").strip()
        if re.fullmatch(r"\d{2}/\d{2}/\d{4}", value):
            return parse_datetime(value)
    return None


def _detail_map(html: str) -> dict[str, str]:
    """Label/value pairs from the right-hand detail box.

    `li.list-item` rows pair `span.d-inline-block.px-2` (label) with
    `span.float-end` (value) — e.g. "Experiencia" -> "Más de 5 años".
    """
    result: dict[str, str] = {}
    for li in HTMLParser(html).css("ul.list-unstyled li.list-item"):
        label = li.css_first("span.d-inline-block.px-2")
        value = li.css_first("span.float-end")
        if label is None or value is None:
            continue
        label_text = label.text(deep=True, separator=" ").strip()
        value_text = value.text(deep=True, separator=" ").strip()
        if label_text and value_text:
            result[label_text] = value_text
    return result


def _work_mode(posting: dict[str, Any], title: str, url: str, detail: dict[str, str]) -> WorkMode:
    """Remote/hybrid/onsite from the strongest signal available.

    Order matters: the posting's own statement first, then the detail box's
    Teletrabajo row if one appears, then the title and URL slug (Tecnoempleo
    puts "Remoto"/"Híbrido"/"Presencial" in both).
    """
    if posting.get("jobLocationType") == "TELECOMMUTE":
        return WorkMode.REMOTE

    telework = detail.get("Teletrabajo")
    if telework:
        lowered = telework.lower()
        if _REMOTO_RE.search(lowered) or lowered.startswith("sí"):
            return WorkMode.REMOTE
        if _HIBRIDO_RE.search(lowered):
            return WorkMode.HYBRID
        if lowered.startswith("no"):
            return WorkMode.ONSITE

    for haystack in (title, url):
        if _REMOTO_RE.search(haystack):
            return WorkMode.REMOTE
        if _HIBRIDO_RE.search(haystack):
            return WorkMode.HYBRID
        if _PRESENCIAL_RE.search(haystack):
            return WorkMode.ONSITE
    return WorkMode.UNKNOWN


def _compose_description(posting: dict[str, Any], html: str, detail: dict[str, str]) -> str | None:
    """ld+json description plus the detail-box facts the scorer reads."""
    parts = [html_to_text(posting.get("description"))]
    facts: list[str] = []
    for key in _DETAIL_KEYS:
        if detail.get(key):
            facts.append(f"{key}: {detail[key]}")
    nivel = _NIVEL_RE.search(html)
    if nivel and nivel.group(1).strip():
        facts.append(f"Nivel Profesional: {nivel.group(1).strip()}")
    if facts:
        parts.append("\n".join(facts))
    joined = "\n\n".join(part for part in parts if part)
    return joined or None
