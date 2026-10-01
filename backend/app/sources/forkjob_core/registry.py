"""Layer A registry: the list of companies whose ATS boards we poll.

Entries are only ever marked `verified` by code that actually got a 200 with a
non-empty posting list back (`discover` / `verify`). Nothing in here guesses a
board token.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import yaml

from .models import Company, Region, dt_to_str, norm_text, str_to_dt

DEFAULT_REGISTRY_PATH = Path(__file__).parent / "data" / "registry.yaml"

#: Layer A platforms. `discover` probes these in order.
KNOWN_ATS = (
    "greenhouse",
    "lever",
    "ashby",
    "workable",
    "smartrecruiters",
    "recruitee",
    "personio",
    "factorial",
    "workday",
    "teamtailor",
)

#: Workday cannot be discovered from a name alone — it needs host + tenant +
#: site, which only appear in the careers page URL. Entered by hand.
UNDISCOVERABLE_ATS = frozenset({"workday"})

_HEADER = """\
# Layer A registry: companies whose public ATS board endpoints we poll.
#
# Managed by `forkjob discover` / `forkjob verify`. Hand edits are fine, but a
# hand-added entry stays verified: false until `verify` confirms it.
"""


class RegistryError(ValueError):
    pass


class Registry:
    """In-memory view of registry.yaml, with atomic save."""

    def __init__(self, companies: list[Company], path: Path = DEFAULT_REGISTRY_PATH) -> None:
        self.companies = companies
        self.path = Path(path)

    # -- io -----------------------------------------------------------------

    @classmethod
    def load(cls, path: Path | str = DEFAULT_REGISTRY_PATH) -> Registry:
        path = Path(path)
        if not path.exists():
            return cls([], path)

        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        entries = raw.get("companies") or []
        if not isinstance(entries, list):
            raise RegistryError(f"{path}: 'companies' must be a list")

        return cls([_company_from_dict(e, path) for e in entries], path)

    def save(self) -> None:
        """Write atomically so an interrupted run cannot truncate the registry.

        PyYAML does not round-trip comments, so the header is re-emitted here.
        Per-entry `notes` survive because they are real fields.
        """
        payload = {
            "version": 1,
            "companies": [_company_to_dict(c) for c in self.sorted()],
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
        return len(self.companies)

    def __iter__(self) -> Iterator[Company]:
        return iter(self.companies)

    def sorted(self) -> list[Company]:
        return sorted(self.companies, key=lambda c: (norm_text(c.name), c.ats))

    def enabled(self) -> list[Company]:
        return [c for c in self.companies if c.enabled]

    def by_key(self, key: str) -> Company | None:
        return next((c for c in self.companies if c.key == key), None)

    def find(self, name: str, ats: str | None = None) -> list[Company]:
        target = norm_text(name)
        return [
            c
            for c in self.companies
            if target in norm_text(c.name) and (ats is None or c.ats == ats)
        ]

    def unverified(self) -> list[Company]:
        return [c for c in self.companies if not c.verified]

    # -- mutations ----------------------------------------------------------

    def add(self, company: Company, *, replace: bool = False) -> Company:
        """Add an entry. Same (ats, token) twice is a no-op unless replace."""
        if company.ats not in KNOWN_ATS:
            raise RegistryError(
                f"unknown ATS {company.ats!r}; expected one of {', '.join(KNOWN_ATS)}"
            )
        if not company.token and company.ats != "workday":
            raise RegistryError(f"{company.ats} entries need a board token")

        existing = self.by_key(company.key)
        if existing is not None:
            if not replace:
                return existing
            self.companies.remove(existing)
        self.companies.append(company)
        return company

    def mark_verified(self, key: str, verified: bool, when: Any = None) -> None:
        company = self.by_key(key)
        if company is None:
            raise RegistryError(f"no registry entry with key {key!r}")
        company.verified = verified
        company.last_verified_at = when


# --------------------------------------------------------------------------
# (de)serialisation
# --------------------------------------------------------------------------


def _company_from_dict(entry: Any, path: Path) -> Company:
    if not isinstance(entry, dict):
        raise RegistryError(f"{path}: every registry entry must be a mapping, got {entry!r}")
    if not entry.get("name"):
        raise RegistryError(f"{path}: registry entry without a name: {entry!r}")
    ats = entry.get("ats")
    if ats not in KNOWN_ATS:
        raise RegistryError(f"{path}: {entry['name']}: unknown ats {ats!r}")

    region_raw = str(entry.get("region") or Region.UNKNOWN.value).upper()
    try:
        region = Region(region_raw)
    except ValueError:
        raise RegistryError(
            f"{path}: {entry['name']}: region must be one of "
            f"{', '.join(r.value for r in Region)}, got {region_raw!r}"
        ) from None

    return Company(
        name=str(entry["name"]),
        ats=ats,
        token=str(entry.get("token") or ""),
        verified=bool(entry.get("verified", False)),
        enabled=bool(entry.get("enabled", True)),
        country=entry.get("country"),
        region=region,
        extra=dict(entry.get("extra") or {}),
        last_verified_at=str_to_dt(entry.get("last_verified_at")),
        notes=entry.get("notes"),
    )


def _company_to_dict(company: Company) -> dict[str, Any]:
    out: dict[str, Any] = {
        "name": company.name,
        "ats": company.ats,
        "token": company.token,
        "verified": company.verified,
    }
    if not company.enabled:
        out["enabled"] = False
    if company.country:
        out["country"] = company.country
    if company.region is not Region.UNKNOWN:
        out["region"] = company.region.value
    if company.extra:
        out["extra"] = company.extra
    if company.last_verified_at:
        out["last_verified_at"] = dt_to_str(company.last_verified_at)
    if company.notes:
        out["notes"] = company.notes
    return out
