"""A4: Semantic Promotion & Durable Memory aday tablosu.

Operasyonel destek tablosudur; bağımsız aranabilir/linklenebilir entity değildir.
Kanonik bilgi f0rknbrain Vault'unda (30 Knowledge/Memory/) ve forkOS operasyonel
tablolarında yaşar.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AgentSemanticCandidate(Base):
    """Kalıcı semantik hafıza adayı."""

    __tablename__ = "agent_semantic_candidate"
    __table_args__ = (
        UniqueConstraint("candidate_key", name="uq_agent_semantic_candidate_key"),
        CheckConstraint(
            "status in ('proposed', 'needs_review', 'ready', 'promoted', 'rejected', 'stale')",
            name="ck_agent_semantic_candidate_status",
        ),
        CheckConstraint(
            "kind in ('identity', 'preference', 'correction', 'constraint', 'goal', 'decision', 'lesson', 'project_knowledge', 'reference', 'commitment')",
            name="ck_agent_semantic_candidate_kind",
        ),
        CheckConstraint(
            "primary_evidence_class in ('explicit_user', 'canonical_source', 'episode_derived', 'model_derived')",
            name="ck_agent_semantic_candidate_evidence",
        ),
        CheckConstraint(
            "suggested_destination in ('operational', 'hot_memory', 'durable_vault', 'procedural_candidate', 'discard')",
            name="ck_agent_semantic_candidate_destination",
        ),
        CheckConstraint("recurrence_count >= 1", name="ck_agent_semantic_candidate_recurrence"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_key: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    statement: Mapped[str] = mapped_column(String(500), nullable=False)
    scope: Mapped[str] = mapped_column(String(32), nullable=False, default="global")
    scope_project: Mapped[str | None] = mapped_column(String(64), nullable=True)
    subject_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    domains: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    suggested_destination: Mapped[str] = mapped_column(String(32), nullable=False)
    primary_evidence_class: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_refs: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rationale: Mapped[str | None] = mapped_column(String(500), nullable=True)
    conditions: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    exceptions: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    sensitivity: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    remote_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="proposed")
    reviewed_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    possible_related_card_ids: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    recurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revision: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
