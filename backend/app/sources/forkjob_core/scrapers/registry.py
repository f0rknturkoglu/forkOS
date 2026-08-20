"""Layer B registry: Spanish job portal sources.

Separate from the Layer A registry by design — a dead portal scraper must never
block an ATS sync, and the two registries have different schemas (URL patterns
and CSS selectors instead of ATS tokens).
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_REGISTRY_B_PATH = Path(__file__).parent.parent / "data" / "portals.yaml"

_HEADER = """\
# Layer B registry: Spanish tech job portals and boards we scrape.
#
# Managed by `forkjob probe`. Hand edits are fine, but a hand-added entry
# stays active: false until `probe` confirms the selectors still work.
#
# Field reference:
#   key       required  short id, e.g. "tecnoempleo", "infojobs"
#   label     required  display name
#   url       required  base URL or search endpoint
#   enabled   optional  default true
#   config    optional  scraper-specific overrides (selectors, API keys, etc.)
"""


#: Where a source's supply comes from. Deliberately about the *nature* of the
#: publisher, not the technology used to read it — an RSS feed and a JSON API
#: from the same kind of board belong in the same group, because that is what
#: decides how much the postings can be trusted.
CATEGORIES = {
    "government": "Official / state-run employment services",
    "remote": "Global remote-first boards",
    "regional": "Country or region specific tech boards",
    "relocation": "Visa sponsorship and relocation focused",
    "community": "Community threads and newsletters",
    "startup": "Startup, VC portfolio and accelerator boards",
    "aggregator": "Boards that republish other boards",
    "social": "Professional networks",
    "custom": "Feeds added by hand through the web UI",
    "other": "Unclassified",
}


@dataclass(slots=True)
class LayerBSource:
    """One Layer B scraping target."""

    key: str
    label: str
    url: str = ""
    enabled: bool = True
    #: Why this source is in the state it is in — verified against what, or
    #: blocked by what. It was being written in portals.yaml and then dropped
    #: on load, so the reasoning never reached the code that acts on it.
    status: str = ""
    #: What kind of supply this is, so the list can be read by where the work
    #: comes from rather than by scraper name. See CATEGORIES.
    category: str = "other"
    #: Scraper-specific configuration: CSS selectors, API keys, pagination params.
    config: dict[str, Any] = field(default_factory=dict)

    @property
    def source(self) -> str:
        return self.key


class LayerBRegistry:
    """In-memory view of portals.yaml, with atomic save."""

    def __init__(self, sources: list[LayerBSource], path: Path = DEFAULT_REGISTRY_B_PATH) -> None:
        self.sources = sources
        self.path = Path(path)

    # -- io -----------------------------------------------------------------

    @classmethod
    def load(cls, path: Path | str = DEFAULT_REGISTRY_B_PATH) -> LayerBRegistry:
        path = Path(path)
        if not path.exists():
            return cls([], path)

        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        entries = raw.get("sources") or []
        if not isinstance(entries, list):
            return cls([], path)

        sources = [_source_from_dict(e) for e in entries if isinstance(e, dict)]
        return cls(sources, path)

    def save(self) -> None:
        payload = {
            "version": 1,
            "sources": [_source_to_dict(s) for s in self.sources],
        }
        body = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=100)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(_HEADER)
                fh.write("\n")
                fh.write(body)
            os.replace(tmp, self.path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    # -- queries ------------------------------------------------------------

    def __len__(self) -> int:
        return len(self.sources)

    def __iter__(self):
        return iter(self.sources)

    def enabled(self) -> list[LayerBSource]:
        return [s for s in self.sources if s.enabled]

    def by_key(self, key: str) -> LayerBSource | None:
        return next((s for s in self.sources if s.key == key), None)

    def sorted(self) -> list[LayerBSource]:
        return sorted(self.sources, key=lambda s: s.label.lower())

    # -- mutations ----------------------------------------------------------

    def add(self, source: LayerBSource, *, replace: bool = False) -> LayerBSource:
        existing = self.by_key(source.key)
        if existing is not None:
            if not replace:
                return existing
            self.sources.remove(existing)
        self.sources.append(source)
        return source


# ---------------------------------------------------------------------------
# (de)serialisation
# ---------------------------------------------------------------------------


def _source_from_dict(entry: dict[str, Any]) -> LayerBSource:
    return LayerBSource(
        key=str(entry.get("key") or ""),
        label=str(entry.get("label") or entry.get("key", "")),
        url=str(entry.get("url") or ""),
        enabled=bool(entry.get("enabled", True)),
        config=dict(entry.get("config") or {}),
        status=str(entry.get("status") or "").strip(),
        category=str(entry.get("category") or "other").strip().lower(),
    )


def _source_to_dict(source: LayerBSource) -> dict[str, Any]:
    out: dict[str, Any] = {
        "key": source.key,
        "label": source.label,
        "url": source.url,
        "enabled": source.enabled,
    }
    if source.category and source.category != "other":
        out["category"] = source.category
    if source.status:
        out["status"] = source.status
    if source.config:
        out["config"] = source.config
    return out


# ---------------------------------------------------------------------------
# Convenience loader
# ---------------------------------------------------------------------------


def load_registry_b(path: Path | str = DEFAULT_REGISTRY_B_PATH) -> LayerBRegistry:
    """Load the Layer B registry, creating an empty one if it does not exist."""
    reg = LayerBRegistry.load(path)
    if not reg.path.exists():
        reg.save()
    return reg
