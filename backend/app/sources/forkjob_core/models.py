"""Core data structures shared by both collection layers.

Three levels of identity live here (see docs/SCHEMA.md):

    JobCluster  one real-world posting. Permanent. Owns user state.
    Job         one record from one source. May break when a URL changes.
    canonical   the Job that currently represents its cluster. Recomputed.

Nothing downstream of normalisation ever sees a raw payload.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


class Layer(StrEnum):
    """Which collection layer produced a record."""

    A = "A"  # ATS adapters — public board endpoints
    B = "B"  # Spanish job portal scrapers


class DateSource(StrEnum):
    """Where `posted_at` came from. Drives the tiered freshness decay.

    Never guess this. An adapter that cannot tell a publish date from an edit
    date must say `UPDATED`, and one with no date at all must say `DISCOVERED`.
    """

    EMPLOYER = "employer"  # source gave a real publish date -> full decay
    UPDATED = "updated"  # only an edit/refresh timestamp -> half decay
    DISCOVERED = "discovered"  # no date at all, first_seen stands in -> no decay


def date_source_for(
    posted_at: datetime | None, updated_at: datetime | None = None
) -> tuple[datetime | None, DateSource]:
    """Pick the most honest (timestamp, provenance) pair a source can claim.

    The tiered freshness ladder: a real publish date decays at full rate
    (`employer`), an edit/refresh timestamp at half rate (`updated`), and a
    posting with no date at all is `discovered`. The caller decides which
    timestamps are publish dates and which are edits — this only orders them.
    """
    if posted_at is not None:
        return posted_at, DateSource.EMPLOYER
    if updated_at is not None:
        return updated_at, DateSource.UPDATED
    return None, DateSource.DISCOVERED


#: Ranking suffix shown in the `list` age column, so a date is never read as
#: more trustworthy than it is.
DATE_SOURCE_MARK = {
    DateSource.EMPLOYER: "",
    DateSource.UPDATED: "*",
    DateSource.DISCOVERED: "?",
}


class WorkMode(StrEnum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    UNKNOWN = "unknown"


class Region(StrEnum):
    TR = "TR"
    EU = "EU"
    #: Layer A boards are global — a Greenhouse board returns US postings too.
    #: They are stored, not dropped, and simply never fill a quota bucket.
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class Status(StrEnum):
    NEW = "new"
    SEEN = "seen"
    SHORTLIST = "shortlist"
    APPLIED = "applied"
    REJECTED = "rejected"
    CLOSED = "closed"
    IGNORED = "ignored"


class RunStatus(StrEnum):
    OK = "ok"
    ERROR = "error"
    PARTIAL = "partial"


#: Statuses the user set by hand. Never overwritten by a sync, including the
#: automatic close sweep.
USER_OWNED_STATUSES: frozenset[Status] = frozenset(
    {Status.SHORTLIST, Status.APPLIED, Status.REJECTED, Status.IGNORED}
)

#: Cluster statuses the close sweep is allowed to move.
SWEEPABLE_STATUSES: frozenset[Status] = frozenset({Status.NEW, Status.SEEN})


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_cluster_id() -> str:
    return str(uuid.uuid4())


# --------------------------------------------------------------------------
# URL canonicalisation
# --------------------------------------------------------------------------

#: Tracking params dropped before hashing. Never drop a param that identifies
#: the posting itself (e.g. Greenhouse `gh_jid`).
_DROP_PARAMS = {
    "source",
    "ref",
    "referrer",
    "gh_src",
    "lever-source",
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "trackingid",
    "trk",
}
_DROP_PARAM_PREFIXES = ("utm_",)


def canonical_url(url: str) -> str:
    """Normalise a posting URL so the same job always hashes identically.

    Lowercases scheme/host, drops `www.`, default ports, fragments, tracking
    params and the trailing slash, and sorts the remaining query params.
    """
    parts = urlsplit(url.strip())
    scheme = (parts.scheme or "https").lower()

    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    port = parts.port
    if port and not ((scheme == "https" and port == 443) or (scheme == "http" and port == 80)):
        host = f"{host}:{port}"

    path = parts.path.rstrip("/")

    # Deduplicated: Greenhouse emits `?gh_jid=123&gh_jid=123` on some boards,
    # and a repeated pair must not hash to a different job than a single one.
    kept = sorted(
        {
            (k, v)
            for k, v in parse_qsl(parts.query, keep_blank_values=False)
            if k.lower() not in _DROP_PARAMS and not k.lower().startswith(_DROP_PARAM_PREFIXES)
        }
    )

    return urlunsplit((scheme, host, path, urlencode(kept), ""))


def make_job_id(url: str) -> str:
    """Fallback identity: first 16 hex chars of SHA1 over the canonical URL.

    Only a fallback — `(source, external_id)` wins when the source provides
    one, because URLs move and external ids do not.
    """
    return hashlib.sha1(canonical_url(url).encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------------------
# Text normalisation (cluster matching)
# --------------------------------------------------------------------------

#: Dropped from company names before comparison, so "Trendyol Grup A.Ş." from
#: a portal and "Trendyol" from its ATS resolve to the same core.
_LEGAL_SUFFIXES = {
    "inc",
    "llc",
    "ltd",
    "limited",
    "gmbh",
    "bv",
    "nv",
    "ab",
    "as",
    "oy",
    "sa",
    "sl",
    "slu",
    "sau",
    "sas",
    "spa",
    "srl",
    "plc",
    "corp",
    "co",
    "sti",
    "ltdsti",
    "anonim",
    "sirketi",
    "sirket",
    "grup",
    "group",
    "holding",
    "technologies",
    "technology",
    "tech",
}

_WS_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_TR_FOLD = str.maketrans("ıİşŞğĞçÇöÖüÜ", "iisSgGcCoOuU")


def norm_text(value: str | None) -> str:
    """Lowercase, strip accents, collapse everything non-alphanumeric."""
    if not value:
        return ""
    folded = value.translate(_TR_FOLD)
    folded = unicodedata.normalize("NFKD", folded)
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    folded = _NON_ALNUM_RE.sub(" ", folded.lower())
    return _WS_RE.sub(" ", folded).strip()


def norm_company(name: str | None) -> str:
    """Company name reduced to a comparable core.

    Single-character fragments go too: "A.Ş." normalises to "a s" and neither
    half carries meaning. Falls back to the plain normalisation if that would
    empty the name out (e.g. "H&M").
    """
    words = [w for w in norm_text(name).split() if len(w) > 1 and w not in _LEGAL_SUFFIXES]
    return " ".join(words) or norm_text(name)


def cluster_key(company: str | None, title: str | None, city: str | None) -> str:
    """Exact-match half of cluster resolution: company + title + city.

    Deliberately coarse. `identity.py` layers fuzzy title matching on top; this
    key only has to be stable and cheap to index.
    """
    return "|".join((norm_company(company), norm_text(title), norm_text(city)))


# --------------------------------------------------------------------------
# Records
# --------------------------------------------------------------------------


@dataclass(slots=True)
class Company:
    """A Layer A registry entry: one company on one ATS platform."""

    name: str
    ats: str
    token: str = ""
    verified: bool = False
    enabled: bool = True
    country: str | None = None
    region: Region = Region.UNKNOWN
    #: ATS-specific connection details. Workday needs host/tenant/site here.
    extra: dict[str, Any] = field(default_factory=dict)
    last_verified_at: datetime | None = None
    notes: str | None = None

    @property
    def key(self) -> str:
        """Registry-unique identity. A company may exist on two ATS platforms."""
        return f"{self.ats}:{self.token or self.extra.get('tenant', norm_text(self.name))}"

    @property
    def source(self) -> str:
        """Source name written onto every Job this entry produces."""
        return f"{self.ats}:{self.token or self.extra.get('tenant', norm_text(self.name))}"


@dataclass(slots=True)
class JobCluster:
    """One real-world posting. Permanent, and the only home for user state.

    Status lives here rather than on `Job` so that a canonical switch — the
    Tecnoempleo record you marked `applied` being superseded by the company's
    own Greenhouse record — cannot lose the mark. No transfer logic needed.
    """

    cluster_id: str = field(default_factory=new_cluster_id)
    status: Status = Status.NEW
    notes: str = ""
    applied_at: datetime | None = None
    created_at: datetime = field(default_factory=utcnow)
    canonical_job_id: str | None = None
    status_changed_at: datetime | None = None

    @property
    def is_user_owned(self) -> bool:
        return self.status in USER_OWNED_STATUSES


@dataclass(slots=True)
class Job:
    """One posting record from one source."""

    job_id: str
    cluster_id: str
    source: str
    layer: Layer
    company: str
    title: str
    url: str

    external_id: str | None = None

    # Where
    location: str | None = None
    city: str | None = None
    region: Region = Region.UNKNOWN
    country: str | None = None
    #: True/False/None(unknown). Hybrid counts as not-remote: the office city
    #: still matters for the quota buckets.
    remote: bool | None = None
    #: Finer detail kept alongside `remote`, since 1|0|NULL cannot express it.
    work_mode: WorkMode = WorkMode.UNKNOWN

    # What
    department: str | None = None
    description: str | None = None
    salary: str | None = None
    language: str | None = None

    # When
    posted_at: datetime | None = None
    date_source: DateSource = DateSource.DISCOVERED

    # Scoring — recomputed every sync, never treated as stored truth
    score: float | None = None
    #: Component breakdown, not a single total. Calibration in step 4 depends
    #: on being able to see which component produced the number.
    reasons: dict[str, Any] = field(default_factory=dict)

    # Lifecycle
    cluster_key: str = ""
    first_seen: datetime = field(default_factory=utcnow)
    last_seen: datetime = field(default_factory=utcnow)
    #: Consecutive *successful* syncs of this source that did not return it.
    missed_syncs: int = 0
    is_open: bool = True

    def __post_init__(self) -> None:
        if not self.cluster_key:
            self.cluster_key = cluster_key(self.company, self.title, self.city or self.location)
        if self.work_mode is not WorkMode.UNKNOWN and self.remote is None:
            self.remote = self.work_mode is WorkMode.REMOTE

    @classmethod
    def build(
        cls,
        *,
        url: str,
        source: str,
        layer: Layer,
        company: str,
        title: str,
        cluster_id: str = "",
        **kw: Any,
    ) -> Job:
        """Construct a Job with a URL-derived job_id and no cluster yet.

        `identity.resolve()` assigns the real cluster before it is stored.
        """
        return cls(
            job_id=make_job_id(url),
            cluster_id=cluster_id,
            source=source,
            layer=layer,
            company=company,
            title=title,
            url=url,
            **kw,
        )

    @property
    def company_norm(self) -> str:
        return norm_company(self.company)

    @property
    def age_days(self) -> int | None:
        """Days since `posted_at`, or since first_seen when there is no date."""
        reference = self.posted_at or (
            self.first_seen if self.date_source is DateSource.DISCOVERED else None
        )
        if reference is None:
            return None
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=UTC)
        return (utcnow() - reference).days

    @property
    def age_label(self) -> str:
        """Age with a mark showing how much the date can be trusted."""
        days = self.age_days
        if days is None:
            return "-"
        return f"{days}g{DATE_SOURCE_MARK[self.date_source]}"

    # -- persistence helpers ------------------------------------------------

    def to_row(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "cluster_id": self.cluster_id,
            "source": self.source,
            "external_id": self.external_id,
            "layer": self.layer.value,
            "company": self.company,
            "company_norm": self.company_norm,
            "title": self.title,
            "url": self.url,
            "location": self.location,
            "city": self.city,
            "department": self.department,
            "description": self.description,
            "salary": self.salary,
            "language": self.language,
            "region": self.region.value,
            "country": self.country,
            "remote": None if self.remote is None else int(self.remote),
            "work_mode": self.work_mode.value,
            "posted_at": dt_to_str(self.posted_at),
            "date_source": self.date_source.value,
            "score": self.score,
            "reasons": json_dumps(self.reasons),
            "cluster_key": self.cluster_key,
            "first_seen": dt_to_str(self.first_seen),
            "last_seen": dt_to_str(self.last_seen),
            "missed_syncs": self.missed_syncs,
            "is_open": int(self.is_open),
        }

    @classmethod
    def from_row(cls, row: Any) -> Job:
        d = dict(row)
        return cls(
            job_id=d["job_id"],
            cluster_id=d["cluster_id"],
            source=d["source"],
            layer=Layer(d["layer"]),
            company=d["company"],
            title=d["title"],
            url=d["url"],
            external_id=d["external_id"],
            location=d["location"],
            city=d["city"],
            region=Region(d["region"] or Region.UNKNOWN.value),
            country=d["country"],
            remote=None if d["remote"] is None else bool(d["remote"]),
            work_mode=WorkMode(d["work_mode"] or WorkMode.UNKNOWN.value),
            department=d["department"],
            description=d["description"],
            salary=d["salary"],
            language=d["language"],
            posted_at=str_to_dt(d["posted_at"]),
            date_source=DateSource(d["date_source"]),
            score=d["score"],
            reasons=json_loads(d["reasons"]),
            cluster_key=d["cluster_key"] or "",
            first_seen=str_to_dt(d["first_seen"]) or utcnow(),
            last_seen=str_to_dt(d["last_seen"]) or utcnow(),
            missed_syncs=d["missed_syncs"] or 0,
            is_open=bool(d["is_open"]),
        )


# --------------------------------------------------------------------------
# Small conversion helpers
# --------------------------------------------------------------------------


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def json_loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def dt_to_str(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat(timespec="seconds")


def str_to_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
