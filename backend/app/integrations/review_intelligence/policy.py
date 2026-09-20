"""H5 politikası — SAF ve deterministik.

Kararlar burada tek yerde toplanır: mod/argüman kuralları, dikkat sıralaması,
terfi varış yeri eşlemesi, aday kimliği ve eşikler. Model çağrısı, ağ ve
veritabanı YOKTUR; böylece politika testlerle doğrudan ölçülebilir.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Literal

from app.integrations.review_intelligence.models import (
    ACTIVE_MODES,
    AttentionReason,
    CandidateKind,
    PromotionDestination,
    ReviewIntelligenceError,
    ReviewMode,
)

#: Mod → izin verilen genel argümanlar (§21). Verilmeyen argüman sessizce
#: yok sayılmaz: uyumsuzluk `INVALID_ARGUMENT` olur.
MODE_ALLOWED_ARGS: dict[str, frozenset[str]] = {
    "continuity": frozenset({"since", "until", "focus_entity_id", "include_knowledge"}),
    "daily_close": frozenset({"reference_date", "include_knowledge"}),
    "weekly_review": frozenset({"reference_date", "include_knowledge"}),
    # period_delta bilgi alanı TAŞIMAZ: bayrak sessizce yok sayılmaz, reddedilir.
    "period_delta": frozenset({"since", "until", "focus_entity_id"}),
    "consolidation_review": frozenset({"since", "until", "focus_entity_id", "include_knowledge"}),
}

#: `since` ZORUNLU modlar (§21).
MODES_REQUIRING_SINCE: frozenset[str] = frozenset({"period_delta"})

#: Terfi varış yeri politikası (§60). Öneridir; H5 buraya YAZMAZ.
DESTINATION_BY_KIND: dict[str, PromotionDestination] = {
    "commitment": "todo",
    "goal": "hot_memory",
    "constraint": "hot_memory",
    "decision": "general_vault",
    "lesson": "general_vault",
    "reference": "general_vault",
    "project_knowledge": "general_vault",
}

#: Entity kapsamı KANITLANMIŞSA (tam olarak bir entity'ye bağlıysa) tercih
#: edilen varış yeri (§60).
ENTITY_SCOPED_DESTINATIONS: dict[str, PromotionDestination] = {
    "decision": "project_vault",
    "project_knowledge": "project_vault",
    "lesson": "project_vault",
    "reference": "project_vault",
}

#: Dikkat sıralaması (§38): küçük sayı önce gelir. Opak puan YOKTUR.
ATTENTION_ORDER: dict[str, int] = {
    "overdue": 10,
    "deadline_1d": 20,
    "deadline_3d": 30,
    "passed_plan_open": 40,
    "deadline_7d": 50,
    "project_without_next_action": 60,
    "unread_accumulation": 70,
    "project_inactive": 80,
}


def attention_rank(reason: str) -> int:
    return ATTENTION_ORDER.get(reason, 999)


def deadline_reason(remaining_days: int) -> AttentionReason:
    """Kalan güne göre GEREKÇE kodu (§38)."""
    if remaining_days <= 1:
        return "deadline_1d"
    if remaining_days <= 3:
        return "deadline_3d"
    return "deadline_7d"


_WHITESPACE_RE = re.compile(r"\s+")


def normalize_for_identity(text: str) -> str:
    """Aday kimliği/dedupe için deterministik normalizasyon (§59/§63)."""
    normalized = unicodedata.normalize("NFKC", text or "").replace("\r\n", "\n")
    return _WHITESPACE_RE.sub(" ", normalized).strip().casefold()


def candidate_id(kind: str, text: str, support_refs: list[str] | tuple[str, ...]) -> str:
    """Deterministik aday kimliği (§59).

    Kimlik vermek için aday SAKLANMAZ: girdi `kind + normalize metin + sıralı
    destek ref'leri`dir, çıktı sabit bir sha256 öneki.
    """
    payload = "|".join([kind, normalize_for_identity(text), ",".join(sorted(support_refs))])
    return "cand_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def destination_for(kind: CandidateKind, *, entity_scoped: bool) -> PromotionDestination:
    """Varış yeri ÖNERİSİ (§60). Model hayal gücü değil, politika kararı."""
    if entity_scoped and kind in ENTITY_SCOPED_DESTINATIONS:
        return ENTITY_SCOPED_DESTINATIONS[kind]
    return DESTINATION_BY_KIND.get(kind, "general_vault")


def validate_mode(mode: str) -> ReviewMode:
    if mode not in ACTIVE_MODES:
        raise ReviewIntelligenceError(
            "INVALID_MODE", f"mode must be one of {list(ACTIVE_MODES)}"
        )
    return mode  # type: ignore[return-value]


def validate_mode_arguments(mode: str, provided: set[str]) -> None:
    """Mod ile uyumsuz argüman sessizce YOK SAYILMAZ (§21/§124)."""
    allowed = MODE_ALLOWED_ARGS[mode]
    unknown = {name for name in provided if name not in allowed}
    if unknown:
        raise ReviewIntelligenceError(
            "INVALID_ARGUMENT",
            f"argument(s) {sorted(unknown)} are not accepted by mode '{mode}' "
            f"(allowed: {sorted(allowed)})",
        )


def period_limit_days(mode: str) -> int | None:
    """Özel dönem modları için üst sınır (§23)."""
    from app.integrations.review_intelligence.models import MAX_H5_PERIOD_DAYS

    if mode in {"period_delta", "consolidation_review"}:
        return MAX_H5_PERIOD_DAYS
    return None


def insight_sort_key(insight: object) -> tuple:
    """Insight sıralaması: tip önceliği, sonra deterministik metin."""
    priority: dict[str, int] = {
        "time_sensitive": 10,
        "risk": 20,
        "change": 30,
        "win": 40,
        "stalled": 50,
        "open_loop": 60,
        "knowledge_health": 70,
    }
    insight_type = getattr(insight, "type", "")
    return (priority.get(insight_type, 999), getattr(insight, "text", ""))


def promotion_sort_key(candidate: object) -> tuple:
    """Terfi sıralaması (§64): yinelenme, destek sayısı, en yeni destek, kimlik."""
    return (
        -int(getattr(candidate, "recurrence_count", 1)),
        -int(getattr(candidate, "source_count", 0)),
        str(getattr(candidate, "candidate_id", "")),
    )


#: Mod → insan-okunur etiket (yalnızca tanılama/iz için).
MODE_LABELS: dict[str, str] = {
    "continuity": "süreklilik",
    "daily_close": "gün kapanışı",
    "weekly_review": "haftalık gözden geçirme",
    "period_delta": "dönem deltası",
    "consolidation_review": "konsolidasyon",
}

#: Dikkat gerekçesi → insan-okunur açıklama (puan değil, olgu).
ATTENTION_LABELS: dict[str, str] = {
    "overdue": "gecikmiş",
    "deadline_1d": "son tarih 1 gün içinde",
    "deadline_3d": "son tarih 3 gün içinde",
    "deadline_7d": "son tarih 7 gün içinde",
    "passed_plan_open": "planlanan zaman geçti, görev hâlâ açık",
    "unread_accumulation": "okunmamış içerik birikti",
    "project_without_next_action": "projenin sonraki adımı yok",
    "project_inactive": "projede anlamlı hareket yok",
}

PeriodKind = Literal["daily", "weekly"]


__all__ = [
    "ATTENTION_LABELS",
    "ATTENTION_ORDER",
    "DESTINATION_BY_KIND",
    "MODE_ALLOWED_ARGS",
    "MODE_LABELS",
    "MODES_REQUIRING_SINCE",
    "attention_rank",
    "candidate_id",
    "deadline_reason",
    "destination_for",
    "insight_sort_key",
    "normalize_for_identity",
    "period_limit_days",
    "promotion_sort_key",
    "validate_mode",
    "validate_mode_arguments",
]
