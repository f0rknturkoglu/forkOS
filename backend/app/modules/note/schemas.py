from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

NoteView = Literal["page", "canvas"]
PageWidth = Literal["compact", "wide", "full"]
MAX_CANVAS_BYTES = 5 * 1024 * 1024
MAX_CANVAS_ELEMENTS = 5_000


def validate_canvas_state(value: dict[str, Any] | None) -> dict[str, Any] | None:
    """Excalidraw sahnesini yerel DB'yi sisirmeden sinirla."""
    if value is None:
        return None
    elements = value.get("elements", [])
    if not isinstance(elements, list):
        raise ValueError("tuval elemanları liste olmalı")
    if len(elements) > MAX_CANVAS_ELEMENTS:
        raise ValueError(f"tuval en fazla {MAX_CANVAS_ELEMENTS} eleman içerebilir")
    try:
        encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
    except (TypeError, ValueError) as exc:
        raise ValueError("tuval verisi geçerli JSON olmalı") from exc
    if len(encoded) > MAX_CANVAS_BYTES:
        raise ValueError("tuval verisi 5 MB sınırını aşıyor")
    return value


class ResolvedLink(BaseModel):
    """Govdedeki [[hedef]] -> gercek kayit."""

    target: str
    id: uuid.UUID
    type: str


class NoteAttachmentOut(BaseModel):
    id: uuid.UUID
    name: str
    mime: str
    size: int
    url: str


class NoteFolderIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    parent_id: uuid.UUID | None = None


class NoteFolderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    parent_id: uuid.UUID | None = None
    position: int | None = Field(default=None, ge=0, le=100_000)


class NoteFolderOut(BaseModel):
    id: uuid.UUID
    name: str
    parent_id: uuid.UUID | None = None
    position: int = 0
    note_count: int = 0
    created_at: datetime
    updated_at: datetime


class NoteIn(BaseModel):
    body: str = Field(min_length=1, max_length=200_000)
    pinned: bool = False
    #: Opsiyonel iliski intent'i (Faz 29): doluysa not oluşturulurken AYNI
    #: transaction icinde notes_about bagi kurulur. Iliski basarisizsa not
    #: da olusmaz (yarim kayit yok). Geriye uyumlu: bos birakilabilir.
    relate_to: uuid.UUID | None = None
    #: Elle eklenen etiketler. Govdedeki #etiketlerle BIRLESTIRILIR
    #: (core/refs.py); ayri bir not-etiketi havuzu yoktur.
    tags: list[str] = Field(default_factory=list)
    canvas_state: dict[str, Any] = Field(default_factory=dict)
    default_view: NoteView = "page"
    page_width: PageWidth = "compact"
    folder_id: uuid.UUID | None = None

    _validate_canvas = field_validator("canvas_state")(validate_canvas_state)


class NoteUpdate(BaseModel):
    body: str | None = Field(default=None, min_length=1, max_length=200_000)
    pinned: bool | None = None
    tags: list[str] | None = None
    canvas_state: dict[str, Any] | None = None
    default_view: NoteView | None = None
    page_width: PageWidth | None = None
    folder_id: uuid.UUID | None = None

    _validate_canvas = field_validator("canvas_state")(validate_canvas_state)


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    body: str
    pinned: bool
    project_id: uuid.UUID | None = None
    folder_id: uuid.UUID | None = None
    journal_day: date | None = None
    created_at: datetime
    updated_at: datetime
    #: Govde + elle eklenenlerin birlesimi.
    tags: list[str] = Field(default_factory=list)
    #: [[...]] yazilmis ama o baslikta kayit olmayan hedefler -- arayuz
    #: bunlari "olustur" olarak gosterir.
    unresolved_links: list[str] = Field(default_factory=list)
    #: Cozulen wikilink'ler: hedef basliktan gercek kayda. Arayuz tiklaninca
    #: dogrudan o kayda gider -- arama uzerinden dolasmaya gerek kalmaz.
    resolved_links: list[ResolvedLink] = Field(default_factory=list)
    attachments: list[NoteAttachmentOut] = Field(default_factory=list)
    canvas_state: dict[str, Any] = Field(default_factory=dict)
    default_view: NoteView = "page"
    page_width: PageWidth = "compact"

    _validate_canvas = field_validator("canvas_state")(validate_canvas_state)
