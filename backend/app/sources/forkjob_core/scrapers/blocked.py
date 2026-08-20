"""Sources assessed 2026-08-18 and found blocked — no parser is written.

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
