"""Thin graph metadata; all operational status stays in canonical modules."""

import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import EntityBacked
from app.db import Base


class GoalRoadmapNode(EntityBacked, Base):
    __tablename__ = "goal_roadmap_node"
    ENTITY_TYPE = "goal_roadmap_node"
    id: Mapped[uuid.UUID] = EntityBacked._entity_pk()
    goal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("goal.id"), index=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("goal_roadmap_node.id"))
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("entity.id", ondelete="SET NULL")
    )
    kind: Mapped[str] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, default=0)
    weight: Mapped[Decimal] = mapped_column(Numeric(16, 4), default=1)
    progress_bearing: Mapped[bool] = mapped_column(Boolean, default=True)
    completion_gate: Mapped[bool] = mapped_column(Boolean, default=False)
    detached: Mapped[bool] = mapped_column(Boolean, default=False)
