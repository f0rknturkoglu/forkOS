"""Operational goals, distinct from H2 semantic intent and project milestones."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import EntityBacked
from app.db import Base


class Goal(EntityBacked, Base):
    __tablename__ = "goal"
    ENTITY_TYPE = "goal"

    id: Mapped[uuid.UUID] = EntityBacked._entity_pk()
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    horizon: Mapped[str] = mapped_column(String(16), nullable=False, default="quarter")
    description: Mapped[str | None] = mapped_column(Text)
    target_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # H2 memory is a narrative source, not synchronized operational state.
    source_memory_id: Mapped[str | None] = mapped_column(String(64))


class GoalMilestone(EntityBacked, Base):
    __tablename__ = "goal_milestone"
    ENTITY_TYPE = "goal_milestone"

    id: Mapped[uuid.UUID] = EntityBacked._entity_pk()
    goal_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("goal.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
