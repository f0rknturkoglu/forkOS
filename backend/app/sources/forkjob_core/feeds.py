"""Load and save user-defined RSS job feeds.

Feeds live in data/feeds.yaml and are managed through the web UI at /feeds.
They are read by the `customfeeds` Layer B scraper, so adding a feed in the
browser is enough to have the next sync collect it — no code change.

Mirrors linkedin_profiles.py: same atomic save, same tolerance for a missing or
malformed file. A broken feeds file must never stop a sync.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

DEFAULT_FEEDS_PATH = Path(__file__).parent / "data" / "feeds.yaml"

_FEEDS_HEADER = """\
# User-defined RSS job feeds.
#
# Managed through the web UI at /feeds — you do not need to edit this file by
# hand. Every enabled feed here is fetched by the `customfeeds` source on the
# next sync.
#
# Feed fields:
#   url       required — the feed URL (RSS or Atom)
#   name      optional — label shown in the list; defaults to the host
#   remote    optional — true if everything on this feed is remote work
#   country   optional — ISO-3166 alpha-2 to stamp on postings with no location
#   enabled   optional — false to keep a feed without fetching it
"""


#: How a source is read. `rss` covers RSS and Atom. `page` is a company's own
#: careers page: no feed, no API, just HTML.
KINDS = ("rss", "page")

#: Selector names a `page` source may define. `item` is the repeating block;
#: the rest are looked up inside it and are all optional.
SELECTOR_FIELDS = ("item", "title", "link", "location", "department")


@dataclass(slots=True)
class Feed:
    """One user-defined source: an RSS feed, or a company's own careers page.

    The `page` kind exists because most companies that do not use an ATS
    publish nothing machine-readable. Measured on six such careers pages
    (ZeniMax, Mitsubishi, Valve and others): zero schema.org JobPosting blocks
    between them, but 6 to 35 posting links each sitting in plain HTML. So the
    listing is there — it just has to be pointed at once per site.
    """

    url: str
    name: str = ""
    remote: bool = False
    country: str = ""
    enabled: bool = True
    kind: str = "rss"
    #: Only meaningful when kind == "page".
    selectors: dict[str, str] = field(default_factory=dict)

    @property
    def label(self) -> str:
        """What to call this feed in the UI."""
        if self.name:
            return self.name
        host = urlsplit(self.url).netloc
        return host[4:] if host.startswith("www.") else host

    @property
    def is_page(self) -> bool:
        return self.kind == "page"

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"url": self.url}
        if self.name:
            out["name"] = self.name
        if self.kind != "rss":
            out["kind"] = self.kind
        if self.selectors:
            out["selectors"] = dict(self.selectors)
        if self.remote:
            out["remote"] = True
        if self.country:
            out["country"] = self.country
        if not self.enabled:
            out["enabled"] = False
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Feed:
        kind = str(data.get("kind", "rss")).strip().lower()
        raw = data.get("selectors")
        selectors = {}
        if isinstance(raw, dict):
            selectors = {
                k: str(v).strip() for k, v in raw.items() if k in SELECTOR_FIELDS and str(v).strip()
            }
        return cls(
            url=str(data.get("url", "")).strip(),
            name=str(data.get("name", "")).strip(),
            remote=bool(data.get("remote", False)),
            country=str(data.get("country", "")).strip().upper(),
            enabled=bool(data.get("enabled", True)),
            kind=kind if kind in KINDS else "rss",
            selectors=selectors,
        )


@dataclass(slots=True)
class Feeds:
    """In-memory collection of user feeds with atomic file save."""

    feeds: list[Feed] = field(default_factory=list)
    path: Path = DEFAULT_FEEDS_PATH

    def __len__(self) -> int:
        return len(self.feeds)

    def __iter__(self):
        return iter(self.feeds)

    def __getitem__(self, index: int) -> Feed:
        return self.feeds[index]

    def enabled(self) -> list[Feed]:
        return [f for f in self.feeds if f.enabled and f.url]

    # -- io ------------------------------------------------------------------

    @classmethod
    def load(cls, path: Path | str = DEFAULT_FEEDS_PATH) -> Feeds:
        path = Path(path)
        if not path.exists():
            return cls([], path)

        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            return cls([], path)

        entries = raw.get("feeds") or []
        if not isinstance(entries, list):
            return cls([], path)

        feeds = [Feed.from_dict(e) for e in entries if isinstance(e, dict)]
        return cls([f for f in feeds if f.url], path)

    def save(self) -> None:
        payload = {"version": 1, "feeds": [f.to_dict() for f in self.feeds]}
        body = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=100)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(_FEEDS_HEADER)
                fh.write("\n")
                fh.write(body)
            os.replace(tmp, self.path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    # -- mutations -----------------------------------------------------------

    def add(self, feed: Feed) -> Feed:
        self.feeds.append(feed)
        self.save()
        return feed

    def update(self, index: int, feed: Feed) -> Feed | None:
        if index < 0 or index >= len(self.feeds):
            return None
        self.feeds[index] = feed
        self.save()
        return feed

    def delete(self, index: int) -> bool:
        if index < 0 or index >= len(self.feeds):
            return False
        self.feeds.pop(index)
        self.save()
        return True

    def toggle(self, index: int) -> Feed | None:
        if index < 0 or index >= len(self.feeds):
            return None
        self.feeds[index].enabled = not self.feeds[index].enabled
        self.save()
        return self.feeds[index]
