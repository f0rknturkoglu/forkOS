"""career-ops esinli, tamamen yerel fırsat istihbaratı.

Bu dosya ağ çağrısı yapmaz. İlan metni, ücret alanı ve forkOS'ta daha önce
toplanan fırsat/görüşme kayıtlarından deterministik sinyaller üretir.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import unicodedata
import uuid
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import touch_entity
from app.core.events import log_event
from app.core.models import Entity
from app.modules.document.models import Document
from app.modules.document.service import extract_local_document_text, get_local_file_path
from app.modules.opportunity import scoring
from app.modules.opportunity.models import Application, Interview, Opportunity
from app.modules.opportunity.schemas import (
    EvaluationGateOut,
    EvaluationMatchOut,
    EvaluationRequirementOut,
    OpportunityEvaluationOut,
    OpportunityEvaluationPatch,
    OpportunityIntelligenceOut,
    ReplyAnalysisOut,
    RiskSignalOut,
    SilentApplicationOut,
)
from app.modules.system.models import Setting
from app.sources import forkjob_port

REPOST_WINDOW_DAYS = 90
SILENCE_THRESHOLD_DAYS = 21
EVALUATION_VERSION = "career-ops-v1"

DEFAULT_CAREER_PROFILE: dict[str, Any] = {
    "current_location": "Ankara, Türkiye",
    "authorized_countries": ["Türkiye"],
    "willing_to_relocate": False,
}

ARCHETYPE_SIGNALS: dict[str, tuple[str, ...]] = {
    "fde": (
        "forward deployed",
        "customer-facing",
        "client-facing",
        "on-site with customers",
        "implementation engineer",
        "müşteri sahası",
    ),
    "sa": (
        "solutions architect",
        "solution architecture",
        "system design",
        "pre-sales",
        "technical architecture",
        "entegrasyon mimarisi",
    ),
    "pm": (
        "product manager",
        "product strategy",
        "product discovery",
        "roadmap",
        "product metrics",
        "ürün stratejisi",
    ),
    "llmops": (
        "llmops",
        "mlops",
        "model evaluation",
        "evaluation pipeline",
        "model monitoring",
        "model observability",
    ),
    "agentic": (
        "agentic",
        "multi-agent",
        "multi agent",
        "human-in-the-loop",
        "tool calling",
        "agent orchestration",
    ),
    "transformation": (
        "digital transformation",
        "change management",
        "operating model",
        "organizational change",
        "kurumsal dönüşüm",
        "değişim yönetimi",
    ),
}

# Ilan gereksinimi cikarmak icin profilden bagimsiz sozluk. Yalniz aday
# profilindeki teknolojileri aramak her satiri yanlis bicimde "strong" yapardi.
TECH_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "C#": ("c#", "c sharp", "csharp"),
    ".NET": (".net", "dotnet", "asp.net", "aspnet", ".net core"),
    "Python": ("python", "fastapi", "django", "flask"),
    "Java": ("java", "spring boot", "spring framework"),
    "Go": ("golang", "go language"),
    "JavaScript": ("javascript", "node.js", "nodejs"),
    "TypeScript": ("typescript",),
    "React": ("react", "react.js", "reactjs", "next.js", "nextjs"),
    "Vue": ("vue", "vue.js", "vuejs"),
    "Angular": ("angular",),
    "SQL": ("sql", "postgresql", "postgres", "mysql", "mssql", "sql server"),
    "NoSQL": ("mongodb", "dynamodb", "cassandra", "nosql"),
    "Redis": ("redis",),
    "Kafka": ("kafka",),
    "Docker": ("docker", "containerization", "containerisation"),
    "Kubernetes": ("kubernetes", "k8s"),
    "AWS": ("aws", "amazon web services"),
    "Azure": ("azure",),
    "GCP": ("gcp", "google cloud platform"),
    "Terraform": ("terraform", "infrastructure as code", "iac"),
    "CI/CD": ("ci/cd", "continuous integration", "continuous delivery"),
    "REST API": ("rest api", "restful"),
    "GraphQL": ("graphql",),
    "Git": ("git", "github", "gitlab"),
    "Linux": ("linux",),
    "Machine Learning": ("machine learning", "pytorch", "tensorflow", "scikit-learn"),
    "LLM / RAG": ("llm", "large language model", "rag", "retrieval augmented generation"),
    "Observability": ("observability", "opentelemetry", "prometheus", "grafana"),
    "System Design": ("system design", "distributed systems", "microservices", "architecture"),
}

RELATED_SKILLS: dict[str, set[str]] = {
    ".net": {"c#", "sql", "azure"},
    "c#": {".net", "sql", "azure"},
    "typescript": {"javascript", "react"},
    "javascript": {"typescript", "react", "vue", "angular"},
    "react": {"typescript", "javascript"},
    "kubernetes": {"docker", "terraform", "aws", "azure", "gcp"},
    "docker": {"kubernetes", "linux", "ci/cd"},
    "aws": {"terraform", "docker", "kubernetes"},
    "azure": {".net", "terraform", "docker", "kubernetes"},
    "gcp": {"terraform", "docker", "kubernetes"},
    "llm / rag": {"python", "machine learning"},
    "machine learning": {"python", "llm / rag"},
    "system design": {"rest api", "graphql", "kafka", "sql"},
}


def _ascii_words(value: str | None) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFKD", value or "")
    plain = "".join(char for char in normalized if not unicodedata.combining(char))
    return tuple(sorted(set(re.findall(r"[a-z0-9+#.]+", plain.casefold()))))


def title_identity(value: str | None) -> tuple[str, ...]:
    """Başlığı kelime kümesi kimliğine indirger; lokasyon kelimelerini korur."""

    return _ascii_words(value)


def organization_identity(value: str | None) -> tuple[str, ...]:
    ignored = {"a", "s", "as", "inc", "llc", "ltd", "limited", "gmbh", "corp", "company"}
    return tuple(word for word in _ascii_words(value) if word not in ignored)


def _parse_amount(raw: str, suffix: str) -> Decimal | None:
    value = raw.strip().replace(" ", "")
    try:
        if suffix:
            return Decimal(value.replace(",", ".")) * 1000
        separators = value.count(".") + value.count(",")
        if separators:
            last = max(value.rfind("."), value.rfind(","))
            decimals = len(value) - last - 1
            if decimals == 3 or separators > 1:
                value = value.replace(".", "").replace(",", "")
            else:
                value = value.replace(",", ".")
        return Decimal(value)
    except InvalidOperation:
        return None


def parse_compensation(value: str | None) -> tuple[int | None, int | None, str | None]:
    if not value:
        return None, None, None
    matches = re.findall(r"(?<![\w])([0-9]+(?:[.,][0-9]+)*)(?:\s*)([kK]?)(?![\w])", value)
    amounts = [_parse_amount(raw, suffix) for raw, suffix in matches]
    amounts = [amount for amount in amounts if amount is not None and amount >= 1000]
    if not amounts:
        return None, None, None
    currency = None
    lowered = value.casefold()
    if "€" in value or "eur" in lowered:
        currency = "EUR"
    elif "$" in value or "usd" in lowered:
        currency = "USD"
    elif "£" in value or "gbp" in lowered:
        currency = "GBP"
    elif "₺" in value or " tl" in f" {lowered}" or "try" in lowered:
        currency = "TRY"
    low = int(min(amounts))
    high = int(max(amounts))
    return low, high if len(amounts) > 1 else None, currency


def _description(opportunity: Opportunity) -> str:
    raw = opportunity.raw or {}
    forkjob = raw.get("forkjob") if isinstance(raw.get("forkjob"), dict) else {}
    return str(forkjob.get("description") or raw.get("description") or opportunity.notes or "")


def _contains(text: str, needles: Sequence[str]) -> bool:
    return any(needle in text for needle in needles)


def quick_signals(
    opportunity: Opportunity,
    *,
    title: str,
    repost_count: int = 0,
    connection_count: int = 0,
    now: datetime | None = None,
) -> OpportunityIntelligenceOut:
    now = now or datetime.now(UTC)
    description = _description(opportunity).casefold()
    title_text = title.casefold()
    remote_text = (opportunity.remote or "").casefold()
    pay_min, pay_max, currency = parse_compensation(opportunity.compensation)
    range_ratio = None
    if pay_min and pay_max and pay_max >= pay_min:
        range_ratio = round((pay_max - pay_min) / pay_min, 2)

    signals: list[RiskSignalOut] = []
    if repost_count >= 2:
        signals.append(
            RiskSignalOut(
                code="repost",
                label="Tekrar ilan",
                detail=f"Son {REPOST_WINDOW_DAYS} günde {repost_count} farklı ilan bağlantısı görüldü.",
                severity="warn",
            )
        )
    if range_ratio is not None and range_ratio > 0.5:
        signals.append(
            RiskSignalOut(
                code="wide_pay_range",
                label="Geniş ücret aralığı",
                detail="Üst ve alt sınır arasındaki fark taban ücretin %50'sini aşıyor.",
                severity="warn",
            )
        )
    if _contains(
        description,
        ("1099", "independent contractor", "b2b contract", "fatura kes", "şahıs şirket"),
    ):
        signals.append(
            RiskSignalOut(
                code="contractor_misclassification",
                label="Taşeronluk koşulu",
                detail="İlan metni faturalandırma veya bağımsız yüklenici koşulu içeriyor.",
                severity="danger",
            )
        )
    if _contains(
        description,
        (
            "ai video interview",
            "automated screening",
            "algorithmic screening",
            "yapay zeka mülakat",
        ),
    ):
        signals.append(
            RiskSignalOut(
                code="ai_screening",
                label="Otomatik eleme bildirimi",
                detail="İlan, AI veya algoritmik aday eleme aracı kullanıldığını belirtiyor.",
                severity="neutral",
            )
        )
    claims_remote = _contains(f"{title_text} {remote_text}", ("remote", "uzaktan", "wfh"))
    requires_office = _contains(
        description,
        (
            "days per week in the office",
            "days a week in the office",
            "haftada 2 gün ofis",
            "haftada 3 gün ofis",
            "on-site required",
        ),
    )
    geo_mismatch = claims_remote and requires_office
    if geo_mismatch:
        signals.append(
            RiskSignalOut(
                code="geo_mismatch",
                label="Konum uyuşmazlığı",
                detail="Başlık uzaktan çalışmayı vaat ederken açıklama ofis zorunluluğu içeriyor.",
                severity="danger",
            )
        )
    no_sponsorship = _contains(
        description,
        (
            "no visa sponsorship",
            "visa sponsorship is not available",
            "cannot sponsor",
            "sponsorluk sağlanmayacaktır",
        ),
    )
    if no_sponsorship:
        signals.append(
            RiskSignalOut(
                code="no_sponsorship",
                label="Vize sponsorluğu yok",
                detail="İlan, çalışma vizesi sponsorluğu sunulmadığını açıkça belirtiyor.",
                severity="danger",
            )
        )
    effective_date = opportunity.published_at or opportunity.found_at
    if effective_date and (now - effective_date).days > REPOST_WINDOW_DAYS:
        signals.append(
            RiskSignalOut(
                code="stale",
                label="Eski ilan",
                detail=f"İlanın görünen tarihi {(now - effective_date).days} gün önce.",
                severity="warn",
            )
        )
    if connection_count > 0:
        signals.append(
            RiskSignalOut(
                code="connection",
                label="Bağlantı var",
                detail=f"Bu kurumda {connection_count} yerel LinkedIn bağlantınız var.",
                severity="neutral",
            )
        )
    return OpportunityIntelligenceOut(
        repost_count=repost_count,
        is_repost=repost_count >= 2,
        connection_count=connection_count,
        pay_min=pay_min,
        pay_max=pay_max,
        pay_currency=currency,
        pay_range_ratio=range_ratio,
        pay_transparency_risk=range_ratio is not None and range_ratio > 0.5,
        geo_mismatch=geo_mismatch,
        sponsorship_status="no_sponsorship" if no_sponsorship else "unstated",
        signals=signals,
    )


def _mentions_term(text: str, term: str) -> bool:
    normalized = " ".join(text.casefold().split())
    needle = " ".join(term.casefold().split())
    if not needle:
        return False
    if needle[0].isalnum() and needle[-1].isalnum():
        return re.search(rf"(?<![\w]){re.escape(needle)}(?![\w])", normalized) is not None
    return needle in normalized


def _description_sentences(value: str) -> list[str]:
    plain = re.sub(r"<[^>]+>", " ", value)
    plain = re.sub(r"[\t\r]+", " ", plain)
    chunks = re.split(r"[\n•]+|(?<=[.!?])\s+", plain)
    result: list[str] = []
    for chunk in chunks:
        compact = " ".join(chunk.strip(" -*\u2022").split())
        if 12 <= len(compact) <= 1200:
            result.append(compact)
    return result


def _requirement_level(statement: str, *, structural: bool) -> tuple[str, str]:
    lowered = statement.casefold()
    preferred_markers = (
        "preferred",
        "nice to have",
        "bonus",
        "plus",
        "tercihen",
        "tercih sebebi",
    )
    critical_markers = (
        "must have",
        "must be",
        "required",
        "mandatory",
        "minimum requirement",
        "zorunlu",
        "gereklidir",
        "şarttır",
    )
    high_markers = (
        "strong experience",
        "proven experience",
        "expertise",
        "deep knowledge",
        "solid understanding",
        "hands-on experience",
        "ileri düzey",
        "deneyimli",
    )
    stated_markers = (
        critical_markers
        + high_markers
        + preferred_markers
        + (
            "experience with",
            "experience in",
            "proficiency",
            "knowledge of",
            "familiarity with",
            "you have",
            "we are looking for",
            "deneyim",
            "bilgi sahibi",
        )
    )

    evidence = (
        "structural"
        if structural
        else "stated"
        if _contains(lowered, stated_markers)
        else "inferred"
    )
    if _contains(lowered, preferred_markers):
        importance = "preferred"
    elif evidence != "inferred" and _contains(lowered, critical_markers):
        importance = "critical"
    elif evidence != "inferred" and _contains(lowered, high_markers) or structural:
        importance = "high"
    elif evidence == "inferred":
        importance = "low_signal"
    else:
        importance = "meaningful"
    return importance, evidence


def _requirement_id(name: str) -> str:
    digest = hashlib.sha1(name.casefold().encode("utf-8"), usedforsecurity=False).hexdigest()[:10]
    return f"req-{digest}"


def extract_requirements(title: str, description: str) -> list[EvaluationRequirementOut]:
    """Pass 1: aday profilini gormeden yalnizca ilandan gereksinim cikar."""

    sentences = _description_sentences(description)
    requirements: list[EvaluationRequirementOut] = []
    seen: set[str] = set()

    for name, aliases in TECH_REQUIREMENTS.items():
        title_hit = next((term for term in aliases if _mentions_term(title, term)), None)
        statement = (
            title
            if title_hit
            else next(
                (
                    sentence
                    for sentence in sentences
                    if any(_mentions_term(sentence, term) for term in aliases)
                ),
                None,
            )
        )
        if not statement:
            continue
        importance, evidence = _requirement_level(statement, structural=bool(title_hit))
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        requirements.append(
            EvaluationRequirementOut(
                id=_requirement_id(name),
                name=name,
                importance=importance,
                evidence=evidence,
                excerpt=statement[:500],
                terms=[name, *aliases],
            )
        )

    generic_patterns: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("Deneyim süresi", (r"\b\d+\+?\s*(?:years?|yrs?|yıl)\b",)),
        ("Lisans derecesi", (r"\b(?:bachelor'?s?|bsc|degree in|lisans)\b",)),
        ("İngilizce", (r"\b(?:fluent|professional|business)\s+english\b", r"\bingilizce\b")),
        ("Müşteri iletişimi", (r"\b(?:customer|client)[ -]facing\b", r"müşteri\s+iletiş")),
        (
            "Teknik liderlik",
            (r"\btechnical leadership\b", r"\bleadership experience\b", r"teknik lider"),
        ),
    )
    for name, patterns in generic_patterns:
        statement = next(
            (
                sentence
                for sentence in sentences
                if any(re.search(p, sentence, re.I) for p in patterns)
            ),
            None,
        )
        if not statement or name.casefold() in seen:
            continue
        importance, evidence = _requirement_level(statement, structural=False)
        seen.add(name.casefold())
        requirements.append(
            EvaluationRequirementOut(
                id=_requirement_id(name),
                name=name,
                importance=importance,
                evidence=evidence,
                excerpt=statement[:500],
                terms=[name],
            )
        )

    if not requirements:
        requirements.append(
            EvaluationRequirementOut(
                id=_requirement_id(f"Rol odağı: {title}"),
                name=f"Rol odağı: {title}"[:240],
                importance="meaningful",
                evidence="structural",
                excerpt=title[:500],
                terms=[],
            )
        )
    return requirements[:16]


def detect_archetype(title: str, description: str) -> tuple[str | None, dict[str, int]]:
    title_text = title.casefold()
    description_text = description.casefold()
    scores: dict[str, int] = {}
    for archetype, phrases in ARCHETYPE_SIGNALS.items():
        score = sum(3 for phrase in phrases if phrase in title_text)
        score += sum(1 for phrase in phrases if phrase in description_text)
        scores[archetype] = score
    winner = max(scores, key=scores.get)
    return (winner if scores[winner] > 0 else None), scores


def _configured_profile_skills() -> tuple[set[str], set[str]]:
    canonical: set[str] = set()
    terms: set[str] = set()
    for skill in forkjob_port.SCORING.scoring.skills:
        normalized_name = skill.name.casefold().strip()
        if normalized_name:
            canonical.add(normalized_name)
        terms.update(term.casefold().strip() for term in skill.terms if term.strip())
    return canonical, terms


def _candidate_text_has_skill(candidate_text: str, requirement: EvaluationRequirementOut) -> bool:
    terms = [requirement.name, *requirement.terms]
    return any(_mentions_term(candidate_text, term) for term in terms if term.strip())


def match_requirements(
    requirements: Sequence[EvaluationRequirementOut],
    *,
    candidate_text: str | None = None,
    candidate_document_title: str | None = None,
) -> list[EvaluationMatchOut]:
    """Pass 2: Pass 1 sabitlendikten sonra yerel aday profiliyle eslestir."""

    profile_canonical, profile_terms = _configured_profile_skills()
    candidate_text = candidate_text or ""
    matches: list[EvaluationMatchOut] = []
    for requirement in requirements:
        requirement_terms = {term.casefold().strip() for term in requirement.terms if term.strip()}
        canonical = requirement.name.casefold().strip()
        if candidate_text and _candidate_text_has_skill(candidate_text, requirement):
            match = "strong"
            evidence = f"{candidate_document_title or 'Aday belgesi'} içinde doğrudan doğrulanabilir bir eşleşme var."
            mitigation = None
        elif requirement_terms & profile_terms or canonical in profile_canonical:
            match = "strong"
            evidence = "Yetenek, yerel uyum profilinde doğrudan tanımlı."
            mitigation = None
        elif related := RELATED_SKILLS.get(canonical, set()) & profile_canonical:
            match = "partial"
            evidence = f"Profilde ilişkili deneyim var: {', '.join(sorted(related))}."
            mitigation = (
                f"{requirement.name} ile bağlantıyı somut bir proje ve çıktıyla CV'de görünür kıl."
            )
        elif requirement.name.startswith("Rol odağı:"):
            match = "partial"
            evidence = "Rol başlığı mevcut uyum profiliyle otomatik olarak doğrulanamadı."
            mitigation = "Rol odağıyla en yakın iki projenin sorumluluk ve sonuçlarını öne çıkar."
        else:
            match = "missing"
            evidence = "Yerel uyum profilinde doğrulanabilir bir kanıt bulunamadı."
            if requirement.importance in {"critical", "high"}:
                mitigation = f"Başvurmadan önce {requirement.name} deneyimini doğrula; yoksa bunu açık bir gap olarak ele al."
            else:
                mitigation = (
                    f"{requirement.name} için benzer deneyimini veya hızlı öğrenme planını belirt."
                )
        matches.append(
            EvaluationMatchOut(
                requirement_id=requirement.id,
                requirement=requirement.name,
                match=match,
                evidence=evidence,
                gap_mitigation=mitigation,
            )
        )
    return matches


COUNTRY_ALIASES: dict[str, tuple[str, ...]] = {
    "Türkiye": ("tr", "turkey", "türkiye", "istanbul", "ankara", "izmir"),
    "Germany": ("de", "germany", "deutschland", "berlin", "munich", "münchen", "hamburg"),
    "United Kingdom": ("uk", "united kingdom", "great britain", "london", "england"),
    "Spain": ("es", "spain", "españa", "madrid", "barcelona"),
    "France": ("fr", "france", "paris"),
    "Netherlands": ("nl", "netherlands", "holland", "amsterdam"),
    "United States": ("us", "usa", "united states", "america"),
    "Canada": ("ca", "canada"),
    "Portugal": ("pt", "portugal", "lisbon", "lisboa"),
    "Sweden": ("se", "sweden", "sverige", "stockholm"),
}


def _country_name(value: str | None) -> str | None:
    normalized = " ".join((value or "").casefold().replace(",", " ").split())
    if not normalized:
        return None
    for country, aliases in COUNTRY_ALIASES.items():
        if normalized == country.casefold() or any(
            _mentions_term(normalized, alias) for alias in aliases
        ):
            return country
    return value.strip() if value and len(value.strip()) > 2 else None


def _sponsorship_status(description: str, authorized: bool | None) -> str:
    lowered = description.casefold()
    if authorized is True:
        return "not_needed"
    if _contains(
        lowered,
        (
            "visa sponsorship available",
            "we sponsor visas",
            "sponsorship provided",
            "relocation and visa support",
            "vize sponsorluğu sağlanır",
        ),
    ):
        return "sponsors"
    if _contains(
        lowered,
        (
            "no visa sponsorship",
            "visa sponsorship is not available",
            "cannot sponsor",
            "must be authorized to work",
            "without sponsorship",
            "sponsorluk sağlanmayacaktır",
        ),
    ):
        return "no_sponsorship"
    return "unstated"


def evaluate_gate(opportunity: Opportunity, profile: dict[str, Any]) -> EvaluationGateOut:
    description = _description(opportunity)
    job_country = _country_name(opportunity.country) or _country_name(opportunity.location)
    authorized_countries = {
        country
        for value in profile.get("authorized_countries", [])
        if isinstance(value, str) and (country := _country_name(value))
    }
    authorized = job_country in authorized_countries if job_country else None
    sponsorship = _sponsorship_status(description, authorized)

    claims_remote = _contains(
        f"{opportunity.remote or ''} {description[:300]}".casefold(),
        ("remote", "uzaktan", "work from home"),
    )
    office_required = _contains(
        description.casefold(),
        (
            "days per week in the office",
            "days a week in the office",
            "on-site required",
            "onsite required",
            "haftada 2 gün ofis",
            "haftada 3 gün ofis",
        ),
    )
    residence_locked = _contains(
        description.casefold(),
        (
            "must reside in",
            "must be based in",
            "remote within",
            "must live in",
            "ikamet etmesi gerekir",
        ),
    )
    geo_mismatch = claims_remote and (office_required or residence_locked)
    willing_to_relocate = bool(profile.get("willing_to_relocate", False))
    hard_blocker = authorized is False and sponsorship == "no_sponsorship"
    if residence_locked and authorized is False and not willing_to_relocate:
        hard_blocker = True

    reasons: list[str] = []
    if geo_mismatch:
        reasons.append("Uzaktan çalışma ifadesi ofis veya ikamet zorunluluğuyla çelişiyor.")
    if authorized is False and sponsorship == "no_sponsorship":
        reasons.append(
            f"{job_country or 'Bu konum'} için çalışma izni yok ve ilan sponsorluk sunmuyor."
        )
    elif authorized is False and sponsorship == "unstated":
        reasons.append(f"{job_country or 'Bu konum'} için sponsorluk durumu netleştirilmeli.")
    return EvaluationGateOut(
        job_country=job_country,
        authorized_to_work=authorized,
        sponsorship_status=sponsorship,
        geo_mismatch=geo_mismatch,
        hard_blocker=hard_blocker,
        reasons=reasons,
    )


IMPORTANCE_WEIGHTS = {"critical": 5, "high": 4, "meaningful": 3, "preferred": 2, "low_signal": 1}
MATCH_FACTORS = {"strong": 1.0, "partial": 0.5, "missing": 0.0}


def _evaluation_score(
    requirements: Sequence[EvaluationRequirementOut],
    matches: Sequence[EvaluationMatchOut],
    gate: EvaluationGateOut,
) -> tuple[int, str]:
    matches_by_id = {item.requirement_id: item for item in matches}
    total = sum(IMPORTANCE_WEIGHTS[item.importance] for item in requirements)
    earned = sum(
        IMPORTANCE_WEIGHTS[item.importance] * MATCH_FACTORS[matches_by_id[item.id].match]
        for item in requirements
        if item.id in matches_by_id
    )
    score = round((earned / total) * 100) if total else 0
    if gate.hard_blocker:
        score = min(score, 25)
        recommendation = "skip"
    elif score >= 75:
        recommendation = "pursue"
    elif score >= 50:
        recommendation = "consider"
    else:
        recommendation = "skip"
    return score, recommendation


def listing_fingerprint(opportunity: Opportunity, *, title: str) -> str:
    """ILAN tarafinin parmak izi (profil ve CV haric).

    Kucuk ve ucuzdur: liste yanitinda her ilan icin PDF metni cikarmak mumkun
    olmadigi icin bayatlama kontrolu bu iki parcaya ayrilir.
    """
    payload = {
        "title": title,
        "description": _description(opportunity),
        "location": opportunity.location,
        "country": opportunity.country,
        "remote": opportunity.remote,
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]


def profile_fingerprint(profile: dict[str, Any]) -> str:
    """Profil + beceri kurallarinin parmak izi: ikisi degisince skor bayatlar."""
    payload = {"profile": profile, "skills": sorted(_configured_profile_skills()[0])}
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]


#: Bayatlama nedenleri. Arayuz bunlari Turkce metne cevirir.
EVALUATION_STALE_REASONS = (
    scoring.STALE_VERSION,
    scoring.STALE_LISTING,
    scoring.STALE_PROFILE,
    scoring.STALE_MISSING,
)


def evaluation_staleness(
    opportunity: Opportunity, *, title: str, profile: dict[str, Any]
) -> str | None:
    """Kayitli degerlendirme bayat mi? Guncelse ``None``.

    Eski skoru guncel gibi sunmamak icin kayitli parmak izleri YENIDEN
    hesaplananlarla karsilastirilir; eski surumle ya da parmak izi hic
    yazilmadan uretilmis degerlendirmeler "missing" sayilir (yeniden hesapla).
    """
    evaluation = opportunity.evaluation or {}
    if not evaluation:
        return None
    if evaluation.get("version") != EVALUATION_VERSION:
        return scoring.STALE_VERSION
    stored_listing = evaluation.get("listing_fingerprint")
    stored_profile = evaluation.get("profile_fingerprint")
    if not stored_listing or not stored_profile:
        return scoring.STALE_MISSING
    if stored_listing != listing_fingerprint(opportunity, title=title):
        return scoring.STALE_LISTING
    if stored_profile != profile_fingerprint(profile):
        return scoring.STALE_PROFILE
    return None


def _evaluation_fingerprint(
    opportunity: Opportunity,
    *,
    title: str,
    profile: dict[str, Any],
    candidate_document_id: uuid.UUID | None = None,
    candidate_text: str | None = None,
) -> str:
    payload = {
        "title": title,
        "description": _description(opportunity),
        "location": opportunity.location,
        "country": opportunity.country,
        "remote": opportunity.remote,
        "profile": profile,
        "skills": sorted(_configured_profile_skills()[0]),
        "candidate_document_id": str(candidate_document_id) if candidate_document_id else None,
        "candidate_text_hash": hashlib.sha256((candidate_text or "").encode("utf-8")).hexdigest()[
            :16
        ],
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]


def build_evaluation(
    opportunity: Opportunity,
    *,
    title: str,
    profile: dict[str, Any] | None = None,
    candidate_document_id: uuid.UUID | None = None,
    candidate_document_title: str | None = None,
    candidate_text: str | None = None,
    now: datetime | None = None,
) -> OpportunityEvaluationOut:
    profile = {**DEFAULT_CAREER_PROFILE, **(profile or {})}
    now = now or datetime.now(UTC)
    description = _description(opportunity)
    requirements = extract_requirements(title, description)
    matches = match_requirements(
        requirements,
        candidate_text=candidate_text,
        candidate_document_title=candidate_document_title,
    )
    archetype, archetype_scores = detect_archetype(title, description)
    gate = evaluate_gate(opportunity, profile)
    score, recommendation = _evaluation_score(requirements, matches, gate)
    notes = None
    if len(description.strip()) < 50:
        notes = "İlan metni çok kısa veya kazınamamış (50 karakterden az). Değerlendirme doğruluğu için ilan metnini düzenleyip açıklamayı ekleyin."
    return OpportunityEvaluationOut(
        version=EVALUATION_VERSION,
        evaluated_at=now,
        listing_fingerprint=listing_fingerprint(opportunity, title=title),
        profile_fingerprint=profile_fingerprint(profile),
        source_fingerprint=_evaluation_fingerprint(
            opportunity,
            title=title,
            profile=profile,
            candidate_document_id=candidate_document_id,
            candidate_text=candidate_text,
        ),
        candidate_source="document" if candidate_text else "profile",
        candidate_document_id=candidate_document_id if candidate_text else None,
        candidate_document_title=candidate_document_title if candidate_text else None,
        archetype=archetype,
        archetype_scores=archetype_scores,
        score=score,
        recommendation=recommendation,
        requirements=requirements,
        matches=matches,
        gate=gate,
        notes=notes,
    )


async def _career_profile(session: AsyncSession) -> dict[str, Any]:
    setting = await session.get(Setting, "opportunity.career_profile")
    if setting is None or not isinstance(setting.value, dict):
        return dict(DEFAULT_CAREER_PROFILE)
    return {**DEFAULT_CAREER_PROFILE, **setting.value}


async def _candidate_document(
    session: AsyncSession,
    item_id: uuid.UUID,
) -> tuple[uuid.UUID | None, str | None, str | None]:
    """Başvuruya bağlı CV'yi, yoksa en güncel yerel CV'yi kanıt kaynağı yap."""

    application = await session.get(Application, item_id)
    preferred_id = application.cv_document_id if application else None
    stmt = (
        select(Document, Entity.title)
        .join(Entity, Entity.id == Document.id)
        .where(
            Entity.archived_at.is_(None),
            func.lower(func.coalesce(Document.category, "")).in_(
                ("cv", "resume", "özgeçmiş", "ozgecmis")
            ),
        )
        .order_by(Document.drive_modified_at.desc().nulls_last(), Document.synced_at.desc())
    )
    rows = list((await session.execute(stmt)).all())
    if preferred_id:
        rows.sort(key=lambda row: row[0].id != preferred_id)

    for document, title in rows:
        path = get_local_file_path(document.id, title)
        if path is None:
            continue
        text = await asyncio.to_thread(
            extract_local_document_text,
            path,
            mime=document.mime,
        )
        if text:
            return document.id, title, text
    return None, None, None


async def evaluate_opportunity(
    session: AsyncSession,
    item_id: uuid.UUID,
) -> OpportunityEvaluationOut | None:
    row = (
        await session.execute(
            select(Opportunity, Entity.title)
            .join(Entity, Entity.id == Opportunity.id)
            .where(Opportunity.id == item_id)
        )
    ).first()
    if row is None:
        return None
    opportunity, title = row
    candidate_document_id, candidate_document_title, candidate_text = await _candidate_document(
        session, item_id
    )
    evaluation = build_evaluation(
        opportunity,
        title=title,
        profile=await _career_profile(session),
        candidate_document_id=candidate_document_id,
        candidate_document_title=candidate_document_title,
        candidate_text=candidate_text,
    )
    if opportunity.evaluation:
        try:
            previous = OpportunityEvaluationOut.model_validate(opportunity.evaluation)
        except ValueError:
            previous = None
        if previous is not None:
            story_ids_by_requirement = {
                match.requirement_id: match.story_ids
                for match in previous.matches
                if match.story_ids
            }
            evaluation.notes = previous.notes
            for match in evaluation.matches:
                match.story_ids = story_ids_by_requirement.get(match.requirement_id, [])
    opportunity.evaluation = evaluation.model_dump(mode="json")
    opportunity.evaluated_at = evaluation.evaluated_at
    await touch_entity(session, opportunity.id)
    await log_event(
        session,
        verb="opportunity.evaluated",
        entity_id=opportunity.id,
        entity_type="opportunity",
        payload={
            "version": evaluation.version,
            "score": evaluation.score,
            "recommendation": evaluation.recommendation,
            "hard_blocker": evaluation.gate.hard_blocker,
        },
    )
    await session.commit()
    return evaluation


async def update_evaluation(
    session: AsyncSession,
    item_id: uuid.UUID,
    patch: OpportunityEvaluationPatch,
) -> OpportunityEvaluationOut | None:
    opportunity = await session.get(Opportunity, item_id)
    if opportunity is None:
        return None
    if not opportunity.evaluation:
        return None
    current = OpportunityEvaluationOut.model_validate(opportunity.evaluation)
    payload = current.model_dump(mode="python")
    payload.update(patch.model_dump(exclude_unset=True))
    payload["evaluated_at"] = datetime.now(UTC)
    requirements = [
        EvaluationRequirementOut.model_validate(item) for item in payload["requirements"]
    ]
    matches = [EvaluationMatchOut.model_validate(item) for item in payload["matches"]]
    gate = EvaluationGateOut.model_validate(payload["gate"])
    payload["requirements"] = requirements
    payload["matches"] = matches
    payload["gate"] = gate
    score, recommendation = _evaluation_score(requirements, matches, gate)
    payload["score"] = score
    payload["recommendation"] = recommendation
    evaluation = OpportunityEvaluationOut.model_validate(payload)
    opportunity.evaluation = evaluation.model_dump(mode="json")
    opportunity.evaluated_at = evaluation.evaluated_at
    await touch_entity(session, opportunity.id)
    await log_event(
        session,
        verb="opportunity.evaluation_updated",
        entity_id=opportunity.id,
        entity_type="opportunity",
        payload={"score": evaluation.score, "recommendation": evaluation.recommendation},
    )
    await session.commit()
    return evaluation


def repost_counts(
    current: Sequence[tuple[Opportunity, str]],
    candidates: Sequence[tuple[Opportunity, str]],
) -> dict[uuid.UUID, int]:
    clusters: dict[tuple[tuple[str, ...], tuple[str, ...]], list[Opportunity]] = defaultdict(list)
    for opportunity, title in candidates:
        key = (organization_identity(opportunity.organization), title_identity(title))
        if key[0] and key[1]:
            clusters[key].append(opportunity)
    result: dict[uuid.UUID, int] = {}
    for opportunity, title in current:
        key = (organization_identity(opportunity.organization), title_identity(title))
        rows = clusters.get(key, [])
        urls = {row.url for row in rows if row.url}
        days = {
            (row.found_at or row.published_at).date()
            for row in rows
            if row.found_at or row.published_at
        }
        result[opportunity.id] = len(urls) if len(urls) >= 2 and len(days) >= 2 else 0
    return result


async def enrich_opportunities(
    session: AsyncSession,
    rows: Sequence[tuple[Opportunity, str]],
    outputs,
):
    if not rows:
        return list(outputs)
    organizations = {row[0].organization for row in rows if row[0].organization}
    candidates = list(rows)
    if organizations:
        cutoff = datetime.now(UTC) - timedelta(days=REPOST_WINDOW_DAYS)
        candidates = list(
            (
                await session.execute(
                    select(Opportunity, Entity.title)
                    .join(Entity, Entity.id == Opportunity.id)
                    .where(
                        Opportunity.organization.in_(organizations), Opportunity.found_at >= cutoff
                    )
                )
            ).all()
        )
    counts = repost_counts(rows, candidates)
    connection_counts: dict[uuid.UUID, int] = {}
    if organizations:
        from app.modules.opportunity.career import _company_matches, normalize_company
        from app.modules.opportunity.models import CareerConnection

        normalized_orgs = {normalize_company(org): org for org in organizations if org}
        connections = (
            await session.execute(
                select(CareerConnection.normalized_company)
                .join(Entity, Entity.id == CareerConnection.id)
                .where(
                    Entity.archived_at.is_(None),
                    CareerConnection.normalized_company.is_not(None),
                )
            )
        ).scalars().all()
        org_conn_counts: dict[str, int] = defaultdict(int)
        for conn_norm in connections:
            for norm_org in normalized_orgs:
                if _company_matches(norm_org, conn_norm or ""):
                    org_conn_counts[norm_org] += 1
        for opportunity, _ in rows:
            norm = normalize_company(opportunity.organization)
            connection_counts[opportunity.id] = org_conn_counts.get(norm, 0)

    # Profil tek kez okunur; bayatlama kontrolu ilan basina yeniden hesaplanir.
    profile = await _career_profile(session)
    return [
        output.model_copy(
            update={
                "intelligence": quick_signals(
                    opportunity,
                    title=title,
                    repost_count=counts.get(opportunity.id, 0),
                    connection_count=connection_counts.get(opportunity.id, 0),
                ),
                "evaluation_stale_reason": evaluation_staleness(
                    opportunity, title=title, profile=profile
                ),
            }
        )
        for (opportunity, title), output in zip(rows, outputs, strict=True)
    ]


def classify_reply(text: str) -> ReplyAnalysisOut:
    normalized = " ".join(text.casefold().split())
    rules = (
        (
            "interview_invite",
            "Mülakat daveti",
            "interview",
            None,
            (
                "interview",
                "mülakat",
                "görüşme",
                "takvim",
                "calendar",
                "availability",
                "uygun olduğunuz",
            ),
        ),
        (
            "rejection",
            "Olumsuz yanıt",
            "rejected",
            None,
            (
                "unfortunately",
                "regret to inform",
                "başka aday",
                "olumsuz",
                "ilerleyemeyeceğiz",
                "not moving forward",
            ),
        ),
        (
            "take_home_assessment",
            "Teknik ödev",
            None,
            "Teknik ödevi tamamla",
            (
                "take-home",
                "take home",
                "case study",
                "technical assessment",
                "coding challenge",
                "teknik ödev",
                "vaka çalışması",
            ),
        ),
        (
            "auto_acknowledgement",
            "Başvuru teyidi",
            "applied",
            None,
            (
                "application received",
                "başvurunuz alınmıştır",
                "başvurunuzu aldık",
                "thank you for applying",
                "başvurunuz bize ulaştı",
            ),
        ),
    )
    ranked = []
    for kind, label, status, todo, needles in rules:
        evidence = [needle for needle in needles if needle in normalized]
        ranked.append((len(evidence), kind, label, status, todo, evidence))
    score, kind, label, status, todo, evidence = max(ranked, key=lambda row: row[0])
    if score == 0:
        return ReplyAnalysisOut(
            kind="unknown",
            label="Belirsiz yanıt",
            confidence=0.0,
            evidence=[],
            suggested_status=None,
            suggested_todo_title=None,
            summary="Metinde güvenilir bir başvuru sonucu sinyali bulunamadı.",
        )
    confidence = min(0.98, 0.58 + (score - 1) * 0.16)
    return ReplyAnalysisOut(
        kind=kind,
        label=label,
        confidence=round(confidence, 2),
        evidence=evidence[:4],
        suggested_status=status,
        suggested_todo_title=todo,
        summary={
            "interview_invite": "İşveren bir görüşme planlamak istiyor.",
            "rejection": "İşveren başvuruyla ilerlemeyeceğini bildiriyor.",
            "take_home_assessment": "Yanıt bir teknik ödev veya değerlendirme içeriyor.",
            "auto_acknowledgement": "İşveren başvurunun ulaştığını teyit ediyor.",
        }[kind],
    )


async def list_silent_applications(
    session: AsyncSession,
    *,
    days: int = SILENCE_THRESHOLD_DAYS,
) -> list[SilentApplicationOut]:
    now = datetime.now(UTC)
    last_interview = func.max(Interview.scheduled_at)
    rows = (
        await session.execute(
            select(
                Opportunity.id,
                Entity.title,
                Opportunity.organization,
                Application.status,
                last_interview,
            )
            .join(Entity, Entity.id == Opportunity.id)
            .join(Application, Application.opportunity_id == Opportunity.id)
            .join(Interview, Interview.opportunity_id == Opportunity.id)
            .where(
                # Sessizlik radarı yalnızca gerçek başvurular için; keşif durumu değil.
                Application.status == "interview",
                Opportunity.trashed_at.is_(None),
                Interview.scheduled_at.is_not(None),
                Interview.scheduled_at <= now - timedelta(days=days),
            )
            .group_by(
                Opportunity.id,
                Entity.title,
                Opportunity.organization,
                Application.status,
            )
            .order_by(last_interview)
        )
    ).all()
    return [
        SilentApplicationOut(
            id=item_id,
            title=title,
            organization=organization,
            status=status,
            last_interview_at=interview_at,
            days_silent=max(0, (now - interview_at).days),
        )
        for item_id, title, organization, status, interview_at in rows
    ]
