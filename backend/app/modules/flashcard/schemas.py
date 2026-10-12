from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DeckIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class DeckPatch(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class CardIn(BaseModel):
    front: str = Field(min_length=1, max_length=2000)
    back: str = Field(min_length=1, max_length=2000)
    #: True ise ters karti da uretilir (On<->Arka), ayni destede.
    reversible: bool = False


class CardPatch(BaseModel):
    front: str | None = Field(default=None, min_length=1, max_length=2000)
    back: str | None = Field(default=None, min_length=1, max_length=2000)
    suspended: bool | None = None


class ReviewIn(BaseModel):
    grade: int = Field(ge=0, le=3)


class DeckOut(BaseModel):
    id: uuid.UUID
    title: str
    card_count: int
    due_count: int
    new_count: int
    #: Olgun kart: interval > 21 gun (Anki esigi). SRS dagilim cubugu kullanir.
    mature_count: int = 0
    created_at: datetime



class CardOut(BaseModel):
    id: uuid.UUID
    deck_id: uuid.UUID
    front: str
    back: str
    interval_days: int
    ease: float
    due_at: datetime | None
    reps: int
    lapses: int
    suspended: bool


class CramCardOut(CardOut):
    """Cram kuyrugu: kart + ait oldugu deste adi (tek listede gosterilir)."""
    deck_title: str


class ReviewOut(BaseModel):
    due_at: datetime
    interval_days: int


class ImportOut(BaseModel):
    deck_id: uuid.UUID
    deck_title: str
    added: int
    skipped: int


class SharedDeckOut(BaseModel):
    id: int
    title: str
    url: str
    notes: int
    likes: int
    has_media: bool


class SharedDeckPreview(BaseModel):
    id: int
    title: str
    url: str
    notes: int
    has_media: bool
    size_bytes: int
    samples: list[list[str]]
