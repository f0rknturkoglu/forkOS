"""Load, merge, and save user-defined LinkedIn search profiles.

Default profiles live in data/portals.yaml under linkedin.config.searches.
User profiles live in a local runtime file and are managed through the web UI.
Both sets are merged at sync time — defaults come first, then user profiles in
the order they were saved.

Search profiles are personal data (what the user is looking for, and where), so
they are written to `linkedin-profiles.yaml.user`, which `.gitignore` excludes.
`linkedin-profiles.yaml` is the tracked template: it ships empty and is only
read once to adopt a file left behind by an older version.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .userdata import user_path

#: Tracked template — shipped with the app, never written at runtime.
TEMPLATE_PROFILES_PATH = Path(__file__).parent / "data" / "linkedin-profiles.yaml"
#: Runtime file — what the web UI reads and writes. Excluded by .gitignore.
USER_PROFILES_PATH = user_path(TEMPLATE_PROFILES_PATH)

_PROFILES_HEADER = """\
# User-defined LinkedIn search profiles — LOCAL, GIT-IGNORED FILE.
#
# Managed through the web UI — you do not need to edit this file by hand.
# Default profiles from data/portals.yaml are merged with these at sync time;
# both sets run together.
#
# This file holds personal search data and is never committed. The tracked
# data/linkedin-profiles.yaml is only an empty template.
#
# Profile fields:
#   term              required — search keyword (e.g. "backend engineer")
#   location          optional — city or country (e.g. "Germany")
#   results_wanted    optional — how many results (default 50)
#   hours_old         optional — only postings this recent (e.g. 72)
#   is_remote         optional — true for remote-only
#   fetch_description optional — fetch full description (slower, more requests)
"""


@dataclass(slots=True)
class LinkedInProfile:
    """One user-defined search profile."""

    term: str
    location: str = ""
    results_wanted: int = 50
    hours_old: int | None = None
    is_remote: bool | None = None
    fetch_description: bool = False

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"term": self.term}
        if self.location:
            out["location"] = self.location
        if self.results_wanted != 50:
            out["results_wanted"] = self.results_wanted
        if self.hours_old is not None:
            out["hours_old"] = self.hours_old
        if self.is_remote is not None:
            out["is_remote"] = self.is_remote
        if self.fetch_description:
            out["fetch_description"] = True
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LinkedInProfile:
        return cls(
            term=str(data.get("term", "")),
            location=str(data.get("location", "")),
            results_wanted=int(data.get("results_wanted", 50)),
            hours_old=data.get("hours_old") if data.get("hours_old") is not None else None,
            is_remote=data.get("is_remote") if "is_remote" in data else None,
            fetch_description=bool(data.get("fetch_description", False)),
        )


def _read_profiles(path: Path) -> list[LinkedInProfile]:
    """Parse a profiles file; missing or malformed reads as "no profiles".

    A broken file must never stop a sync, and the caller cannot tell the
    difference between "not there yet" and "unreadable" — both mean the
    defaults from portals.yaml still apply.
    """
    if not path.exists():
        return []
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return []
    entries = raw.get("profiles") or []
    if not isinstance(entries, list):
        return []
    return [LinkedInProfile.from_dict(entry) for entry in entries if isinstance(entry, dict)]


@dataclass(slots=True)
class LinkedInProfiles:
    """In-memory collection of user profiles with atomic file save."""

    profiles: list[LinkedInProfile] = field(default_factory=list)
    #: Resolved at instantiation so the module constant always wins.
    path: Path = field(default_factory=lambda: USER_PROFILES_PATH)

    def __len__(self) -> int:
        return len(self.profiles)

    def __iter__(self):
        return iter(self.profiles)

    def __getitem__(self, index: int) -> LinkedInProfile:
        return self.profiles[index]

    # -- io ------------------------------------------------------------------

    @classmethod
    def load(cls, path: Path | str | None = None) -> LinkedInProfiles:
        """Profiles from the runtime file, adopting a legacy tracked file once.

        `path` is an explicit override for tests and tooling; without it the
        runtime file wins. A user upgrading from a version that still wrote
        profiles into the tracked template keeps them: the template is read
        once, moved into the runtime file, and never written again.
        """
        if path is not None:
            target = Path(path)
            return cls(_read_profiles(target), target)

        collection = cls(_read_profiles(USER_PROFILES_PATH), USER_PROFILES_PATH)
        if collection.profiles:
            return collection
        legacy = _read_profiles(TEMPLATE_PROFILES_PATH)
        if not legacy:
            return collection
        collection.profiles = legacy
        collection.save()
        return collection

    def save(self) -> None:
        payload = {
            "version": 1,
            "profiles": [p.to_dict() for p in self.profiles],
        }
        body = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=100)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(_PROFILES_HEADER)
                fh.write("\n")
                fh.write(body)
            os.replace(tmp, self.path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    # -- mutations -----------------------------------------------------------

    def add(self, profile: LinkedInProfile) -> LinkedInProfile:
        self.profiles.append(profile)
        self.save()
        return profile

    def update(self, index: int, profile: LinkedInProfile) -> LinkedInProfile | None:
        if index < 0 or index >= len(self.profiles):
            return None
        self.profiles[index] = profile
        self.save()
        return profile

    def delete(self, index: int) -> bool:
        if index < 0 or index >= len(self.profiles):
            return False
        self.profiles.pop(index)
        self.save()
        return True

    # -- merge ---------------------------------------------------------------

    def merge_with_defaults(self, defaults: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return default profiles followed by user profiles as dicts.

        Default profiles from portals.yaml come first so their names are
        stable; user profiles follow in the order they were saved.
        """
        result: list[dict[str, Any]] = [dict(d) for d in defaults]
        for profile in self.profiles:
            result.append(profile.to_dict())
        return result
