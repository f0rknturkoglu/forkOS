"""Universal Inbox ve Bookmark Library AYNI tablo.

collection='inbox'  -> Inbox ekrani
digerleri           -> Bookmark Library
Surukle-birak = tek UPDATE; link ve event'ler kopmaz.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.models import EntityBacked
from app.db import Base

COLLECTIONS = ("inbox", "read_later", "learning", "reference", "projects", "archive")
READ_STATUSES = ("unread", "reading", "read")
SOURCES = ("extension", "manual", "rss", "youtube")


class Bookmark(EntityBacked, Base):
    __tablename__ = "bookmark"
    ENTITY_TYPE = "bookmark"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE"), primary_key=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    url_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    selection: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    collection: Mapped[str] = mapped_column(String(32), nullable=False, default="inbox")
    queue_kind: Mapped[str | None] = mapped_column(String(32))
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="extension")
    read_status: Mapped[str] = mapped_column(String(16), nullable=False, default="unread")
    favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # extension retry'lerinde cift kayit olmamasi icin
    client_uuid: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), unique=True)

    # Pocket Engine alanlari
    content_html: Mapped[str | None] = mapped_column(Text)
    content_text: Mapped[str | None] = mapped_column(Text)
    hero_image_url: Mapped[str | None] = mapped_column(Text)
    favicon_url: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(128))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reading_time_min: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scroll_progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    highlights: Mapped[list[BookmarkHighlight]] = relationship(
        "BookmarkHighlight", back_populates="bookmark", cascade="all, delete-orphan", order_by="BookmarkHighlight.anchor_index"
    )


class BookmarkHighlight(Base):
    __tablename__ = "bookmark_highlight"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    bookmark_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("bookmark.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    color: Mapped[str] = mapped_column(String(16), nullable=False, default="yellow")
    anchor_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    bookmark: Mapped[Bookmark] = relationship("Bookmark", back_populates="highlights")

