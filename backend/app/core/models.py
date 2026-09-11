"""Cekirdek tablolar. HER modul tablosunun PK'si entity.id'ye FK olmali."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, ClassVar

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Entity(Base):
    """Sistemdeki her seyin kimlik kaydi. Link, event, tag, search buna bagli."""
    __tablename__ = "entity"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    search_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now())
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    search_vec: Mapped[Any] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('simple', immutable_unaccent(title || ' ' || search_text))",
                 persisted=True),
        deferred=True,
    )


class EntityBacked:
    """Modul tablolari icin mixin.

    class Bookmark(EntityBacked, Base):
        ENTITY_TYPE = "bookmark"
        __tablename__ = "bookmark"
    """
    ENTITY_TYPE: ClassVar[str]

    @staticmethod
    def _entity_pk() -> Mapped[uuid.UUID]:
        return mapped_column(
            PgUUID(as_uuid=True),
            ForeignKey("entity.id", ondelete="CASCADE"),
            primary_key=True,
        )


class Link(Base):
    """Iki entity arasinda yonlu iliski. bookmark <-> project, todo <-> opportunity..."""
    __tablename__ = "link"
    __table_args__ = (
        UniqueConstraint("from_id", "to_id", "relation", name="link_uniq"),
        CheckConstraint("from_id <> to_id", name="link_no_self"),
        Index(
            "media_collection_item_link_idx",
            "from_id",
            "to_id",
            postgresql_where=text("relation = 'media.collection_item'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    from_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE"), nullable=False)
    to_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE"), nullable=False)
    relation: Mapped[str] = mapped_column(String(64), nullable=False, default="related")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now())


class Event(Base):
    """Append-only activity log. ASLA UPDATE/DELETE etme.

    Weekly Review, Today feed ve Activity ekrani tamamen buradan beslenir.
    """
    __tablename__ = "event"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="SET NULL"))
    entity_type: Mapped[str | None] = mapped_column(String(64))  # entity silinse de kalir
    verb: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now())


class Tag(Base):
    __tablename__ = "tag"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name: Mapped[str] = mapped_column(Text, nullable=False)
    color: Mapped[str | None] = mapped_column(String(16))


class EntityTag(Base):
    __tablename__ = "entity_tag"

    entity_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True)


class SavedView(Base):
    """Kaydedilmis filtre. filter alani modul bazli JSON DSL."""
    __tablename__ = "saved_view"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name: Mapped[str] = mapped_column(Text, nullable=False)
    module: Mapped[str] = mapped_column(String(64), nullable=False)
    filter: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    sort: Mapped[str | None] = mapped_column(String(64))
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class SourceRun(Base):
    """Scraper/feed saglik kaydi. 'Sessiz olum'leri yakalamak icin."""
    __tablename__ = "source_run"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ok")
    items_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    #: tls | dns | timeout | http_403 | http_404 | http_429 | http_5xx |
    #: parser | circuit_open | unknown. Arayuz hata sinifini bununla gosterir.
    error_kind: Mapped[str | None] = mapped_column(String(24))
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("source_sync_batch.id", ondelete="SET NULL")
    )


class SourceSyncBatch(Base):
    """Manuel kaynak cekimlerinin kalici operasyonel ilerleme kaydi."""
    __tablename__ = "source_sync_batch"
    __table_args__ = (
        Index("source_sync_batch_scope_time_idx", "scope", text("created_at desc")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    scope: Mapped[str] = mapped_column(Text, nullable=False, default="opportunity")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    source_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    total_sources: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_sources: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ok_sources: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    empty_sources: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_sources: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Notification(Base):
    __tablename__ = "notification"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    kind: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    body: Mapped[str | None] = mapped_column(Text)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE")
    )
    importance: Mapped[int] = mapped_column(SmallInteger, default=1)
    dedup_key: Mapped[str] = mapped_column(Text, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
