"""Scoring and balance configuration, loaded from config.yaml.

The scoring model is additive and segment-blind:

    score = base
          + skill_bonus
          + level_bonus          junior / entry / graduate / becario
          - seniority_penalty    senior / staff / lead / principal / manager
          + visa_bonus           sponsorship offered            (EU only)
          - visa_penalty         sponsorship refused            (EU only)
          - language_penalty     explicit Spanish requirement
          - experience_penalty   years demanded beyond none
          - relocation_penalty   TR office outside Ankara/İstanbul
          - freshness_decay      tiered by date_source

There is deliberately no region multiplier. "EU 50% / TR 50%" is a portfolio
quota, not a quality signal — putting it in the score would sink every TR
posting systematically. The quota is applied by `balance.py` at list time.

Every weight lives here so calibration never touches code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path("config.yaml")


@dataclass(slots=True)
class SkillWeight:
    """One technology worth points, with the spellings it appears under."""

    name: str
    points: float = 5.0
    aliases: list[str] = field(default_factory=list)

    @property
    def terms(self) -> list[str]:
        return [self.name, *self.aliases]


@dataclass(slots=True)
class SeniorityTier:
    """A rung on the ladder above me, and what it costs a posting."""

    label: str
    penalty: float
    words: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ExperienceBand:
    """Years of experience demanded -> score delta. First match by max_years."""

    max_years: int
    delta: float
    label: str = ""


@dataclass(slots=True)
class ScoringConfig:
    #: Every posting starts here. Bonuses and penalties move it.
    base: float = 50.0

    # -- stack ---------------------------------------------------------------
    skills: list[SkillWeight] = field(default_factory=list)
    #: Cap on the total stack bonus, so a keyword-stuffed posting cannot win
    #: on skills alone.
    skill_max: float = 25.0
    #: A skill named in the title counts for more than one buried in prose.
    skill_title_multiplier: float = 1.5

    # -- role relevance ------------------------------------------------------
    #: Terms that make a posting a software engineering role. Without this the
    #: level bonus alone floats any junior posting to the top — an "Accounting
    #: Associate" scored 75 before this existed. Kill words are a blacklist and
    #: cannot keep up; this is the whitelist.
    role_terms: list[str] = field(default_factory=list)
    role_mismatch_penalty: float = 40.0
    #: A role term only in the description is weak evidence — nearly every
    #: posting at a tech company says "engineer" somewhere — so it buys only a
    #: little relief, not a pass.
    role_description_relief: float = 0.25

    # -- level ---------------------------------------------------------------
    level_words: list[str] = field(default_factory=list)
    level_bonus: float = 25.0
    #: Level words in the description are a weaker signal than in the title —
    #: "you will work with our graduate programme" is not a graduate role.
    level_description_factor: float = 0.3

    # -- seniority -----------------------------------------------------------
    seniority_tiers: list[SeniorityTier] = field(default_factory=list)
    #: Seniority is read from the title only. A description mentioning "senior
    #: engineers" says nothing about the level of the role being advertised.
    seniority_title_only: bool = True

    # -- visa (EU postings only) ---------------------------------------------
    visa_bonus: float = 20.0
    visa_penalty: float = 35.0
    #: Sponsorship wording is irrelevant for TR postings — I can already work
    #: there — so the signal is scored only in the EU region.
    visa_eu_only: bool = True

    # -- earning from Ankara -------------------------------------------------
    #: A second, independent axis from visa. Sponsorship means moving; these
    #: mean the money can reach a Turkish invoice while I stay put. Scored in
    #: every region, because a worldwide-remote role has no region.
    #: Points per named payment rail, strongest first.
    payment_rail_bonus: dict[str, float] = field(
        default_factory=lambda: {
            # Naming an EOR is the strongest single signal here: no company
            # mentions Deel unless it has already solved paying people abroad.
            "eor": 18.0,
            "b2b": 12.0,
            "crypto": 10.0,
            # Weakest — a posting naming Wise may just be listing a perk.
            "transfer": 4.0,
        }
    )
    #: Cap, so a posting listing every rail cannot win on payment terms alone.
    payment_rail_max: float = 25.0
    #: Remote wording wide enough to include Turkey. Bare "remote" earns
    #: nothing: most remote postings are remote within one country.
    open_remote_bonus: float = 20.0
    #: "US only", "must reside in Germany". Charged even when the posting is
    #: otherwise perfect, because it is the one condition I cannot satisfy.
    geo_locked_penalty: float = 45.0

    # -- language ------------------------------------------------------------
    #: Charged only on an explicit requirement in the text. A posting merely
    #: *written* in Spanish is not charged: plenty of them work in English.
    spanish_requirement_penalty: float = 15.0
    english_working_bonus: float = 5.0

    # -- experience ----------------------------------------------------------
    experience_bands: list[ExperienceBand] = field(default_factory=list)

    # -- relocation ----------------------------------------------------------
    #: TR cities where an office role is workable without moving house.
    tr_office_cities: list[str] = field(default_factory=lambda: ["ankara", "istanbul"])
    #: A TR office role anywhere else is a genuine mismatch, not a bucket
    #: preference — it is the one location signal that stays in the score.
    tr_relocation_penalty: float = 20.0

    # -- freshness -----------------------------------------------------------
    #: Days before decay starts biting.
    freshness_grace_days: int = 7
    freshness_penalty_per_day: float = 0.4
    freshness_max_penalty: float = 20.0
    #: Tiered by how much the date can be trusted. A posting with no date is
    #: never treated as old.
    freshness_factors: dict[str, float] = field(
        default_factory=lambda: {"employer": 1.0, "updated": 0.5, "discovered": 0.0}
    )

    # -- hard filter ---------------------------------------------------------
    kill_words: list[str] = field(default_factory=list)
    #: Killed postings get this score and hide from the default view. They are
    #: never deleted — score is a ranking signal, not a delete condition.
    kill_score: float = -1.0

    # -- bounds --------------------------------------------------------------
    score_cap: float = 100.0
    score_floor: float = 0.0


@dataclass(slots=True)
class BalanceConfig:
    """Portfolio quota applied by `list`, not by the scorer."""

    #: Bucket -> share of the listing. EU 50%, and the TR half split
    #: remote 60 / office 40.
    #: Empty by default: the list goes by score. Fixed shares fought the data —
    #: a 50% TR quota filled half the list with 0-to-20 point postings because
    #: Turkey had nothing above 70. Set shares here to bring them back.
    quotas: dict[str, float] = field(default_factory=dict)
    #: A bucket only earns slots for postings at or above this score. Without
    #: it, a bucket with six weak postings claims six slots — which is how a
    #: 50% TR quota filled half the list with 0-to-20 point sales roles while
    #: Turkey had nothing above 70. Weak postings still show up in the
    #: leftovers; they just do not create an entitlement.
    quota_min_score: float = 30.0
    #: Round-robin across buckets rather than sorting purely by score.
    interleave: bool = True
    #: Guaranteed slots per bucket, applied before any share. This is what
    #: keeps a strong TR or worldwide-remote posting from being buried under a
    #: wall of EU ones, without imposing a ratio the supply cannot meet.
    floor: int = 2
    #: Buckets with no quota (OTHER) only fill slots the others cannot use.
    allow_overflow: bool = True


@dataclass(slots=True)
class Config:
    scoring: ScoringConfig = field(default_factory=lambda: default_scoring())
    balance: BalanceConfig = field(default_factory=BalanceConfig)
    _path: Path = field(default=DEFAULT_CONFIG_PATH, repr=False)


# ---------------------------------------------------------------------------
# Built-in defaults — my profile (new grad, C#/.NET, Ankara, no Spanish)
# ---------------------------------------------------------------------------

DEFAULT_SKILLS: list[SkillWeight] = [
    SkillWeight("c#", 8.0, ["c sharp", "csharp"]),
    SkillWeight(".net", 8.0, ["dotnet", "asp.net", "aspnet", ".net core", "entity framework"]),
    SkillWeight("sql", 5.0, ["t-sql", "mssql", "sql server", "postgresql", "postgres", "mysql"]),
    SkillWeight("oop", 3.0, ["object oriented", "object-oriented"]),
    SkillWeight("typescript", 5.0),
    SkillWeight("react", 5.0, ["react.js", "reactjs"]),
    SkillWeight("python", 5.0, ["fastapi", "django", "flask"]),
    SkillWeight("sqlite", 2.0),
    SkillWeight("llm", 4.0, ["genai", "generative ai", "rag", "agentic", "ai agent"]),
    SkillWeight("javascript", 3.0, ["node.js", "nodejs"]),
    SkillWeight("rest", 2.0, ["rest api", "restful"]),
    SkillWeight("docker", 2.0),
    SkillWeight("azure", 3.0),
    SkillWeight("git", 1.0),
]

#: What counts as my line of work, in the languages my sources post in.
#: Kept to terms that name a *role*. Field names like "cloud", "platform",
#: "systems" or "development" were tried and pulled in "Cloud Billing
#: Associate" and "Business Development Representative" — a field is not a job.
DEFAULT_ROLE_TERMS: list[str] = [
    "software", "engineer", "engineering", "developer", "programmer",
    "backend", "back-end", "frontend", "front-end",
    "full stack", "fullstack", "full-stack",
    "sde", "swe", "devops", "sre", "data engineer", "ml engineer",
    "machine learning engineer", "ai engineer", "test engineer", "qa engineer",
    "web developer", "computer science",
    "yazılım", "geliştirici", "mühendis",
    "desarrollador", "programador", "ingeniero",
]

DEFAULT_LEVEL_WORDS: list[str] = [
    "junior", "jr.", "jr", "entry level", "entry-level", "graduate",
    "new grad", "new graduate", "recent graduate", "associate", "trainee",
    "intern", "internship", "becario", "becaria", "prácticas", "practicas",
    "early career", "stajyer", "işe yeni başlayan",
]

#: Ordered most senior first — the first tier whose word appears wins.
DEFAULT_SENIORITY_TIERS: list[SeniorityTier] = [
    SeniorityTier("executive", 45.0, [
        "head of", "director", "vp ", "vice president", "chief", "cto", "cio",
        "founding engineer", "general manager",
    ]),
    SeniorityTier("principal", 40.0, [
        "principal", "distinguished", "fellow", "architect", "staff engineer",
        "staff software", "staff data", "staff platform",
    ]),
    SeniorityTier("lead", 32.0, [
        "lead", "tech lead", "team lead", "technical lead", "manager",
        "engineering manager", "supervisor", "takım lideri",
    ]),
    SeniorityTier("senior", 25.0, [
        "senior", "sr.", "sr ", "expert", "specialist iii", "iii", "iv",
        "kıdemli",
    ]),
    SeniorityTier("mid", 8.0, [
        "mid-level", "mid level", "intermediate", "ii",
    ]),
]

#: I have no professional experience, so anything above a token requirement is
#: a real barrier. First band whose max_years covers the demand wins.
DEFAULT_EXPERIENCE_BANDS: list[ExperienceBand] = [
    ExperienceBand(1, 5.0, "entry-friendly"),
    ExperienceBand(2, 0.0, "reachable"),
    ExperienceBand(3, -8.0, "a stretch"),
    ExperienceBand(5, -18.0, "out of reach"),
    ExperienceBand(99, -30.0, "far out of reach"),
]

#: Whole professions I am not applying for, plus hard legal blockers. A match
#: sets the score to kill_score and hides the posting from the default view.
DEFAULT_KILL_WORDS: list[str] = [
    "account executive", "sales representative", "sales manager",
    "business development", "recruiter", "talent acquisition",
    "accountant", "bookkeeper", "physician", "nurse", "attorney",
    "paralegal", "truck driver", "warehouse", "barista", "chef",
    "security clearance", "top secret", "us citizenship required",
    "must be a us citizen", "polygraph",
]


def default_scoring() -> ScoringConfig:
    """A ScoringConfig pre-filled with my profile."""
    return ScoringConfig(
        skills=list(DEFAULT_SKILLS),
        role_terms=list(DEFAULT_ROLE_TERMS),
        level_words=list(DEFAULT_LEVEL_WORDS),
        seniority_tiers=list(DEFAULT_SENIORITY_TIERS),
        experience_bands=list(DEFAULT_EXPERIENCE_BANDS),
        kill_words=list(DEFAULT_KILL_WORDS),
    )


# ---------------------------------------------------------------------------
# Load / save
# ---------------------------------------------------------------------------


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> Config:
    """Load config.yaml, falling back to the built-in profile defaults."""
    path = Path(path)
    cfg = Config(_path=path)
    if not path.exists():
        return cfg

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return cfg

    cfg.scoring = _load_scoring(raw.get("scoring") or {})
    cfg.balance = _load_balance(raw.get("balance") or {})
    return cfg


def _load_scoring(raw: dict[str, Any]) -> ScoringConfig:
    sc = default_scoring()

    for key in (
        "base", "skill_max", "skill_title_multiplier", "level_bonus",
        "level_description_factor", "visa_bonus", "visa_penalty",
        "spanish_requirement_penalty", "english_working_bonus",
        "role_mismatch_penalty", "role_description_relief",
        "tr_relocation_penalty", "freshness_penalty_per_day",
        "freshness_max_penalty", "kill_score", "score_cap", "score_floor",
    ):
        if key in raw:
            setattr(sc, key, float(raw[key]))

    if "freshness_grace_days" in raw:
        sc.freshness_grace_days = int(raw["freshness_grace_days"])
    if "visa_eu_only" in raw:
        sc.visa_eu_only = bool(raw["visa_eu_only"])
    if "seniority_title_only" in raw:
        sc.seniority_title_only = bool(raw["seniority_title_only"])

    if isinstance(raw.get("freshness_factors"), dict):
        sc.freshness_factors = {
            str(k): float(v) for k, v in raw["freshness_factors"].items()
        }

    if raw.get("skills") is not None:
        sc.skills = [
            SkillWeight(
                name=str(entry.get("name", "")).lower(),
                points=float(entry.get("points", 5.0)),
                aliases=[str(a).lower() for a in entry.get("aliases") or []],
            )
            for entry in raw["skills"]
            if isinstance(entry, dict) and entry.get("name")
        ]

    if raw.get("role_terms") is not None:
        sc.role_terms = [str(w).lower() for w in raw["role_terms"]]

    if raw.get("level_words") is not None:
        sc.level_words = [str(w).lower() for w in raw["level_words"]]

    if raw.get("seniority_tiers") is not None:
        sc.seniority_tiers = [
            SeniorityTier(
                label=str(entry.get("label", "")),
                penalty=float(entry.get("penalty", 0.0)),
                words=[str(w).lower() for w in entry.get("words") or []],
            )
            for entry in raw["seniority_tiers"]
            if isinstance(entry, dict)
        ]

    if raw.get("experience_bands") is not None:
        sc.experience_bands = [
            ExperienceBand(
                max_years=int(entry.get("max_years", 99)),
                delta=float(entry.get("delta", 0.0)),
                label=str(entry.get("label", "")),
            )
            for entry in raw["experience_bands"]
            if isinstance(entry, dict)
        ]
        sc.experience_bands.sort(key=lambda b: b.max_years)

    if raw.get("tr_office_cities") is not None:
        sc.tr_office_cities = [str(c).lower() for c in raw["tr_office_cities"]]

    if raw.get("kill_words") is not None:
        sc.kill_words = [str(w).lower() for w in raw["kill_words"]]

    return sc


def _load_balance(raw: dict[str, Any]) -> BalanceConfig:
    bc = BalanceConfig()
    quotas = raw.get("quotas")
    if isinstance(quotas, dict):
        parsed = {str(k).upper(): float(v) for k, v in quotas.items()}
        # Accept both 0.50 and 50 — percentages are the more natural way to
        # write a quota by hand.
        if any(v > 1.0 for v in parsed.values()):
            total = sum(parsed.values()) or 1.0
            parsed = {k: v / total for k, v in parsed.items()}
        bc.quotas = parsed
    if "interleave" in raw:
        bc.interleave = bool(raw["interleave"])
    if "floor" in raw:
        bc.floor = int(raw["floor"])
    if "quota_min_score" in raw:
        bc.quota_min_score = float(raw["quota_min_score"])
    if "allow_overflow" in raw:
        bc.allow_overflow = bool(raw["allow_overflow"])
    return bc


def save_config(config: Config, path: Path | str | None = None) -> None:
    """Write the config back to disk."""
    target = Path(path) if path else config._path
    target.parent.mkdir(parents=True, exist_ok=True)

    sc, bc = config.scoring, config.balance
    payload = {
        "scoring": {
            "base": sc.base,
            "skills": [
                {"name": s.name, "points": s.points, "aliases": s.aliases}
                for s in sc.skills
            ],
            "skill_max": sc.skill_max,
            "skill_title_multiplier": sc.skill_title_multiplier,
            "role_terms": sc.role_terms,
            "role_mismatch_penalty": sc.role_mismatch_penalty,
            "role_description_relief": sc.role_description_relief,
            "level_words": sc.level_words,
            "level_bonus": sc.level_bonus,
            "level_description_factor": sc.level_description_factor,
            "seniority_tiers": [
                {"label": t.label, "penalty": t.penalty, "words": t.words}
                for t in sc.seniority_tiers
            ],
            "seniority_title_only": sc.seniority_title_only,
            "visa_bonus": sc.visa_bonus,
            "visa_penalty": sc.visa_penalty,
            "visa_eu_only": sc.visa_eu_only,
            "spanish_requirement_penalty": sc.spanish_requirement_penalty,
            "english_working_bonus": sc.english_working_bonus,
            "experience_bands": [
                {"max_years": b.max_years, "delta": b.delta, "label": b.label}
                for b in sc.experience_bands
            ],
            "tr_office_cities": sc.tr_office_cities,
            "tr_relocation_penalty": sc.tr_relocation_penalty,
            "freshness_grace_days": sc.freshness_grace_days,
            "freshness_penalty_per_day": sc.freshness_penalty_per_day,
            "freshness_max_penalty": sc.freshness_max_penalty,
            "freshness_factors": sc.freshness_factors,
            "kill_words": sc.kill_words,
            "kill_score": sc.kill_score,
            "score_cap": sc.score_cap,
            "score_floor": sc.score_floor,
        },
        "balance": {
            "quotas": bc.quotas,
            "quota_min_score": bc.quota_min_score,
            "interleave": bc.interleave,
            "floor": bc.floor,
            "allow_overflow": bc.allow_overflow,
        },
    }

    body = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=100)
    target.write_text(_CONFIG_HEADER + body, encoding="utf-8")


_CONFIG_HEADER = """\
# forkjob scoring & balance configuration.
#
# The score is additive and segment-blind — no region multiplier. The EU/TR
# split is a listing quota under `balance`, applied by `list`, not by scoring.
# Edit and re-run `sync`; scores are recomputed every run.

"""


def save_default_config(path: Path | str = DEFAULT_CONFIG_PATH) -> None:
    """Write a commented default config.yaml if none exists."""
    path = Path(path)
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    save_config(Config(_path=path), path)
