"""UK licensed sponsor register — visa-sponsoring company filter.

This is not a job source — it is a cross-reference filter for Layer A company
names. The UK Home Office publishes a CSV of ~100k organisations licensed to
sponsor Skilled Worker and Temporary Worker visas. Matching a collected job's
company against this list answers "can they sponsor a UK visa?" independently
of whatever the posting itself says.

Usage::

    from forkjob.sponsors import SponsorRegister
    reg = SponsorRegister.load()
    if reg.contains("Monzo Bank"):
        print("UK visa sponsor")

The CSV is fetched from GOV.UK and cached locally. The module extracts the
first column (organisation name) and normalises it for fuzzy matching.
"""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path

import httpx

from .models import norm_company

#: Known GOV.UK URL stem — the date segment changes with each release, so we
#: fetch the landing page first.
_LANDING_URL = "https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers"
_CACHE_PATH = Path("data/cache/uk-sponsors.csv")
_USER_AGENT = "forkjob/0.1 (personal job search bot; +https://github.com/f0rkjob)"

#: CSV column name patterns that hold the organisation name.
_ORG_COLUMNS = re.compile(r"(?i)^(organisation|company|sponsor|employer)\s*(name)?$")


class SponsorRegister:
    """In-memory set of normalised company names from the UK sponsor list."""

    def __init__(self, names: set[str]) -> None:
        self._names = names

    def contains(self, company: str) -> bool:
        """Return True if the company appears in the sponsor register."""
        return norm_company(company) in self._names

    def __len__(self) -> int:
        return len(self._names)

    def __bool__(self) -> bool:
        return bool(self._names)

    @classmethod
    def load(cls, cache: Path = _CACHE_PATH) -> SponsorRegister:
        """Load from the local cache, downloading it first if missing."""
        if not cache.exists():
            cls._download(cache)
        return cls._parse(cache)

    @classmethod
    def _download(cls, path: Path) -> None:
        """Fetch the latest CSV from GOV.UK."""
        # 1. Find the current CSV URL from the landing page.
        csv_url = cls._find_csv_url()
        if not csv_url:
            raise RuntimeError("Could not find UK sponsor CSV URL on GOV.UK")

        # 2. Download it.
        resp = httpx.get(
            csv_url,
            headers={"User-Agent": _USER_AGENT},
            timeout=30,
            follow_redirects=True,
        )
        resp.raise_for_status()

        # 3. Cache it.
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(resp.content)

    @staticmethod
    def _find_csv_url() -> str | None:
        """Scrape the GOV.UK landing page for the CSV download link."""
        try:
            resp = httpx.get(
                _LANDING_URL,
                headers={"User-Agent": _USER_AGENT},
                timeout=15,
                follow_redirects=True,
            )
            resp.raise_for_status()
        except Exception:
            return None

        # Find CSV URLs in the page.
        urls = re.findall(
            r'https://assets\.publishing\.service\.gov\.uk/[^"\']+\.csv',
            resp.text,
        )
        for url in urls:
            if "Worker_and_Temporary_Worker" in url:
                return url
        return urls[0] if urls else None

    @classmethod
    def _parse(cls, path: Path) -> SponsorRegister:
        """Parse the CSV and build the normalised name set."""
        text = path.read_text(encoding="utf-8", errors="replace")
        # The CSV may have a BOM or preamble rows — skip until we find the header.
        reader = csv.reader(io.StringIO(text))
        org_col: int | None = None

        names: set[str] = set()

        for row in reader:
            if len(row) < 2:
                continue

            # Find the header row — it starts with "Organisation Name" or similar.
            if org_col is None:
                for i, val in enumerate(row):
                    if _ORG_COLUMNS.match(val.strip()):
                        org_col = i
                        break
                if org_col is not None:
                    [v.strip() for v in row]
                    continue
                continue

            # Data row.
            if org_col is not None and org_col < len(row):
                name = row[org_col].strip()
                if name and not name.startswith("Sponsor") and not name.startswith("Tier"):
                    names.add(norm_company(name))

        return cls(names)
