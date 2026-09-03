"""Raw payload -> Job field values.

Everything here is deliberately conservative. An unrecognised location stays
UNKNOWN and an undated posting stays `discovered`: a wrong guess quietly moves
a job into the wrong quota bucket or fakes a freshness the data cannot support.
"""

import html
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

from selectolax.parser import HTMLParser

from .geo import city_from_name, country_from_name, region_for
from .models import Region, WorkMode, norm_text

#: Descriptions are kept for scoring signals (visa wording, language demands),
#: not for reading in full. Cap keeps the database sane at a few thousand jobs.
MAX_DESCRIPTION_CHARS = 20_000

_WS_RE = re.compile(r"[ \t\r\f\v]+")
_BLANKS_RE = re.compile(r"\n{3,}")

#: Location fragments that mean "not tied to an office".
_REMOTE_WORDS = {
    "remote",
    "remoto",
    "remota",
    "en remoto",
    "teletrabajo",
    "uzaktan",
    "anywhere",
    "distributed",
    "work from home",
    "wfh",
    "home office",
    "fully remote",
    "remote first",
    "remote friendly",
}

_HYBRID_WORDS = {"hybrid", "hibrido", "híbrido", "hibrit", "semipresencial"}

#: Only strong, unambiguous phrasings are read out of description prose.
#: "we are not a remote company" is exactly the trap loose matching falls into.
_DESC_REMOTE_RE = re.compile(
    r"\b(fully|100%|totally|completely)\s+remote\b"
    r"|\bremote[- ]first\b"
    r"|\bwork from anywhere\b"
    r"|\b(100%|totalmente)\s+(en\s+)?remoto\b"
    r"|\btrabajo\s+(en\s+)?remoto\b",
    re.IGNORECASE,
)
_DESC_HYBRID_RE = re.compile(
    r"\bhybrid\s+(work|working|model|role|position|setup|schedule)\b"
    r"|\b(modelo|trabajo|formato)\s+h[ií]brido\b"
    r"|\bsemipresencial\b"
    r"|\b\d\s*days?\s+(a|per)\s+week\s+in\s+the\s+office\b",
    re.IGNORECASE,
)


@dataclass(slots=True)
class LocationInfo:
    raw: str | None = None
    city: str | None = None
    country: str | None = None
    region: Region = Region.UNKNOWN
    work_mode: WorkMode = WorkMode.UNKNOWN
    #: Every country the string mentioned, in the order they appeared.
    countries: tuple[str, ...] = ()


# --------------------------------------------------------------------------
# HTML
# --------------------------------------------------------------------------


def html_to_text(raw: str | None, *, limit: int = MAX_DESCRIPTION_CHARS) -> str | None:
    """Flatten posting HTML to readable text.

    Greenhouse double-escapes `content` (`&lt;p&gt;`), so unescape first, then
    parse. Unescaping twice is safe: plain text has nothing left to unescape.
    """
    if not raw:
        return None

    text = html.unescape(raw)
    if "<" in text:
        tree = HTMLParser(text)
        for tag in tree.css("script, style"):
            tag.decompose()
        text = tree.text(separator="\n")

    text = html.unescape(text).replace("\xa0", " ")
    text = _WS_RE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = _BLANKS_RE.sub("\n\n", text).strip()

    if len(text) > limit:
        text = text[:limit].rstrip() + "…"
    return text or None


# --------------------------------------------------------------------------
# Dates
# --------------------------------------------------------------------------


def parse_datetime(value: str | None) -> datetime | None:
    """Parse the ISO 8601 shapes ATS APIs actually emit."""
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        else:
            return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


# --------------------------------------------------------------------------
# Location
# --------------------------------------------------------------------------

#: Boards list alternatives with these separators: "Remote, Canada; Remote, US".
_LOCATION_SPLIT_RE = re.compile(r"\s*[;|/]\s*|\s+or\s+|\s+&\s+", re.IGNORECASE)
_FRAGMENT_SPLIT_RE = re.compile(r"\s*[,–—-]\s*")

#: Preference when a posting lists several places: the buckets I care about win.
_REGION_RANK = {Region.TR: 0, Region.EU: 1, Region.OTHER: 2, Region.UNKNOWN: 3}


def parse_location(raw: str | None, *, description: str | None = None) -> LocationInfo:
    """Resolve a board's free-text location into city / country / work mode."""
    info = LocationInfo(raw=raw)
    if not raw or not raw.strip():
        info.work_mode = _work_mode_from_description(description, remote_hint=False)
        info.region = Region.UNKNOWN
        return info

    remote_hint = False
    hybrid_hint = _contains_any(raw, _HYBRID_WORDS)
    candidates: list[tuple[int, str | None, str | None]] = []
    seen_countries: list[str] = []

    for chunk in _LOCATION_SPLIT_RE.split(raw):
        chunk = chunk.strip()
        if not chunk:
            continue

        city: str | None = None
        country: str | None = None

        for fragment in _FRAGMENT_SPLIT_RE.split(chunk):
            fragment = fragment.strip()
            if not fragment:
                continue
            if _is_remote_word(fragment):
                remote_hint = True
                continue
            if country is None:
                resolved = country_from_name(fragment)
                if resolved:
                    country = resolved
                    if city is None:
                        city = city_from_name(fragment)
                    continue
            if city is None:
                city = city_from_name(fragment)

        if country and country not in seen_countries:
            seen_countries.append(country)
        if city or country:
            candidates.append((_REGION_RANK[region_for(country)], city, country))

    if candidates:
        candidates.sort(key=lambda c: c[0])
        _, info.city, info.country = candidates[0]
    info.countries = tuple(seen_countries)
    info.region = region_for(info.country)

    if remote_hint and not hybrid_hint:
        info.work_mode = WorkMode.REMOTE
    elif hybrid_hint:
        info.work_mode = WorkMode.HYBRID
    else:
        info.work_mode = _work_mode_from_description(
            description, remote_hint=False, has_place=bool(info.city or info.country)
        )
    return info


def _work_mode_from_description(
    description: str | None, *, remote_hint: bool, has_place: bool = False
) -> WorkMode:
    """Fall back to description prose, then to 'there is an office' reasoning."""
    if remote_hint:
        return WorkMode.REMOTE
    if description:
        if _DESC_HYBRID_RE.search(description):
            return WorkMode.HYBRID
        if _DESC_REMOTE_RE.search(description):
            return WorkMode.REMOTE
    # A named place with no remote signal anywhere is treated as onsite: boards
    # that offer remote almost always say so in the location field.
    return WorkMode.ONSITE if has_place else WorkMode.UNKNOWN


def _is_remote_word(fragment: str) -> bool:
    return norm_text(fragment) in {norm_text(w) for w in _REMOTE_WORDS}


def _contains_any(text: str, words: set[str]) -> bool:
    normalised = norm_text(text)
    return any(norm_text(word) in normalised for word in words)


def detect_language(text: str | None, *, declared: str | None = None) -> str | None:
    """Trust the board's own language field; only guess when it is missing.

    The guess is a crude Spanish/English stopword ratio — enough to flag a
    posting written in Spanish, which the scorer treats as a weak signal only.
    """
    if declared:
        return declared.strip().lower()[:5] or None
    if not text:
        return None

    tokens = norm_text(text[:4000]).split()
    if len(tokens) < 20:
        return None
    spanish = sum(1 for t in tokens if t in _ES_STOPWORDS)
    english = sum(1 for t in tokens if t in _EN_STOPWORDS)
    if spanish > english and spanish >= 5:
        return "es"
    if english > spanish and english >= 5:
        return "en"
    return None


_EN_STOPWORDS = {
    "the",
    "and",
    "in",
    "of",
    "to",
    "a",
    "is",
    "for",
    "with",
    "as",
    "on",
    "at",
    "by",
    "from",
    "an",
    "our",
    "team",
    "experience",
    "company",
    "you",
    "will",
}

_ES_STOPWORDS = {
    "de",
    "la",
    "el",
    "en",
    "y",
    "los",
    "las",
    "para",
    "con",
    "por",
    "que",
    "una",
    "un",
    "del",
    "al",
    "se",
    "su",
    "como",
    "más",
    "mas",
    "nuestro",
    "nuestra",
    "experiencia",
    "trabajo",
    "equipo",
    "empresa",
}
# --------------------------------------------------------------------------
# Dates
# --------------------------------------------------------------------------


def parse_epoch_ms(value: Any) -> datetime | None:
    """Unix epoch timestamp -> UTC datetime, or None.

    The five copies this replaces disagreed on the unit: wellfound, RemoteOK
    and Arc.dev publish seconds, EURES and No Fluff Jobs publish milliseconds.
    Values above 1e12 are milliseconds (year 33658+ in seconds), everything
    else is seconds — the same threshold No Fluff Jobs already used.
    """
    if not isinstance(value, (int, float)) or value <= 0:
        return None
    seconds = value / 1000 if value > 1_000_000_000_000 else value
    return datetime.fromtimestamp(seconds, tz=UTC)


def parse_rfc822(value: Any) -> datetime | None:
    """RFC 822 date ("Fri, 07 Aug 2026 04:40:08 +0000") -> datetime, else None.

    The standard RSS pubDate shape; parsing quirks (None, empty, malformed)
    are the caller's "no date" case, never an exception.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return parsedate_to_datetime(value.strip())
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------
# Sitemaps
# --------------------------------------------------------------------------

_LOC_RE = re.compile(r"<loc>\s*(.*?)\s*</loc>", re.S | re.I)
_SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def sitemap_locations(text: str) -> list[str]:
    """Every `<loc>` URL from a sitemap body, stripped, in document order.

    Sitemaps pretty-print their XML (`<loc>\n  https://…\n</loc>`), so the
    captured URL is stripped here once instead of per scraper.
    """
    return [loc.strip() for loc in _LOC_RE.findall(text or "")]


def sitemap_child(node: Any, tag: str) -> Any | None:
    """Find a child with or without the sitemap namespace.

    Written out rather than chained with `or`: an ElementTree element with no
    children is falsy, so `find(ns) or find(plain)` discards every match that
    has no sub-elements — which is every <lastmod> there is.
    """
    found = node.find(f"sm:{tag}", _SITEMAP_NS)
    return found if found is not None else node.find(tag)


# --------------------------------------------------------------------------
# Salary display
# --------------------------------------------------------------------------


def format_salary(
    low: Any,
    high: Any,
    currency: str | None = None,
    *,
    suffix: str = "",
) -> str | None:
    """One display string for a salary band: "32-35 €K".

    The scrapers that feed this disagree on units (hourly rates, thousands,
    monthly periods), so they extract their own min/max/currency/suffix and
    this only joins them: a range renders as "low-high", a single-sided band
    as that value, then currency and suffix. None when neither side has a
    value.
    """
    if low in (None, 0) and high in (None, 0):
        return None
    if low is not None and high is not None and low != high:
        band = f"{low:g}-{high:g}"
    else:
        band = f"{low if low not in (None, 0) else high:g}"
    out = [band]
    if currency:
        out.append(currency)
    text = " ".join(out)
    return f"{text} {suffix}".strip() if suffix else text


# --------------------------------------------------------------------------
# Location
# --------------------------------------------------------------------------


def parse_single_country(value: Any) -> str | None:
    """Resolve a location only when it names exactly one known country.

    "UK" resolves; "USA, Canada, EMEA, LATAM" does not, and neither do "EMEA"
    or "Anywhere". Taking the first of a list would invent a location the
    posting never claimed. Accepts either a list of location names (Wellfound)
    or a comma-separated string (Jobicy, Jobgether).
    """
    if isinstance(value, list):
        if len(value) != 1 or not isinstance(value[0], str):
            return None
        text = value[0].strip()
    elif isinstance(value, str):
        text = value.strip()
    else:
        return None
    if not text:
        return None
    parts = [p.strip() for p in text.split(",") if p.strip()]
    if len(parts) != 1:
        return None
    return country_from_name(parts[0])
