"""Small model authoring contract; deterministic binding to the canonical approval contract.

The model supplies content only. It cannot choose entity IDs, tools, permissions,
measurement values or mutation state. Dates use the configured local day boundary.
"""

import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, TypeAdapter, field_validator

from app.core.time import local_datetime, local_today
from app.modules.goal.studio_schemas import StudioProposal


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Metric(Closed):
    title: str = Field(min_length=1, max_length=300)
    target_value: Decimal = Field(gt=0, max_digits=20, decimal_places=4, allow_inf_nan=False)
    unit: str = Field(min_length=1, max_length=60)


class Milestone(Closed):
    title: str = Field(min_length=1, max_length=300)
    due_date: date | None = None


class Notes(Closed):
    assumptions: list[str] = Field(default_factory=list, max_length=12)
    missing_information: list[str] = Field(default_factory=list, max_length=12)
    warnings: list[str] = Field(default_factory=list, max_length=12)

    @field_validator("assumptions", "missing_information", "warnings", mode="before")
    @classmethod
    def narrative_notes(cls, value):
        # Authoring may express one note as text; the public proposal stays list-only.
        return (
            [value]
            if isinstance(value, str) and value.strip()
            else ([] if isinstance(value, str) else value)
        )


class GoalContent(Notes):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1, max_length=5000)
    schedule: str | None = Field(
        default=None, max_length=3000, validation_alias=AliasChoices("schedule", "discussion")
    )
    target_date: date | None = None
    metric: Metric | None = None
    milestones: list[Milestone] = Field(default_factory=list, max_length=6)


class GoalDraft(GoalContent):
    kind: Literal["goal"]


class PlanDraft(Notes):
    kind: Literal["plan"]
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1, max_length=5000)
    start_date: date
    end_date: date
    goals: list[GoalContent] = Field(min_length=1, max_length=3)


AUTHORING = TypeAdapter(Annotated[GoalDraft | PlanDraft, Field(discriminator="kind")])


def local_date(value):
    return local_datetime(value).isoformat() if value else None


def user_deadline(data):
    """Calendar arithmetic only for an explicit user-authored relative deadline.

    It is anchored to the original message day, including across a retry/midnight.
    Assistant replies, page evidence and provider payloads never enter this parser.
    """
    turns = sorted(data.get("turns", {}).values(), key=lambda turn: turn["at"], reverse=True)
    for turn in turns:
        matches = list(
            re.finditer(
                r"\b(\d{1,4})\s*gün\s+(?:kaldı|sonra|içinde)\b", turn["message"], re.IGNORECASE
            )
        )
        if matches:
            days = int(matches[-1][1])
            if 0 < days <= 3650:
                return local_today(datetime.fromisoformat(turn["at"])) + timedelta(days=days)
    return None


def canonical_proposal(value, *, goal_id=None, target_date=None):
    # Existing canonical envelopes remain accepted for saved sessions and explicit revisions.
    if not isinstance(value, dict) or "kind" not in value:
        return StudioProposal.model_validate(value)
    draft = AUTHORING.validate_python(value)
    operations = []
    if isinstance(draft, PlanDraft):
        operations.append(
            {
                "type": "plan.create",
                "key": "plan",
                "data": {
                    "title": draft.title,
                    "summary": draft.description,
                    "start_at": local_date(draft.start_date),
                    "end_at": local_date(draft.end_date),
                },
            }
        )
        goals = draft.goals
    else:
        goals = [draft]
    for index, goal in enumerate(goals):
        key = f"goal_{index}"
        description = goal.description + ("\n\n" + goal.schedule if goal.schedule else "")
        data = {"title": goal.title, "description": description}
        deadline = target_date if isinstance(draft, GoalDraft) and target_date else goal.target_date
        if deadline:
            data["target_at"] = local_date(deadline)
        if isinstance(draft, PlanDraft):
            data["horizon"] = "long_term"
            operation = {"type": "goal.create", "key": key, "plan_ref": "plan", "data": data}
        elif goal_id:
            operation = {"type": "goal.update", "key": key, "target_id": goal_id, "data": data}
        else:
            data["horizon"] = "short_term"
            operation = {"type": "goal.create", "key": key, "data": data}
        operations.append(operation)
        goal_ref = goal_id if goal_id and isinstance(draft, GoalDraft) else key
        if goal.metric:
            operations.append(
                {
                    "type": "key_result.save",
                    "key": f"metric_{index}",
                    "goal_ref": goal_ref,
                    "data": goal.metric.model_dump(mode="json"),
                }
            )
        for position, milestone in enumerate(goal.milestones):
            operations.append(
                {
                    "type": "milestone.create",
                    "key": f"milestone_{index}_{position}",
                    "goal_ref": goal_ref,
                    "data": {
                        "title": milestone.title,
                        "due_at": local_date(milestone.due_date),
                        "position": position,
                    },
                }
            )
    return StudioProposal.model_validate(
        {
            "rationale": draft.description,
            "assumptions": list(
                dict.fromkeys(
                    draft.assumptions + [v for g in goals if g is not draft for v in g.assumptions]
                )
            ),
            "missing_information": list(
                dict.fromkeys(
                    draft.missing_information
                    + [v for g in goals if g is not draft for v in g.missing_information]
                )
            ),
            "warnings": list(
                dict.fromkeys(
                    draft.warnings + [v for g in goals if g is not draft for v in g.warnings]
                )
            ),
            "operations": operations,
        }
    )
