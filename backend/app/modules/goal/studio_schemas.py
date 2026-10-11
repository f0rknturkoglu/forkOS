"""Versioned, closed proposals wrapping the canonical Goal service contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_serializer, model_validator

from app.modules.goal.schemas import GoalIn, GoalMilestoneIn, GoalMilestonePatch, GoalPatch
from app.modules.goal.strategy_schemas import KeyResultIn, PillarIn, PlanIn


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StudioGoalIn(GoalIn):
    model_config = ConfigDict(extra="forbid")


class StudioGoalPatch(GoalPatch):
    model_config = ConfigDict(extra="forbid")

    @model_serializer(mode="wrap")
    def supplied_fields(self, handler):
        # Missing patch fields must stay missing through preview, storage and HTTP roundtrips.
        return {key: value for key, value in handler(self).items() if key in self.model_fields_set}


class StudioMilestoneIn(GoalMilestoneIn):
    model_config = ConfigDict(extra="forbid")


class StudioMilestonePatch(GoalMilestonePatch):
    model_config = ConfigDict(extra="forbid")

    @model_serializer(mode="wrap")
    def supplied_fields(self, handler):
        return {key: value for key, value in handler(self).items() if key in self.model_fields_set}


class Operation(Closed):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")


class NewPlan(Operation):
    type: Literal["plan.create"]
    data: PlanIn


class NewPillar(Operation):
    type: Literal["pillar.create"]
    plan_ref: str = Field(max_length=64)
    data: PillarIn


class NewGoal(Operation):
    type: Literal["goal.create"]
    data: StudioGoalIn
    plan_ref: str | None = Field(None, max_length=64)
    pillar_ref: str | None = Field(None, max_length=64)
    parent_ref: str | None = Field(None, max_length=64)


class EditGoal(Operation):
    type: Literal["goal.update"]
    target_id: UUID
    data: StudioGoalPatch


class SaveKR(Operation):
    type: Literal["key_result.save"]
    goal_ref: str = Field(max_length=64)
    target_id: UUID | None = None
    data: KeyResultIn


class NewMilestone(Operation):
    type: Literal["milestone.create"]
    goal_ref: str = Field(max_length=64)
    data: StudioMilestoneIn


class EditMilestone(Operation):
    type: Literal["milestone.update"]
    target_id: UUID
    data: StudioMilestonePatch


StudioOperation = Annotated[
    NewPlan | NewPillar | NewGoal | EditGoal | SaveKR | NewMilestone | EditMilestone,
    Field(discriminator="type"),
]


class StudioProposal(Closed):
    schema_version: Literal[1] = 1
    rationale: str = Field(min_length=1, max_length=3000)
    assumptions: list[str] = Field(default_factory=list, max_length=12)
    missing_information: list[str] = Field(default_factory=list, max_length=12)
    warnings: list[str] = Field(default_factory=list, max_length=12)
    evidence_refs: list[UUID] = Field(default_factory=list, max_length=30)
    operations: list[StudioOperation] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def bounded(self):
        if any(
            len(v) > 500
            for values in (self.assumptions, self.missing_information, self.warnings)
            for v in values
        ):
            raise ValueError("Açıklamalar en fazla 500 karakter olabilir")
        keys = [op.key for op in self.operations]
        if len(set(keys)) != len(keys):
            raise ValueError("İşlem anahtarları tekrarlanamaz")
        targets = [str(op.target_id) for op in self.operations if getattr(op, "target_id", None)]
        if len(set(targets)) != len(targets):
            raise ValueError("Aynı kayıt bir revizyonda iki kez düzenlenemez")
        for op in self.operations:
            for value in op.data.model_dump().values():
                if isinstance(value, datetime) and value.tzinfo is None:
                    raise ValueError("Tarihler saat dilimi içermeli")
            if isinstance(op, NewGoal) and op.data.source_memory_id:
                raise ValueError(
                    "Goal Studio bu sürümde H2 hafıza bağlamı göndermez; yeni hafıza referansı kabul edilmez"
                )
            if isinstance(op, SaveKR) and op.data.manual_value is not None:
                raise ValueError(
                    "Goal Studio ölçüm yazmaz; güncel değer normal KR arayüzünde kullanıcı tarafından girilir"
                )
            if isinstance(op, EditMilestone) and op.data.completed is not None:
                raise ValueError(
                    "Model önerisi tamamlanma kanıtı değildir; milestone tamamlama normal arayüzdedir"
                )
        return self


class StudioSessionIn(Closed):
    client_uuid: UUID
    goal_id: UUID | None = None


class StudioTurnIn(Closed):
    client_uuid: UUID
    message: str = Field(min_length=1, max_length=6000)


class StudioDecisionIn(Closed):
    revision_id: UUID
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision: Literal["approve", "reject"]


class StudioStatus(Closed):
    state: Literal["not_configured", "unavailable", "unsupported", "ready"]
    message: str
    provider_notice: str = "Hermes kendi yapılandırmasına göre bulut sağlayıcı kullanabilir. Bu geçit yalnız doğrulanmış yerel, araçsız profili kabul eder."


class StudioApplied(Closed):
    id: UUID
    type: str


class StudioRevisionOut(Closed):
    id: UUID
    fingerprint: str
    state: str
    proposal: StudioProposal
    before: dict
    results: dict[str, StudioApplied]
    expires_at: datetime
    error: str | None = None


class StudioSessionOut(Closed):
    id: UUID
    state: str
    messages: list[dict]
    revision: StudioRevisionOut | None
    pending_turn: StudioTurnIn | None = None
    progress: str = ""
    error: str | None = None
