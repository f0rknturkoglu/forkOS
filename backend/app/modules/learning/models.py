from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, SmallInteger, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import EntityBacked
from app.db import Base


class Course(EntityBacked, Base):
    __tablename__ = "course"
    ENTITY_TYPE = "course"
    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE"), primary_key=True
    )
    platform: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="planned")
    progress_pct: Mapped[int] = mapped_column(SmallInteger, default=0)
    started_at: Mapped[date | None] = mapped_column(Date)
    completed_at: Mapped[date | None] = mapped_column(Date)
    certificate_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="SET NULL")
    )
    notes: Mapped[str | None] = mapped_column(Text)
