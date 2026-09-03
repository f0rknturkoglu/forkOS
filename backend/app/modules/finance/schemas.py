from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.core.time import local_today

# Rozeti/logosu hazir gelen markalar. Liste KISIT DEGIL: "sub" serbest bir
# slug'dir, buradakiler yalnizca arayuzde renkli rozet kazanir. Netflix'i
# eklemek icin once bu listeye yazmak gerekmiyor.
KNOWN_SUB_BRANDS = [
    "netflix",
    "youtube",
    "spotify",
    "amazon_prime",
    "icloud",
    "wow",
    "disney_plus",
    "chatgpt",
]
SUB_SLUG = re.compile(r"^[a-z0-9][a-z0-9_]{0,31}$")

FREQUENCIES = ["monthly", "quarterly", "yearly"]


def _check_sub(v: str | None) -> str | None:
    if v in (None, ""):
        return None
    if not SUB_SLUG.match(v):
        raise ValueError("sub kucuk harf, rakam ve alt cizgiden olusmali (en fazla 32)")
    return v


def _check_frequency(v: str | None) -> str | None:
    if v is not None and v not in FREQUENCIES:
        raise ValueError(f"frequency su olmali: {FREQUENCIES}")
    return v


class ExpenseIn(BaseModel):
    title: str = Field(min_length=1)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="TRY", min_length=3, max_length=3)
    category: str = "other"
    spent_on: date = Field(default_factory=local_today)
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


class IncomeIn(BaseModel):
    title: str = Field(min_length=1)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="TRY", min_length=3, max_length=3)
    category: str = "salary"
    received_on: date = Field(default_factory=local_today)
    note: str | None = None


class IncomePatch(BaseModel):
    title: str | None = None
    amount: Decimal | None = Field(None, gt=0, max_digits=12, decimal_places=2)
    currency: str | None = Field(None, min_length=3, max_length=3)
    category: str | None = None
    received_on: date | None = None
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
    sub: str | None = None

    @field_validator("sub")
    @classmethod
    def sub_known(cls, v: str | None) -> str | None:
        return _check_sub(v)

    @field_validator("frequency")
    @classmethod
    def frequency_known(cls, v: str) -> str:
        return _check_frequency(v) or "monthly"


class RecurringPatch(BaseModel):
    title: str | None = None
    amount: Decimal | None = Field(None, gt=0, max_digits=12, decimal_places=2)
    currency: str | None = Field(None, min_length=3, max_length=3)
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

    @field_validator("frequency")
    @classmethod
    def frequency_known(cls, v: str | None) -> str | None:
        return _check_frequency(v)
