from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import EntityBacked
from app.db import Base


class GoalStudioSession(EntityBacked, Base):
    __tablename__ = "goal_studio_session"
    ENTITY_TYPE = "goal_studio_session"
    id: Mapped[uuid.UUID] = EntityBacked._entity_pk()
    client_uuid: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), unique=True)
    state: Mapped[str] = mapped_column(String(32))
    data: Mapped[dict] = mapped_column(JSONB)


class GoalStudioRevision(EntityBacked, Base):
    __tablename__ = "goal_studio_revision"
    ENTITY_TYPE = "goal_studio_revision"
    id: Mapped[uuid.UUID] = EntityBacked._entity_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("goal_studio_session.id"))
    state: Mapped[str] = mapped_column(String(32))
    fingerprint: Mapped[str] = mapped_column(String(64))
    proposal: Mapped[dict] = mapped_column(JSONB)
    before: Mapped[dict] = mapped_column(JSONB)
    results: Mapped[dict] = mapped_column(JSONB)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None]
