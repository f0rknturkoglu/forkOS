"""C8 career strategy read model: deterministic, advisory, and local-only.

No canonical objects are created here. Analytics counts are descriptive and
never treated as employer motives or as a measure of a person's worth.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity
from app.integrations.obsidian import semantic_memory as semantic_storage
from app.modules.goal import service as goal_service
from app.modules.learning.models import StudyArea, StudyTopic
from app.modules.opportunity.career_analytics import CareerAnalyticsSnapshot, snapshot
from app.modules.opportunity.interview_intelligence import revision
from app.modules.project.models import Milestone, Project
from app.modules.review.models import Review
from app.modules.todo.models import Todo


class StrategicSignal(BaseModel):
    title: str
    topic: str | None = None
    evidence_type: Literal[
        "observed_fact",
        "explicit_feedback",
        "descriptive_pattern",
        "model_interpretation",
        "user_statement",
    ]
    evidence_refs: list[str] = Field(default_factory=list)
    sample_size: int
    confidence: Literal["low", "medium", "high"]
    caveat: str


class ProjectMilestoneProgress(BaseModel):
    project_id: str
    title: str
    completed_milestones: int
    milestone_count: int
    progress_percent: int | None
    evidence_refs: list[str]


class GoalProgress(BaseModel):
    goal_id: str
    title: str
    status: str
    completed_milestones: int
    milestone_count: int
    progress_percent: int | None
    evidence_refs: list[str]
    changed_since_last_review: str | None = None


class RecommendedAction(BaseModel):
    title: str
    why: str
    evidence_refs: list[str]


class CareerStrategySnapshot(BaseModel):
    generated_at: str
    period: dict[str, str]
    evidence_revision: str
    population: int
    evaluated_population: int
    summary: str
    what_changed: str
    existing_goals: list[StrategicSignal]
    signals: list[StrategicSignal]
    goal_progress: list[GoalProgress]
    project_progress: list[ProjectMilestoneProgress]
    primary_action: RecommendedAction | None
    alternatives: list[RecommendedAction]
    uncertainties: list[str]
    audit: list[str]


def build_strategy(
    analytics: CareerAnalyticsSnapshot,
    *,
    projects: list[dict],
    milestones: list[dict],
    topics: list[dict],
    todos: list[dict],
    now: datetime,
    goals: list[dict] | None = None,
    canonical_goals: list[dict] | None = None,
    areas: list[dict] | None = None,
    previous_goal_progress: list[dict] | None = None,
) -> CareerStrategySnapshot:
    """Pure reducer; stable revision excludes wall time and rendered prose."""
    material = {
        "period_days": round(
            (
                datetime.fromisoformat(analytics.period["end"])
                - datetime.fromisoformat(analytics.period["start"])
            ).total_seconds()
            / 86400
        ),
        "funnel": analytics.funnel,
        "candidate_context_revision": analytics.candidate_context_revision,
        "gaps": [g.model_dump() for g in analytics.skill_gaps],
        "rejection_patterns": analytics.rejection_patterns,
        "projects": projects,
        "milestones": milestones,
        "topics": topics,
        "areas": areas or [],
        "todos": todos,
        "goals": goals or [],
        "canonical_goals": canonical_goals or [],
    }
    evidence_revision = revision(material)
    existing_goals = [
        StrategicSignal(
            title=goal["statement"],
            evidence_type="user_statement",
            evidence_refs=[f"memory:{goal['id']}"],
            sample_size=1,
            confidence="high",
            caveat="Kullanıcı onaylı mevcut yön; kariyer analitiğiyle otomatik doğrulanmış bir sonuç değil.",
        )
        for goal in (goals or [])[:3]
    ]
    signals: list[StrategicSignal] = []
    for gap in sorted(
        analytics.skill_gaps,
        key=lambda g: (-g.missing_count, -g.partial_count, g.requirement),
    ):
        if gap.missing_count < analytics.minimum_sample:
            continue
        signals.append(
            StrategicSignal(
                title=f"{gap.requirement}: {gap.missing_count}/{gap.opportunities_seen} güncel değerlendirmede eksik",
                topic=gap.requirement,
                evidence_type="descriptive_pattern",
                evidence_refs=gap.evidence_refs[:20],
                sample_size=gap.opportunities_seen,
                confidence="medium"
                if gap.opportunities_seen >= analytics.minimum_sample
                else "low",
                caveat="Yalnızca güncel değerlendirilmiş ilanlar; işveren gerekçesi veya nedensel açıklama değil.",
            )
        )
    for rejection in analytics.rejection_patterns:
        if rejection.get("classification") != "explicit_reason":
            continue
        reason = str(rejection.get("reason") or "").strip()
        if not reason:
            continue
        signals.append(
            StrategicSignal(
                title=f"Bildirilen görüşme geri bildirimi: {reason[:180]}",
                evidence_type="explicit_feedback",
                evidence_refs=[str(ref) for ref in rejection.get("evidence_refs", [])][:5],
                sample_size=1,
                confidence="low",
                caveat="Kullanıcının kaydettiği işveren alıntısı; bağımsız doğrulama veya genellenebilir neden değil.",
            )
        )
    project_progress = []
    by_project: dict[str, list[dict]] = {}
    for milestone in milestones:
        by_project.setdefault(milestone["project_id"], []).append(milestone)
    for project in projects:
        rows = by_project.get(project["id"], [])
        completed = sum(bool(row["completed_at"]) for row in rows)
        project_progress.append(
            ProjectMilestoneProgress(
                project_id=project["id"],
                title=project["title"],
                completed_milestones=completed,
                milestone_count=len(rows),
                progress_percent=round(completed / len(rows) * 100) if rows else None,
                evidence_refs=[f"milestone:{row['id']}" for row in rows[:20]],
            )
        )
    previous_by_id = {
        str(item.get("goal_id")): item
        for item in (previous_goal_progress or [])
        if isinstance(item, dict) and item.get("goal_id")
    }
    goal_progress = [
        GoalProgress(
            goal_id=item["id"],
            title=item["title"],
            status=item["status"],
            completed_milestones=item["completed_milestones"],
            milestone_count=item["milestone_count"],
            progress_percent=item["progress_percent"],
            evidence_refs=[f"goal_milestone:{row['id']}" for row in item["milestones"][:20]],
            changed_since_last_review=(
                f"{item['completed_milestones'] - previous_by_id[item['id']]['completed_milestones']:+d} tamamlanan taş"
                if item["id"] in previous_by_id
                and isinstance(previous_by_id[item["id"]].get("completed_milestones"), int)
                and previous_by_id[item["id"]].get("milestone_count") == item["milestone_count"]
                and item["completed_milestones"]
                != previous_by_id[item["id"]]["completed_milestones"]
                else None
            ),
        )
        for item in (canonical_goals or [])
    ]
    actions: list[RecommendedAction] = []
    upcoming = sorted(
        (
            item
            for item in todos
            if item["due_at"]
            and item["status"] != "done"
            and datetime.fromisoformat(item["due_at"]) <= now + timedelta(days=7)
        ),
        key=lambda item: (item["due_at"], item["id"]),
    )
    for item in upcoming[:2]:
        actions.append(
            RecommendedAction(
                title=item["title"],
                why="Açık görev; son tarihi mevcut. Öncelik gerekçesi son tarihtir.",
                evidence_refs=[f"todo:{item['id']}"],
            )
        )
    for goal in canonical_goals or []:
        if len(actions) >= 3:
            break
        if goal["status"] != "active":
            continue
        incomplete = [row for row in goal["milestones"] if not row["completed_at"]]
        if incomplete:
            actions.append(
                RecommendedAction(
                    title=incomplete[0]["title"],
                    why=f"Onaylı {goal['title']} hedefinin açık kilometre taşı.",
                    evidence_refs=[f"goal_milestone:{incomplete[0]['id']}", f"goal:{goal['id']}"],
                )
            )
    for project in projects:
        if len(actions) >= 3:
            break
        if project["status"] == "active" and project["next_action"]:
            actions.append(
                RecommendedAction(
                    title=project["next_action"],
                    why=f"{project['title']} projesinde kullanıcı tarafından kayıtlı sonraki adım.",
                    evidence_refs=[f"project:{project['id']}"],
                )
            )
    for topic in topics:
        if len(actions) >= 3:
            break
        if topic["status"] == "in_progress":
            actions.append(
                RecommendedAction(
                    title=f"{topic['title']} konusuna devam et",
                    why="Kanonik öğrenme kaydında çalışma sürüyor; süre/etki tahmin edilmedi.",
                    evidence_refs=[f"study_topic:{topic['id']}"],
                )
            )
    summary = (
        f"{analytics.population} keşfedilmiş ilanın {analytics.evaluated_population} tanesinde güncel değerlendirme var. "
        f"{sum(signal.topic is not None for signal in signals)} tekrarlayan eksik beceri sinyali görüldü."
        if analytics.population
        else "Bu dönemde kariyer yönü çıkarmaya yetecek ilan kanıtı yok."
    )
    changed = [item for item in goal_progress if item.changed_since_last_review]
    what_changed = (
        "; ".join(f"{item.title}: {item.changed_since_last_review}" for item in changed[:3])
        if changed
        else (
            "Son haftalık değerlendirmeye göre karşılaştırılabilir hedef ilerlemesi değişmedi."
            if previous_goal_progress is not None
            else "Önceki haftalık değerlendirmede karşılaştırılabilir hedef kaydı yok."
        )
    )
    return CareerStrategySnapshot(
        generated_at=now.isoformat(),
        period=analytics.period,
        evidence_revision=evidence_revision,
        population=analytics.population,
        evaluated_population=analytics.evaluated_population,
        summary=summary,
        what_changed=what_changed,
        existing_goals=existing_goals,
        signals=signals[:10],
        goal_progress=goal_progress[:50],
        project_progress=project_progress[:50],
        primary_action=actions[0] if actions else None,
        alternatives=actions[1:3],
        uncertainties=[
            "Fırsat kohortu keşif tarihine göre; sonuçların gerçekleşme tarihi aynı dönem olmak zorunda değil.",
            "Bilinmeyen yanıt/sonuç başarısızlık sayılmaz. Örneklem küçükse oran yorumlanmaz.",
            "Proje kilometre taşları kariyer hedefi olduğunu kanıtlamaz; yüzdeler yalnızca kendi tamamlanma ölçüsüdür.",
        ],
        audit=[
            "Değişim yalnızca son kayıtlı haftalık değerlendirmedeki aynı paydalı hedef kilometre taşlarıyla karşılaştırılır.",
            "Açık kullanıcı hedefi ile kariyer kanıtı arasındaki çelişki otomatik olarak hükme bağlanmıyor.",
            "Bu okuma çıktısı hedef, proje, öğrenme veya görev oluşturmaz; öneri hazırlama ayrı işlemdir.",
        ],
    )


async def strategy_snapshot(
    session: AsyncSession, *, days: int = 30, minimum: int = 3, now: datetime | None = None
) -> CareerStrategySnapshot:
    moment = now or datetime.now(UTC)
    analytics = await snapshot(session, days=days, minimum=minimum, now=moment)
    projects_rows = (
        await session.execute(
            select(Project, Entity.title, Entity.updated_at)
            .join(Entity, Entity.id == Project.id)
            .order_by(Project.id)
            .limit(200)
        )
    ).all()
    projects = [
        {
            "id": str(item.id),
            "title": title,
            "status": item.status,
            "next_action": item.next_action,
            "stack": item.stack or [],
            "updated_at": updated_at.isoformat(),
        }
        for item, title, updated_at in projects_rows
    ]
    ids = [item.id for item, _, _ in projects_rows]
    milestone_rows = (
        await session.scalars(
            select(Milestone)
            .where(Milestone.project_id.in_(ids))
            .order_by(Milestone.id)
            .limit(1000)
        )
    ).all()
    milestones = [
        {
            "id": str(item.id),
            "project_id": str(item.project_id),
            "completed_at": item.completed_at.isoformat() if item.completed_at else None,
        }
        for item in milestone_rows
    ]
    topic_rows = (
        await session.execute(
            select(StudyTopic, Entity.title)
            .join(Entity, Entity.id == StudyTopic.id)
            .order_by(StudyTopic.id)
            .limit(1000)
        )
    ).all()
    topics = [
        {"id": str(item.id), "title": title, "status": item.status} for item, title in topic_rows
    ]
    area_rows = (
        await session.execute(
            select(StudyArea.id, Entity.title, StudyArea.active)
            .join(Entity, Entity.id == StudyArea.id)
            .order_by(StudyArea.id)
            .limit(200)
        )
    ).all()
    areas = [{"id": str(id_), "title": title, "active": active} for id_, title, active in area_rows]
    todo_rows = (
        await session.execute(
            select(Todo, Entity.title)
            .join(Entity, Entity.id == Todo.id)
            .where(Todo.status != "done", Todo.due_at.is_not(None))
            .order_by(Todo.due_at, Todo.id)
            .limit(100)
        )
    ).all()
    todos = [
        {
            "id": str(item.id),
            "title": title,
            "status": item.status,
            "due_at": item.due_at.isoformat() if item.due_at else None,
        }
        for item, title in todo_rows
    ]
    vault_root = semantic_storage.readable_root()
    profile = semantic_storage.get_semantic_profile(vault_root) if vault_root else None
    goals = [
        {"id": card.card_id, "statement": card.statement, "revision": card.revision}
        for card in (profile.goals if profile else [])
    ]
    canonical_goals = [
        item.model_dump(mode="json") for item in await goal_service.list_goals(session)
    ]
    previous_review = await session.scalar(
        select(Review)
        .where(Review.kind == "weekly")
        .order_by(Review.period_start.desc(), Review.id.desc())
        .limit(1)
    )
    stored_goals = (previous_review.stats or {}).get("career_goals") if previous_review else None
    previous_goal_progress = stored_goals if isinstance(stored_goals, list) else None
    return build_strategy(
        analytics,
        projects=projects,
        milestones=milestones,
        topics=topics,
        todos=todos,
        now=moment,
        goals=goals,
        canonical_goals=canonical_goals,
        areas=areas,
        previous_goal_progress=previous_goal_progress,
    )
