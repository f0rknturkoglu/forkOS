from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import EntityBacked
from app.db import Base

KINDS = [
    "movie",
    "show",
    "anime",
    "manga",
    "book",
    "audiobook",
    "podcast",
    "music",
    "game",
]
STATUSES = ["planned", "in_progress", "paused", "completed", "dropped"]
UNIT_TYPES = [
    "season",
    "episode",
    "volume",
    "chapter",
    "album",
    "track",
    "podcast_episode",
]
CYCLE_STATUSES = ["active", "paused", "completed", "dropped"]
CONSUMPTION_ACTIONS = ["quick", "set", "complete_unit", "uncomplete_unit", "finish"]
MEASURES = ["item", "episode", "chapter", "page", "minute", "hour", "track"]
MEDIA_COLLECTION_ITEM_RELATION = "media.collection_item"


def _quoted(values: list[str]) -> str:
    return ",".join(f"'{value}'" for value in values)


class MediaItem(EntityBacked, Base):
    __tablename__ = "media_item"
    __table_args__ = (
        CheckConstraint(f"kind in ({_quoted(KINDS)})", name="media_item_kind_check"),
        CheckConstraint(f"status in ({_quoted(STATUSES)})", name="media_item_status_check"),
        CheckConstraint(
            f"progress_measure is null or progress_measure in ({_quoted(MEASURES)})",
            name="media_item_progress_measure_check",
        ),
    )
    ENTITY_TYPE = "media_item"

    id: Mapped[uuid.UUID] = EntityBacked._entity_pk()
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="planned")
    progress: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    score: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    summary: Mapped[str | None] = mapped_column(Text)
    release_date: Mapped[date | None] = mapped_column(Date)
    progress_measure: Mapped[str | None] = mapped_column(Text)
    review: Mapped[str | None] = mapped_column(Text)
    favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    owned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ownership: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    monitored: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    provider: Mapped[str | None] = mapped_column(Text)
    provider_ids: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    cover_url: Mapped[str | None] = mapped_column(Text)
    cover_path: Mapped[str | None] = mapped_column(Text)
    backdrop_url: Mapped[str | None] = mapped_column(Text)
    backdrop_path: Mapped[str | None] = mapped_column(Text)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MediaUnit(EntityBacked, Base):
    __tablename__ = "media_unit"
    __table_args__ = (
        CheckConstraint(
            f"unit_type in ({_quoted(UNIT_TYPES)})", name="media_unit_type_check"
        ),
        CheckConstraint(
            f"progress_measure is null or progress_measure in ({_quoted(MEASURES)})",
            name="media_unit_progress_measure_check",
        ),
        Index("media_unit_media_idx", "media_id", "unit_type", "number"),
        Index(
            "media_unit_provider_ref_uniq",
            "media_id",
            "provider",
            "provider_id",
            unique=True,
            postgresql_where=text("provider is not null and provider_id is not null"),
        ),
    )
    ENTITY_TYPE = "media_unit"

    id: Mapped[uuid.UUID] = EntityBacked._entity_pk()
    media_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("media_item.id", ondelete="RESTRICT"), nullable=False
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("media_unit.id", ondelete="SET NULL")
    )
    unit_type: Mapped[str] = mapped_column(Text, nullable=False)
    number: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    duration_min: Mapped[int | None] = mapped_column(Integer)
    release_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    progress_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    progress_measure: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[str | None] = mapped_column(Text)
    provider_id: Mapped[str | None] = mapped_column(Text)
    provider_ids: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    cover_url: Mapped[str | None] = mapped_column(Text)
    cover_path: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MediaCycle(EntityBacked, Base):
    __tablename__ = "media_cycle"
    __table_args__ = (
        UniqueConstraint("media_id", "ordinal", name="media_cycle_media_ordinal_uniq"),
        CheckConstraint(
            f"status in ({_quoted(CYCLE_STATUSES)})", name="media_cycle_status_check"
        ),
        Index(
            "media_cycle_one_open_idx",
            "media_id",
            unique=True,
            postgresql_where=text(
                "completed_at is null and status in ('active','paused')"
            ),
        ),
    )
    ENTITY_TYPE = "media_cycle"

    id: Mapped[uuid.UUID] = EntityBacked._entity_pk()
    media_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("media_item.id", ondelete="RESTRICT"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_caught_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    score: Mapped[int | None] = mapped_column(SmallInteger)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MediaConsumption(EntityBacked, Base):
    __tablename__ = "media_consumption"
    __table_args__ = (
        UniqueConstraint("client_uuid", name="media_consumption_client_uuid_uniq"),
        CheckConstraint(
            f"action in ({_quoted(CONSUMPTION_ACTIONS)})",
            name="media_consumption_action_check",
        ),
        CheckConstraint(
            f"measure is null or measure in ({_quoted(MEASURES)})",
            name="media_consumption_measure_check",
        ),
        Index("media_consumption_media_time_idx", "media_id", text("occurred_at desc")),
        Index("media_consumption_cycle_time_idx", "cycle_id", text("occurred_at desc")),
    )
    ENTITY_TYPE = "media_consumption"

    id: Mapped[uuid.UUID] = EntityBacked._entity_pk()
    media_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("media_item.id", ondelete="RESTRICT"), nullable=False
    )
    cycle_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("media_cycle.id", ondelete="RESTRICT"), nullable=False
    )
    unit_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("media_unit.id", ondelete="SET NULL")
    )
    client_uuid: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    measure: Mapped[str | None] = mapped_column(Text)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    progress_after: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    duration_min: Mapped[int | None] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MediaCollection(EntityBacked, Base):
    __tablename__ = "media_collection"
    ENTITY_TYPE = "media_collection"

    id: Mapped[uuid.UUID] = EntityBacked._entity_pk()
    description: Mapped[str | None] = mapped_column(Text)
    color: Mapped[str | None] = mapped_column(String(16))
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
