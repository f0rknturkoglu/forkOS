from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import EntityBacked
from app.db import Base

# Ryot kulvari: film/dizi/anime/manga/kitap/oyun ve daha fazlasi
KINDS = [
    "movie", "show", "anime", "manga", "book",
    "audiobook", "podcast", "music", "game",
]
STATUSES = ["planned", "in_progress", "paused", "completed", "dropped"]


class MediaItem(EntityBacked, Base):
    __tablename__ = "media_item"
    ENTITY_TYPE = "media_item"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="planned")
    progress: Mapped[int | None] = mapped_column(Integer)
    total: Mapped[int | None] = mapped_column(Integer)
    score: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
