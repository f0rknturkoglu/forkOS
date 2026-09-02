"""Sources assessed and found blocked — no parser is written.

Each raises rather than guessing, so the registry stays honest: `sync` skips
the source and `portals.yaml` records why. Details are in the status lines.
"""

from __future__ import annotations

from typing import Any

from ..models import Job
from .base import ScraperBase, ScraperHttpClient


class _BlockedScraper(ScraperBase):
    """Base for a source that cannot be collected without browser automation."""

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        return self.parse("")

    def parse(self, html: Any) -> list[Job]:
        raise NotImplementedError(self._blocked_reason)

    @property
    def _blocked_reason(self) -> str:
        raise NotImplementedError


class CryptoJobsListScraper(_BlockedScraper):
    source_key = "cryptojobslist"
    label = "CryptoJobsList"
    base_url = "https://cryptojobslist.com"

    _blocked_reason = (
        "cryptojobslist: the site answers 403 with a Cloudflare challenge to "
        "every honest UA (only Googlebot/Twitterbot pass), and the "
        "api.cryptojobslist.com jobs.rss feed was empty when checked "
        "2026-08-18. Revisit if the block lifts or the api feed fills."
    )


class RubyOnRemoteScraper(_BlockedScraper):
    source_key = "rubyonremote"
    label = "Ruby on Remote"
    base_url = "https://rubyonremote.com"

    _blocked_reason = (
        "rubyonremote: hard Cloudflare challenge on /, sitemap, feed.rss and "
        "remote_companies.json — honest UA, search-bot UAs, headless browser "
        "and Jina proxy all 403. Bypassing means browser automation, which "
        "this project does not do."
    )


class NodeskScraper(_BlockedScraper):
    source_key = "nodesk"
    label = "Nodesk"
    base_url = "https://nodesk.co"

    _blocked_reason = (
        "nodesk: the /remote-jobs listing is client-rendered (Supabase "
        "fetch) with no verified public listing API, and detail pages carry "
        "no stable id. Revisit if a public listing endpoint appears."
    )


class JustJoinItScraper(_BlockedScraper):
    source_key = "justjoinit"
    label = "JustJoin.it"
    base_url = "https://justjoin.it"

    _blocked_reason = (
        "justjoinit: blocked by robots.txt, checked 2026-08-09. /api/ is "
        "disallowed for every agent, and the scraper correctly refuses rather "
        "than fetching. There is a permitted route — /sitemaps/active-jobs.xml, "
        "which redirects to public.justjoin.com and indexes per-posting "
        "sitemaps — but using it means fetching each posting page one by one, "
        "which is a different scraper than the one written here. Keep off "
        "until then."
    )


class LandingJobsScraper(_BlockedScraper):
    source_key = "landingjobs"
    label = "Landing.jobs"
    base_url = "https://landing.jobs"

    _blocked_reason = (
        "landingjobs: blocked by robots.txt, checked 2026-08-09. /api/, /jobs? "
        "and /jobs/search are all disallowed for every agent, so the internal "
        "API the scraper was written against is off limits. The permitted "
        "sitemap holds only 2069 category and city pages — not one individual "
        "posting — so there is no allowed path to the listings. Keep off."
    )


class HoneypotScraper(_BlockedScraper):
    source_key = "honeypot"
    label = "Honeypot.io"
    base_url = "https://www.honeypot.io"

    _blocked_reason = (
        "honeypot: site unreachable, checked 2026-08-09. www.honeypot.io does "
        "not accept connections at all — robots.txt included — so this is not "
        "a wrong API URL but a host that is no longer serving. Was reverse "
        "recruiting for DE/NL/AT with explicit visa status. Keep off."
    )


class OfferZenScraper(_BlockedScraper):
    source_key = "offerzen"
    label = "OfferZen"
    base_url = "https://www.offerzen.com"

    _blocked_reason = (
        "offerzen: no public postings to read, checked 2026-08-09. The guessed "
        "/api/v1/jobs is a 404, /jobs redirects to marketing pages, and neither "
        "the landing page nor a category page carries a JobPosting, ld+json or "
        "__NEXT_DATA__ block. OfferZen is a reverse marketplace — companies "
        "approach candidates behind a login — so there is no listing to scrape."
    )

