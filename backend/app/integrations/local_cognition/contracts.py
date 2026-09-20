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

from app.integrations.local_cognition import temporal as temporal_svc
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


ConsolidationKind = Literal[
    "decision",
    "lesson",
    "commitment",
    "goal",
    "constraint",
    "project_knowledge",
    "reference",
]

#: Konsolidasyon adaylarının tavanları (§54).
MAX_CONSOLIDATION_CANDIDATES = 30
MAX_CONSOLIDATION_TEXT_CHARS = 500


class ConsolidationCandidate(BaseModel):
    """Geçici malzemeden çıkarılmış TEK kalıcılık adayı (sürüm: v1).

    `text` model kaynaklı ADAY İFADEDİR; kanıt değildir. Kanıt, sağlanan
    metinde birebir bulunması zorunlu olan `source_excerpt`'tir (§55).
    """

    model_config = _STRICT

    kind: ConsolidationKind
    text: str = Field(..., min_length=1, max_length=MAX_CONSOLIDATION_TEXT_CHARS)
    source_excerpt: str = Field(..., min_length=1, max_length=MAX_SOURCE_EXCERPT_CHARS)


class ConsolidationExtraction(BaseModel):
    """`consolidation_candidates_v1` çıktısı."""

    model_config = _STRICT

    candidates: list[ConsolidationCandidate] = Field(
        default_factory=list, max_length=MAX_CONSOLIDATION_CANDIDATES
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


#: Otomatik korunan kimlik sayısı tavanı (§7). Açık terimler önce gelir ve
#: bu tavana DAHİL DEĞİLDİR.
MAX_AUTO_PROTECTED_TERMS = 8

#: Kanonik UUID (8-4-4-4-12, onaltılık).
_AUTO_UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
#: http/https URL; sondaki cümle noktalaması ayrıca kırpılır.
_AUTO_URL_RE = re.compile(r"https?://[^\s<>\"')]+")
#: `owner/repo` benzeri kimlik: her iki taraf HARFLE başlar, böylece tarih
#: (`12/09/2026`) ve rastgele eğik çizgili ifadeler korunmaz (§6).
_AUTO_SLUG_RE = re.compile(
    r"(?<![\w./-])([A-Za-z][\w.-]*/[A-Za-z][\w.-]*)(?![\w/-])"
)
#: Sürüm dizeleri: `v2.4.1`, `2.4.1`, `1.0`.
_AUTO_VERSION_RE = re.compile(r"\bv?\d+\.\d+(?:\.\d+)*\b")

#: URL sonundan kırpılan cümle noktalaması.
_TRAILING_PUNCTUATION = ".,;:!?)]}\"'"


def detect_identifiers(source_text: str) -> tuple[str, ...]:
    """Kaynak metindeki apaçık kimlikleri GÖRÜNME SIRASINA göre döner.

    Deterministik ve muhafazakârdır: model çıkarımı yoktur, sözlük yoktur.
    Yalnızca UUID, URL, `owner/repo` ve sürüm dizeleri tanınır.
    """
    if not source_text:
        return ()

    found: list[tuple[int, str]] = []
    for pattern in (_AUTO_UUID_RE, _AUTO_URL_RE, _AUTO_SLUG_RE, _AUTO_VERSION_RE):
        for match in pattern.finditer(source_text):
            value = match.group(1) if pattern is _AUTO_SLUG_RE else match.group(0)
            if pattern is _AUTO_URL_RE:
                value = value.rstrip(_TRAILING_PUNCTUATION)
            if value:
                found.append((match.start(), value))

    ordered: list[str] = []
    seen: set[str] = set()
    for _position, value in sorted(found, key=lambda row: row[0]):
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(value)
    return tuple(ordered[:MAX_AUTO_PROTECTED_TERMS])


def effective_protected_terms(
    source_text: str, explicit_terms: list[str] | None
) -> tuple[str, ...]:
    """PROMPT ve DOĞRULAYICI için TEK korunan terim listesi (§5/§9).

    Sıra: açık terimler (verilen sırayla), sonra kaynaktan otomatik tanınan
    kimlikler (görünme sırası). Açık terimler önceliklidir ve otomatik tavana
    dahil değildir.

    Aynı yardımcıyı iki taraf da kullanır; aksi hâlde prompt ile doğrulayıcı
    yeniden ayrışır ve "sessizce kaybolan kimlik" hatası geri gelir.
    """
    terms: list[str] = []
    seen: set[str] = set()

    def _add(value: str) -> None:
        cleaned = (value or "").strip()
        if not cleaned:
            return
        key = cleaned.casefold()
        if key in seen:
            return
        seen.add(key)
        terms.append(cleaned)

    for term in explicit_terms or []:
        _add(term)
    for term in detect_identifiers(source_text):
        _add(term)
    return tuple(terms)


def excerpt_is_sourced(excerpt: str, source_text: str) -> bool:
    """`source_excerpt` gerçekten sağlanan metinden mi geliyor?"""
    normalized_excerpt = normalize_for_matching(excerpt)
    if not normalized_excerpt:
        return False
    return normalized_excerpt in normalize_for_matching(source_text)


def field_is_sourced(field: str, container: str) -> bool:
    """Çıkarılan HAM alan, kapsayıcı metnin bir parçası mı? (H4.1 §7)

    `date_text` gibi alanlar kaynaktan ALINTI olmalıdır. Karşılaştırma
    NFKC + tire + boşluk normalizasyonu + büyük/küçük harf duyarsızdır; büyük
    harf farkı olguyu değiştirmediği için burada esneklik güvenlidir.
    Yine de bulanık/semantik eşleştirme YAPILMAZ: alan ya alıntıdır ya değildir.
    """
    normalized_field = temporal_svc.normalize(field)
    if not normalized_field:
        return False
    return normalized_field in temporal_svc.normalize(container)


#: Pydantic'in uzunluk ihlali tipleri (liste ve dize ayrı tipler kullanır).
_TOO_LONG_TYPES = frozenset({"too_long", "string_too_long"})

#: Tarih/saat alanları TAM ADLA eşleşir. Alt dize kontrolü (`"date" in location`)
#: koleksiyon anahtarının kendisiyle yanlış eşleşiyordu: `candidates` içindeki
#: "candi**date**s" her şema hatasını `INVALID_DATE` yapıyordu.
_DATE_FIELDS = frozenset({"start_date", "end_date", "due_date"})
_TIME_FIELDS = frozenset({"start_time", "end_time", "due_time", "day_of_week"})


def _code_for_validation_error(error: ValidationError, collection_key: str) -> ValidationCode:
    """Pydantic hatasını sınırlı bir doğrulama koduna eşler."""
    for detail in error.errors():
        location = detail.get("loc", ())
        field = str(location[-1]) if location else ""
        error_type = str(detail.get("type", ""))
        if error_type in _TOO_LONG_TYPES:
            return "OUTPUT_TOO_LARGE"
        if error_type == "too_short" and field == collection_key:
            return "OUTPUT_SCHEMA_MISMATCH"
        if field in _DATE_FIELDS:
            return "INVALID_DATE"
        if field in _TIME_FIELDS:
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
    """`academic_calendar_v1` doğrulaması — KAYNAK TEMELLİ (H4.1 §11).

    Zincir: `source_excerpt` → `date_text` → normalize tarih.

    - `date_text` kaynaktan alıntı olmalıdır (`SOURCE_FIELD_NOT_SUPPORTED`).
    - Normalize tarih YALNIZCA deterministik ayrıştırıcı onaylarsa kabul edilir;
      ayrıştırıcı çözemiyorsa model `null` döndürmek ZORUNDADIR.
    - Eksik normalizasyon (null) geçerlidir: H4, uydurma tarihi eksik tarihe
      tercih eder (§12).
    """

    def sanity(item: AcademicCalendarEvent) -> ValidationCode | None:
        if not field_is_sourced(item.date_text, item.source_excerpt):
            return "SOURCE_FIELD_NOT_SUPPORTED"

        expected_start, expected_end = temporal_svc.parse_date_range(item.date_text)
        if item.start_date is not None and item.start_date != expected_start:
            return "INVALID_DATE"
        if item.end_date is not None and item.end_date != expected_end:
            return "INVALID_DATE"
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
    """`weekly_schedule_v1` doğrulaması — KAYNAK TEMELLİ (H4.1 §18/§19).

    Aynı gün varsayımı geçerlidir: `end_time > start_time`. Gece yarısını aşan
    bloklar v1 kapsamı DIŞINDADIR.

    Gün ve saatler kaynaktan ÇIKARILIR ve model değerleriyle karşılaştırılır:
    tek başına geçerli olmak yetmez, kaynağa karşılık gelmelidir. Kaynakta
    tanınan gün yoksa ya da birden fazla farklı gün geçiyorsa öğe reddedilir
    (tahmin yok).
    """

    def sanity(item: WeeklyScheduleBlock) -> ValidationCode | None:
        weekday = temporal_svc.find_weekday(item.source_excerpt)
        if weekday is None or item.day_of_week != weekday:
            return "INVALID_TIME"

        times = temporal_svc.parse_times(item.source_excerpt)
        if len(times) < 2:
            return "INVALID_TIME"
        if item.start_time != times[0] or item.end_time != times[1]:
            return "INVALID_TIME"
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
    """`deadline_candidates_v1` doğrulaması — KAYNAK TEMELLİ (H4.1 §13/§14).

    `due_date` deterministik tarih çözümüyle, `due_time` ise kaynakta geçen
    gerçek bir saatle uyuşmalıdır. Kaynakta saat yoksa `due_time` null kalır:
    `23:59` gibi varsayılanlar UYDURULAMAZ.
    """

    def sanity(item: DeadlineCandidate) -> ValidationCode | None:
        if not field_is_sourced(item.date_text, item.source_excerpt):
            return "SOURCE_FIELD_NOT_SUPPORTED"

        expected_start, expected_end = temporal_svc.parse_date_range(item.date_text)
        expected = expected_start or expected_end
        if item.due_date is not None and item.due_date != expected:
            return "INVALID_DATE"

        if item.due_time is not None:
            allowed = set(temporal_svc.parse_times(item.date_text)) | set(
                temporal_svc.parse_times(item.source_excerpt)
            )
            if item.due_time not in allowed:
                return "INVALID_TIME"
        return None

    return _validate_collection(
        payload=payload,
        model=DeadlineExtraction,
        collection_key="deadlines",
        source_text=source_text,
        sanity=sanity,
    )


def validate_consolidation(payload: Any, source_text: str) -> ValidationOutcome:
    """`consolidation_candidates_v1` doğrulaması (§55).

    `source_excerpt` katı kaynak kuralına uyar (sağlanan pakette birebir
    bulunmalı). `text` bilinçli olarak model kaynaklı aday ifadedir ve ayrıca
    kaynağa bağlanması BEKLENMEZ: yeniden yazım serbesttir, kanıt değildir.
    """

    def sanity(item: ConsolidationCandidate) -> ValidationCode | None:
        return None

    return _validate_collection(
        payload=payload,
        model=ConsolidationExtraction,
        collection_key="candidates",
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
    # Açık terimler + kaynaktan otomatik tanınan kimlikler (UUID/URL/slug/sürüm).
    for term in effective_protected_terms(source_text, protected_terms):
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
    "consolidation_candidates_v1": validate_consolidation,
}

#: Çıkarım sözleşmesi → (koleksiyon anahtarı, JSON şeması). Sağlayıcıya
#: gönderilen `format` alanı buradan gelir; serbest şema KABUL EDİLMEZ.
EXTRACTION_SCHEMAS: dict[str, tuple[str, dict[str, Any]]] = {
    "academic_calendar_v1": ("events", AcademicCalendarExtraction.model_json_schema()),
    "weekly_schedule_v1": ("blocks", WeeklyScheduleExtraction.model_json_schema()),
    "deadline_candidates_v1": ("deadlines", DeadlineExtraction.model_json_schema()),
    "consolidation_candidates_v1": ("candidates", ConsolidationExtraction.model_json_schema()),
}

CLASSIFICATION_SCHEMA: dict[str, Any] = ClassificationPayload.model_json_schema()
QUERY_REWRITE_SCHEMA: dict[str, Any] = QueryRewritePayload.model_json_schema()

#: Prompt'ta kullanılan üst sınırlar (dokümantasyonla aynı sayılar).
MAX_CLASSIFICATION_GOAL = MAX_CLASSIFICATION_GOAL_CHARS
MAX_PROTECTED = MAX_PROTECTED_TERMS
MAX_REWRITE = MAX_REWRITE_CHARS
