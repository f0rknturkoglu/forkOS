"""Typed public goal workspace and inference snapshot."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.modules.goal.package_schemas import Closed, PlanningConstraints
from app.modules.goal.roadmap import RoadmapNodeOut
from app.modules.goal.strategy_schemas import Measurement


class GoalIdentity(Closed):
    id: UUID
    title: str
    description: str
    target_at: datetime | None
    parent_goal_id: UUID | None
    horizon: str


class SnapshotNode(RoadmapNodeOut):
    index: int


class SnapshotRoadmap(Closed):
    percent: int | None
    requirements: int
    known: int
    truncated: bool
    nodes: list[SnapshotNode] = Field(max_length=60)


class SnapshotTask(Closed):
    id: UUID
    title: str
    status: str
    recurring_template: bool


class SnapshotTopic(Closed):
    id: UUID
    title: str
    status: str
    area_id: UUID


class SnapshotResource(Closed):
    id: UUID
    title: str
    source: str
    topic_id: UUID
    has_url: bool
    pending_need: bool = False
    missing_source: bool = False


class SnapshotSlot(Closed):
    id: UUID
    entity_id: UUID
    day: date
    start_min: int | None
    duration_min: int | None


class SnapshotProject(Closed):
    id: UUID
    title: str
    percent: int | None
    completed: int
    total: int
    coverage: str


class SnapshotMeasurement(Closed):
    id: UUID
    title: str
    measurement: Measurement
    unit: str
    target_value: str
    measured_at: datetime | None
    source_key: str


class SnapshotOutcome(Closed):
    percent: str | None
    measurements: list[SnapshotMeasurement] = Field(max_length=10)


class ActivityWindow(Closed):
    count: int
    completed_todos: int
    evidence_ids: list[str] = Field(max_length=12)
    truncated: bool


class AcceptedRevision(Closed):
    id: UUID
    fingerprint: str
    constraints: PlanningConstraints | None
    assumptions: list[str]


class SnapshotReview(Closed):
    id: UUID
    created_at: datetime
    outcome_percent: int | None = None
    execution_percent: int | None = None


class GoalContextSnapshot(Closed):
    schema_version: Literal[2]
    collected_at: datetime
    goal: GoalIdentity
    roadmap: SnapshotRoadmap
    todos: list[SnapshotTask] = Field(max_length=100)
    learning: list[SnapshotTopic] = Field(max_length=100)
    resources: list[SnapshotResource] = Field(max_length=50)
    planned_slots: list[SnapshotSlot] = Field(max_length=100)
    projects: list[SnapshotProject] = Field(max_length=100)
    outcome: SnapshotOutcome
    activity_windows: dict[Literal["7", "30", "90"], ActivityWindow]
    accepted_revisions: list[AcceptedRevision] = Field(max_length=5)
    reviews: list[SnapshotReview] = Field(max_length=5)
    truncated: bool
    warnings: list[str]
    scope: str
    recorded_constraints: PlanningConstraints | None = None


class RoadmapOwner(Closed):
    goal_id: UUID
    node_id: UUID
