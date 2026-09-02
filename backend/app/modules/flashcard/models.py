from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import EntityBacked
from app.db import Base


class FlashcardDeck(EntityBacked, Base):
    """Kart destesi. Entity.title destek adini tasir (global arama bulur)."""

    __tablename__ = "flashcard_deck"
    ENTITY_TYPE = "flashcard_deck"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class FlashcardCard(EntityBacked, Base):
    """Tek kart. Entity.title on yuzdur; arka yuz `back` kolonunda.

    `due_at` NULL = henuz hic tekrar edilmemis (yeni kart). SM-2 alanlari
    (interval_days, ease) tekrar edildikce guncellenir.
    """

    __tablename__ = "flashcard_card"
    ENTITY_TYPE = "flashcard_card"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE"), primary_key=True
    )
    deck_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("flashcard_deck.id", ondelete="CASCADE")
    )
    front: Mapped[str] = mapped_column(Text, nullable=False, default="")
    back: Mapped[str] = mapped_column(Text, nullable=False, default="")
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ease: Mapped[float] = mapped_column(Float, nullable=False, default=2.5)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lapses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    suspended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
