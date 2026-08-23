"""Rule-based signal detection: what a posting says about fit.

Pure detection — this module finds signals and never assigns points. The
weights live in config.yaml and are applied by `score.py`, so a calibration
change never touches this file.

Every rule is deterministic and explainable. No LLM call anywhere: I have to
be able to justify each point by hand.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .config import ExperienceBand, ScoringConfig, SeniorityTier
from .models import Job, norm_text


@dataclass(slots=True)
class SkillHit:
    name: str
    points: float
    in_title: bool = False


@dataclass(slots=True)
class Signals:
    """Everything the rules found in one posting."""

    kill_word: str | None = None
    role_term: str | None = None
    role_in_title: bool = False
    skills: list[SkillHit] = field(default_factory=list)
    level_word: str | None = None
    level_in_title: bool = False
    seniority: SeniorityTier | None = None
    seniority_word: str | None = None
    visa: int = 0  # +1 sponsors, -1 refuses, 0 silent
    visa_phrase: str | None = None
    spanish_required: bool = False
    english_working: bool = False
    years_required: int | None = None
    experience_band: ExperienceBand | None = None
    #: How the money could reach Ankara without moving house. Separate axis
    #: from `visa`: sponsorship is about relocating, these are about staying.
    payment_rails: list[str] = field(default_factory=list)
    #: Remote wording wide enough to include Turkey, e.g. "work from anywhere",
    #: "EMEA", "UTC+3". Plain "remote" is not enough — most remote postings are
    #: remote *within one country*.
    open_remote_phrase: str | None = None
    #: Wording that shuts Turkey out: "US only", "must reside in Germany".
    geo_locked_phrase: str | None = None


def detect(job: Job, sc: ScoringConfig) -> Signals:
    """Run every rule over one posting."""
    title = (job.title or "").lower()
    title_norm = norm_text(job.title)
    description = job.description or ""
    desc_lower = description.lower()
    # Skills and level words cluster near the top, and scanning further mostly
    # picks up boilerplate about the company's other roles.
    desc_head = desc_lower[:6000]
    # Visa, language and experience are scanned in full instead. They are the
    # decisive signals and they turn up last: Manfred prints its relocation FAQ
    # at the very bottom, 6962 characters into one real posting — the head-only
    # scan silently missed every one of them.
    desc_full = desc_lower

    signals = Signals()
    signals.kill_word = _find_kill_word(title, desc_head, sc)
    if signals.kill_word:
        return signals  # nothing else matters once a posting is killed

    signals.role_term, signals.role_in_title = _find_role(title_norm, desc_head, sc)
    signals.skills = _find_skills(title, desc_head, sc)
    signals.level_word, signals.level_in_title = _find_level(title_norm, desc_head, sc)
    signals.seniority, signals.seniority_word = _find_seniority(title_norm, desc_head, sc)
    signals.visa, signals.visa_phrase = _find_visa(desc_full)
    signals.spanish_required = bool(_SPANISH_REQUIRED_RE.search(desc_full))
    signals.english_working = bool(_ENGLISH_WORKING_RE.search(desc_full))
    signals.years_required = _find_years(desc_full)
    if signals.years_required is not None:
        signals.experience_band = _band_for(signals.years_required, sc)

    # Earning from Ankara. Scanned over title and description together because
    # "Remote (Worldwide)" is usually in the title and never in the prose.
    haystack = f"{title}\n{desc_full}"
    signals.payment_rails = _find_payment_rails(haystack)
    signals.open_remote_phrase = _first_match(_OPEN_REMOTE_RE, haystack)
    signals.geo_locked_phrase = _first_match(_GEO_LOCKED_RE, haystack)
    return signals


# ---------------------------------------------------------------------------
# Kill words
# ---------------------------------------------------------------------------


def _find_kill_word(title: str, description: str, sc: ScoringConfig) -> str | None:
    for word in sc.kill_words:
        if word in title or word in description:
            return word
    return None


# ---------------------------------------------------------------------------
# Role relevance
#
# The whitelist half of filtering. Kill words remove professions one by one and
# can never keep up; this asks the opposite question — is this my line of work
# at all? Without it the level bonus alone lifts any "Junior <anything>" to the
# top of the list.
# ---------------------------------------------------------------------------


def _find_role(title_norm: str, description: str, sc: ScoringConfig) -> tuple[str | None, bool]:
    for term in sc.role_terms:
        if _mentions(title_norm, norm_text(term)):
            return term, True
    for term in sc.role_terms:
        if _mentions(description, term):
            return term, False
    return None, False


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------


def _find_skills(title: str, description: str, sc: ScoringConfig) -> list[SkillHit]:
    """Match each configured skill at most once, title match noted separately."""
    hits: list[SkillHit] = []
    for skill in sc.skills:
        in_title = any(_mentions(title, term) for term in skill.terms)
        in_desc = in_title or any(_mentions(description, term) for term in skill.terms)
        if in_desc:
            hits.append(SkillHit(name=skill.name, points=skill.points, in_title=in_title))
    return hits


def _mentions(haystack: str, term: str) -> bool:
    """Substring match with word boundaries where the term allows them.

    A trailing "s" is accepted, because postings say "our engineers" and
    "React developers" far more often than the singular.

    "c#", ".net" and "c++" cannot use \\b — the punctuation is the boundary —
    so they fall back to a plain substring test.
    """
    if not term or not haystack:
        return False
    if term[0].isalnum() and term[-1].isalnum():
        return re.search(rf"(?<![a-z0-9]){re.escape(term)}s?(?![a-z0-9])", haystack) is not None
    return term in haystack


# ---------------------------------------------------------------------------
# Level and seniority
#
# Read from the title. A description saying "you will report to a senior
# engineer" or "our graduate programme" says nothing about the advertised
# level, which is exactly how a junior role ends up ranked as senior.
# ---------------------------------------------------------------------------


def _find_level(title_norm: str, description: str, sc: ScoringConfig) -> tuple[str | None, bool]:
    for word in sc.level_words:
        if _mentions(title_norm, norm_text(word)):
            return word, True
    for word in sc.level_words:
        if _mentions(description, word):
            return word, False
    return None, False


def _find_seniority(
    title_norm: str, description: str, sc: ScoringConfig
) -> tuple[SeniorityTier | None, str | None]:
    for tier in sc.seniority_tiers:
        for word in tier.words:
            if _mentions(title_norm, norm_text(word)):
                return tier, word
    if sc.seniority_title_only:
        return None, None
    for tier in sc.seniority_tiers:
        for word in tier.words:
            if _mentions(description, word):
                return tier, word
    return None, None


# ---------------------------------------------------------------------------
# Visa / sponsorship
# ---------------------------------------------------------------------------

#: Checked first: "no visa sponsorship" contains "visa sponsorship".
_VISA_NEGATIVE_RE = re.compile(
    r"\bno\s+visa\s+sponsor\w*"
    r"|\b(?:cannot|can't|do(?:es)?\s+not|will\s+not|unable\s+to)\s+sponsor"
    r"|\bwithout\s+(?:the\s+)?need\s+for\s+sponsor\w*"
    r"|\bnot\s+(?:able\s+to\s+)?(?:offer|provide)\s+(?:visa\s+)?sponsor\w*"
    r"|\bmust\s+(?:already\s+)?(?:have|possess|hold)\s+(?:the\s+)?"
    r"(?:right|authori[sz]ation|permit|eligibility)\s+to\s+work"
    r"|\b(?:must\s+be|are)\s+(?:legally\s+)?(?:authori[sz]ed|eligible)\s+to\s+work"
    r"|\beu\s+citizens?\s+only\b|\bcitizens?\s+of\s+the\s+eu\s+only\b"
    r"|\bsecurity\s+clearance\b"
    r"|\bpermiso\s+de\s+trabajo(?:\s+en\s+vigor)?\b"
    r"|\bno\s+(?:se\s+)?(?:ofrece|gestiona|patrocina)\w*\s+(?:el\s+)?visado\b"
    # Manfred asks every employer the same question and prints the answer.
    # Verified across 7 offers on 2026-08-08: a "No" here is the clearest
    # relocation refusal any source in this project produces.
    r"|(?:fuera\s+de\s+espa[nñ]a|no\s+vivo\s+en\s+espa[nñ]a)[^?]{0,40}\?\s*\**\s*no\b"
    r"|\bresid(?:e|a|encia|ir)\s+(?:en|dentro\s+de)\s+(?:espa[nñ]a|la\s+uni[oó]n\s+europea)\b"
    r"|\bpasaporte\s+de\s+la\s+uni[oó]n\s+europea\b"
    r"|\bremota?\s+para\s+el\s+territorio\s+nacional\b",
    re.IGNORECASE,
)

_VISA_POSITIVE_RE = re.compile(
    r"\bvisa\s+sponsor\w*|\bsponsor\w*\s+(?:a\s+)?(?:visa|work\s+permit)"
    r"|\bwe\s+sponsor\b|\bsponsorship\s+(?:is\s+)?available\b"
    r"|\brelocation\s+(?:package|assistance|support|bonus)\b"
    r"|\bwe\s+(?:offer|provide)\s+relocation\b"
    r"|\bblue\s+card\b"
    r"|\b(?:ofrecemos|gestionamos|patrocinamos)\s+(?:el\s+)?visado\b"
    r"|\bpaquete\s+de\s+reubicaci[oó]n\b",
    re.IGNORECASE,
)


def _find_visa(description: str) -> tuple[int, str | None]:
    match = _VISA_NEGATIVE_RE.search(description)
    if match:
        return -1, match.group(0).strip()
    match = _VISA_POSITIVE_RE.search(description)
    if match:
        return 1, match.group(0).strip()
    return 0, None


# ---------------------------------------------------------------------------
# Language
#
# A posting written in Spanish is not charged — many Spanish companies work in
# English. Only an explicit requirement counts.
# ---------------------------------------------------------------------------

_SPANISH_REQUIRED_RE = re.compile(
    r"\bimprescindible\s+(?:el\s+)?(?:castellano|espa[nñ]ol)\b"
    r"|\b(?:castellano|espa[nñ]ol)\s+(?:imprescindible|nativo|obligatorio|requerido)\b"
    r"|\bse\s+requiere\s+(?:un\s+)?(?:nivel\s+(?:alto|nativo|avanzado)\s+de\s+)?espa[nñ]ol\b"
    r"|\bnivel\s+(?:alto|nativo|avanzado|c1|c2)\s+de\s+espa[nñ]ol\b"
    r"|\bspanish\s+(?:is\s+)?(?:required|mandatory|essential|compulsory)\b"
    r"|\b(?:fluent|native|professional)\s+(?:in\s+)?spanish\s+(?:is\s+)?(?:required|mandatory|essential|a\s+must)\b"
    r"|\bfluency\s+in\s+spanish\s+(?:is\s+)?(?:required|mandatory|essential)\b"
    r"|\bmust\s+(?:be\s+fluent\s+in|speak)\s+spanish\b",
    re.IGNORECASE,
)

_ENGLISH_WORKING_RE = re.compile(
    r"\benglish\s+is\s+(?:our|the)\s+(?:working|official|company)\s+language\b"
    r"|\b(?:working|company|official)\s+language\s+is\s+english\b"
    r"|\bwe\s+work\s+(?:fully\s+)?in\s+english\b"
    r"|\benglish[- ]speaking\s+(?:environment|company|team|workplace)\b"
    r"|\bno\s+spanish\s+(?:is\s+)?required\b|\bspanish\s+(?:is\s+)?not\s+required\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Years of experience
# ---------------------------------------------------------------------------

_YEARS_PATTERNS = (
    # A range names its own floor: "3-5 years" is a three-year door, and
    # matching the 5 would have overstated every ranged requirement.
    re.compile(
        r"(\d{1,2})\s*[-–—]\s*\d{1,2}\s*\+?\s*(?:years?|a[nñ]os?|yıl)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(\d{1,2})\s*\+?\s*(?:or\s+more\s+)?years?\s+(?:of\s+)?"
        r"(?:relevant\s+|professional\s+|work\s+|hands[- ]on\s+|industry\s+)?experience",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:minimum|at\s+least|min\.?|m[ií]nimo(?:\s+de)?)\s+(?:of\s+)?(\d{1,2})\s*\+?\s*"
        r"(?:years?|a[nñ]os?)",
        re.IGNORECASE,
    ),
    re.compile(r"(\d{1,2})\s*\+?\s*a[nñ]os?\s+de\s+experiencia", re.IGNORECASE),
    re.compile(r"(\d{1,2})\s*\+?\s*yıl\w*\s+(?:iş\s+)?deneyim", re.IGNORECASE),
)


def _find_years(description: str) -> int | None:
    """Smallest credible requirement wins — "3-5 years" is a 3-year door."""
    found: list[int] = []
    for pattern in _YEARS_PATTERNS:
        for match in pattern.finditer(description):
            try:
                years = int(match.group(1))
            except (ValueError, IndexError):
                continue
            if 0 < years <= 25:
                found.append(years)
    return min(found) if found else None


def _band_for(years: int, sc: ScoringConfig) -> ExperienceBand | None:
    for band in sorted(sc.experience_bands, key=lambda b: b.max_years):
        if years <= band.max_years:
            return band
    return sc.experience_bands[-1] if sc.experience_bands else None


# ---------------------------------------------------------------------------
# Earning from Ankara
#
# A different question from the visa rules above. Sponsorship asks "will they
# move me?"; these ask "can they pay me where I already live?". A posting can
# be strong on one axis and silent on the other, so they are scored apart.
#
# Three things have to be true for that to work: the company must hire outside
# its own country (open remote), it must have a way to pay someone who is not
# on its payroll (an EOR, a contractor invoice, or crypto), and the posting must
# not be locked to a country Turkey is not in.
# ---------------------------------------------------------------------------

#: Employer-of-record platforms. Naming one is the single most reliable signal
#: in this whole family: a company does not mention Deel unless it has already
#: solved paying people abroad.
_EOR_RE = re.compile(
    r"\b(deel|oyster\s?hr|papaya\s+global|velocity\s+global"
    r"|globalization\s+partners|remotepass|omnipresent|rippling\s+eor"
    r"|employer\s+of\s+record|\beor\b|multiplier\s+(?:global\s+)?(?:payroll|employ|hr|payment))\b",
    re.IGNORECASE,
)

#: Contractor / B2B wording — invoicing from a Turkish company.
_B2B_RE = re.compile(
    r"\bb2b\b|\bcontractor\b|\bindependent\s+contractor\b|\bcontract\s+basis\b"
    r"|\bself[-\s]?employed\b|\binvoice\s+(?:us|monthly|your)\b"
    r"|\bw-?8ben\b|\b1099\b|\boutside\s+ir35\b"
    r"|\bfreelance\s+(?:contract|basis|role)\b",
    re.IGNORECASE,
)

#: Crypto and stablecoin payroll.
_CRYPTO_PAY_RE = re.compile(
    r"\busdc\b|\busdt\b|\bstablecoin\b|\bcrypto\s+(?:payroll|salary)\b"
    r"|\bpaid\s+in\s+(?:crypto|usdc|usdt|stablecoins?)\b"
    r"|\btoken\s+(?:compensation|package|grant)\b|\bdao\s+payroll\b",
    re.IGNORECASE,
)

#: Cross-border transfer rails. Weaker than the above — a posting naming Wise
#: is probably already paying people abroad, but it might just be a perk.
_TRANSFER_RE = re.compile(
    r"\bwise\s+(?:transfer|payment)\b|\btransferwise\b|\bpayoneer\b"
    r"|\bswift\s+transfer\b|\bsepa\b",
    re.IGNORECASE,
)

#: Remote wide enough to reach Turkey. Deliberately narrow: bare "remote" says
#: nothing, and "remote (US)" is the commonest posting on every board here.
_OPEN_REMOTE_RE = re.compile(
    r"\bwork\s+(?:remotely\s+)?from\s+anywhere\b|\banywhere\s+in\s+the\s+world\b"
    # Boards state this as a policy rather than a place, e.g. Cryptocurrency
    # Jobs writes "100% remote with no geographical restrictions".
    r"|\bno\s+geo(?:graphic(?:al)?)?\s+restrictions?\b"
    r"|\b100%\s+remote\b|\bremote[-\s]first\b"
    r"|\bremote\s*[-(,]?\s*(?:worldwide|global|anywhere)\b"
    r"|\b(?:worldwide|global(?:ly)?|fully)\s+remote\b"
    r"|\bemea\b|\bcemea\b"
    r"|\bremote\s+(?:in\s+)?europe\b|\beurope[-\s]wide\b"
    r"|\butc\s*\+\s*[1-4]\b|\bgmt\s*\+\s*[1-4]\b"
    r"|\bcet\s*[±+-]\s*\d\b"
    # "we hire worldwide" / "hiring globally" — the same promise as
    # "worldwide remote", just written as a sentence rather than a label.
    r"|\bhir(?:e|ing)\s+(?:from\s+)?(?:anywhere|worldwide|globally)\b"
    r"|\b(?:fully\s+)?distributed\s+team\b|\basync[-\s]first\b"
    r"|\bt[uü]rkiye\b|\bturkey\b",
    re.IGNORECASE,
)

#: Wording that excludes Turkey outright. Kept separate from the visa penalty:
#: this is about where the work may be *done*, not about sponsorship.
_GEO_LOCKED_RE = re.compile(
    r"\b(?:us|u\.s\.|usa|uk|canada|australia)[-\s]only\b"
    r"|\bonly\s+(?:in|within)\s+the\s+(?:us|uk|usa|united\s+states)\b"
    r"|\bmust\s+(?:reside|be\s+located|be\s+based|live)\s+in\b"
    r"|\bresidents?\s+of\s+the\s+(?:us|uk|united\s+states)\s+only\b"
    r"|\bremote\s*\(\s*(?:us|usa|uk|united\s+states)[^)]*\)"
    r"|\blocal\s+candidates?\s+only\b"
    r"|\bwithin\s+commuting\s+distance\b",
    re.IGNORECASE,
)

#: Rail name -> the label stored on the job, ordered strongest first so the
#: reasons read in order of how much they actually settle.
_RAILS = (
    ("eor", _EOR_RE),
    ("b2b", _B2B_RE),
    ("crypto", _CRYPTO_PAY_RE),
    ("transfer", _TRANSFER_RE),
)


def _find_payment_rails(haystack: str) -> list[str]:
    """Which ways of paying someone abroad this posting names.

    Filters Dutch/German false positives: "deel" means "part" in Dutch
    and "eor" appears in many German compound words.
    """
    rails = [name for name, pattern in _RAILS if pattern.search(haystack)]
    # The EOR regex fires on Dutch "deel" (part) and German words containing
    # "eor". Verify it's a real EOR mention.
    if (
        "eor" in rails
        and _is_dutch_or_german(haystack)
        and not _has_real_eor(haystack)
    ):
        rails.remove("eor")
    return rails


#: Dutch/German words that indicate the text is not English. If these appear
#: alongside an EOR regex match, the match is almost certainly a false positive.
_DUTCH_DE_WORDS = re.compile(
    r"\b(uitmaken|onderdeel|werktijden|functieomschrijving|sollicitatie"
    r"|vacature|arbeidsovereenkomst|dienstverband|werknemer|werkgever"
    r"|vergoeding|aanstelling|collega|afdeling|verantwoordelijk)",
    re.IGNORECASE,
)
_GERMAN_DE_WORDS = re.compile(
    r"\b(dienstleistung|verantwortung|unternehmen|beschreibung"
    r"|voraussetzung|arbeitszeit|vergütung|mitarbeiter|einstellung"
    r"|bewerbung|stellenanzeige|serviceorientiert|theoretisch)",
    re.IGNORECASE,
)


def _is_dutch_or_german(text: str) -> bool:
    """Quick check: does the text contain Dutch or German vocabulary?"""
    return bool(_DUTCH_DE_WORDS.search(text) or _GERMAN_DE_WORDS.search(text))


def _has_real_eor(text: str) -> bool:
    """Check for unambiguous EOR platform names that don't have Dutch/German
    false-positive equivalents."""
    # These are proper nouns and brands — they don't mean anything else.
    real_eor = re.compile(
        r"\b(oyster\s?hr|papaya\s+global|velocity\s+global"
        r"|globalization\s+partners|remotepass|omnipresent"
        r"|rippling\s+eor|employer\s+of\s+record)\b",
        re.IGNORECASE,
    )
    return bool(real_eor.search(text))


def _first_match(pattern: re.Pattern[str], haystack: str) -> str | None:
    found = pattern.search(haystack)
    return found.group(0).strip() if found else None
