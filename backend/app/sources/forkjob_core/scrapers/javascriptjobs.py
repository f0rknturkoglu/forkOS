"""JavaScript Jobs (javascript.jobs, formerly jsremotely.com) — JS stack remote.

    GET https://javascript.jobs/remote[?page=N]

SSR listing, verified 2026-08-18: HTTP 200 with an honest UA; each posting is
a `a.jobcardStyle1[href="/job/<slug>"]` card carrying title, an employment
badge, a remote badge and a relative age ("3D"). jsremotely.com now 301s to
javascript.jobs — the scraper uses the canonical host. robots.txt allows
everything.

Why it matters: a stack-specific board; JS roles are a big slice of the
remote-B2B market. The detail page's JSON-LD is malformed (missing commas),
so the listing card is read instead — no per-posting requests at all.

Field notes:
- The card's `<a>` href is the posting URL; the trailing slug is the only id
  available (the site ships no numeric id), so the URL is the external id.
- Ages are relative prose ("3D"), never an absolute publish date →
  date_source is `discovered`, nothing is invented.
- Company is not in the card; detail pages carry it in malformed JSON, so
  company is unknown for now.
"""

from __future__ import annotations

from typing import Any

from selectolax.parser import HTMLParser, Node

from ..models import DateSource, Job, Layer, WorkMode
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError

LISTING_URL = "https://javascript.jobs/remote"
BASE_URL = "https://javascript.jobs"
DEFAULT_MAX_PAGES = 3

CARD = "a.jobcardStyle1"


class JavascriptJobsScraper(ScraperBase):
    source_key = "javascriptjobs"
    label = "JavaScript Jobs"
    base_url = BASE_URL

    def __init__(self, config: Any = None, *, max_pages: int = DEFAULT_MAX_PAGES) -> None:
        super().__init__(config)
        self.max_pages = max_pages

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()
        for page in range(1, self.max_pages + 1):
            url = LISTING_URL if page == 1 else f"{LISTING_URL}?page={page}"
            html = await self.isolate(url, lambda: client.get_html(url))
            if html is None:
                break
            page_jobs = self.parse(html)
            if not page_jobs:
                break
            fresh = self.dedup_seen(seen, page_jobs)
            jobs.extend(fresh)
            if not fresh:
                break
        return jobs

    def parse(self, html: str) -> list[Job]:
        jobs: list[Job] = []
        for card in HTMLParser(html or "").css(CARD):
            job = self.build_job(card)
            if job is not None:
                jobs.append(job)
        return jobs

    def build_job(self, card: Node) -> Job | None:
        href = (card.attributes.get("href") or "").strip()
        if not href:
            return None
        url = href if href.startswith("http") else f"{BASE_URL}{href}"

        title_node = card.css_first("div.tw-text-\\[\\#18191C\\]")
        if title_node is None:
            title_node = card.css_first("div")
        title = " ".join(title_node.text(strip=True).split()) if title_node else ""
        if not title:
            return None

        text = card.text(separator=" ", deep=True).lower()
        work_mode = WorkMode.REMOTE if "remote" in text else WorkMode.UNKNOWN

        return Job.build(
            url=url,
            source=self.source,
            layer=Layer.B,
            company="?",
            title=title,
            external_id=url.rstrip("/").rsplit("/", 1)[-1] or None,
            work_mode=work_mode,
            remote=True if work_mode is WorkMode.REMOTE else None,
            date_source=DateSource.DISCOVERED,
        )
