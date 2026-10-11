"""Small typed product contexts. No arbitrary browser state, provider or tool arguments."""

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.integrations.review_intelligence.models import Coverage, SourceRef
from app.modules.semantic_memory.schemas import SemanticCandidateRead


class ContextInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReviewContext(ContextInput):
    kind: Literal["review"]
    period_kind: Literal["daily", "weekly", "monthly", "yearly"]
    period_start: date
    review_id: UUID | None = None


class ProjectContext(ContextInput):
    kind: Literal["project"]
    entity_id: UUID


class GoalContext(ContextInput):
    kind: Literal["goal"]
    entity_id: UUID


class CareerContext(ContextInput):
    kind: Literal["career"]
    entity_id: UUID


class LearningContext(ContextInput):
    kind: Literal["learning"]
    entity_id: UUID


class PlanningContext(ContextInput):
    kind: Literal["planning"]
    todo_ids: list[UUID] = Field(min_length=1, max_length=10)
    day: date

    @model_validator(mode="after")
    def unique(self):
        if len(set(self.todo_ids)) != len(self.todo_ids):
            raise ValueError("Görevler tekrarlanamaz")
        return self


AssistanceContext = Annotated[
    ReviewContext
    | ProjectContext
    | GoalContext
    | CareerContext
    | LearningContext
    | PlanningContext,
    Field(discriminator="kind"),
]


class ContextFact(BaseModel):
    text: str
    status: Literal["fact", "candidate", "missing"] = "fact"
    support_refs: list[str] = Field(default_factory=list)
    timestamp: str | None = None


class ContextLink(BaseModel):
    id: UUID
    type: str
    title: str
    route: str
    schedulable: bool = False


class AssistanceSummary(BaseModel):
    title: str
    generated_at: datetime
    facts: list[ContextFact] = Field(default_factory=list)
    links: list[ContextLink] = Field(default_factory=list)
    sources: list[SourceRef] = Field(default_factory=list)
    coverage: Coverage | None = None
    warnings: list[str] = Field(default_factory=list)
    truncated: bool = False
    memory_candidates: list[SemanticCandidateRead] = Field(default_factory=list)
    strategy_snapshot: dict | None = None
