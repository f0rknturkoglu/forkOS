"""Closed V2 compilation operations. Only server/user previews contain canonical IDs."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_serializer, model_validator


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PackageOperation(Closed):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")


class NodeData(Closed):
    title: str = Field(min_length=1, max_length=300)
    kind: Literal["period", "phase", "milestone", "record", "child_goal"]
    description: str | None = Field(None, max_length=3000)
    position: int = Field(0, ge=0, le=1000)
    weight: Decimal = Field(
        Decimal(1), gt=0, le=100, max_digits=16, decimal_places=4, allow_inf_nan=False
    )
    progress_bearing: bool = True
    completion_gate: bool = False


class NewNode(PackageOperation):
    type: Literal["roadmap.create"]
    data: NodeData
    goal_ref: str = Field(max_length=64)
    parent_ref: str | None = Field(None, max_length=64)
    target_ref: str | None = Field(None, max_length=64)
    depends_on: list[str] = Field(default_factory=list, max_length=12)


class EditNode(PackageOperation):
    type: Literal["roadmap.update"]
    target_id: UUID
    data: NodeData
    parent_ref: str | None = Field(None, max_length=64)
    detached: bool = False
    depends_on: list[str] | None = Field(None, max_length=12)


class AreaData(Closed):
    title: str = Field(min_length=1, max_length=100)


class NewArea(PackageOperation):
    type: Literal["learning.area"]
    data: AreaData


class TopicData(Closed):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(None, max_length=5000)


class NewTopic(PackageOperation):
    type: Literal["learning.topic"]
    data: TopicData
    area_ref: str = Field(max_length=64)
    parent_ref: str | None = Field(None, max_length=64)


class TaskData(Closed):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(None, max_length=5000)
    due_at: datetime | None = None
    priority: int = Field(2, ge=0, le=3)


class NewTask(PackageOperation):
    type: Literal["todo.create"]
    data: TaskData
    project_ref: str | None = Field(None, max_length=64)
    topic_ref: str | None = Field(None, max_length=64)


class ScheduleData(Closed):
    day: date
    duration_min: int = Field(30, ge=1, le=480)
    start_min: int | None = Field(None, ge=0, le=1439)
    note: str | None = Field(None, max_length=5000)
    calendar_override: bool = False

    @model_validator(mode="after")
    def bounded_day(self):
        if self.start_min is not None and self.start_min + self.duration_min > 1440:
            raise ValueError("Plan gün sınırını geçemez")
        return self


class ScheduleTask(PackageOperation):
    type: Literal["plan.schedule"]
    data: ScheduleData
    task_ref: str = Field(max_length=64)
    replace_slot_id: UUID | None = None


class LinkData(Closed):
    relation: Literal[
        "advances_goal",
        "advances_goal_milestone",
        "belongs_to",
        "prepares_for",
        "learns_from",
        "references",
    ]


class ConnectRecord(PackageOperation):
    type: Literal["record.link"]
    data: LinkData
    from_ref: str = Field(max_length=64)
    to_ref: str = Field(max_length=64)


class PlanningConstraints(Closed):
    daily_capacity_min: int = Field(30, ge=1, le=480)
    capacity_confirmed: bool = False
    unavailable_days: list[date] = Field(default_factory=list, max_length=30)
    weekdays: list[int] = Field(default_factory=lambda: list(range(7)), min_length=1, max_length=7)
    available_start_min: int | None = Field(None, ge=0, le=1439)
    available_end_min: int | None = Field(None, ge=1, le=1440)

    @model_validator(mode="after")
    def hours(self):
        if any(d < 0 or d > 6 for d in self.weekdays) or len(set(self.weekdays)) != len(
            self.weekdays
        ):
            raise ValueError("Geçersiz çalışma günleri")
        if (self.available_start_min is None) != (self.available_end_min is None):
            raise ValueError("Çalışma saatlerinin başlangıç ve bitişi birlikte verilmeli")
        if (
            self.available_start_min is not None
            and self.available_end_min <= self.available_start_min
        ):
            raise ValueError("Çalışma saati aralığı geçersiz")
        return self


class ResourceData(Closed):
    title: str = Field(min_length=1, max_length=300)
    kind: Literal["link", "video", "article", "course", "book", "doc", "exercise"] = "exercise"
    note: str | None = Field(None, max_length=5000)


class NewResource(PackageOperation):
    type: Literal["learning.resource"]
    data: ResourceData
    topic_ref: str = Field(max_length=64)


class TaskPatch(Closed):
    title: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = Field(None, max_length=5000)
    priority: int | None = Field(None, ge=0, le=3)
    due_at: datetime | None = None

    @model_validator(mode="after")
    def meaningful(self):
        if not self.model_fields_set:
            raise ValueError("Görev düzenlemesi boş olamaz")
        if any(
            k in self.model_fields_set and getattr(self, k) is None for k in ("title", "priority")
        ):
            raise ValueError("Görev adı ve önceliği boş olamaz")
        return self

    @model_serializer(mode="wrap")
    def supplied(self, handler):
        return {k: v for k, v in handler(self).items() if k in self.model_fields_set}


class EditTask(PackageOperation):
    type: Literal["todo.update"]
    target_id: UUID
    data: TaskPatch
