from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import EntityBacked
from app.db import Base


class PomodoroSession(EntityBacked, Base):
    __tablename__ = "pomodoro_session"
    ENTITY_TYPE = "pomodoro_session"

    id: Mapped[uuid.UUID] = EntityBacked._entity_pk()
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    planned_min: Mapped[int] = mapped_column(Integer, nullable=False, default=25)
    actual_min: Mapped[int | None] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="focus")
    context_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="SET NULL"))
    topic: Mapped[str | None] = mapped_column(Text)
    interrupted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
