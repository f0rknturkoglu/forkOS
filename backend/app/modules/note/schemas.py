from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


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


class NoteUpdate(BaseModel):
    body: str | None = Field(default=None, min_length=1, max_length=200_000)
    pinned: bool | None = None
    tags: list[str] | None = None


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    body: str
    pinned: bool
    project_id: uuid.UUID | None = None
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
