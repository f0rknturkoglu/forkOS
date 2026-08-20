from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import EntityBacked
from app.db import Base


class Habit(EntityBacked, Base):
    __tablename__ = "habit"
    ENTITY_TYPE = "habit"

    id: Mapped[uuid.UUID] = EntityBacked._entity_pk()
    cadence: Mapped[str] = mapped_column(String(16), nullable=False, default="daily")
    target_per_week: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    color: Mapped[str | None] = mapped_column(String(32))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class HabitLog(Base):
    __tablename__ = "habit_log"

    habit_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("habit.id", ondelete="CASCADE"), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    note: Mapped[str | None] = mapped_column(Text)
