from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from app.core.time import local_today

from sqlalchemy import CHAR, Boolean, Date, Numeric, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import EntityBacked
from app.db import Base


class Expense(EntityBacked, Base):
    __tablename__ = "expense"
    ENTITY_TYPE = "expense"

    id: Mapped[uuid.UUID] = EntityBacked._entity_pk()
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(CHAR(3), default="TRY")
    category: Mapped[str] = mapped_column(Text)
    spent_on: Mapped[date] = mapped_column(Date, default=local_today)
    note: Mapped[str | None] = mapped_column(Text)
    # abonelik markasi (netflix/spotify/...) -- gorsel rozet icin serbest slug
    sub: Mapped[str | None] = mapped_column(Text)


class Income(EntityBacked, Base):
    """Gelir kaydi. Gider ile ayni sekle sahip; net hesabi ikisinden cikar."""

    __tablename__ = "income"
    ENTITY_TYPE = "income"

    id: Mapped[uuid.UUID] = EntityBacked._entity_pk()
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(CHAR(3), default="TRY")
    category: Mapped[str] = mapped_column(Text, default="salary")
    received_on: Mapped[date] = mapped_column(Date, default=local_today)
    note: Mapped[str | None] = mapped_column(Text)


class RecurringPayment(EntityBacked, Base):
    __tablename__ = "recurring_payment"
    ENTITY_TYPE = "recurring_payment"

    id: Mapped[uuid.UUID] = EntityBacked._entity_pk()
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(CHAR(3), default="TRY")
    category: Mapped[str] = mapped_column(Text, default="subscriptions")
    billing_day: Mapped[int | None] = mapped_column(SmallInteger)
    frequency: Mapped[str] = mapped_column(Text, default="monthly")
    next_due_at: Mapped[date | None] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[str | None] = mapped_column(Text)
    # abonelik markasi (netflix/spotify/...) -- gorsel rozet icin serbest slug
    sub: Mapped[str | None] = mapped_column(Text)
