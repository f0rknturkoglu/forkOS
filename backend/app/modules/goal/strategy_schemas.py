"""Closed strategy contracts. Decimal values never accept NaN/infinity."""

from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.goal.schemas import GoalOut, _title

Number = Decimal
ProviderKey = Literal[
    "manual",
    "applications_applied",
    "applications_interview",
    "applications_offer",
    "goal_milestones",
    "linked_completion",
]


class MetricConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    linked_entity_id: UUID | None = None
    since: AwareDatetime | None = None


class KeyResultIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    status: Literal["active", "paused", "completed", "retired"] = "active"
    unit: str = Field(default="adet", min_length=1, max_length=60)
    direction: Literal["increase", "decrease"] = "increase"
    baseline_value: Number = Field(
        default=Decimal(0), max_digits=20, decimal_places=4, allow_inf_nan=False
    )
    target_value: Number = Field(max_digits=20, decimal_places=4, allow_inf_nan=False)
    weight: Number = Field(
        default=Decimal(1), gt=0, max_digits=16, decimal_places=4, allow_inf_nan=False
    )
    source_key: ProviderKey = "manual"
    source_config: MetricConfig = Field(default_factory=MetricConfig)
    manual_value: Number | None = Field(
        default=None, max_digits=20, decimal_places=4, allow_inf_nan=False
    )
    trajectory_model: Literal["linear", "deadline", "none"] = "none"
    start_at: AwareDatetime | None = None
    target_at: AwareDatetime | None = None
    position: int = 0
    _clean = field_validator("title")(_title)

    @model_validator(mode="after")
    def valid(self):
        delta = self.target_value - self.baseline_value
        if (
            delta == 0
            or (self.direction == "increase" and delta < 0)
            or (self.direction == "decrease" and delta > 0)
        ):
            raise ValueError("Hedef değeri yönle uyumlu ve başlangıçtan farklı olmalı")
        if self.trajectory_model == "linear" and (not self.start_at or not self.target_at):
            raise ValueError("Doğrusal rota için başlangıç ve hedef tarihi gerekli")
        if self.start_at and self.target_at and self.target_at <= self.start_at:
            raise ValueError("Hedef tarihi başlangıçtan sonra olmalı")
        if self.trajectory_model == "deadline" and not self.target_at:
            raise ValueError("Son tarih rotası için hedef tarihi gerekli")
        if self.source_key == "linked_completion" and not self.source_config.linked_entity_id:
            raise ValueError("Bağlı kayıt gerekli")
        if self.source_key != "linked_completion" and self.source_config.linked_entity_id:
            raise ValueError("Bu sağlayıcı bağlı kayıt kabul etmez")
        if (
            self.source_key in {"manual", "goal_milestones", "linked_completion"}
            and self.source_config.since
        ):
            raise ValueError("Bu sağlayıcı zaman filtresi kabul etmez")
        return self


class PlanIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=300)
    start_at: AwareDatetime
    end_at: AwareDatetime
    status: Literal["active", "paused", "archived", "superseded"] = "active"
    summary: str | None = Field(default=None, max_length=5000)
    narrative_path: str | None = Field(default=None, max_length=500)
    change_reason: str | None = Field(default=None, max_length=1000)
    _clean = field_validator("title")(_title)

    @model_validator(mode="after")
    def dates(self):
        if self.end_at <= self.start_at:
            raise ValueError("Plan bitişi başlangıçtan sonra olmalı")
        return self


class PlanOut(PlanIn):
    id: UUID
    revision: int
    created_at: AwareDatetime
    updated_at: AwareDatetime


class PillarIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=300)
    weight: Number = Field(
        default=Decimal(1), gt=0, max_digits=16, decimal_places=4, allow_inf_nan=False
    )
    position: int = 0
    _clean = field_validator("title")(_title)


class PillarOut(PillarIn):
    id: UUID
    plan_id: UUID


class Reason(BaseModel):
    code: str
    explanation: str


class Measurement(BaseModel):
    current_value: Number | None
    progress_percent: int | None
    expected_percent: int | None = None
    trajectory: Literal["ahead", "on_track", "behind", "not_applicable", "unknown"] = "unknown"
    confidence: Literal["high", "medium", "low"] = "low"
    reasons: list[Reason] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class KeyResultOut(KeyResultIn):
    id: UUID
    goal_id: UUID
    measured_at: AwareDatetime | None
    measurement: Measurement


class ObjectiveState(BaseModel):
    goal: GoalOut
    key_results: list[KeyResultOut]
    strategic_progress_percent: int | None
    milestone_progress_percent: int | None
    measurable_count: int
    active_kr_count: int
    confidence: Literal["high", "medium", "low"]
    reasons: list[Reason]
    trajectory: str
    expected_percent: int | None
    linked_entity_ids: list[UUID]
    evidence_refs: list[str]


class Allocation(BaseModel):
    entity_id: UUID
    count: Decimal
    share_percent: float


class Alignment(BaseModel):
    method: str = "meaningful-events-links-v1"
    window_days: Literal[7, 30, 90]
    start_at: AwareDatetime
    end_at: AwareDatetime
    eligible_count: int
    linked_count: int
    unaligned_count: int
    percent: int | None
    objectives: list[Allocation]
    pillars: list[Allocation]
    warnings: list[Reason]
    evidence_refs: list[str]


class Finding(BaseModel):
    code: str
    severity: Literal["info", "warning"] = "warning"
    entity_refs: list[str]
    evidence_refs: list[str]
    observed_facts: str
    window_start: AwareDatetime
    window_end: AwareDatetime


class Aggregate(BaseModel):
    id: UUID
    progress_percent: int | None
    measurable_objectives: int
    active_objectives: int
    confidence: str
    method: str = "weighted-active-objectives-pillar-weight-v1; minimum 80% measurable coverage"


class ProviderMetadata(BaseModel):
    key: ProviderKey
    label: str
    description: str


class StrategyOverview(BaseModel):
    schema_version: int = 1
    method: str = "strategy-v1"
    calculated_at: AwareDatetime
    plans: list[PlanOut]
    pillars: list[PillarOut]
    objectives: list[ObjectiveState]
    plan_progress: list[Aggregate]
    pillar_progress: list[Aggregate]
    alignment: Alignment
    findings: list[Finding]
    providers: list[ProviderMetadata]
    warnings: list[Reason]


class HistoryItem(BaseModel):
    id: UUID
    kind: Literal["plan_revision", "review_snapshot"]
    occurred_at: AwareDatetime
    title: str
    state: dict


class StrategyHistory(BaseModel):
    truncated: bool = False
    items: list[HistoryItem]
    comparable: bool
    comparison_reason: str
    progress_deltas: dict[str, int] = Field(default_factory=dict)
    alignment_delta: int | None = None
