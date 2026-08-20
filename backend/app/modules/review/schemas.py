from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel


class ReviewPreview(BaseModel):
    kind: str
    period_start: date
    period_end: date
    stats: dict
    unfinished_todos: list[dict]


class ReviewIn(BaseModel):
    kind: str
    period_start: date
    decisions: dict = {}
    note: str | None = None


class ReviewOut(BaseModel):
    id: uuid.UUID
    kind: str
    period_start: date
    period_end: date
    stats: dict
    decisions: dict
    note: str | None
