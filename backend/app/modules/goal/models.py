"""Operational goals, distinct from H2 semantic intent and project milestones."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
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
    strategic_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("strategic_plan.id")
    )
    pillar_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("strategic_pillar.id")
    )
    parent_goal_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("goal.id")
    )
    priority: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    weight: Mapped[Decimal] = mapped_column(Numeric(16, 4), default=1, nullable=False)
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


class StrategicPlan(EntityBacked, Base):
    __tablename__ = "strategic_plan"
    ENTITY_TYPE = "strategic_plan"
    id: Mapped[uuid.UUID] = EntityBacked._entity_pk()
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    narrative_path: Mapped[str | None] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class StrategicPillar(EntityBacked, Base):
    __tablename__ = "strategic_pillar"
    ENTITY_TYPE = "strategic_pillar"
    id: Mapped[uuid.UUID] = EntityBacked._entity_pk()
    plan_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("strategic_plan.id"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    weight: Mapped[Decimal] = mapped_column(Numeric(16, 4), default=1, nullable=False)


class StrategicPlanRevision(EntityBacked, Base):
    """Immutable, inspectable entity: no support-table PK exception needed."""

    __tablename__ = "strategic_plan_revision"
    ENTITY_TYPE = "strategic_plan_revision"
    __table_args__ = (UniqueConstraint("plan_id", "revision"),)
    id: Mapped[uuid.UUID] = EntityBacked._entity_pk()
    plan_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("strategic_plan.id"), nullable=False
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[dict] = mapped_column(JSONB, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)


class KeyResult(EntityBacked, Base):
    __tablename__ = "key_result"
    ENTITY_TYPE = "key_result"
    id: Mapped[uuid.UUID] = EntityBacked._entity_pk()
    goal_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("goal.id"), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    unit: Mapped[str] = mapped_column(String(60), default="adet", nullable=False)
    direction: Mapped[str] = mapped_column(String(16), default="increase", nullable=False)
    baseline_value: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    target_value: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    weight: Mapped[Decimal] = mapped_column(Numeric(16, 4), default=1, nullable=False)
    source_key: Mapped[str] = mapped_column(String(64), default="manual", nullable=False)
    source_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    manual_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    measured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trajectory_model: Mapped[str] = mapped_column(String(16), default="none", nullable=False)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    target_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
