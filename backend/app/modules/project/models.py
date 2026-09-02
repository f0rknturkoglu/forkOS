from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import ARRAY, Date, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import EntityBacked
from app.db import Base


class Project(EntityBacked, Base):
    __tablename__ = "project"
    ENTITY_TYPE = "project"

    id: Mapped[uuid.UUID] = EntityBacked._entity_pk()
    status: Mapped[str] = mapped_column(Text, default="active")
    github_repo: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    stack: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    next_action: Mapped[str | None] = mapped_column(Text)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    position: Mapped[int] = mapped_column(Integer, default=0)


class Milestone(EntityBacked, Base):
    __tablename__ = "milestone"
    ENTITY_TYPE = "milestone"

    #: PK entity.id'ye FK (kural 1) -- deadline_provider entity tablosundan
    #: baslik okur; milestone son tarihleri /api/deadlines'a boyle ulasir.
    id: Mapped[uuid.UUID] = EntityBacked._entity_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("project.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(Text)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    position: Mapped[int] = mapped_column(Integer, default=0)


class GithubActivity(Base):
    __tablename__ = "github_activity"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    repo: Mapped[str] = mapped_column(Text, primary_key=True)
    commit_count: Mapped[int] = mapped_column(Integer, default=0)
