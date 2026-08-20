"""Sources that have been assessed but not implemented.

Each raises rather than guessing. A guessed selector fails silently and looks
like a working scraper reporting zero jobs, which is worse than an honest
error — so this says exactly what is missing.

Registered and disabled, so `sync` skips it but `portals.yaml` still accounts
for it.
"""

from __future__ import annotations

from typing import Any

from ..models import Job
from .base import ScraperBase, ScraperHttpClient


class RemoteRocketshipScraper(ScraperBase):
    """Remote Rocketship — blocked at the door, not by policy.

    robots.txt permits it. The site itself answers **403 with a Cloudflare
    "Just a moment" challenge** to an honest User-Agent, checked 2026-08-08.

    Getting past that would mean impersonating a browser or solving the
    challenge, which is the one thing this project does not do — so this is
    not a discovery task and there is nothing to capture. If the block is ever
    lifted, the structure can be looked at then.
    """

    source_key = "remoterocketship"
    label = "Remote Rocketship"
    base_url = "https://www.remoterocketship.com"

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        return self.parse("")

    def parse(self, html: Any) -> list[Job]:
        raise NotImplementedError(
            "remoterocketship: the site returns 403 with a Cloudflare challenge "
            "to an honest User-Agent, despite robots.txt permitting the path. "
            "Working around that is out of scope, so no parser exists."
        )
