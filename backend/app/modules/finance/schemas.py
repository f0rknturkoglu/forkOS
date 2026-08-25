from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

# Abonelik markalari (ilk paket): WOW, YouTube, Spotify, Amazon Prime, iCloud+
SUB_BRANDS = ["wow", "youtube", "spotify", "amazon_prime", "icloud"]


def _check_sub(v: str | None) -> str | None:
    if v is not None and v not in SUB_BRANDS:
        raise ValueError(f"sub su olmali: {SUB_BRANDS}")
    return v


class ExpenseIn(BaseModel):
    title: str = Field(min_length=1)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="TRY", min_length=3, max_length=3)
    category: str = "other"
    spent_on: date = Field(default_factory=date.today)
    note: str | None = None
    sub: str | None = None

    @field_validator("sub")
    @classmethod
    def sub_known(cls, v: str | None) -> str | None:
        return _check_sub(v)


class ExpensePatch(BaseModel):
    title: str | None = None
    amount: Decimal | None = Field(None, gt=0, max_digits=12, decimal_places=2)
    currency: str | None = Field(None, min_length=3, max_length=3)
    category: str | None = None
    spent_on: date | None = None
    note: str | None = None
    sub: str | None = None

    @field_validator("sub")
    @classmethod
    def sub_known(cls, v: str | None) -> str | None:
        return _check_sub(v)


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
    sub: str | None = None

    @field_validator("sub")
    @classmethod
    def sub_known(cls, v: str | None) -> str | None:
        return _check_sub(v)


class RecurringPatch(BaseModel):
    title: str | None = None
    amount: Decimal | None = Field(None, gt=0, max_digits=12, decimal_places=2)
    category: str | None = None
    billing_day: int | None = Field(None, ge=1, le=31)
    frequency: str | None = None
    next_due_at: date | None = None
    active: bool | None = None
    note: str | None = None
    sub: str | None = None

    @field_validator("sub")
    @classmethod
    def sub_known(cls, v: str | None) -> str | None:
        return _check_sub(v)
