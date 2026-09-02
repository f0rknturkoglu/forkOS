from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EntityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    title: str
    created_at: datetime
    updated_at: datetime


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_id: uuid.UUID | None
    entity_type: str | None
    verb: str
    payload: dict
    occurred_at: datetime


class SavedViewIn(BaseModel):
    name: str
    module: str
    filter: dict = {}
    sort: str | None = None
    pinned: bool = False
    position: int = 0


class SavedViewOut(SavedViewIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class SavedViewCreate(BaseModel):
    """POST /views govdesi: position sunucu tarafinda (max+1) hesaplanir."""

    name: str
    module: str
    filter: dict
    sort: str | None = None


class SavedViewPatch(BaseModel):
    """PATCH /views/{id} govdesi: verilen alanlar guncellenir."""

    name: str | None = None
    filter: dict | None = None
    sort: str | None = None
    pinned: bool | None = None


class RelatedOut(BaseModel):
    """GET /entities/{id}/related satiri: iliski + yon + karsi entity ozeti."""

    relation: str
    direction: str
    label: str
    entity: EntityOut


class LinkIn(BaseModel):
    from_id: uuid.UUID
    to_id: uuid.UUID
    relation: str = "related"


class TagOut(BaseModel):
    name: str
    count: int


class SourceRunOut(BaseModel):
    source: str
    status: str
    items_found: int
    error: str | None = None
    started_at: datetime
    finished_at: datetime | None = None


class NotificationOut(BaseModel):
    id: int
    kind: str
    title: str
    body: str | None
    entity_id: uuid.UUID | None
    entity_type: str | None = None
    importance: int
    created_at: datetime
    read_at: datetime | None
