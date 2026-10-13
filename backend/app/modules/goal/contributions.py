"""Current contribution scope; never deletes ambiguous V1/manual Link history."""

from dataclasses import dataclass, field

from sqlalchemy import select

from app.core.models import Entity, Event, Link
from app.modules.goal.roadmap_models import GoalRoadmapNode


@dataclass
class ContributionScope:
    declared: set = field(default_factory=set)
    active: set = field(default_factory=set)
    independent: set = field(default_factory=set)
    milestone_goals: dict = field(default_factory=dict)
    truncated: bool = False

    def pair(self, source, destination):
        return source, self.milestone_goals.get(destination, destination)

    def allows(self, source, destination):
        pair = self.pair(source, destination)
        # A hidden roadmap milestone also hides its automatically attached work.
        container = (destination, pair[1])
        if (
            container in self.declared
            and container not in self.active
            and pair not in self.independent
        ):
            return False
        return pair not in self.declared or pair in self.active or pair in self.independent


async def current_scope(db, goal_ids, milestone_goals=None):
    """Active nodes own V2 contributions; explicit independent links survive detach.

    Manual link.created evidence, or a Link predating the first roadmap node,
    establishes independence. Old equal-time/no-event links are ambiguous: keep
    their rows/history, but suppress the detached-only contribution read-side.
    """
    scope = ContributionScope(milestone_goals=milestone_goals or {})
    rows = (
        await db.execute(
            select(GoalRoadmapNode, Entity)
            .join(Entity, Entity.id == GoalRoadmapNode.id)
            .where(GoalRoadmapNode.goal_id.in_(goal_ids))
            .order_by(GoalRoadmapNode.id)
            .limit(10001)
        )
    ).all()
    scope.truncated = len(rows) > 10000
    rows = rows[:10000]
    hidden = {n.id for n, e in rows if n.detached or e.archived_at}
    for _ in range(32):
        expanded = hidden | {n.id for n, _ in rows if n.parent_id in hidden}
        if expanded == hidden:
            break
        hidden = expanded
    earliest = {}
    for node, entity in rows:
        if not node.target_id:
            continue
        pair = node.target_id, node.goal_id
        scope.declared.add(pair)
        earliest[pair] = min(earliest.get(pair, entity.created_at), entity.created_at)
        if node.id not in hidden:
            scope.active.add(pair)
    links = (
        await db.scalars(
            select(Link)
            .where(
                Link.to_id.in_([*goal_ids, *scope.milestone_goals]),
                Link.relation.in_(["advances_goal", "advances_goal_milestone"]),
            )
            .order_by(Link.id)
            .limit(10001)
        )
    ).all()
    scope.truncated |= len(links) > 10000
    links = links[:10000]
    current = {(lk.from_id, str(lk.to_id), lk.relation): lk for lk in links}
    for lk in links:
        pair = scope.pair(lk.from_id, lk.to_id)
        if pair not in earliest or lk.created_at < earliest[pair]:
            scope.independent.add(pair)
    if scope.declared and links:
        events = (
            await db.scalars(
                select(Event)
                .where(
                    Event.entity_id.in_({lk.from_id for lk in links}),
                    Event.verb == "link.created",
                    Event.occurred_at >= min(lk.created_at for lk in links),
                )
                .order_by(Event.occurred_at.desc())
                .limit(10001)
            )
        ).all()
        scope.truncated |= len(events) > 10000
        for event in events[:10000]:
            data = event.payload or {}
            lk = current.get((event.entity_id, data.get("to_id"), data.get("relation")))
            if lk and event.occurred_at >= lk.created_at and data.get("source") != "roadmap":
                scope.independent.add(scope.pair(lk.from_id, lk.to_id))
    return scope
