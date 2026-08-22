from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import EntityBacked
from app.db import Base


class Feed(EntityBacked, Base):
    __tablename__ = "feed"
    ENTITY_TYPE = "feed"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE"), primary_key=True)
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    site_url: Mapped[str | None] = mapped_column(Text)
    favicon_url: Mapped[str | None] = mapped_column(Text)     # feed/channel logosu
    category: Mapped[str | None] = mapped_column(String(64))
    etag: Mapped[str | None] = mapped_column(Text)              # conditional GET
    last_modified: Mapped[str | None] = mapped_column(Text)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[str | None] = mapped_column(String(32))
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class FeedItem(EntityBacked, Base):
    __tablename__ = "feed_item"
    ENTITY_TYPE = "feed_item"
    __table_args__ = (UniqueConstraint("feed_id", "guid", name="feed_item_uniq"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE"), primary_key=True)
    feed_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("feed.id", ondelete="CASCADE"), nullable=False)
    guid: Mapped[str] = mapped_column(Text, nullable=False)     # yoksa sha256(url + title)
    url: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str | None] = mapped_column(Text)          # content:encoded (okuma bolmesi)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now())
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
