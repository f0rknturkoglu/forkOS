"""A bounded goal scope. Current evidence never includes unrelated notes or secrets."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import Text, cast, or_, select

from app.core.models import Entity, Event, Link
from app.modules.goal import roadmap, service
from app.modules.goal.studio_models import GoalStudioRevision, GoalStudioSession
from app.modules.learning.models import LearningResource, StudyTopic
from app.modules.review.models import Review
from app.modules.todo.models import PlanSlot, Todo


async def build(db, goal_id):
    goal = await service.get_goal(db, goal_id)
    if not goal:
        raise ValueError("Hedef bulunamadı")
    cache = await roadmap.prepare(db, await service.list_goals(db))
    graph = await roadmap.read(db, goal_id, _cache=cache)
    from app.modules.goal.roadmap_models import GoalRoadmapNode

    declared = set(
        (
            await db.scalars(
                select(GoalRoadmapNode.target_id)
                .where(
                    GoalRoadmapNode.goal_id.in_(cache["computed"]),
                    GoalRoadmapNode.target_id.is_not(None),
                )
                .limit(10001)
            )
        ).all()
    )
    suppressed = declared - {
        n.target_id for g in cache["computed"].values() for n in g.nodes if n.target_id
    }
    ids = {
        goal_id,
        *[n.target_id for g in cache["computed"].values() for n in g.nodes if n.target_id],
        *[n.id for g in cache["computed"].values() for n in g.nodes],
    }
    links = (
        await db.scalars(
            select(Link)
            .where(
                Link.to_id.in_(ids),
                Link.from_id.not_in(suppressed),
                Link.relation.in_(
                    ["advances_goal", "advances_goal_milestone", "belongs_to", "prepares_for"]
                ),
            )
            .limit(301)
        )
    ).all()
    ids.update(lk.from_id for lk in links[:300])
    entities = {
        e.id: e
        for e in (
            await db.scalars(select(Entity).where(Entity.id.in_(ids), Entity.archived_at.is_(None)))
        ).all()
    }
    tasks = (await db.scalars(select(Todo).where(Todo.id.in_(entities)).limit(101))).all()
    topics = (
        await db.scalars(select(StudyTopic).where(StudyTopic.id.in_(entities)).limit(101))
    ).all()
    slots = (
        await db.scalars(
            select(PlanSlot)
            .where(PlanSlot.entity_id.in_(entities))
            .order_by(PlanSlot.day.desc())
            .limit(101)
        )
    ).all()
    resources = (
        await db.execute(
            select(LearningResource, Entity)
            .join(Entity, Entity.id == LearningResource.id)
            .where(
                LearningResource.topic_id.in_([t.id for t in topics]), Entity.archived_at.is_(None)
            )
            .limit(51)
        )
    ).all()
    bookmark_ids = {r.bookmark_id for r, _ in resources if r.bookmark_id}
    live_bookmarks = set(
        (
            await db.scalars(
                select(Entity.id).where(Entity.id.in_(bookmark_ids), Entity.archived_at.is_(None))
            )
        ).all()
    )
    from app.core.contributions import COUNTED_VERBS

    now = datetime.now(UTC)
    events = (
        await db.scalars(
            select(Event)
            .where(
                Event.entity_id.in_(ids),
                Event.verb.in_(COUNTED_VERBS),
                Event.occurred_at >= now - timedelta(days=90),
            )
            .order_by(Event.occurred_at.desc(), Event.id)
            .limit(301)
        )
    ).all()
    # Outcome provider remains canonical. Do not infer outcome from execution work.
    from app.modules.goal.strategy import overview

    overview_data = await overview(db)
    objective = next((o for o in overview_data.objectives if o.goal.id == goal_id), None)
    accepted = (
        await db.scalars(
            select(GoalStudioRevision)
            .join(GoalStudioSession, GoalStudioSession.id == GoalStudioRevision.session_id)
            .where(
                GoalStudioRevision.state == "applied",
                or_(
                    GoalStudioSession.data["goal_id"].astext == str(goal_id),
                    cast(GoalStudioRevision.results, Text).contains(str(goal_id)),
                    GoalStudioRevision.before.has_key(str(goal_id)),
                ),
            )
            .order_by(GoalStudioRevision.expires_at.desc())
            .limit(101)
        )
    ).all()
    revisions = accepted[:5]
    constraints = next(
        (r.proposal.get("planning") for r in accepted if r.proposal.get("planning")), None
    )
    from app.core.progress import project_progress

    projects = await project_progress(db, [i for i, e in entities.items() if e.type == "project"])
    windows = {}
    for days in (7, 30, 90):
        ev = [e for e in events if e.occurred_at >= now - timedelta(days=days)]
        windows[str(days)] = {
            "count": len(ev),
            "completed_todos": len(
                {e.entity_id for e in ev if e.verb == "todo.completed" and e.entity_id}
            ),
            "evidence_ids": [str(e.id) for e in ev[:12]],
            "truncated": len(events) > 300,
        }
    # Historical review evidence must explicitly reference this goal. Global reviews are excluded.
    reviews = (
        await db.execute(
            select(Review, Entity.created_at)
            .where(cast(Review.stats, Text).contains(str(goal_id)))
            .join(Entity, Entity.id == Review.id)
            .order_by(Entity.created_at.desc())
            .limit(51)
        )
    ).all()
    history = []
    for review, at in reviews:
        snap = review.stats.get("strategy_snapshot", {})
        match = next(
            (o for o in snap.get("objectives", []) if o.get("goal", {}).get("id") == str(goal_id)),
            None,
        )
        if match:
            history.append(
                {
                    "id": str(review.id),
                    "created_at": at.isoformat(),
                    "outcome_percent": match.get("strategic_progress_percent"),
                    "execution_percent": match.get("roadmap_progress_percent"),
                }
            )
    history = history[:5]

    return {
        "schema_version": 2,
        "recorded_constraints": constraints,
        "collected_at": now.isoformat(),
        "goal": {
            "id": str(goal.id),
            "title": goal.title,
            "description": (goal.description or "")[:2000],
            "target_at": goal.target_at.isoformat() if goal.target_at else None,
            "parent_goal_id": str(goal.parent_goal_id) if goal.parent_goal_id else None,
            "horizon": goal.horizon,
        },
        "roadmap": {
            "percent": graph.percent,
            "requirements": graph.total_requirements,
            "known": graph.known_requirements,
            "truncated": graph.truncated,
            "nodes": [
                {"index": i, **n.model_dump(mode="json")}
                for i, n in enumerate(
                    sorted(
                        graph.nodes,
                        key=lambda n: (
                            {
                                "period": 0,
                                "phase": 1,
                                "child_goal": 2,
                                "milestone": 3,
                                "record": 4,
                            }.get(n.kind, 5),
                            n.position,
                            str(n.id),
                        ),
                    )[:60]
                )
            ],
        },
        "todos": [
            {
                "id": str(t.id),
                "title": entities[t.id].title,
                "status": t.status,
                "recurring_template": bool(t.recur),
            }
            for t in tasks[:100]
        ],
        "learning": [
            {
                "id": str(t.id),
                "title": entities[t.id].title,
                "status": t.status,
                "area_id": str(t.area_id),
            }
            for t in topics[:100]
        ],
        "resources": [
            {
                "id": str(r.id),
                "title": e.title,
                "source": r.source,
                "topic_id": str(r.topic_id),
                "has_url": bool(r.url or r.bookmark_id in live_bookmarks),
                "pending_need": bool(
                    not r.url and (r.note or "").startswith("Henüz seçilmemiş kaynak ihtiyacı;")
                ),
                "missing_source": r.source == "bookmark" and r.bookmark_id not in live_bookmarks,
            }
            for r, e in resources[:50]
        ],
        "planned_slots": [
            {
                "id": str(s.id),
                "entity_id": str(s.entity_id),
                "day": s.day.isoformat(),
                "start_min": s.start_min,
                "duration_min": s.duration_min,
            }
            for s in slots[:100]
        ],
        "projects": [
            {
                "id": str(i),
                "title": entities[i].title,
                **{k: v for k, v in p.items() if k != "requirements"},
            }
            for i, p in projects.items()
        ],
        "outcome": {
            "percent": str(objective.strategic_progress_percent)
            if objective and objective.strategic_progress_percent is not None
            else None,
            "measurements": [
                {
                    "id": str(k.id),
                    "title": k.title,
                    "unit": k.unit,
                    "target_value": str(k.target_value),
                    "measured_at": k.measured_at.isoformat() if k.measured_at else None,
                    "source_key": k.source_key,
                    "measurement": k.measurement.model_dump(mode="json"),
                }
                for k in objective.key_results[:10]
            ]
            if objective
            else [],
        },
        "activity_windows": windows,
        "accepted_revisions": [
            {
                "id": str(r.id),
                "fingerprint": r.fingerprint,
                "constraints": r.proposal.get("planning"),
                "assumptions": r.proposal.get("assumptions", []),
            }
            for r in revisions
        ],
        "reviews": history,
        "truncated": graph.truncated
        or len(graph.nodes) > 60
        or len(tasks) > 100
        or len(topics) > 100
        or len(slots) > 100
        or len(resources) > 50
        or len(links) > 300
        or len(events) > 300,
        "warnings": graph.warnings,
        "scope": "Yalnız hedefin açık bağlantıları. Etkinlik sonuç başarısı veya hareketsizliğin nedeni değildir.",
    }


def for_inference(snapshot):
    """Keep totals authoritative while bounding detail to a 20 KB provider context."""
    import copy
    import json

    result = copy.deepcopy(snapshot)
    result["goal"]["description"] = result["goal"]["description"][:1200]
    for node in result["roadmap"]["nodes"]:
        node["title"] = node["title"][:180]
        node["description"] = (node.get("description") or "")[:400]
    for key in ("todos", "learning", "resources", "projects"):
        for item in result[key]:
            item["title"] = item["title"][:180]
    arrays = [
        result["roadmap"]["nodes"],
        result["todos"],
        result["learning"],
        result["resources"],
        result["planned_slots"],
        result["accepted_revisions"],
    ]
    limits = (30, 20, 20, 20, 28, 2)
    for array, limit in zip(arrays, limits, strict=True):
        if len(array) > limit:
            result["truncated"] = True
            del array[limit:]
    while len(json.dumps(result, ensure_ascii=False).encode()) > 20000 and any(arrays):
        max(arrays, key=lambda a: len(json.dumps(a, ensure_ascii=False))).pop()
        result["truncated"] = True
    if len(json.dumps(result, ensure_ascii=False).encode()) > 20000:
        raise ValueError("Hedef bağlamı 20 KB sınırına indirilemedi")
    return result
