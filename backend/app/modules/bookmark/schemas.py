from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class CaptureIn(BaseModel):
    """Extension ve Life OS ici quick capture ayni endpoint'i kullanir."""
    client_uuid: uuid.UUID | None = None
    url: str
    title: str = ""
    description: str | None = None
    selection: str | None = None
    note: str | None = None
    collection: str = "inbox"
    source: str = "extension"
    tags: list[str] = []

    @field_validator("url")
    @classmethod
    def url_must_be_http(cls, v: str) -> str:
        v = v.strip()
        if not v.lower().startswith(("http://", "https://")):
            raise ValueError("url http(s) ile baslamali")
        return v


class BookmarkUpdate(BaseModel):
    """Kismi guncelleme. Verilmeyen alana dokunulmaz."""
    title: str | None = None
    note: str | None = None
    description: str | None = None
    collection: str | None = None
    read_status: str | None = None
    favorite: bool | None = None
    tags: list[str] | None = None


class BookmarkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    url: str
    description: str | None = None
    collection: str
    source: str
    read_status: str
    favorite: bool
    note: str | None = None
    selection: str | None = None
    saved_at: datetime
    tags: list[str] = []


class CaptureResult(BaseModel):
    id: uuid.UUID
    duplicate: bool = False
    existing_id: uuid.UUID | None = None
    collection: str = "inbox"


class CollectionCount(BaseModel):
    collection: str
    count: int


class BookmarkStats(BaseModel):
    inbox: int
    unread: int
    saved_today: int
    total: int
    collections: list[CollectionCount]
