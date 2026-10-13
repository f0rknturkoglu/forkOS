"""Local title candidates only. Similarity is a suggestion, never silent reuse."""

import re

from pydantic import BaseModel
from sqlalchemy import case, or_, select

from app.core.models import Entity

TYPES = {
    "goal",
    "project",
    "todo",
    "study_area",
    "study_topic",
    "learning_resource",
    "course",
    "bookmark",
    "flashcard_deck",
}


class Candidate(BaseModel):
    token: str
    id: str
    type: str
    title: str
    source: str = "Yerel kayıt · başlık eşleşmesi · onay gerektirir"
    updated_at: str


async def discover(db, query):
    words = list(dict.fromkeys(re.findall(r"[^\W_]{3,}", query.casefold())))[:8]
    if not words:
        return []
    escaped = [w.replace("%", r"\%").replace("_", r"\_") for w in words]
    rows = (
        await db.scalars(
            select(Entity)
            .where(
                Entity.archived_at.is_(None),
                Entity.type.in_(TYPES),
                or_(*[Entity.title.ilike(f"%{w}%") for w in escaped]),
            )
            .order_by(
                case(
                    (Entity.type == "study_area", 0),
                    (Entity.type == "goal", 1),
                    (Entity.type == "project", 2),
                    else_=3,
                ),
                Entity.updated_at.desc(),
                Entity.id,
            )
            .limit(30)
        )
    ).all()
    from app.modules.learning.models import LearningResource, StudyTopic

    matched_areas = [e.id for e in rows if e.type == "study_area"]
    associated = []
    if matched_areas:
        topics = (
            await db.scalars(
                select(Entity)
                .join(StudyTopic, StudyTopic.id == Entity.id)
                .where(StudyTopic.area_id.in_(matched_areas), Entity.archived_at.is_(None))
                .order_by(StudyTopic.position, Entity.id)
                .limit(20)
            )
        ).all()
        resources = (
            await db.scalars(
                select(Entity)
                .join(LearningResource, LearningResource.id == Entity.id)
                .where(
                    LearningResource.topic_id.in_([e.id for e in topics]),
                    Entity.archived_at.is_(None),
                )
                .order_by(Entity.updated_at.desc(), Entity.id)
                .limit(10)
            )
        ).all()
        associated = [*topics, *resources]
    unique = {}
    for e in [
        *[e for e in rows if e.type in {"study_area", "goal", "project"}],
        *associated,
        *rows,
    ]:
        unique.setdefault(e.id, e)
    rows = list(unique.values())[:30]
    return [
        Candidate(
            token=f"candidate_{i}",
            id=str(e.id),
            type=e.type,
            title=e.title,
            updated_at=e.updated_at.isoformat(),
        ).model_dump()
        for i, e in enumerate(rows)
    ]


async def include_scope(db, candidates, snapshot):
    """Current goal tasks remain resolvable even for a short question like 'ilk işi taşı'."""
    from uuid import UUID

    scoped = list(
        dict.fromkeys(
            [
                snapshot["goal"]["id"],
                *[t["area_id"] for t in snapshot["learning"][:4]],
                *[t["id"] for t in snapshot["todos"][:12]],
                *[t["id"] for t in snapshot["learning"][:8]],
                *[p["id"] for p in snapshot["projects"][:5]],
                *[r["id"] for r in snapshot["resources"][:4]],
            ]
        )
    )
    rows = {
        str(e.id): e
        for e in (
            await db.scalars(
                select(Entity).where(
                    Entity.id.in_([UUID(i) for i in scoped]),
                    Entity.archived_at.is_(None),
                    Entity.type.in_(TYPES),
                )
            )
        ).all()
    }
    result = []
    used = set()
    for identity in scoped:
        if identity in rows:
            e = rows[identity]
            result.append(
                Candidate(
                    token=f"candidate_{len(result)}",
                    id=identity,
                    type=e.type,
                    title=e.title,
                    updated_at=e.updated_at.isoformat(),
                    source="Seçili hedefin mevcut kaydı · onay gerektirir",
                ).model_dump()
            )
            used.add(identity)
    for candidate in candidates:
        if candidate["id"] not in used and len(result) < 30:
            result.append({**candidate, "token": f"candidate_{len(result)}"})
            used.add(candidate["id"])
    return result[:30]
