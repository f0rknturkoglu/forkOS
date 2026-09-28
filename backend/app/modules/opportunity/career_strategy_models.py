"""Evidence-bound C8 proposals; entity-backed to preserve link/search contracts."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import EntityBacked
from app.db import Base


class CareerActionProposal(EntityBacked, Base):
    __tablename__ = "career_action_proposal"
    ENTITY_TYPE = "career_action_proposal"

    id: Mapped[uuid.UUID] = EntityBacked._entity_pk()
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="proposed")
    title: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    sample_size: Mapped[int | None] = mapped_column(Integer)
    estimated_scope: Mapped[str | None] = mapped_column(String(120))
    related_goal_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("goal.id", ondelete="SET NULL")
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    strategy_revision: Mapped[str] = mapped_column(String(80), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    materialization_status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="pending"
    )
    target_type: Mapped[str | None] = mapped_column(String(32))
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="SET NULL")
    )
    warnings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
