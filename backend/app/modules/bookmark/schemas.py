from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

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
    # Pocket Engine opsiyonel alanlari
    hero_image_url: str | None = None
    favicon_url: str | None = None
    author: str | None = None
    reading_time_min: int | None = None
    word_count: int | None = None

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
    queue_kind: str | None = None
    tags: list[str] | None = None
    hero_image_url: str | None = None
    favicon_url: str | None = None
    author: str | None = None
    reading_time_min: int | None = None
    scroll_progress: int | None = None


class BookmarkBulkActionIn(BaseModel):
    bookmark_ids: list[uuid.UUID]
    action: Literal["move", "delete", "tag", "read_status"]
    collection: str | None = None
    tags: list[str] | None = None
    read_status: str | None = None


class BookmarkBulkActionResult(BaseModel):
    affected: int
    action: str


class ConvertToTaskIn(BaseModel):
    priority: int = 2
    plan_day: str | None = None
    due_at: datetime | None = None


class CreateNoteFromBookmarkIn(BaseModel):
    pinned: bool = False
    additional_text: str | None = None


class BookmarkHighlightIn(BaseModel):
    text: str
    note: str | None = None
    color: str = "yellow"
    anchor_index: int = 0


class BookmarkHighlightOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    bookmark_id: uuid.UUID
    text: str
    note: str | None = None
    color: str = "yellow"
    anchor_index: int = 0
    created_at: datetime


class BookmarkProgressUpdate(BaseModel):
    scroll_progress: int


class BookmarkFullTextOut(BaseModel):
    id: uuid.UUID
    title: str
    url: str
    content_html: str | None = None
    content_text: str | None = None
    hero_image_url: str | None = None
    favicon_url: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    reading_time_min: int = 1
    word_count: int = 0
    scroll_progress: int = 0
    highlights: list[BookmarkHighlightOut] = []


class BookmarkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    url: str
    description: str | None = None
    collection: str
    queue_kind: str | None = None
    source: str
    read_status: str
    favorite: bool
    note: str | None = None
    selection: str | None = None
    saved_at: datetime
    tags: list[str] = []
    is_duplicate: bool = False
    existing_collection: str | None = None

    # Pocket Engine alanlari
    hero_image_url: str | None = None
    favicon_url: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    reading_time_min: int = 1
    word_count: int = 0
    scroll_progress: int = 0
    highlights_count: int = 0


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
