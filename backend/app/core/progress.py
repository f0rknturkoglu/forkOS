"""Canonical execution evidence, shared by Projects and Living Goals."""

from uuid import UUID

from sqlalchemy import select

from app.core.models import Entity, Link
from app.modules.learning.models import StudyTopic
from app.modules.project.models import Milestone
from app.modules.todo.models import Todo


async def canonical_evidence(db, ids: set[UUID]):
    entities = {e.id: e for e in (await db.scalars(select(Entity).where(Entity.id.in_(ids)))).all()}
    values = {i: None for i in ids}
    todos = {t.id: t for t in (await db.scalars(select(Todo).where(Todo.id.in_(ids)))).all()}
    topics = {
        t.id: t for t in (await db.scalars(select(StudyTopic).where(StudyTopic.id.in_(ids)))).all()
    }
    for i, row in todos.items():
        # A recurring template is not a completed occurrence. Generated occurrence IDs are stable.
        values[i] = None if row.recur else float(row.status == "done")
    for i, row in topics.items():
        values[i] = float(row.status == "done")
    for row in (await db.scalars(select(Milestone).where(Milestone.id.in_(ids)))).all():
        values[row.id] = float(bool(row.completed_at))
    for i, e in entities.items():
        if e.archived_at:
            values[i] = None
    return entities, values


async def project_progress(db, project_ids: list[UUID]):
    """Each milestone is one unit; unassigned tasks each one. Unique canonical IDs."""

    links = (
        await db.scalars(
            select(Link)
            .where(Link.to_id.in_(project_ids), Link.relation == "belongs_to")
            .limit(5001)
        )
    ).all()
    steps = (
        await db.scalars(select(Milestone).where(Milestone.project_id.in_(project_ids)).limit(5001))
    ).all()
    if len(links) > 5000 or len(steps) > 5000:
        return {
            i: {"percent": None, "completed": 0, "total": 0, "coverage": "limit"}
            for i in project_ids
        }
    ids = {lk.from_id for lk in links} | {m.id for m in steps}
    entities, values = await canonical_evidence(db, ids)
    result = {}
    todos = (await db.scalars(select(Todo).where(Todo.id.in_(ids)))).all()
    for pid in project_ids:
        owned = {
            lk.from_id
            for lk in links
            if lk.to_id == pid and lk.from_id in entities and entities[lk.from_id].type == "todo"
        }
        owned -= {t.parent_id for t in todos if t.id in owned and t.parent_id in owned}
        groups = []
        assigned = set()
        for m in steps:
            if m.project_id != pid:
                continue
            children = {t.id for t in todos if t.id in owned and t.milestone_id == m.id}
            assigned |= children
            if m.id not in entities or entities[m.id].archived_at:
                req = {str(m.id): None}
            elif m.completed_at or not children:
                req = {str(m.id): float(bool(m.completed_at))}
            else:
                req = {str(i): values[i] for i in sorted(children, key=str)}
            groups.append((req, 1))
        groups.extend(({str(i): values[i]}, 1) for i in sorted(owned - assigned, key=str))
        units = [
            sum(req.values()) / len(req) if None not in req.values() else None for req, _ in groups
        ]
        known = [v for v in units if v is not None]
        requirements = {key: value for req, _ in groups for key, value in req.items()}
        result[pid] = {
            "requirements": requirements,
            "groups": groups,
            "percent": round(sum(known) / len(units) * 100)
            if units and len(known) == len(units)
            else None,
            "completed": sum(v == 1 for v in known),
            "total": len(units),
            "coverage": "complete" if len(known) == len(units) else "partial",
        }
    return result
