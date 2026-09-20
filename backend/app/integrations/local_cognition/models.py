"""H4 yerel bilis (Local Cognition) sözleşmeleri.

H4, Hermes'in **açıkça istediği** dar bir bilişsel primitifi yerel bir modelle
yürütür. Bu modül girdi/çıktı sözleşmelerini, sınırları ve kodları tanımlar.

Değişmez ilkeler:

  - **Lane açıkça verilir.** H4 hedef ayrıştıran bir ajan DEĞİLDİR; hangi
    primitifin gerektiğine Hermes karar verir.
  - **Sinyal ≠ karar.** `input_chars`, yetenekler ve sağlık *sinyaldir*;
    seçim `policy.py` içindeki deterministik kurallarla yapılır.
  - **Model önerir, doğrulayıcı karar verir.** Model çıktısı asla doğrudan
    kabul edilmez.
  - **H4 hiçbir doğruluğa sahip değildir.** Entity/Link/Event/Todo/Vault/Sıcak
    Hafıza yazmaz; kanonik yazma yolu H1'dir.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, ValidationError

# ---------------------------------------------------------------------------
# Lane'ler
# ---------------------------------------------------------------------------

Lane = Literal["classify", "structured_extract", "query_rewrite"]

#: Üretimde AKTİF olan lane'ler.
ACTIVE_LANES: tuple[str, ...] = ("classify", "structured_extract", "query_rewrite")

#: Ertelenen lane'ler: H4.1 (`rerank`) ve H4.x/H5 (`compress`) araştırması.
#: Söz verilmeyen yetenek açılmaz; `INVALID_LANE` ile reddedilir.
DEFERRED_LANES: tuple[str, ...] = ("rerank", "compress")

#: H4'ün ASLA yapmadığı işler: muhakeme Hermes'e aittir.
REJECTED_LANES: tuple[str, ...] = ("reason", "chat", "answer", "plan")

# ---------------------------------------------------------------------------
# Slotlar ve yürütme sınırı
# ---------------------------------------------------------------------------

SlotName = Literal["local-small", "local-medium"]
SLOT_PRIORITY: tuple[str, ...] = ("local-small", "local-medium")

#: Model yürütmesi yalnızca yapılandırılmış loopback sağlayıcı üzerindedir.
ExecutionBoundary = Literal["local_loopback"]

Capability = Literal["classify", "structured_extract", "query_rewrite", "structured_output"]

# ---------------------------------------------------------------------------
# Sınırlar (§29/§81)
# ---------------------------------------------------------------------------

MIN_TEXT_CHARS = 2
MAX_TEXT_CHARS = 24000

MIN_LABELS = 2
MAX_LABELS = 20
MIN_LABEL_CHARS = 1
MAX_LABEL_CHARS = 80

MAX_CLASSIFICATION_GOAL_CHARS = 300

MAX_PROTECTED_TERMS = 20
MIN_PROTECTED_TERM_CHARS = 1
MAX_PROTECTED_TERM_CHARS = 100

MIN_REWRITE_CHARS = 2
MAX_REWRITE_CHARS = 200

#: Çıkarım koleksiyonlarının sert tavanı; sınırsız model dizisi YOKTUR.
MAX_EXTRACTION_ITEMS = 80
MAX_TITLE_CHARS = 200
MAX_DATE_TEXT_CHARS = 120
MAX_SOURCE_EXCERPT_CHARS = 500

#: Deneme tavanları (§71): toplam model çağrısı ≤ 3.
MAX_SMALL_ATTEMPTS = 2
MAX_MEDIUM_ATTEMPTS = 1
MAX_TOTAL_ATTEMPTS = MAX_SMALL_ATTEMPTS + MAX_MEDIUM_ATTEMPTS

#: Sağlayıcı yanıtı için kaba üst sınır (§48).
MAX_PROVIDER_RESPONSE_BYTES = 1024 * 1024

# ---------------------------------------------------------------------------
# Kodlar
# ---------------------------------------------------------------------------

#: Genel hata kodları (§87). Her biri ayrı bir durumu anlatır; "MODEL_ERROR"
#: gibi tek bir çuvala indirgenmez.
FailureCode = Literal[
    "H4_DISABLED",
    "INVALID_LANE",
    "INVALID_ARGUMENT",
    "INVALID_LOCAL_MODEL_ENDPOINT",
    "MODEL_PROVIDER_UNAVAILABLE",
    "MODEL_UNAVAILABLE",
    "NO_ELIGIBLE_MODEL",
    "CONTEXT_TOO_LARGE",
    "VALIDATION_FAILED",
    "LOCAL_CAPABILITY_UNAVAILABLE",
]

#: Doğrulama alt kodları (§76). Sağlayıcının ham istisna metni ASLA dışarı
#: çıkmaz; yalnızca bu sınırlı kodlar görünür.
ValidationCode = Literal[
    "INVALID_MODEL_JSON",
    "OUTPUT_SCHEMA_MISMATCH",
    "INVALID_CLASS_LABEL",
    "SOURCE_EXCERPT_NOT_FOUND",
    "SOURCE_FIELD_NOT_SUPPORTED",
    "INVALID_DATE",
    "INVALID_TIME",
    "PROTECTED_TERM_LOST",
    "OUTPUT_TOO_LARGE",
]

#: Yönlendirme gerekçe kodları (§64). Serbest metin muhakeme YOKTUR.
ReasonCode = Literal[
    "LANE_CLASSIFY",
    "LANE_STRUCTURED_EXTRACT",
    "LANE_QUERY_REWRITE",
    "STRUCTURED_OUTPUT_REQUIRED",
    "LOCAL_SMALL_SELECTED",
    "LOCAL_SMALL_UNAVAILABLE",
    "LOCAL_SMALL_CONTEXT_EXCEEDED",
    "LOCAL_SMALL_VALIDATION_FAILED",
    "LOCAL_MEDIUM_SELECTED",
    "ESCALATED_TO_LOCAL_MEDIUM",
    "LOCAL_MEDIUM_UNAVAILABLE",
    "LOCAL_MEDIUM_CONTEXT_EXCEEDED",
    "LOCAL_MEDIUM_VALIDATION_FAILED",
    "NO_ELIGIBLE_MODEL",
    "LOCAL_CAPABILITY_UNAVAILABLE",
]

LANE_REASON_CODES: dict[str, ReasonCode] = {
    "classify": "LANE_CLASSIFY",
    "structured_extract": "LANE_STRUCTURED_EXTRACT",
    "query_rewrite": "LANE_QUERY_REWRITE",
}

# ---------------------------------------------------------------------------
# Girdi modelleri (lane başına ayrık birleşim)
# ---------------------------------------------------------------------------

#: Şemada GÖRÜNÜR sınırlar; yürütmede bağımsız dayatılır (§29).
TextField = Annotated[str, Field(min_length=MIN_TEXT_CHARS, max_length=MAX_TEXT_CHARS)]
LabelItem = Annotated[str, Field(min_length=MIN_LABEL_CHARS, max_length=MAX_LABEL_CHARS)]
ProtectedTermItem = Annotated[str, Field(min_length=MIN_PROTECTED_TERM_CHARS, max_length=MAX_PROTECTED_TERM_CHARS)]

ExtractionContractName = Literal[
    "academic_calendar_v1",
    "weekly_schedule_v1",
    "deadline_candidates_v1",
    "consolidation_candidates_v1",
]

EXTRACTION_CONTRACTS: tuple[str, ...] = (
    "academic_calendar_v1",
    "weekly_schedule_v1",
    "deadline_candidates_v1",
    "consolidation_candidates_v1",
)


class ClassifyRequest(BaseModel):
    """`classify`: verilen etiketlerden BİRİNİ seçer."""

    lane: Literal["classify"]
    text: TextField
    labels: list[LabelItem] = Field(
        ...,
        min_length=MIN_LABELS,
        max_length=MAX_LABELS,
        description="Aday etiketler (2-20, tekil). Model YALNIZCA bunlardan birini döndürebilir.",
    )
    classification_goal: str = Field(
        ...,
        min_length=1,
        max_length=MAX_CLASSIFICATION_GOAL_CHARS,
        description="Sınıflandırmanın amacı (insan-okunur, ≤300 karakter).",
    )


class StructuredExtractRequest(BaseModel):
    """`structured_extract`: adlandırılmış, sürümlü bir sözleşmeye göre çıkarım."""

    lane: Literal["structured_extract"]
    text: TextField
    contract: ExtractionContractName = Field(
        ...,
        description="Sürümlü çıkarım sözleşmesi. Serbest JSON şeması KABUL EDİLMEZ.",
    )


class QueryRewriteRequest(BaseModel):
    """`query_rewrite`: arama için sınırlı yeniden yazım (yanıt DEĞİL)."""

    lane: Literal["query_rewrite"]
    text: TextField
    protected_terms: list[ProtectedTermItem] = Field(
        default_factory=list,
        max_length=MAX_PROTECTED_TERMS,
        description="Aynen korunması zorunlu terimler (≤20).",
    )


LaneRequest = ClassifyRequest | StructuredExtractRequest | QueryRewriteRequest


# ---------------------------------------------------------------------------
# Çıktı modelleri
# ---------------------------------------------------------------------------


class ClassificationResult(BaseModel):
    """Sınıflandırma sonucu. Olasılık/güven alanı KASITLI olarak yoktur (§39)."""

    lane: Literal["classify"] = "classify"
    label: str = Field(..., description="Sağlanan etiketlerden biri.")


class ExtractionResult(BaseModel):
    """Doğrulanmış çıkarım sonucu."""

    lane: Literal["structured_extract"] = "structured_extract"
    contract: ExtractionContractName
    items: list[dict] = Field(default_factory=list, description="Doğrulanmış öğeler.")


class QueryRewriteResult(BaseModel):
    """Yeniden yazılmış sorgu. Orijinal sorgu çağıranda kalır (§40)."""

    lane: Literal["query_rewrite"] = "query_rewrite"
    rewritten_query: str = Field(
        ..., min_length=MIN_REWRITE_CHARS, max_length=MAX_REWRITE_CHARS
    )


LaneResult = ClassificationResult | ExtractionResult | QueryRewriteResult


class AttemptRecord(BaseModel):
    """Tek bir model denemesinin GÜVENLİ meta verisi (§66).

    Ham prompt, ham model çıktısı, kaynak metin, kanıt paketi veya sıcak hafıza
    burada YER ALMAZ.
    """

    slot: SlotName
    model_id: str = Field(..., description="Yapılandırmadan gelen gerçek model kimliği.")
    attempt_number: int = Field(..., ge=1, le=MAX_TOTAL_ATTEMPTS)
    latency_ms: float = Field(..., ge=0)
    validation_status: Literal["valid", "invalid", "provider_error"]
    failure_code: str | None = Field(default=None, description="Sınırlı doğrulama/sağlayıcı kodu.")


class RouteDecision(BaseModel):
    """Yönlendirme kararının incelenebilir kaydı (§65).

    Birincil gözlemlenebilirlik budur: hangi slot seçildi, neden, kaç deneme
    yapıldı ve sonuç doğrulamadan geçti mi.
    """

    lane: Lane
    selected_slot: SlotName | None = None
    selected_model: str | None = None
    execution_boundary: ExecutionBoundary = "local_loopback"
    input_chars: int = Field(..., ge=0)
    required_capabilities: list[str] = Field(default_factory=list)
    reason_codes: list[ReasonCode] = Field(default_factory=list)
    attempts: list[AttemptRecord] = Field(default_factory=list)
    validation_status: Literal["valid", "invalid", "not_attempted"] = "not_attempted"
    escalated: bool = False
    escalation_reason: str | None = Field(
        default=None, description="Yukarı çıkışın sınırlı gerekçesi (varsa)."
    )
    latency_ms: float = Field(default=0.0, ge=0)


class LocalCognitionResponse(BaseModel):
    """H4 aracının tek çıktısı (§109).

    Gizli muhakeme YOKTUR: sonuç, sınırlı kodlar ve karar kaydı.
    """

    status: Literal["success", "needs_escalation"]
    lane: Lane
    result: LaneResult | None = None
    failure_code: str | None = None
    recovery_hint: str | None = None
    route_decision: RouteDecision


class H4Error(Exception):
    """Model-okunur, sınırlı H4 hatası. Ham istisna metni taşımaz."""

    def __init__(self, code: FailureCode, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


# ---------------------------------------------------------------------------
# Lane/argüman uyumu (§30)
# ---------------------------------------------------------------------------


def _bounded_validation_message(exc: ValidationError) -> str:
    """Pydantic hatasını SINIRLI tek satıra indirir (ham metin sızmaz)."""
    errors = exc.errors()
    if not errors:
        return "invalid argument"
    first = errors[0]
    location = ".".join(str(part) for part in first.get("loc", ()))
    message = str(first.get("msg", "invalid"))
    return f"{location}: {message}"[:200]


def _construct(model: type[BaseModel], **payload: object) -> Any:
    """Modeli kurar; sınır ihlali SINIRLI `INVALID_ARGUMENT` hatasına dönüşür.

    Aksi hâlde doğrudan çağıranlar ham pydantic istisnası görürdü: sınırlar
    uygulanmış olurdu ama hata yüzeyi sözleşmeye uymazdı.
    """
    try:
        return model(**payload)
    except ValidationError as exc:
        raise H4Error("INVALID_ARGUMENT", _bounded_validation_message(exc)) from exc


def build_lane_request(
    *,
    lane: str,
    text: str,
    contract: str | None = None,
    labels: list[str] | None = None,
    classification_goal: str | None = None,
    protected_terms: list[str] | None = None,
) -> LaneRequest:
    """Düz taşıma argümanlarından ayrık lane isteği kurar.

    Lane ile uyumsuz argüman sessizce YOK SAYILMAZ; `INVALID_ARGUMENT` ile
    reddedilir. Böylece "classify + contract" gibi belirsiz çağrılar modele
    ulaşmadan durur.
    """
    if lane in DEFERRED_LANES:
        raise H4Error(
            "INVALID_LANE",
            f"lane '{lane}' is not active in H4 core (deferred research lane)",
        )
    if lane in REJECTED_LANES:
        raise H4Error("INVALID_LANE", f"lane '{lane}' is not supported; Hermes performs reasoning")
    if lane not in ACTIVE_LANES:
        raise H4Error("INVALID_LANE", f"lane must be one of {list(ACTIVE_LANES)}")

    def _reject(field: str, expected: str) -> None:
        raise H4Error(
            "INVALID_ARGUMENT",
            f"'{field}' is not accepted by lane '{lane}' ({expected})",
        )

    if lane == "classify":
        if contract is not None:
            _reject("contract", "classify uses labels + classification_goal")
        if protected_terms:
            _reject("protected_terms", "classify uses labels + classification_goal")
        if labels is None or classification_goal is None:
            raise H4Error(
                "INVALID_ARGUMENT", "lane 'classify' requires labels and classification_goal"
            )
        return _construct(
            ClassifyRequest,
            lane="classify",
            text=text,
            labels=labels,
            classification_goal=classification_goal,
        )  # type: ignore[return-value]

    if lane == "structured_extract":
        if labels is not None or classification_goal is not None:
            _reject("labels/classification_goal", "structured_extract uses contract")
        if protected_terms:
            _reject("protected_terms", "structured_extract uses contract")
        if contract is None:
            raise H4Error("INVALID_ARGUMENT", "lane 'structured_extract' requires contract")
        if contract not in EXTRACTION_CONTRACTS:
            raise H4Error(
                "INVALID_ARGUMENT",
                f"unknown extraction contract '{contract}'; allowed: {list(EXTRACTION_CONTRACTS)}",
            )
        return _construct(
            StructuredExtractRequest, lane="structured_extract", text=text, contract=contract
        )  # type: ignore[return-value]

    if labels is not None or classification_goal is not None or contract is not None:
        _reject("labels/classification_goal/contract", "query_rewrite uses text + protected_terms")
    return _construct(
        QueryRewriteRequest,
        lane="query_rewrite",
        text=text,
        protected_terms=protected_terms or [],
    )  # type: ignore[return-value]


def validate_lane_request(request: LaneRequest) -> LaneRequest:
    """Ayrık isteğin sınırlarını ÇALIŞMA ZAMANINDA bağımsız dayatır (§29).

    Şema ilk savunmadır; doğrudan Python çağıranları onu atlayabildiği için
    burada yeniden doğrulanır. Kırpma YOKTUR: ihlal `INVALID_ARGUMENT` olur.
    """
    try:
        if isinstance(request, ClassifyRequest):
            if not (MIN_LABELS <= len(request.labels) <= MAX_LABELS):
                raise ValueError(f"labels must contain {MIN_LABELS}-{MAX_LABELS} entries")
            normalized = [label.strip() for label in request.labels]
            if any(not label for label in normalized):
                raise ValueError("labels must not be blank")
            if len(set(normalized)) != len(normalized):
                raise ValueError("labels must be unique")
            if len(request.classification_goal.strip()) == 0:
                raise ValueError("classification_goal must not be blank")
        elif isinstance(request, QueryRewriteRequest):
            if len(request.protected_terms) > MAX_PROTECTED_TERMS:
                raise ValueError(f"protected_terms must contain at most {MAX_PROTECTED_TERMS} entries")
            if any(not term.strip() for term in request.protected_terms):
                raise ValueError("protected_terms must not contain blank entries")
        elif not isinstance(request, StructuredExtractRequest):  # pragma: no cover - savunma
            raise ValueError("unknown lane request")
        if not (MIN_TEXT_CHARS <= len(request.text) <= MAX_TEXT_CHARS):
            raise ValueError(f"text must be {MIN_TEXT_CHARS}-{MAX_TEXT_CHARS} characters")
        return request
    except ValidationError as exc:
        raise H4Error("INVALID_ARGUMENT", _bounded_validation_message(exc)) from exc
    except ValueError as exc:
        raise H4Error("INVALID_ARGUMENT", str(exc)[:200]) from exc


__all__ = [
    "ACTIVE_LANES",
    "AttemptRecord",
    "ClassificationResult",
    "ClassifyRequest",
    "DEFERRED_LANES",
    "EXTRACTION_CONTRACTS",
    "ExecutionBoundary",
    "ExtractionContractName",
    "ExtractionResult",
    "FailureCode",
    "H4Error",
    "LANE_REASON_CODES",
    "Lane",
    "LaneRequest",
    "LaneResult",
    "LocalCognitionResponse",
    "MAX_ATTEMPTS",
    "QueryRewriteRequest",
    "QueryRewriteResult",
    "REJECTED_LANES",
    "ReasonCode",
    "RouteDecision",
    "SLOT_PRIORITY",
    "SlotName",
    "StructuredExtractRequest",
    "ValidationCode",
    "build_lane_request",
    "validate_lane_request",
]

#: Geriye dönük okunabilirlik için kısa ad (testler ve eval aracı kullanır).
MAX_ATTEMPTS = MAX_TOTAL_ATTEMPTS
