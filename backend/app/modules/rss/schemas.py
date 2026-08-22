from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class FeedIn(BaseModel):
    url: str
    title: str = ""
    category: str | None = None

    @field_validator("url")
    @classmethod
    def url_must_be_http(cls, v: str) -> str:
        v = v.strip()
        if not v.lower().startswith(("http://", "https://")):
            raise ValueError("url http(s) ile baslamali")
        return v


class FeedUpdate(BaseModel):
    title: str | None = None
    category: str | None = None
    active: bool | None = None


class FeedOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    url: str
    site_url: str | None = None
    favicon_url: str | None = None
    category: str | None = None
    active: bool
    error_count: int
    last_status: str | None = None
    last_fetched_at: datetime | None = None
    unread: int = 0


class FeedItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    feed_id: uuid.UUID
    feed_title: str = ""
    title: str
    url: str | None = None
    author: str | None = None
    summary: str | None = None
    content: str | None = None               # yalnizca detay ucunda dolu
    published_at: datetime | None = None
    fetched_at: datetime
    read_at: datetime | None = None
    saved_bookmark_id: uuid.UUID | None = None


class SaveItemIn(BaseModel):
    collection: str = "read_later"


class ImportResult(BaseModel):
    added: int
    skipped: int
    feeds: list[str] = []


class RssStats(BaseModel):
    feeds: int
    active_feeds: int
    failing_feeds: int
    unread: int
    today: int = 0
    saved: int = 0
