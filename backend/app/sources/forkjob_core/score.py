"""Deterministic, additive, segment-blind scoring.

    score = base
          + skill_bonus            capped, title mentions weigh more
          + level_bonus            junior / entry / graduate / becario
          - seniority_penalty      senior / staff / lead / principal / manager
          + visa_bonus             sponsorship offered           (EU only)
          - visa_penalty           sponsorship refused           (EU only)
          - language_penalty       explicit Spanish requirement
          + english_bonus          English is the working language
          - experience_penalty     years demanded I do not have
          - relocation_penalty     TR office outside Ankara/İstanbul
          - freshness_decay        scaled by how much the date can be trusted

No region multiplier: the score answers "how well does this fit me", not
"which market is it in". The EU/TR quota is a listing concern (`balance.py`).

`reasons` is stored per component rather than as one total, because
calibration needs to answer "this should have been 70, it came out 45 — which
part is wrong?". A single number cannot be calibrated.
"""

from __future__ import annotations

from typing import Any

from .config import Config, ScoringConfig
from .match import Signals, detect
from .models import Job, Region, WorkMode, norm_text


def score_job(job: Job, config: Config) -> None:
    """Compute `job.score` and `job.reasons` in place."""
    sc = config.scoring
    signals = detect(job, sc)

    if signals.kill_word:
        # Killed, not deleted: it drops out of the default view but stays in
        # the database, because the score is a ranking signal, not a verdict.
        job.score = sc.kill_score
        job.reasons = {"killed": signals.kill_word, "total": sc.kill_score}
        return

    reasons: dict[str, Any] = {"base": sc.base}
    total = sc.base

    total += _apply_role(signals, sc, reasons)
    total += _apply_skills(signals, sc, reasons)
    total += _apply_level(signals, sc, reasons)
    total += _apply_seniority(signals, sc, reasons)
    total += _apply_visa(job, signals, sc, reasons)
    total += _apply_earning(signals, sc, reasons)
    total += _apply_language(signals, sc, reasons)
    total += _apply_experience(signals, sc, reasons)
    total += _apply_relocation(job, sc, reasons)
    total += _apply_freshness(job, sc, reasons)

    job.score = round(max(sc.score_floor, min(sc.score_cap, total)), 1)
    reasons["total"] = job.score
    job.reasons = reasons


def score_jobs(jobs: list[Job], config: Config) -> None:
    for job in jobs:
        score_job(job, config)


# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------


def _apply_role(signals: Signals, sc: ScoringConfig, reasons: dict[str, Any]) -> float:
    """Charge a posting that is not a software engineering role.

    Kill words are a blacklist and will always trail reality; this is the
    whitelist that keeps "Accounting Associate" from riding the junior bonus to
    the top of the list. A term found only in the description is weak evidence,
    so it earns relief rather than a clean pass.
    """
    if not sc.role_terms:
        return 0.0

    if signals.role_in_title:
        reasons["role"] = {"term": signals.role_term, "where": "title", "delta": 0.0}
        return 0.0

    if signals.role_term:
        penalty = sc.role_mismatch_penalty * (1.0 - sc.role_description_relief)
        reasons["role"] = {
            "term": signals.role_term,
            "where": "description only",
            "delta": -round(penalty, 1),
        }
        return -penalty

    reasons["role"] = {"term": None, "where": "not found", "delta": -sc.role_mismatch_penalty}
    return -sc.role_mismatch_penalty


def _apply_skills(signals: Signals, sc: ScoringConfig, reasons: dict[str, Any]) -> float:
    if not signals.skills:
        return 0.0

    breakdown: dict[str, float] = {}
    raw = 0.0
    for hit in signals.skills:
        points = hit.points * (sc.skill_title_multiplier if hit.in_title else 1.0)
        breakdown[hit.name] = round(points, 1)
        raw += points

    awarded = min(raw, sc.skill_max)
    reasons["skills"] = breakdown
    reasons["skills_total"] = round(awarded, 1)
    if raw > sc.skill_max:
        # Recorded so calibration can tell "great match" from "cap reached".
        reasons["skills_capped_from"] = round(raw, 1)
    return awarded


def _apply_level(signals: Signals, sc: ScoringConfig, reasons: dict[str, Any]) -> float:
    """Reward an entry-level posting — but only one in my field.

    The bonus is conditional on the role matching in the title. A "Junior
    Accountant" being junior is no use to me, and without this condition the
    level bonus alone was carrying non-engineering postings to the top.
    """
    if not signals.level_word:
        return 0.0
    if sc.role_terms and not signals.role_in_title:
        reasons["level"] = {
            "word": signals.level_word,
            "where": "title" if signals.level_in_title else "description",
            "bonus": 0.0,
            "note": "withheld — not a software role",
        }
        return 0.0

    factor = 1.0 if signals.level_in_title else sc.level_description_factor
    bonus = sc.level_bonus * factor
    reasons["level"] = {
        "word": signals.level_word,
        "where": "title" if signals.level_in_title else "description",
        "bonus": round(bonus, 1),
    }
    return bonus


def _apply_seniority(signals: Signals, sc: ScoringConfig, reasons: dict[str, Any]) -> float:
    tier = signals.seniority
    if tier is None:
        return 0.0
    reasons["seniority"] = {
        "level": tier.label,
        "word": signals.seniority_word,
        "penalty": -round(tier.penalty, 1),
    }
    return -tier.penalty


def _apply_visa(job: Job, signals: Signals, sc: ScoringConfig, reasons: dict[str, Any]) -> float:
    if signals.visa == 0:
        return 0.0

    signal = "sponsors" if signals.visa > 0 else "refuses"

    # Sponsorship wording is meaningless for a TR posting — I can already work
    # there — so it is not *scored* outside the EU. It is still recorded, so
    # the `list` visa column can tell "no barrier here" from "never said".
    if sc.visa_eu_only and job.region is not Region.EU:
        reasons["visa"] = {
            "signal": signal,
            "phrase": signals.visa_phrase,
            "delta": 0.0,
            "note": "not scored outside the EU",
        }
        return 0.0

    delta = sc.visa_bonus if signals.visa > 0 else -sc.visa_penalty
    reasons["visa"] = {
        "signal": signal,
        "phrase": signals.visa_phrase,
        "delta": round(delta, 1),
    }
    return delta


def _apply_earning(signals: Signals, sc: ScoringConfig, reasons: dict[str, Any]) -> float:
    """Score whether this job could pay a Turkish invoice without me moving.

    Independent of `_apply_visa` on purpose. Sponsorship answers "will they
    move me?" and is scored in the EU only; this answers "can they pay me where
    I already live?", which has no region at all — a worldwide-remote contract
    is as reachable from Ankara as from anywhere else.
    """
    delta = 0.0
    detail: dict[str, Any] = {}

    if signals.payment_rails:
        rails = {}
        subtotal = 0.0
        for rail in signals.payment_rails:
            points = sc.payment_rail_bonus.get(rail, 0.0)
            if points:
                rails[rail] = points
                subtotal += points
        capped = min(subtotal, sc.payment_rail_max)
        if rails:
            detail["rails"] = rails
            if capped < subtotal:
                detail["capped_to"] = sc.payment_rail_max
            delta += capped

    if signals.open_remote_phrase:
        detail["open_remote"] = signals.open_remote_phrase
        delta += sc.open_remote_bonus

    if signals.geo_locked_phrase:
        # Charged even against a posting that also reads as open: an explicit
        # residency requirement is a harder fact than a "worldwide" adjective.
        detail["geo_locked"] = signals.geo_locked_phrase
        delta -= sc.geo_locked_penalty

    if not detail:
        return 0.0

    detail["delta"] = round(delta, 1)
    reasons["earning"] = detail
    return delta


def _apply_language(signals: Signals, sc: ScoringConfig, reasons: dict[str, Any]) -> float:
    if signals.spanish_required:
        reasons["language"] = {
            "signal": "spanish required",
            "delta": -round(sc.spanish_requirement_penalty, 1),
        }
        return -sc.spanish_requirement_penalty
    if signals.english_working:
        reasons["language"] = {
            "signal": "english working language",
            "delta": round(sc.english_working_bonus, 1),
        }
        return sc.english_working_bonus
    return 0.0


def _apply_experience(signals: Signals, sc: ScoringConfig, reasons: dict[str, Any]) -> float:
    band = signals.experience_band
    if band is None or signals.years_required is None:
        return 0.0
    reasons["experience"] = {
        "years": signals.years_required,
        "band": band.label,
        "delta": round(band.delta, 1),
    }
    return band.delta


def _apply_relocation(job: Job, sc: ScoringConfig, reasons: dict[str, Any]) -> float:
    """Charge a TR office role in a city I would have to move to.

    This is the one location signal that belongs in the score: it is a real
    mismatch, not a market preference. Unknown cities are not charged — a
    guess here would sink perfectly good postings.
    """
    if job.region is not Region.TR:
        return 0.0
    if job.work_mode is WorkMode.REMOTE or job.remote is True:
        return 0.0

    city = norm_text(job.city or job.location)
    if not city:
        return 0.0
    if any(ok in city for ok in (norm_text(c) for c in sc.tr_office_cities)):
        return 0.0

    reasons["relocation"] = {
        "city": job.city or job.location,
        "delta": -round(sc.tr_relocation_penalty, 1),
    }
    return -sc.tr_relocation_penalty


def _apply_freshness(job: Job, sc: ScoringConfig, reasons: dict[str, Any]) -> float:
    """Tiered decay: a date I cannot trust cannot make a posting look old."""
    days = job.age_days
    factor = sc.freshness_factors.get(job.date_source.value, 0.0)

    if days is None or factor <= 0.0:
        reasons["freshness"] = {
            "days": days,
            "source": job.date_source.value,
            "penalty": 0.0,
            "note": "no decay — date not trustworthy enough",
        }
        return 0.0

    over = max(0, days - sc.freshness_grace_days)
    penalty = min(over * sc.freshness_penalty_per_day, sc.freshness_max_penalty) * factor
    reasons["freshness"] = {
        "days": days,
        "source": job.date_source.value,
        "penalty": -round(penalty, 1),
    }
    return -penalty


# ---------------------------------------------------------------------------
# Human-readable rendering
# ---------------------------------------------------------------------------


def summarise(reasons: dict[str, Any]) -> str:
    """One-line summary for the list view, e.g.
    "base 50 | +25 junior | c#,sql | -15 español | -3 15g*"
    """
    if not reasons:
        return ""
    if "killed" in reasons:
        return f"killed: {reasons['killed']}"

    parts = [f"base {_num(reasons.get('base', 0))}"]

    role = reasons.get("role")
    if isinstance(role, dict) and role.get("delta"):
        parts.append(f"{_signed(role['delta'])} not my field")

    level = reasons.get("level")
    if isinstance(level, dict):
        parts.append(f"+{_num(level['bonus'])} {level['word']}")

    seniority = reasons.get("seniority")
    if isinstance(seniority, dict):
        # Show the word that actually matched, not just its tier. "-32 lead"
        # on a posting titled "Product Manager Junior" reads like a bug; the
        # matched word was "manager", which explains itself.
        word = seniority.get("word")
        label = seniority["level"]
        parts.append(
            f"{_num(seniority['penalty'])} {word}"
            if word and word != label
            else f"{_num(seniority['penalty'])} {label}"
        )

    skills = reasons.get("skills")
    if isinstance(skills, dict) and skills:
        named = ",".join(list(skills)[:4])
        parts.append(f"+{_num(reasons.get('skills_total', 0))} {named}")

    visa = reasons.get("visa")
    if isinstance(visa, dict):
        parts.append(f"{_signed(visa['delta'])} visa {visa['signal']}")

    earning = reasons.get("earning")
    if isinstance(earning, dict):
        # Name the rails rather than the total: "eor,b2b" says why, "+25" does
        # not, and this is the axis the whole earn-from-Ankara case rests on.
        bits = list(earning.get("rails", {}))
        if earning.get("open_remote"):
            bits.append("open")
        if earning.get("geo_locked"):
            bits.append("geo-locked")
        parts.append(f"{_signed(earning['delta'])} {','.join(bits)}")

    language = reasons.get("language")
    if isinstance(language, dict):
        parts.append(f"{_signed(language['delta'])} {language['signal']}")

    experience = reasons.get("experience")
    if isinstance(experience, dict) and experience["delta"]:
        parts.append(f"{_signed(experience['delta'])} {experience['years']}y")

    relocation = reasons.get("relocation")
    if isinstance(relocation, dict):
        parts.append(f"{_signed(relocation['delta'])} {relocation['city']}")

    freshness = reasons.get("freshness")
    if isinstance(freshness, dict) and freshness.get("penalty"):
        mark = {"employer": "", "updated": "*", "discovered": "?"}.get(
            freshness.get("source", ""), ""
        )
        parts.append(f"{_signed(freshness['penalty'])} {freshness['days']}g{mark}")

    return " | ".join(parts)


def visa_status(job_reasons: dict[str, Any], region: Any = None) -> str:
    """Three-state visa answer for the list column: ok | no | ?

    "?" means the posting never addressed it, which is the common case and is
    genuinely different from "no barrier" — most listings simply say nothing.
    """
    visa = job_reasons.get("visa")
    if not isinstance(visa, dict):
        return "?"
    return "ok" if visa.get("signal") == "sponsors" else "no"


def _num(value: Any) -> str:
    number = float(value)
    return str(int(number)) if number == int(number) else f"{number:.1f}"


def _signed(value: Any) -> str:
    number = float(value)
    return f"+{_num(number)}" if number > 0 else _num(number)
