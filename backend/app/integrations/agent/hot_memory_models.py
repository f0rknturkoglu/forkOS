"""H2 sıcak hafıza modelleri: katı girdiler ve sınırlı okuma modelleri.

Sınırlar bilinçli olarak küçüktür: sıcak hafıza, "her şeyi hatırla" deposu
değil, gelecekteki konuşmalara taşınacak KÜÇÜK ve kalıcı bağlamdır. Sığmayan
bilgi normal Vault bilgisine aittir.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

#: Kanonik türler (§14) ve kaynak modları (§43).
MemoryKindValue = Literal["profile", "preference", "goal", "constraint", "decision"]
SourceModeValue = Literal["explicit_user", "approved_candidate"]
EffectiveStatusFilter = Literal["active", "expired", "retired", "all"]

#: §41 boyut sınırları — `obsidian.hot_memory` sabitleriyle aynı olmalıdır.
MAX_TITLE = 120
MAX_TEXT = 1200
MAX_TAGS = 8
MAX_TAG_LENGTH = 50
MAX_RELATED = 5
MAX_RETIRED_REASON = 240
MAX_REVISION_LENGTH = 64
MAX_QUERY_LENGTH = 200


def _uuid_str(v: Any) -> str:
    import uuid as _uuid

    if isinstance(v, _uuid.UUID):
        return str(v)
    try:
        return str(_uuid.UUID(str(v).strip()))
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"geçersiz kimlik: {v!r}") from exc


def _optional_uuid_str(v: Any) -> str | None:
    return None if v is None else _uuid_str(v)


def _iso_str(v: str | None) -> str | None:
    if v is None:
        return None
    text = v.strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00") if text.endswith("Z") else text
    datetime.fromisoformat(normalized)
    return text


def _bounded_text(v: str, *, maximum: int, label: str) -> str:
    if not isinstance(v, str):
        raise ValueError(f"{label} metin olmalı")
    stripped = v.strip()
    if not stripped:
        raise ValueError(f"{label} boş olamaz")
    if len(stripped) > maximum:
        raise ValueError(f"{label} en fazla {maximum} karakter olabilir")
    return stripped


def _tags(v: list[str] | None) -> list[str]:
    if v is None:
        return []
    cleaned: list[str] = []
    for tag in v:
        if not isinstance(tag, str):
            raise ValueError("etiketler metin olmalı")
        text = tag.strip()
        if not text:
            continue
        if len(text) > MAX_TAG_LENGTH:
            raise ValueError(f"etiket en fazla {MAX_TAG_LENGTH} karakter olabilir")
        if text not in cleaned:
            cleaned.append(text)
    if len(cleaned) > MAX_TAGS:
        raise ValueError(f"en fazla {MAX_TAGS} etiket kullanılabilir")
    return cleaned


def _related(v: list[str] | None) -> list[str]:
    if v is None:
        return []
    ids = [_uuid_str(entry) for entry in v]
    if len(ids) > MAX_RELATED:
        raise ValueError(f"en fazla {MAX_RELATED} ilgili kayıt bağlanabilir")
    return list(dict.fromkeys(ids))


# ---------------------------------------------------------------------------
# Okuma modelleri
# ---------------------------------------------------------------------------


class HotMemoryItem(BaseModel):
    """Bağlama (context) giren sınırlı öğe — yol taşımaz (§50)."""

    memory_id: str
    kind: MemoryKindValue
    title: str
    text: str
    importance: int
    updated_at: str
    expires_at: str | None = None
    related_forkos_ids: list[str] = Field(default_factory=list)
    revision: str


class HotMemoryListItem(HotMemoryItem):
    """Yönetim/liste öğesi — göreli yol ve durum bilgisi ekler (§54)."""

    status: Literal["active", "retired"]
    effective_status: Literal["active", "expired", "retired"]
    source_mode: SourceModeValue
    created_at: str
    tags: list[str] = Field(default_factory=list)
    #: Vault köküne GÖRELİ yol; mutlak yol asla dönmez.
    relative_path: str


class HotMemoryContextData(BaseModel):
    """Sıcak hafıza bağlam paketi (§50)."""

    profile: list[HotMemoryItem] = Field(default_factory=list)
    preferences: list[HotMemoryItem] = Field(default_factory=list)
    goals: list[HotMemoryItem] = Field(default_factory=list)
    constraints: list[HotMemoryItem] = Field(default_factory=list)
    decisions: list[HotMemoryItem] = Field(default_factory=list)
    active_total: int = 0
    returned_total: int = 0
    omitted_total: int = 0
    invalid_count: int = 0
    truncated: bool = False
    warnings: list[str] = Field(default_factory=list)


class HotMemoryListData(BaseModel):
    """Liste/keşif sonucu (§54)."""

    items: list[HotMemoryListItem] = Field(default_factory=list)
    total: int = 0
    returned: int = 0
    truncated: bool = False
    invalid_count: int = 0
    invalid_paths: list[str] = Field(default_factory=list)
    conflict_ids: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Girdi modelleri
# ---------------------------------------------------------------------------


class HotMemoryStoreIn(BaseModel):
    """Onaylanmış yeni bir sıcak hafıza öğesi (§56). Yol ya da kimlik ALMAZ."""

    model_config = ConfigDict(extra="forbid")

    kind: MemoryKindValue
    title: str
    text: str
    importance: int = Field(default=2, ge=1, le=3)
    source_mode: SourceModeValue
    expires_at: str | None = None
    related_forkos_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        return _bounded_text(v, maximum=MAX_TITLE, label="başlık")

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        return _bounded_text(v, maximum=MAX_TEXT, label="metin")

    @field_validator("expires_at")
    @classmethod
    def validate_expires(cls, v: str | None) -> str | None:
        return _iso_str(v)

    @field_validator("related_forkos_ids")
    @classmethod
    def validate_related(cls, v: list[str]) -> list[str]:
        return _related(v)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        return _tags(v)


class HotMemoryUpdateIn(BaseModel):
    """Var olan öğeyi düzeltir (§60).

    `memory_id` ve `expected_revision` ZORUNLU; `status`/`created_at`/
    `source_mode` serbest alan değildir (durum değişimi `retire` iledir).
    Verilmeyen alan korunur, açık `null` temizler (H1.1 sözleşmesi).
    """

    model_config = ConfigDict(extra="forbid")

    memory_id: str
    expected_revision: str = Field(min_length=MAX_REVISION_LENGTH, max_length=MAX_REVISION_LENGTH)
    kind: MemoryKindValue | None = None
    title: str | None = None
    text: str | None = None
    importance: int | None = Field(default=None, ge=1, le=3)
    expires_at: str | None = None
    related_forkos_ids: list[str] | None = None
    tags: list[str] | None = None

    @field_validator("memory_id")
    @classmethod
    def validate_memory_id(cls, v: Any) -> str:
        return _uuid_str(v)

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str | None) -> str | None:
        return None if v is None else _bounded_text(v, maximum=MAX_TITLE, label="başlık")

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str | None) -> str | None:
        return None if v is None else _bounded_text(v, maximum=MAX_TEXT, label="metin")

    @field_validator("expires_at")
    @classmethod
    def validate_expires(cls, v: str | None) -> str | None:
        return _iso_str(v)

    @field_validator("related_forkos_ids")
    @classmethod
    def validate_related(cls, v: list[str] | None) -> list[str] | None:
        return None if v is None else _related(v)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str] | None) -> list[str] | None:
        return None if v is None else _tags(v)


class HotMemoryRetireIn(BaseModel):
    """Emeklilik girdisi (§64). Silme DEĞİLDİR; aktif bağlamdan çıkarır."""

    model_config = ConfigDict(extra="forbid")

    memory_id: str
    expected_revision: str = Field(min_length=MAX_REVISION_LENGTH, max_length=MAX_REVISION_LENGTH)
    reason: str | None = None

    @field_validator("memory_id")
    @classmethod
    def validate_memory_id(cls, v: Any) -> str:
        return _uuid_str(v)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip()
        if not stripped:
            return None
        if len(stripped) > MAX_RETIRED_REASON:
            raise ValueError(f"gerekçe en fazla {MAX_RETIRED_REASON} karakter olabilir")
        return stripped
