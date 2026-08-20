"""Universal Inbox ve Bookmark Library AYNI tablo.

collection='inbox'  -> Inbox ekrani
digerleri           -> Bookmark Library
Surukle-birak = tek UPDATE; link ve event'ler kopmaz.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import EntityBacked
from app.db import Base

COLLECTIONS = ("inbox", "read_later", "learning", "reference", "projects", "archive")
READ_STATUSES = ("unread", "reading", "read")
SOURCES = ("extension", "manual", "rss", "youtube")


class Bookmark(EntityBacked, Base):
    __tablename__ = "bookmark"
    ENTITY_TYPE = "bookmark"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE"), primary_key=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    url_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    selection: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    collection: Mapped[str] = mapped_column(String(32), nullable=False, default="inbox")
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="extension")
    read_status: Mapped[str] = mapped_column(String(16), nullable=False, default="unread")
    favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now())
    # extension retry'lerinde cift kayit olmamasi icin
    client_uuid: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), unique=True)
