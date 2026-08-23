"""Hacker News "Ask HN: Who is hiring?" — the monthly hiring thread.

    GET https://hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring
    GET https://hn.algolia.com/api/v1/search?tags=comment,story_<id>

Posted on the first of every month by the `whoishiring` account. Engineering
leads write the postings themselves, so remote and visa terms are stated
plainly rather than buried in a careers page.

What the shape of this source demands:

* The same account posts a *second* thread, "Who wants to be hired?", where
  candidates advertise themselves. Same tag, same day — filtering by title is
  the only thing separating job postings from job seekers.
* Only top-level comments are postings. Replies (`parent_id != story_id`) are
  conversation: "just applied on your website", "is this open to juniors?".
* The convention is a pipe-separated first line —
  `Company | Role | Location | REMOTE | Full-time | $110k-$130k` — but it is a
  convention, not a schema. Fields appear in any order and any of them may be
  missing, so each pipe segment is classified by what it looks like rather than
  by its position.

Verified 2026-08-09 against the August 2026 thread: 308 comments.
"""

from __future__ import annotations

import html
import re
from datetime import UTC, datetime
from typing import Any

from ..geo import CA_PROVINCE_CODES, US_STATE_CODES, country_from_name, region_for
from ..models import DateSource, Job, Layer, Region, WorkMode
from .base import ScraperBase, ScraperHttpClient, ScraperPermanentError

STORY_URL = (
    "https://hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring&hitsPerPage=12"
)
COMMENTS_URL = "https://hn.algolia.com/api/v1/search?tags=comment,story_{story_id}"
ITEM_URL = "https://news.ycombinator.com/item?id={item_id}"

#: The hiring thread, not the "who wants to be hired" companion thread.
HIRING_TITLE = re.compile(r"who\s+is\s+hiring", re.I)
SEEKING_TITLE = re.compile(r"who\s+wants\s+to\s+be\s+hired", re.I)

REMOTE_WORDS = re.compile(r"\bremote\b|\bwfh\b", re.I)
ONSITE_WORDS = re.compile(r"\bon[\s-]?site\b|\bin[\s-]?office\b", re.I)
HYBRID_WORDS = re.compile(r"\bhybrid\b", re.I)
VISA_WORDS = re.compile(r"\bvisa\b|\bsponsor\w*\b|\brelocation\b", re.I)
SALARY = re.compile(r"[€$£]\s?\d|\d+\s?k\s?[-–]\s?\d+\s?k", re.I)
EMPLOYMENT = re.compile(
    r"\b(full[\s-]?time|part[\s-]?time|contract|intern(ship)?|freelance)\b", re.I
)


class HackerNewsScraper(ScraperBase):
    source_key = "hackernews"
    label = "HN Who is Hiring"
    base_url = "https://news.ycombinator.com"

    def __init__(self, config: Any = None, *, max_threads: int = 1, max_pages: int = 6) -> None:
        super().__init__(config)
        #: How many monthly threads back to read. One is the current month.
        self.max_threads = max_threads
        self.max_pages = max_pages

    async def scrape(self, client: ScraperHttpClient) -> list[Job]:
        try:
            index = await client.get_json(STORY_URL)
        except ScraperPermanentError:
            return []

        stories = self._hiring_stories(index)[: self.max_threads]
        jobs: list[Job] = []
        for story in stories:
            jobs.extend(await self._thread(client, story))
        return jobs

    @staticmethod
    def _hiring_stories(index: Any) -> list[dict[str, Any]]:
        """Newest first, hiring threads only."""
        hits = index.get("hits") if isinstance(index, dict) else None
        if not isinstance(hits, list):
            return []
        stories = []
        for hit in hits:
            if not isinstance(hit, dict):
                continue
            title = hit.get("title") or ""
            if SEEKING_TITLE.search(title) or not HIRING_TITLE.search(title):
                continue
            stories.append(hit)
        return stories

    async def _thread(self, client: ScraperHttpClient, story: dict[str, Any]) -> list[Job]:
        story_id = str(story.get("objectID") or "")
        if not story_id:
            return []
        base = COMMENTS_URL.format(story_id=story_id)

        jobs: list[Job] = []
        for page in range(self.max_pages):
            try:
                payload = await client.get_json(f"{base}&hitsPerPage=100&page={page}")
            except ScraperPermanentError:
                break
            hits = payload.get("hits") if isinstance(payload, dict) else None
            if not isinstance(hits, list) or not hits:
                break
            for hit in hits:
                job = self._parse_comment(hit, story_id)
                if job is not None:
                    jobs.append(job)
            pages = payload.get("nbPages")
            if isinstance(pages, int) and page + 1 >= pages:
                break
        return jobs

    def _parse_comment(self, hit: Any, story_id: str) -> Job | None:
        if not isinstance(hit, dict):
            return None
        # Replies are conversation, not postings.
        if str(hit.get("parent_id") or "") != story_id:
            return None

        text = self._plain_text(hit.get("comment_text") or "")
        if not text.strip():
            return None

        lines = [line for line in text.splitlines() if line.strip()]
        if not lines:
            return None
        header = lines[0]
        fields = [part.strip() for part in header.split("|") if part.strip()]
        if len(fields) < 2:
            # No pipe convention followed — not enough structure to trust.
            return None

        company = self._company(fields[0])
        if not company or len(company) > 80:
            return None

        title, rest = self._role(fields[1:])
        if not title:
            return None

        location, work_mode = self._place(rest, text)
        salary = next((f for f in rest if SALARY.search(f)), None)

        country = self._country_of(location)

        item_id = str(hit.get("objectID") or "")
        posted_at = self._created(hit.get("created_at_i"))

        return Job.build(
            url=ITEM_URL.format(item_id=item_id),
            source=self.source,
            layer=Layer.B,
            company=company,
            title=title,
            external_id=item_id,
            location=location,
            country=country,
            region=region_for(country) if country else Region.UNKNOWN,
            work_mode=work_mode,
            remote=True if work_mode is WorkMode.REMOTE else None,
            description=text,
            salary=salary,
            posted_at=posted_at,
            # The employer wrote this comment; its timestamp is the posting date.
            date_source=DateSource.EMPLOYER if posted_at else DateSource.DISCOVERED,
        )

    @staticmethod
    def _company(field: str) -> str:
        """Strip the URL people append to their company name.

        "Eleos Technologies (https://eleostech.com)" and bare
        "Flywheel Motion https://…?utm_source=hn" are both common.
        """
        field = re.sub(r"\(\s*https?://[^)]*\)", "", field)
        field = re.sub(r"https?://\S+", "", field)
        return field.strip(" -–—,|").strip()

    @classmethod
    def _role(cls, fields: list[str]) -> tuple[str | None, list[str]]:
        """Find the job title among the segments after the company.

        The role is usually second, but plenty of postings lead with the
        location or the contract type — "Aptura AI | London | Full-Time |
        Senior Engineer" would otherwise be filed as a job called "Full-Time".
        """
        for index, field in enumerate(fields):
            if SALARY.search(field) or re.search(r"https?://|\bwww\.", field):
                continue
            # "ONSITE, REMOTE" and "Full-time / Contract" are descriptors even
            # though neither is a single word, so strip the punctuation and ask
            # whether anything is left that is not a descriptor.
            residue = re.sub(
                r"[,/&()+]|\bor\b|\band\b",
                " ",
                EMPLOYMENT.sub(
                    " ", HYBRID_WORDS.sub(" ", ONSITE_WORDS.sub(" ", REMOTE_WORDS.sub(" ", field)))
                ),
            ).strip()
            if not residue:
                continue
            if cls._country_of(field):
                continue
            return field, fields[:index] + fields[index + 1 :]
        return None, fields

    @staticmethod
    def _country_of(location: str | None) -> str | None:
        """Resolve a country from a free-text location.

        "London" resolves on its own, but "New York, NY" does not — the
        fragments have to be tried separately, and a bare US state code is
        itself the answer.
        """
        if not location:
            return None
        direct = country_from_name(location)
        if direct:
            return direct
        for part in re.split(r"[,/()]", location):
            part = part.strip()
            if not part:
                continue
            # State codes are checked first because "CA" is both California and
            # the ISO code for Canada — "Hawthorne, CA" is Los Angeles, not
            # Ontario, and the same two letters cannot mean both.
            if part.upper() in US_STATE_CODES:
                return "US"
            if part.upper() in CA_PROVINCE_CODES:
                return "CA"
            found = country_from_name(part)
            if found:
                return found
        return None

    def _place(self, fields: list[str], text: str) -> tuple[str | None, WorkMode]:
        """Classify the pipe segments rather than trusting their order."""
        work_mode = WorkMode.UNKNOWN
        location = None

        for field in fields:
            if HYBRID_WORDS.search(field):
                work_mode = WorkMode.HYBRID
            elif REMOTE_WORDS.search(field) and work_mode is WorkMode.UNKNOWN:
                work_mode = WorkMode.REMOTE
            elif ONSITE_WORDS.search(field) and work_mode is WorkMode.UNKNOWN:
                work_mode = WorkMode.ONSITE

        for field in fields:
            if SALARY.search(field) or EMPLOYMENT.match(field):
                continue
            if REMOTE_WORDS.fullmatch(field) or ONSITE_WORDS.fullmatch(field):
                continue
            if self._country_of(field):
                location = field
                break
            # A place usually has a comma or is short and title-cased.
            if "," in field or (len(field) < 40 and field[:1].isupper()):
                location = location or field

        if location and REMOTE_WORDS.fullmatch(location.strip()):
            location, work_mode = None, WorkMode.REMOTE
        if work_mode is WorkMode.UNKNOWN and REMOTE_WORDS.search(text[:400]):
            work_mode = WorkMode.REMOTE
        return location, work_mode

    @staticmethod
    def _plain_text(comment_html: str) -> str:
        """Algolia returns HN's own markup: <p> breaks, entities, <a> links."""
        text = re.sub(r"<p>", "\n", comment_html)
        text = re.sub(r"<[^>]+>", "", text)
        return html.unescape(text).strip()

    @staticmethod
    def _created(value: Any) -> datetime | None:
        if isinstance(value, (int, float)) and value > 1_000_000_000:
            return datetime.fromtimestamp(value, tz=UTC)
        return None
