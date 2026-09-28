"""C8 durable proposals and narrow, user-approved canonical materialization."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import create_entity, touch_entity
from app.core.events import log_event
from app.core.links import link
from app.modules.goal import service as goal_service
from app.modules.goal.models import Goal, GoalMilestone
from app.modules.goal.schemas import GoalIn, GoalMilestoneIn
from app.modules.learning import service as learning_service
from app.modules.learning.models import StudyArea
from app.modules.learning.schemas import TopicIn
from app.modules.opportunity.career_strategy import CareerStrategySnapshot, strategy_snapshot
from app.modules.opportunity.career_strategy_models import CareerActionProposal
from app.modules.opportunity.interview_intelligence import revision
from app.modules.project.models import Project
from app.modules.todo import service as todo_service
from app.modules.todo.schemas import TodoIn

ProposalType = Literal["goal", "milestone", "learning", "project", "todo"]


class ProposalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: ProposalType
    title: str
    rationale: str
    evidence_refs: list[str]
    sample_size: int | None
    estimated_scope: str | None
    related_goal_id: uuid.UUID | None
    strategy_revision: str
    fingerprint: str
    status: Literal["proposed", "approved", "rejected", "materialized", "expired"]
    materialization_status: Literal[
        "pending", "materialized", "unsupported_target", "failed", "stale"
    ]
    target_type: str | None
    target_id: uuid.UUID | None
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime
    decided_at: datetime | None


@dataclass(frozen=True)
class Draft:
    type: ProposalType
    title: str
    rationale: str
    evidence_refs: tuple[str, ...]
    sample_size: int | None
    estimated_scope: str
    related_goal_id: uuid.UUID | None
    payload: dict


class ProposalError(Exception):
    def __init__(self, code: str, message: str, status: int = 409):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def _fingerprint(draft: Draft, strategy_revision: str) -> str:
    target = " ".join(draft.title.casefold().split())
    return revision(
        [
            draft.type,
            target,
            str(draft.related_goal_id or ""),
            strategy_revision,
            sorted(draft.evidence_refs),
        ]
    )


def _drafts(
    snapshot: CareerStrategySnapshot,
    *,
    goals: list[Goal],
    goal_milestones: list[GoalMilestone],
    projects: list[Project],
    area_id: uuid.UUID | None,
) -> list[Draft]:
    drafts: list[Draft] = []
    linked_memory_ids = {goal.source_memory_id for goal in goals if goal.source_memory_id}
    for memory_goal in snapshot.existing_goals:
        memory_id = memory_goal.evidence_refs[0].split(":", 1)[1]
        if memory_id in linked_memory_ids or len(memory_goal.title) > 300:
            continue
        drafts.append(
            Draft(
                "goal",
                memory_goal.title,
                "Onaylı H2 hedef niyeti için ölçülebilir operasyonel hedef önerisi; otomatik hedef oluşturulmaz.",
                tuple(memory_goal.evidence_refs),
                1,
                "Tek hedef",
                None,
                {"title": memory_goal.title, "horizon": "long_term", "source_memory_id": memory_id},
            )
        )
    gaps = [signal for signal in snapshot.signals if signal.topic and signal.evidence_refs]
    for signal in gaps[:2]:
        topic = signal.topic or ""
        drafts.append(
            Draft(
                "learning",
                f"{topic} konusunu çalış",
                f"{signal.title}. Bu yalnızca değerlendirilmiş ilanlardaki betimsel sıklıktır.",
                tuple(signal.evidence_refs),
                signal.sample_size,
                "Tek öğrenme konusu",
                None,
                {"title": f"{topic} konusunu çalış", "area_id": str(area_id) if area_id else None},
            )
        )
    for goal in goals:
        if goal.status != "active":
            continue
        existing = [item for item in goal_milestones if item.goal_id == goal.id]
        if gaps and not existing:
            signal = gaps[0]
            topic = signal.topic or "beceri"
            drafts.append(
                Draft(
                    "milestone",
                    f"{topic} ile bir uygulama yayımla",
                    f"{signal.title}; mevcut operasyonel hedefe ölçülebilir çıktı önerisi.",
                    tuple([f"goal:{goal.id}", *signal.evidence_refs]),
                    signal.sample_size,
                    "Tek tamamlanabilir çıktı",
                    goal.id,
                    {"goal_id": str(goal.id), "title": f"{topic} ile bir uygulama yayımla"},
                )
            )
        incomplete = [item for item in existing if item.completed_at is None]
        if incomplete:
            item = sorted(incomplete, key=lambda row: (row.position, str(row.id)))[0]
            drafts.append(
                Draft(
                    "todo",
                    f"{item.title} için ilk çalışma adımını tamamla",
                    "Onaylı hedefin açık kilometre taşına bağlı tek görev önerisi.",
                    (f"goal:{goal.id}", f"goal_milestone:{item.id}"),
                    1,
                    "Tek görev",
                    goal.id,
                    {
                        "title": f"{item.title} için ilk çalışma adımını tamamla",
                        "goal_milestone_id": str(item.id),
                    },
                )
            )
    for signal in gaps[:1]:
        for project in projects:
            if project.status != "active" or signal.topic not in [
                s.casefold() for s in project.stack or []
            ]:
                continue
            drafts.append(
                Draft(
                    "project",
                    f"Mevcut projeyi {signal.topic} kanıtına bağla",
                    "Mevcut projedeki teknoloji ile tekrarlayan değerlendirme sinyalini ilişkilendirme önerisi; yeni proje açılmaz.",
                    tuple(signal.evidence_refs),
                    signal.sample_size,
                    "Mevcut projeye bağ",
                    None,
                    {"project_id": str(project.id)},
                )
            )
            break
    # One refresh is intentionally bounded; no automatic batch of leaf tasks.
    return drafts[:8]


async def list_proposals(session: AsyncSession, *, limit: int = 30) -> list[ProposalOut]:
    rows = (
        await session.scalars(
            select(CareerActionProposal)
            .order_by(CareerActionProposal.created_at.desc(), CareerActionProposal.id.desc())
            .limit(min(max(limit, 1), 100))
        )
    ).all()
    return [ProposalOut.model_validate(row) for row in rows]


async def refresh_proposals(session: AsyncSession) -> list[ProposalOut]:
    # Serialize simultaneous local refreshes; unique fingerprint is the final guard.
    await session.scalar(select(func.pg_advisory_xact_lock(82080081)))
    snapshot = await strategy_snapshot(session, days=90, minimum=3)
    goals = (await session.scalars(select(Goal).order_by(Goal.id))).all()
    goal_ids = [goal.id for goal in goals]
    milestones = (
        await session.scalars(select(GoalMilestone).where(GoalMilestone.goal_id.in_(goal_ids)))
    ).all()
    projects = (await session.scalars(select(Project).order_by(Project.id).limit(200))).all()
    area_id = await session.scalar(
        select(StudyArea.id)
        .where(StudyArea.active.is_(True))
        .order_by(StudyArea.position, StudyArea.id)
        .limit(1)
    )
    # Prior pending decisions from another evidence revision are visibly expired.
    stale = (
        await session.scalars(
            select(CareerActionProposal).where(
                CareerActionProposal.status == "proposed",
                CareerActionProposal.strategy_revision != snapshot.evidence_revision,
            )
        )
    ).all()
    for row in stale:
        row.status = "expired"
        row.materialization_status = "stale"
        await touch_entity(session, row.id)
        await log_event(
            session,
            verb="career_proposal.expired",
            entity_id=row.id,
            entity_type=CareerActionProposal.ENTITY_TYPE,
            payload={"strategy_revision": row.strategy_revision},
        )
    existing = {
        row.fingerprint: row for row in (await session.scalars(select(CareerActionProposal))).all()
    }
    for draft in _drafts(
        snapshot,
        goals=list(goals),
        goal_milestones=list(milestones),
        projects=list(projects),
        area_id=area_id,
    ):
        if not draft.evidence_refs:
            continue
        fingerprint = _fingerprint(draft, snapshot.evidence_revision)
        if fingerprint in existing:
            continue
        entity = await create_entity(
            session,
            type=CareerActionProposal.ENTITY_TYPE,
            title=draft.title,
            search_text=draft.rationale,
        )
        row = CareerActionProposal(
            id=entity.id,
            type=draft.type,
            title=draft.title,
            rationale=draft.rationale,
            evidence_refs=list(draft.evidence_refs)[:20],
            sample_size=draft.sample_size,
            estimated_scope=draft.estimated_scope,
            related_goal_id=draft.related_goal_id,
            payload=draft.payload,
            strategy_revision=snapshot.evidence_revision,
            fingerprint=fingerprint,
        )
        session.add(row)
        existing[fingerprint] = row
        await log_event(
            session,
            verb="career_proposal.created",
            entity_id=row.id,
            entity_type=CareerActionProposal.ENTITY_TYPE,
            payload={"type": row.type, "strategy_revision": row.strategy_revision},
        )
    await session.commit()
    return await list_proposals(session)


async def _materialize(session: AsyncSession, row: CareerActionProposal) -> tuple[str, uuid.UUID]:
    payload = row.payload or {}
    if row.type == "goal":
        try:
            result = await goal_service.create_goal(
                session, GoalIn.model_validate(payload), commit=False
            )
        except ValueError as exc:
            raise ProposalError("UNSUPPORTED_TARGET", str(exc)) from exc
        return "goal", result.id
    if row.type == "milestone":
        goal_id = uuid.UUID(str(payload.get("goal_id")))
        if await session.get(Goal, goal_id) is None:
            raise ProposalError("UNSUPPORTED_TARGET", "Hedef artık mevcut değil")
        result = await goal_service.add_goal_milestone(
            session,
            goal_id,
            GoalMilestoneIn(title=str(payload.get("title") or "")),
            commit=False,
        )
        if result is None:
            raise ProposalError("UNSUPPORTED_TARGET", "Hedef artık mevcut değil")
        return "goal_milestone", result.id
    if row.type == "learning":
        area_raw = payload.get("area_id")
        if not area_raw:
            raise ProposalError("UNSUPPORTED_TARGET", "Öğrenme alanı yok; önce bir alan seçilmeli")
        area_id = uuid.UUID(str(area_raw))
        if await session.get(StudyArea, area_id) is None:
            raise ProposalError("UNSUPPORTED_TARGET", "Öğrenme alanı artık mevcut değil")
        result = await learning_service.create_topic(
            session, TopicIn(title=row.title, area_id=area_id), commit=False
        )
        if row.related_goal_id:
            await link(session, result["id"], row.related_goal_id, "advances_goal")
        return "study_topic", result["id"]
    if row.type == "todo":
        goal_id = row.related_goal_id
        milestone_id = uuid.UUID(str(payload.get("goal_milestone_id")))
        milestone = await session.get(GoalMilestone, milestone_id)
        if goal_id is None or milestone is None or milestone.goal_id != goal_id:
            raise ProposalError("UNSUPPORTED_TARGET", "Hedef kilometre taşı artık mevcut değil")
        result = await todo_service.create(session, TodoIn(title=row.title), commit=False)
        await link(session, result.id, goal_id, "advances_goal")
        await link(session, result.id, milestone_id, "advances_goal_milestone")
        return "todo", result.id
    if row.type == "project":
        project_raw = payload.get("project_id")
        if not project_raw:
            raise ProposalError("UNSUPPORTED_TARGET", "Yeni proje C8 tarafından oluşturulmaz")
        project_id = uuid.UUID(str(project_raw))
        if await session.get(Project, project_id) is None:
            raise ProposalError("UNSUPPORTED_TARGET", "İlgili proje artık mevcut değil")
        await link(session, row.id, project_id, "targets")
        return "project", project_id
    raise ProposalError("UNSUPPORTED_TARGET", "Bilinmeyen öneri tipi")


async def approve_proposal(session: AsyncSession, proposal_id: uuid.UUID) -> ProposalOut:
    row = (
        await session.scalars(
            select(CareerActionProposal)
            .where(CareerActionProposal.id == proposal_id)
            .with_for_update()
        )
    ).one_or_none()
    if row is None:
        raise ProposalError("NOT_FOUND", "Öneri bulunamadı", 404)
    if row.status == "materialized":
        return ProposalOut.model_validate(row)
    if row.status not in {"proposed", "approved"}:
        raise ProposalError("INVALID_STATE", "Bu öneri artık onaylanamaz")
    try:
        current = await strategy_snapshot(session, days=90, minimum=3)
    except ValueError as exc:
        raise ProposalError(
            "STALE_PROPOSAL", "H2 hedef hafızası doğrulanamadı; önerileri yenile"
        ) from exc
    if current.evidence_revision != row.strategy_revision:
        raise ProposalError("STALE_PROPOSAL", "Kanıt veya hedef durumu değişti; önerileri yenile")
    row.status = "approved"
    row.decided_at = datetime.now(UTC)
    await log_event(
        session,
        verb="career_proposal.approved",
        entity_id=row.id,
        entity_type=CareerActionProposal.ENTITY_TYPE,
        payload={"strategy_revision": row.strategy_revision},
    )
    try:
        target_type, target_id = await _materialize(session, row)
    except ProposalError as exc:
        if exc.code != "UNSUPPORTED_TARGET":
            raise
        row.materialization_status = "unsupported_target"
        row.warnings = [exc.message]
        await touch_entity(session, row.id)
        await log_event(
            session,
            verb="career_proposal.unsupported",
            entity_id=row.id,
            entity_type=CareerActionProposal.ENTITY_TYPE,
            payload={"reason": exc.message},
        )
    else:
        row.target_type = target_type
        row.target_id = target_id
        row.status = "materialized"
        row.materialization_status = "materialized"
        if target_type != "project":
            await link(session, target_id, row.id, "originated_from")
        if row.related_goal_id and target_type not in {"project", "goal_milestone"}:
            await link(session, target_id, row.related_goal_id, "advances_goal")
        await touch_entity(session, row.id)
        await log_event(
            session,
            verb="career_proposal.materialized",
            entity_id=row.id,
            entity_type=CareerActionProposal.ENTITY_TYPE,
            payload={"target_type": target_type, "target_id": str(target_id)},
        )
    await session.commit()
    return ProposalOut.model_validate(row)


async def reject_proposal(session: AsyncSession, proposal_id: uuid.UUID) -> ProposalOut:
    row = (
        await session.scalars(
            select(CareerActionProposal)
            .where(CareerActionProposal.id == proposal_id)
            .with_for_update()
        )
    ).one_or_none()
    if row is None:
        raise ProposalError("NOT_FOUND", "Öneri bulunamadı", 404)
    if row.status != "proposed":
        raise ProposalError("INVALID_STATE", "Yalnız bekleyen öneri reddedilebilir")
    row.status = "rejected"
    row.decided_at = datetime.now(UTC)
    await touch_entity(session, row.id)
    await log_event(
        session,
        verb="career_proposal.rejected",
        entity_id=row.id,
        entity_type=CareerActionProposal.ENTITY_TYPE,
        payload={"strategy_revision": row.strategy_revision},
    )
    await session.commit()
    return ProposalOut.model_validate(row)
