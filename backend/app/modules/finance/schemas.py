from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class ExpenseIn(BaseModel):
    title: str = Field(min_length=1)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="TRY", min_length=3, max_length=3)
    category: str = "other"
    spent_on: date = Field(default_factory=date.today)
    note: str | None = None


class ExpensePatch(BaseModel):
    title: str | None = None
    amount: Decimal | None = Field(None, gt=0, max_digits=12, decimal_places=2)
    currency: str | None = Field(None, min_length=3, max_length=3)
    category: str | None = None
    spent_on: date | None = None
    note: str | None = None


class RecurringIn(BaseModel):
    title: str = Field(min_length=1)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="TRY", min_length=3, max_length=3)
    category: str = "subscriptions"
    billing_day: int | None = Field(None, ge=1, le=31)
    frequency: str = "monthly"
    next_due_at: date | None = None
    active: bool = True
    note: str | None = None


class RecurringPatch(BaseModel):
    title: str | None = None
    amount: Decimal | None = Field(None, gt=0, max_digits=12, decimal_places=2)
    category: str | None = None
    billing_day: int | None = Field(None, ge=1, le=31)
    frequency: str | None = None
    next_due_at: date | None = None
    active: bool | None = None
    note: str | None = None
