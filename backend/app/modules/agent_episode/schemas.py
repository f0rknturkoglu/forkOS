"""A3: sürümlü, sınırlı ve ham transkript kabul etmeyen epizodik devir sözleşmesi.

Bu modül A3'ün DIŞ dünyaya bakan tek yüzeyidir. Kasıtlı olarak `extra="forbid"`
kullanır: `conversation_history` gibi bir alan gönderilirse doğrulama hatası
olur, sessizce yok sayılmaz.
"""

from __future__ import annotations

import unicodedata
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Sınırlar (§4/§17/§12)
# ---------------------------------------------------------------------------

#: Plugin tarafındaki sert girdi tavanları. Sunucu bunları BAĞIMSIZ dayatır.
MAX_EPISODE_USER_CHARS = 2000
MAX_EPISODE_ASSISTANT_CHARS = 6000
MAX_EPISODE_TURN_CHARS = 8000

#: Tek turda üretilebilecek en fazla epizodik ifade.
MAX_ITEMS_PER_TURN = 6

#: Mühürlenmiş bir devirdeki toplam ifade tavanı.
MAX_EPISODE_ITEMS = 12

#: Tür başına tavanlar (§17).
MAX_TOPICS = 3
MAX_OUTCOMES = 4
MAX_OPEN_THREADS = 4
MAX_SESSION_DECISIONS = 3
MAX_NEXT_FOCUS = 3

#: İfade başına kaynak referansı tavanı.
MAX_SUPPORT_REFS_PER_ITEM = 5

#: İfade metni tavanı; DB CHECK kısıtıyla aynı sayıdır.
MAX_ITEM_TEXT_CHARS = 300

#: Bir devrin tur defterinde tutulabilecek en fazla satır. Budama `delivered_at`
#: sırasına göre yapılır, yani mühürlenmemiş (gözlemlenmemiş) turlar da sayılır:
#: sınır "defter boyu"dur, "gözlemlenen tur sayısı" değil.
MAX_EPISODE_TURNS = 200

#: Render edilen `<forkos-handoff>` gövdesinin sert tavanı (§17).
MAX_HANDOFF_RENDER_CHARS = 1800

#: Saklama (§18): son N mühürlü devir VE en fazla bu kadar gün.
MAX_SEALED_EPISODES = 20
EPISODE_RETENTION_DAYS = 14

#: Taslak (mühürlenmemiş) devir bu süreden sonra fırsatçı olarak budanır.
DRAFT_STALE_HOURS = 24

#: Bir ifadenin kaynak metinden birebir taşıyabileceği en uzun parça.
#: Bu tavanı aşan ifade "ham transkript sızıntısı" sayılır ve REDDEDİLİR (§5).
MAX_VERBATIM_ITEM_SPAN_CHARS = 120

EpisodeKind = Literal[
    "topic", "outcome", "open_thread", "session_decision", "next_focus", "reference"
]

#: Epistemik sınıf (§7/§10).
#:
#: - `turn_derived`: başarılı bir Hermes turundan türetilmiş tarihsel iddia.
#: - `canonical_supported`: ayrıca kanonik kaynak referansıyla desteklenebilen
#:   tarihsel gözlem.
#: - `observed_during_session`: oturum penceresinde kanonik olarak GERÇEKLEŞMİŞ
#:   gözlem. Bu oturumun YAPTIĞI iddia EDİLMEZ (§10) — arka plan worker'ı veya
#:   başka bir kullanıcı eylemi olabilir; nedensellik kurulmaz.
EpisodeEvidenceClass = Literal["turn_derived", "canonical_supported", "observed_during_session"]

EpisodeStatus = Literal["draft", "sealed", "sealed_degraded", "sealed_empty"]

#: Sınırlı gerekçe kodları (§28). Serbest hata metni dışarı çıkmaz.
EpisodeReasonCode = Literal[
    "EPISODE_EXTRACTION_UNAVAILABLE",
    "EPISODE_EXTRACTION_TIMEOUT",
    "EPISODE_VALIDATION_FAILED",
    "EPISODE_EMPTY",
    "EPISODE_FINALIZE_DEGRADED",
    "EPISODE_HANDOFF_UNAVAILABLE",
    "EPISODE_SESSION_NOT_FOUND",
    "EPISODE_INPUT_TRUNCATED",
    "EPISODE_SEALED",
    "SOURCE_BINDING_UNAVAILABLE",
    "SOURCE_STALE",
    "H5_UNAVAILABLE",
    "LOCAL_COGNITION_UNAVAILABLE",
    "VERBATIM_LEAKAGE",
    "SCOPE_AMBIGUOUS",
    "SECRET_LEAKAGE",
]

_STRICT = ConfigDict(extra="forbid")

Harness = Literal["hermes", "codex", "claude"]


def normalize_for_matching(text: str) -> str:
    """Eşleştirme ve tekilleştirme için asgari normalizasyon.

    NFKC + boşluk sadeleştirme + küçük harf. Bulanık veya anlamsal eşleştirme
    YAPILMAZ: iki metin ya aynıdır ya değildir. H4'ün kendi normalizasyonuyla
    aynı sınıftadır.
    """
    if not text:
        return ""
    return " ".join(unicodedata.normalize("NFKC", text).lower().split())


def _clean_identity(value: str) -> str:
    if not value.strip() or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("invalid identity")
    return value


# ---------------------------------------------------------------------------
# Tur gözlemi (§14)
# ---------------------------------------------------------------------------


class EpisodeTurnIn(BaseModel):
    """`post_llm_call` gözlemi. Ham transkript alanı KABUL ETMEZ.

    `conversation_history` bu şemada YOKTUR ve `extra="forbid"` sayesinde
    gönderilirse 422 olur. `user_message`/`assistant_response` yalnız bu istek
    boyunca yaşayan GEÇİCİ girdilerdir; yanıt bunları geri döndürmez.
    """

    model_config = _STRICT

    schema_version: Literal[1]
    harness: Harness
    session_id: str = Field(min_length=1, max_length=256)
    turn_id: str = Field(min_length=1, max_length=256)
    platform: str = Field(default="unknown", max_length=64)
    user_message: str | None = Field(default=None, max_length=MAX_EPISODE_USER_CHARS)
    assistant_response: str | None = Field(default=None, max_length=MAX_EPISODE_ASSISTANT_CHARS)
    user_truncated: bool = False
    assistant_truncated: bool = False

    @field_validator("session_id", "turn_id")
    @classmethod
    def validate_identity(cls, value: str) -> str:
        return _clean_identity(value)

    @field_validator("platform")
    @classmethod
    def normalize_platform(cls, value: str) -> str:
        value = value.strip().lower()
        if not value or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for char in value):
            raise ValueError("invalid platform")
        return value

    @model_validator(mode="after")
    def enforce_turn_budget(self) -> EpisodeTurnIn:
        """Bileşik tur tavanı SUNUCUDA dayatılır; plugin kendi kopyasını tutsa da
        sınır tek bir yerde anlamlı kalır."""
        total = len(self.user_message or "") + len(self.assistant_response or "")
        if total > MAX_EPISODE_TURN_CHARS:
            raise ValueError("turn exceeds MAX_EPISODE_TURN_CHARS")
        return self

    @property
    def truncated(self) -> bool:
        """Tur kırpılarak mı geldi? Kırpılan tur sessizce yutulmaz."""
        return self.user_truncated or self.assistant_truncated


class EpisodeTurnOut(BaseModel):
    """Tur gözleminin GÜVENLİ yanıtı: yalnız sayaç ve sınırlı kodlar."""

    accepted: bool
    duplicate: bool
    derived_item_count: int = Field(ge=0, le=MAX_ITEMS_PER_TURN)
    degraded_reasons: list[EpisodeReasonCode] = Field(default_factory=list)
    latency_ms: float = Field(default=0.0, ge=0)


# ---------------------------------------------------------------------------
# Mühürleme (§15)
# ---------------------------------------------------------------------------


class EpisodeFinalizeIn(BaseModel):
    """Oturum kapanışı. Transkript YOK; yalnız kimlik ve platform."""

    model_config = _STRICT

    schema_version: Literal[1]
    harness: Harness
    session_id: str = Field(min_length=1, max_length=256)
    platform: str = Field(default="unknown", max_length=64)

    @field_validator("session_id")
    @classmethod
    def validate_identity(cls, value: str) -> str:
        return _clean_identity(value)

    @field_validator("platform")
    @classmethod
    def normalize_platform(cls, value: str) -> str:
        value = value.strip().lower()
        if not value or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for char in value):
            raise ValueError("invalid platform")
        return value


class EpisodeFinalizeOut(BaseModel):
    sealed: bool
    duplicate: bool
    status: EpisodeStatus
    episode_id: int
    item_count: int = Field(ge=0, le=MAX_EPISODE_ITEMS)
    turn_count: int = Field(ge=0)
    scope_project: str | None = None
    sealed_at: datetime
    degraded_reasons: list[EpisodeReasonCode] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Durum (§30)
# ---------------------------------------------------------------------------


class EpisodeStatusOut(BaseModel):
    """Metadata-only tanılama: ham konuşma YOK."""

    available: bool
    last_sealed_at: datetime | None = None
    last_episode_item_count: int = Field(default=0, ge=0, le=MAX_EPISODE_ITEMS)
    last_scope_project: str | None = None
    recent_handoff_available: bool = False
    draft_episode_count: int = Field(default=0, ge=0)
    degraded_reasons: list[EpisodeReasonCode] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Devir okuma modeli (§23)
# ---------------------------------------------------------------------------


class EpisodeSupportRef(BaseModel):
    """Bir ifadenin kanonik kökeni. Uydurma referans ÜRETİLMEZ."""

    model_config = _STRICT

    source_id: str = Field(max_length=128)
    source_type: str = Field(max_length=32)
    source_version: str | None = Field(default=None, max_length=64)
    scope_project: str | None = Field(default=None, max_length=64)


class SessionHandoffItem(BaseModel):
    """Tek epizodik ifade: tür, türetilmiş metin, epistemik sınıf ve köken."""

    model_config = _STRICT

    ordinal: int = Field(ge=0)
    kind: EpisodeKind
    text: str = Field(max_length=MAX_ITEM_TEXT_CHARS)
    evidence_class: EpisodeEvidenceClass
    support_refs: list[EpisodeSupportRef] = Field(default_factory=list)
    turn_digest: str | None = Field(default=None, max_length=64)
    source_role: str | None = Field(default=None, max_length=16)
    evidence_digest: str | None = Field(default=None, max_length=64)
    historical_support_stale: bool = False


class SessionHandoffV1(BaseModel):
    """Önceki ilgili oturumun sınırlı, kaynağa bağlı epizodik devri.

    Bu bir TARİHSEL özettir: güncel kanonik durum DEĞİLDİR, yetkilendirme
    DEĞİLDİR ve içindeki talimat benzeri metin güvenilmeyen veridir (§21/§26).
    """

    model_config = _STRICT

    schema_version: Literal[1] = 1
    episode_id: int
    source_session_key: str = Field(max_length=64)
    sealed_at: datetime
    scope_project: str | None = None
    items: list[SessionHandoffItem] = Field(default_factory=list)
    degraded_reasons: list[EpisodeReasonCode] = Field(default_factory=list)


#: Tür sırası: render ve kesme sırası deterministik olmalı (§15).
KIND_ORDER: tuple[str, ...] = (
    "topic",
    "outcome",
    "open_thread",
    "session_decision",
    "next_focus",
    "reference",
)

KIND_CAPS: dict[str, int] = {
    "topic": MAX_TOPICS,
    "outcome": MAX_OUTCOMES,
    "open_thread": MAX_OPEN_THREADS,
    "session_decision": MAX_SESSION_DECISIONS,
    "next_focus": MAX_NEXT_FOCUS,
    "reference": MAX_EPISODE_ITEMS,
}


def bounded_indices(items: list[SessionHandoffItem]) -> list[int]:
    """Tür ve toplam tavanları uygular; KALAN girdilerin indekslerini döner.

    Kesme kararı yalnız tür tavanlarına ve ordinal sırasına bağlıdır: hiçbir
    ifade "daha önemli göründüğü için" öne alınmaz. İndeks döndürmek, çağıranın
    ifade–tur eşleşmesini kaybetmeden sınırları uygulamasını sağlar.
    """
    per_kind: dict[str, int] = {}
    kept: list[int] = []
    for index in sorted(range(len(items)), key=lambda position: items[position].ordinal):
        if len(kept) >= MAX_EPISODE_ITEMS:
            break
        kind = items[index].kind
        used = per_kind.get(kind, 0)
        if used >= KIND_CAPS.get(kind, MAX_EPISODE_ITEMS):
            continue
        per_kind[kind] = used + 1
        kept.append(index)
    return kept


def dedupe_indices(items: list[SessionHandoffItem]) -> list[int]:
    """Aynı normalize metni bir kez tutar; KALAN girdilerin indekslerini döner.

    İlk görülme kazanır: A3 epizodik bir kayıttır ve bir konunun oturumdaki
    GİRİŞ anı onun tarihsel yeridir. Farklı metinler (ör. "konuşuldu" ve
    "tamamlandı") ayrı ifadeler olarak kalır.
    """
    seen: set[str] = set()
    kept: list[int] = []
    for index, item in enumerate(items):
        key = normalize_for_matching(item.text)
        if not key or key in seen:
            continue
        seen.add(key)
        kept.append(index)
    return kept


def _reindex(items: list[SessionHandoffItem]) -> list[SessionHandoffItem]:
    return [
        item.model_copy(
            update={
                "ordinal": position,
                "support_refs": item.support_refs[:MAX_SUPPORT_REFS_PER_ITEM],
            }
        )
        for position, item in enumerate(items)
    ]


def bound_handoff_items(handoff: SessionHandoffV1) -> SessionHandoffV1:
    """Tür tavanlarını, toplam tavanı ve ref tavanını uygular."""
    items = handoff.items
    return handoff.model_copy(update={"items": _reindex([items[i] for i in bounded_indices(items)])})


