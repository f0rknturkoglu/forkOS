"""H4 çıkarım sözleşmeleri ve DETERMİNİSTİK doğrulayıcıları.

Model bir ÖNERİ üretir; kabul kararı buradadır. Doğrulama LLM ile değil,
kesin kurallarla yapılır (§77).

Sözleşmeler adlandırılmış ve SÜRÜMLÜDÜR: serbest JSON şeması kabul edilmez
(§31), böylece çıktı incelenebilir, doğrulanabilir ve değerlendirilebilir kalır.
Uyumsuz bir değişiklik `_v2` olur, sessiz şema kayması olmaz.

Kaynak kanıtı zorunludur: her öğenin `source_excerpt` alanı, sağlanan metnin
içinde **birebir** bulunmalıdır (yalnızca satır sonu + boşluk normalizasyonu ve
Unicode NFKC uygulanır). Bulanık eşleştirme yapılmaz; uydurulmuş metin geçemez.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.integrations.local_cognition.models import (
    MAX_CLASSIFICATION_GOAL_CHARS,
    MAX_DATE_TEXT_CHARS,
    MAX_EXTRACTION_ITEMS,
    MAX_LABEL_CHARS,
    MAX_PROTECTED_TERMS,
    MAX_REWRITE_CHARS,
    MAX_SOURCE_EXCERPT_CHARS,
    MAX_TITLE_CHARS,
    MIN_REWRITE_CHARS,
    ValidationCode,
)

# ---------------------------------------------------------------------------
# Sözleşme modelleri
# ---------------------------------------------------------------------------

_STRICT = ConfigDict(extra="forbid")

CalendarCategory = Literal[
    "registration",
    "classes",
    "exam",
    "holiday",
    "deadline",
    "orientation",
    "payment",
    "other",
]
DayOfWeek = Literal[
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
]
DeadlineKind = Literal[
    "submission", "application", "exam", "payment", "registration", "appointment", "other"
]

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


class AcademicCalendarEvent(BaseModel):
    """Akademik takvimde tek bir olay (sürüm: v1)."""

    model_config = _STRICT

    title: str = Field(..., min_length=1, max_length=MAX_TITLE_CHARS)
    category: CalendarCategory
    date_text: str = Field(
        ...,
        min_length=1,
        max_length=MAX_DATE_TEXT_CHARS,
        description="Kaynaktaki tarih ifadesinin AYNEN korunmuş hâli.",
    )
    start_date: date | None = Field(
        default=None, description="Güvenle normalize edilebiliyorsa; aksi hâlde null."
    )
    end_date: date | None = None
    source_excerpt: str = Field(..., min_length=1, max_length=MAX_SOURCE_EXCERPT_CHARS)


class AcademicCalendarExtraction(BaseModel):
    """`academic_calendar_v1` çıktısı."""

    model_config = _STRICT

    events: list[AcademicCalendarEvent] = Field(
        default_factory=list, max_length=MAX_EXTRACTION_ITEMS
    )


class WeeklyScheduleBlock(BaseModel):
    """Haftalık programda tek bir blok (sürüm: v1)."""

    model_config = _STRICT

    title: str = Field(..., min_length=1, max_length=MAX_TITLE_CHARS)
    day_of_week: DayOfWeek
    start_time: str = Field(..., pattern=_TIME_RE.pattern, description="HH:MM (24 saat).")
    end_time: str = Field(..., pattern=_TIME_RE.pattern, description="HH:MM (24 saat).")
    source_excerpt: str = Field(..., min_length=1, max_length=MAX_SOURCE_EXCERPT_CHARS)


class WeeklyScheduleExtraction(BaseModel):
    """`weekly_schedule_v1` çıktısı."""

    model_config = _STRICT

    blocks: list[WeeklyScheduleBlock] = Field(
        default_factory=list, max_length=MAX_EXTRACTION_ITEMS
    )


class DeadlineCandidate(BaseModel):
    """Tek bir son tarih adayı (sürüm: v1)."""

    model_config = _STRICT

    title: str = Field(..., min_length=1, max_length=MAX_TITLE_CHARS)
    kind: DeadlineKind
    date_text: str = Field(..., min_length=1, max_length=MAX_DATE_TEXT_CHARS)
    due_date: date | None = None
    due_time: str | None = Field(default=None, pattern=_TIME_RE.pattern)
    source_excerpt: str = Field(..., min_length=1, max_length=MAX_SOURCE_EXCERPT_CHARS)


class DeadlineExtraction(BaseModel):
    """`deadline_candidates_v1` çıktısı."""

    model_config = _STRICT

    deadlines: list[DeadlineCandidate] = Field(
        default_factory=list, max_length=MAX_EXTRACTION_ITEMS
    )


class ClassificationPayload(BaseModel):
    """`classify` çıktısı. Güven/olasılık alanı KABUL EDİLMEZ (§39)."""

    model_config = _STRICT

    label: str = Field(..., min_length=1, max_length=MAX_LABEL_CHARS)


class QueryRewritePayload(BaseModel):
    """`query_rewrite` çıktısı."""

    model_config = _STRICT

    rewritten_query: str = Field(
        ..., min_length=MIN_REWRITE_CHARS, max_length=MAX_REWRITE_CHARS
    )


# ---------------------------------------------------------------------------
# Doğrulama sonucu
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValidationOutcome:
    """Doğrulamanın sonucu: kabul edilen veri ya da sınırlı bir kod."""

    ok: bool
    payload: dict[str, Any] | None = None
    code: ValidationCode | None = None
    message: str = ""

    @staticmethod
    def valid(payload: dict[str, Any]) -> ValidationOutcome:
        return ValidationOutcome(ok=True, payload=payload)

    @staticmethod
    def invalid(code: ValidationCode, message: str) -> ValidationOutcome:
        return ValidationOutcome(ok=False, code=code, message=message)


# ---------------------------------------------------------------------------
# Deterministik yardımcılar
# ---------------------------------------------------------------------------


def normalize_for_matching(text: str) -> str:
    """Kaynak karşılaştırması için asgari normalizasyon (§78).

    Yalnızca: Unicode NFKC, satır sonu birleştirme ve boşluk daraltma.
    Harf büyüklüğü KORUNUR; bulanık eşleştirme yapılmaz, böylece uydurulmuş
    metin kaynakta bulunmuş gibi geçemez.
    """
    normalized = unicodedata.normalize("NFKC", text or "")
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    return " ".join(normalized.split())


def excerpt_is_sourced(excerpt: str, source_text: str) -> bool:
    """`source_excerpt` gerçekten sağlanan metinden mi geliyor?"""
    normalized_excerpt = normalize_for_matching(excerpt)
    if not normalized_excerpt:
        return False
    return normalized_excerpt in normalize_for_matching(source_text)


#: Pydantic'in uzunluk ihlali tipleri (liste ve dize ayrı tipler kullanır).
_TOO_LONG_TYPES = frozenset({"too_long", "string_too_long"})


def _code_for_validation_error(error: ValidationError, collection_key: str) -> ValidationCode:
    """Pydantic hatasını sınırlı bir doğrulama koduna eşler."""
    for detail in error.errors():
        location = ".".join(str(part) for part in detail.get("loc", ()))
        error_type = str(detail.get("type", ""))
        if error_type in _TOO_LONG_TYPES:
            return "OUTPUT_TOO_LARGE"
        if error_type == "too_short" and location.startswith(collection_key):
            return "OUTPUT_SCHEMA_MISMATCH"
        if "date" in location:
            return "INVALID_DATE"
        if "time" in location:
            return "INVALID_TIME"
    return "OUTPUT_SCHEMA_MISMATCH"


def _validate_collection(
    *,
    payload: dict[str, Any],
    model: type[BaseModel],
    collection_key: str,
    source_text: str,
    sanity: Callable[[BaseModel], ValidationCode | None],
) -> ValidationOutcome:
    """Ortak koleksiyon doğrulaması: şema → kaynak kanıtı → tutarlılık."""
    if not isinstance(payload, dict):
        return ValidationOutcome.invalid("OUTPUT_SCHEMA_MISMATCH", "payload must be an object")
    try:
        parsed = model.model_validate(payload)
    except ValidationError as exc:
        return ValidationOutcome.invalid(
            _code_for_validation_error(exc, collection_key), "payload does not match the contract"
        )

    items = getattr(parsed, collection_key)
    for item in items:
        if not excerpt_is_sourced(item.source_excerpt, source_text):
            return ValidationOutcome.invalid(
                "SOURCE_EXCERPT_NOT_FOUND",
                "an item's source_excerpt is not present in the supplied text",
            )
        problem = sanity(item)
        if problem is not None:
            return ValidationOutcome.invalid(problem, "an item is internally inconsistent")

    return ValidationOutcome.valid(parsed.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# Lane doğrulayıcıları
# ---------------------------------------------------------------------------


def validate_academic_calendar(payload: Any, source_text: str) -> ValidationOutcome:
    """`academic_calendar_v1` doğrulaması (§33/§34/§79)."""

    def sanity(item: AcademicCalendarEvent) -> ValidationCode | None:
        if item.start_date and item.end_date and item.end_date < item.start_date:
            return "INVALID_DATE"
        return None

    return _validate_collection(
        payload=payload,
        model=AcademicCalendarExtraction,
        collection_key="events",
        source_text=source_text,
        sanity=sanity,
    )


def validate_weekly_schedule(payload: Any, source_text: str) -> ValidationOutcome:
    """`weekly_schedule_v1` doğrulaması (§36/§80).

    Aynı gün varsayımı geçerlidir: `end_time > start_time`. Gece yarısını aşan
    bloklar v1 kapsamı DIŞINDADIR.
    """

    def sanity(item: WeeklyScheduleBlock) -> ValidationCode | None:
        if item.end_time <= item.start_time:
            return "INVALID_TIME"
        return None

    return _validate_collection(
        payload=payload,
        model=WeeklyScheduleExtraction,
        collection_key="blocks",
        source_text=source_text,
        sanity=sanity,
    )


def validate_deadlines(payload: Any, source_text: str) -> ValidationOutcome:
    """`deadline_candidates_v1` doğrulaması."""

    def sanity(item: DeadlineCandidate) -> ValidationCode | None:
        return None

    return _validate_collection(
        payload=payload,
        model=DeadlineExtraction,
        collection_key="deadlines",
        source_text=source_text,
        sanity=sanity,
    )


def validate_classification(
    payload: Any, source_text: str, labels: list[str]
) -> ValidationOutcome:
    """`classify` doğrulaması: etiket SAĞLANAN kümeden olmalı (§39)."""
    if not isinstance(payload, dict):
        return ValidationOutcome.invalid("OUTPUT_SCHEMA_MISMATCH", "payload must be an object")
    try:
        parsed = ClassificationPayload.model_validate(payload)
    except ValidationError as exc:
        return ValidationOutcome.invalid(
            _code_for_validation_error(exc, "label"), "payload does not match the contract"
        )
    allowed = [label.strip() for label in labels]
    if parsed.label not in allowed:
        return ValidationOutcome.invalid(
            "INVALID_CLASS_LABEL", "the model returned a label that was not supplied"
        )
    return ValidationOutcome.valid(parsed.model_dump(mode="json"))


def validate_query_rewrite(
    payload: Any, source_text: str, protected_terms: list[str]
) -> ValidationOutcome:
    """`query_rewrite` doğrulaması: korunan terimler AYNEN kalmalı (§41/§42)."""
    if not isinstance(payload, dict):
        return ValidationOutcome.invalid("OUTPUT_SCHEMA_MISMATCH", "payload must be an object")
    try:
        parsed = QueryRewritePayload.model_validate(payload)
    except ValidationError as exc:
        code: ValidationCode = (
            "OUTPUT_TOO_LARGE"
            if any(str(detail.get("type", "")) in _TOO_LONG_TYPES for detail in exc.errors())
            else "OUTPUT_SCHEMA_MISMATCH"
        )
        return ValidationOutcome.invalid(code, "payload does not match the contract")

    normalized_rewrite = normalize_for_matching(parsed.rewritten_query)
    for term in protected_terms:
        if normalize_for_matching(term) not in normalized_rewrite:
            return ValidationOutcome.invalid(
                "PROTECTED_TERM_LOST", "the rewrite dropped a protected term"
            )
    return ValidationOutcome.valid(parsed.model_dump(mode="json"))


#: Sözleşme adı → doğrulayıcı. Sürüm kimliği sözleşmenin parçasıdır.
EXTRACTION_VALIDATORS: dict[str, Callable[[Any, str], ValidationOutcome]] = {
    "academic_calendar_v1": validate_academic_calendar,
    "weekly_schedule_v1": validate_weekly_schedule,
    "deadline_candidates_v1": validate_deadlines,
}

#: Çıkarım sözleşmesi → (koleksiyon anahtarı, JSON şeması). Sağlayıcıya
#: gönderilen `format` alanı buradan gelir; serbest şema KABUL EDİLMEZ.
EXTRACTION_SCHEMAS: dict[str, tuple[str, dict[str, Any]]] = {
    "academic_calendar_v1": ("events", AcademicCalendarExtraction.model_json_schema()),
    "weekly_schedule_v1": ("blocks", WeeklyScheduleExtraction.model_json_schema()),
    "deadline_candidates_v1": ("deadlines", DeadlineExtraction.model_json_schema()),
}

CLASSIFICATION_SCHEMA: dict[str, Any] = ClassificationPayload.model_json_schema()
QUERY_REWRITE_SCHEMA: dict[str, Any] = QueryRewritePayload.model_json_schema()

#: Prompt'ta kullanılan üst sınırlar (dokümantasyonla aynı sayılar).
MAX_CLASSIFICATION_GOAL = MAX_CLASSIFICATION_GOAL_CHARS
MAX_PROTECTED = MAX_PROTECTED_TERMS
MAX_REWRITE = MAX_REWRITE_CHARS
