"""Persisted bounded roadmap with current canonical evidence and legacy read adapter."""

from collections import defaultdict
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.entity import create_entity, touch_entity
from app.core.events import log_event
from app.core.links import link, unlink
from app.core.models import Entity, Link
from app.core.progress import canonical_evidence, project_progress
from app.modules.goal.models import Goal, GoalMilestone
from app.modules.goal.roadmap_models import GoalRoadmapNode

LIMIT = 1000


class RoadmapNodeOut(BaseModel):
    id: UUID
    title: str
    kind: str
    parent_id: UUID | None = None
    target_id: UUID | None = None
    target_type: str | None = None
    description: str | None = None
    position: int = 0
    percent: int | None = None
    completed: bool = False
    missing: bool = False
    progress_bearing: bool = True
    completion_gate: bool = False
    weight: float = 1
    persisted: bool = True
    updated_at: datetime | None = None
    canonical_percent: int | None = None
    target_title: str | None = None
    dependencies: list[UUID] = Field(default_factory=list)


class RoadmapOut(BaseModel):
    goal_id: UUID
    nodes: list[RoadmapNodeOut]
    percent: int | None = None
    scope_count: int = 0
    completed_scope_count: int = 0
    completed_requirements: int = 0
    unplanned_count: int = 0
    known_requirements: int = 0
    total_requirements: int = 0
    legacy: bool = False
    truncated: bool = False
    warnings: list[str] = Field(default_factory=list)


async def save_node(
    db,
    goal_id,
    data,
    *,
    parent_id=None,
    target_id=None,
    depends_on=None,
    node_id=None,
    detached=False,
):
    goal = await db.get(Goal, goal_id)
    entity = await db.get(Entity, goal_id)
    if not goal or not entity or entity.archived_at:
        raise ValueError("Hedef bulunamadı")
    nodes = (
        await db.scalars(select(GoalRoadmapNode).where(GoalRoadmapNode.goal_id == goal_id))
    ).all()
    if len(nodes) >= LIMIT and node_id is None:
        raise ValueError("Yol haritası 1000 düğümle sınırlı")
    by_id = {n.id: n for n in nodes}
    if node_id:
        if node_id not in by_id:
            raise ValueError("Düğüm bulunamadı")
        target_id = by_id[node_id].target_id
    if parent_id and (parent_id not in by_id or by_id[parent_id].detached):
        raise ValueError("Üst düğüm aynı hedefin etkin yol haritasında olmalı")
    cursor, seen = parent_id, {node_id} if node_id else set()
    while cursor:
        if cursor in seen:
            raise ValueError("Yol haritasında döngü olamaz")
        seen.add(cursor)
        cursor = by_id[cursor].parent_id
    if target_id and not detached:
        target = await db.get(Entity, target_id)
        if (
            not target
            or target.archived_at
            or target.type
            not in {
                "goal",
                "goal_milestone",
                "todo",
                "study_topic",
                "project",
                "bookmark",
                "learning_resource",
                "course",
                "flashcard_deck",
            }
        ):
            raise ValueError("Bağlanacak kayıt yok, arşivlenmiş veya desteklenmiyor")
        if data.kind in {"period", "phase"}:
            raise ValueError(
                "Dönem ve aşama yalnız graph gruplarıdır; kanonik hedef leaf düğümde bağlanır"
            )
        if target.type == "goal" and data.kind != "child_goal":
            raise ValueError("Hedef bağlantısı child_goal düğümü olmalı")
        if target.type == "goal_milestone" and data.kind != "milestone":
            raise ValueError("Hedef adımı milestone düğümü olmalı")
        if data.kind == "child_goal":
            child = await db.get(Goal, target_id)
            if not child or child.id == goal_id:
                raise ValueError("Geçerli, farklı bir alt hedef gerekli")
            scoped = (
                await db.scalars(
                    select(GoalRoadmapNode)
                    .where(
                        GoalRoadmapNode.kind == "child_goal", GoalRoadmapNode.detached.is_(False)
                    )
                    .limit(5001)
                )
            ).all()
            if len(scoped) > 5000:
                raise ValueError("Alt hedef bağlantısı kapsam sınırını aşıyor")
            adjacency = defaultdict(list)
            canonical_parents = (
                await db.execute(select(Goal.id, Goal.parent_goal_id).limit(501))
            ).all()
            if len(canonical_parents) > 500:
                raise ValueError("Hedef hiyerarşisi kapsamı çok büyük")
            for child_id, parent_goal in canonical_parents:
                if parent_goal:
                    adjacency[parent_goal].append(child_id)
            for existing in scoped:
                if existing.target_id:
                    adjacency[existing.goal_id].append(existing.target_id)
            frontier, visited = [target_id], set()
            while frontier:
                current = frontier.pop()
                if current == goal_id:
                    raise ValueError("Alt hedef bağlantıları döngü oluşturamaz")
                if current not in visited:
                    visited.add(current)
                    frontier.extend(adjacency[current])
        if data.kind == "milestone":
            step = await db.get(GoalMilestone, target_id)
            if not step or step.goal_id != goal_id:
                raise ValueError("Adım aynı hedefe ait olmalı")
    elif not detached and data.kind in {"record", "milestone", "child_goal"}:
        raise ValueError("Bu düğüm kanonik kayıt gerektirir")
    if data.completion_gate and data.kind != "milestone":
        raise ValueError("Sonuç kapısı bir hedef adımına bağlanmalı")
    if node_id:
        node = by_id.get(node_id)
        if not node:
            raise ValueError("Düğüm bulunamadı")
        node.parent_id, node.detached = parent_id, detached
        for k, v in data.model_dump(exclude={"title"}).items():
            setattr(node, k, v)
        await touch_entity(db, node.id, title=data.title)
    else:
        node_entity = await create_entity(db, type="goal_roadmap_node", title=data.title)
        node = GoalRoadmapNode(
            id=node_entity.id,
            goal_id=goal_id,
            parent_id=parent_id,
            target_id=target_id,
            **data.model_dump(exclude={"title"}),
        )
        db.add(node)
    await db.flush()
    # Dependency edges point from prerequisite to dependent. Existing hierarchy edges also count.
    edges = [(n.parent_id, n.id) for n in nodes if n.parent_id and not n.detached]
    deps = (
        await db.scalars(
            select(Link).where(Link.relation == "roadmap_requires", Link.from_id.in_(by_id))
        )
    ).all()
    edges += [
        (lk.to_id, lk.from_id)
        for lk in deps
        if not (node_id and depends_on is not None and lk.from_id == node_id)
    ]
    edges += [(parent_id, node.id)] if parent_id else []
    for dependency in depends_on or []:
        if dependency not in by_id or by_id[dependency].detached:
            raise ValueError("Ön koşul aynı etkin yol haritasında olmalı")
        edges.append((dependency, node.id))
    graph = defaultdict(list)
    for a, b in edges:
        graph[a].append(b)
    visiting, visited = set(), set()

    def visit(i):
        if len(visiting) >= 32:
            raise ValueError("Yol haritası derinliği 32 ile sınırlı")
        if i in visiting:
            raise ValueError("Yol haritası bağımlılıkları döngü oluşturuyor")
        if i in visited:
            return
        visiting.add(i)
        for child in graph[i]:
            visit(child)
        visiting.remove(i)
        visited.add(i)

    for i in list(graph):
        visit(i)
    if node_id and depends_on is not None:
        for old in deps:
            if old.from_id == node.id:
                await unlink(db, node.id, old.to_id, "roadmap_requires")
    for dependency in depends_on or []:
        await link(db, node.id, dependency, "roadmap_requires")
    if target_id and not detached:
        await link(db, node.id, target_id, "targets")
        await link(db, target_id, goal_id, "advances_goal")
    await log_event(
        db,
        verb="goal.roadmap_updated" if node_id else "goal.roadmap_created",
        entity_id=node.id,
        entity_type=node.ENTITY_TYPE,
        payload={"goal_id": str(goal_id), "detached": detached},
    )
    return node


async def prepare(db, goals):
    from app.modules.goal.work import load_work

    rows = (
        await db.execute(
            select(GoalRoadmapNode, Entity)
            .join(Entity, Entity.id == GoalRoadmapNode.id)
            .where(
                GoalRoadmapNode.goal_id.in_([g.id for g in goals]),
            )
            .order_by(GoalRoadmapNode.position, GoalRoadmapNode.id)
            .limit(10001)
        )
    ).all()
    truncated = len(rows) > 10000
    rows = rows[:10000]
    targets = {n.target_id for n, _ in rows if n.target_id}
    legacy = await load_work(db, goals)
    targets.update(a.id for work in legacy.values() for a in work.actions)
    targets.update(m.id for work in legacy.values() for m in work.milestones)
    entities, values = await canonical_evidence(db, targets)
    milestones = (
        await db.scalars(select(GoalMilestone).where(GoalMilestone.id.in_(targets)))
    ).all()
    for m in milestones:
        if m.id in entities and not entities[m.id].archived_at:
            values[m.id] = float(bool(m.completed_at))
    projects = await project_progress(db, [i for i, e in entities.items() if e.type == "project"])
    for i, pr in projects.items():
        values[i] = pr["percent"] / 100 if pr["percent"] is not None else None
    expanded_ids = {UUID(k) for pr in projects.values() for k in pr.get("requirements", {})}
    more_entities, more_values = await canonical_evidence(db, expanded_ids)
    entities.update(more_entities)
    values.update({i: v for i, v in more_values.items() if i in more_entities})
    from app.modules.todo.models import Todo

    task_parents = dict(
        (await db.execute(select(Todo.id, Todo.parent_id).where(Todo.id.in_(values)))).all()
    )
    dependencies = (
        await db.scalars(
            select(Link)
            .where(Link.from_id.in_([n.id for n, _ in rows]), Link.relation == "roadmap_requires")
            .limit(20001)
        )
    ).all()
    requirement_ids = {UUID(i) for pr in projects.values() for i in pr.get("requirements", {})}
    preparation = (
        await db.scalars(
            select(Link)
            .where(
                Link.from_id.in_(targets | requirement_ids),
                Link.to_id.in_(targets),
                Link.relation == "prepares_for",
            )
            .limit(5001)
        )
    ).all()
    return {
        "rows": rows,
        "entities": entities,
        "values": values,
        "dependencies": dependencies[:20000],
        "preparation": preparation[:5000],
        "truncated": truncated or len(dependencies) > 20000 or len(preparation) > 5000,
        "goals": {g.id: g for g in goals},
        "legacy": legacy,
        "root_units": {},
        "groups": {i: pr.get("groups", []) for i, pr in projects.items()},
        "supports": {
            i: {UUID(k) for k in pr.get("requirements", {})} for i, pr in projects.items()
        },
        "overrides": {i: set() for i in projects},
        "computed": {},
        "task_parents": task_parents,
        "project_requirements": {i: pr.get("requirements", {}) for i, pr in projects.items()},
    }


async def read_many(db, goals):
    cache = await prepare(db, goals)
    return {g.id: await read(db, g.id, _cache=cache) for g in goals}


async def read(db, goal_id, *, stack=(), _cache=None):
    from app.modules.goal import service

    if goal_id in stack or len(stack) >= 12:
        return RoadmapOut(
            goal_id=goal_id, nodes=[], truncated=True, warnings=["Hedef hiyerarşisi sınırı"]
        )
    if _cache is None:
        _cache = await prepare(db, await service.list_goals(db))
    if goal_id not in _cache["goals"]:
        raise ValueError("Hedef bulunamadı veya 500 hedef sınırı aşıldı")
    if goal_id in _cache["computed"]:
        return _cache["computed"][goal_id]
    all_rows = [(n, e) for n, e in _cache["rows"] if n.goal_id == goal_id]
    hidden = {n.id for n, e in all_rows if n.detached or e.archived_at}
    for _ in range(32):
        new_hidden = hidden | {n.id for n, _ in all_rows if n.parent_id in hidden}
        if new_hidden == hidden:
            break
        hidden = new_hidden
    rows = [(n, e) for n, e in all_rows if n.id not in hidden]
    if not rows and all_rows:
        result = RoadmapOut(goal_id=goal_id, nodes=[], legacy=False)
        _cache["computed"][goal_id] = result
        return result
    if not rows:
        return await legacy_read(
            db, goal_id, work=_cache["legacy"][goal_id], _cache=_cache, stack=stack
        )
    truncated = len(rows) > LIMIT or _cache["truncated"]
    rows = rows[:LIMIT]
    targets = {n.target_id for n, _ in rows if n.target_id}
    entities, values = _cache["entities"], dict(_cache["values"])
    for i in targets:
        e = entities.get(i)
        if e and e.type == "goal" and not e.archived_at:
            if i not in _cache["goals"]:
                values[i] = None
                truncated = True
            else:
                child = await read(db, i, stack=(*stack, goal_id), _cache=_cache)
                values[i] = child.percent / 100 if child.percent is not None else None
    dependencies = _cache["dependencies"]
    nodes = {}
    children = defaultdict(list)
    for n, e in rows:
        target = entities.get(n.target_id)
        missing = bool(
            (n.target_id and (not target or target.archived_at))
            or (not n.target_id and n.kind in {"record", "milestone", "child_goal"})
        )
        node = RoadmapNodeOut(
            id=n.id,
            title=e.title,
            updated_at=e.updated_at,
            kind=n.kind,
            parent_id=n.parent_id,
            target_id=n.target_id,
            target_type=target.type if target else None,
            target_title=target.title if target else None,
            canonical_percent=round(values[n.target_id] * 100)
            if target and target.type in {"project", "goal"} and values.get(n.target_id) is not None
            else None,
            description=n.description,
            position=n.position,
            weight=float(n.weight),
            progress_bearing=n.progress_bearing,
            completion_gate=n.completion_gate,
            missing=missing,
            dependencies=[lk.to_id for lk in dependencies if lk.from_id == n.id],
        )
        nodes[n.id] = node
        children[n.parent_id].append(n.id)
    for child in _cache["goals"].values():
        if child.parent_goal_id == goal_id and child.id not in {n.target_id for n, _ in all_rows}:
            state = await read(db, child.id, _cache=_cache, stack=(*stack, goal_id))
            nodes[child.id] = RoadmapNodeOut(
                id=child.id,
                title=child.title,
                kind="child_goal",
                target_id=child.id,
                target_type="goal",
                weight=float(child.weight),
                persisted=False,
            )
            values[child.id] = state.percent / 100 if state.percent is not None else None
            children[None].append(child.id)
    # Manual V1 steps/links added after the package stay visible without bulk rewriting history.
    work = _cache["legacy"][goal_id]
    represented = {n.target_id for n, _ in all_rows if n.target_id}
    for step in work.milestones:
        if len(nodes) >= LIMIT:
            truncated = True
            break
        if step.id not in represented:
            nodes[step.id] = RoadmapNodeOut(
                id=step.id,
                title=step.title,
                kind="milestone",
                target_id=step.id,
                target_type="goal_milestone",
                persisted=False,
            )
            values[step.id] = step.progress_percent / 100
            children[None].append(step.id)
            represented.add(step.id)
    for action in work.actions:
        if len(nodes) >= LIMIT:
            truncated = True
            break
        if action.id not in represented:
            parent = next((i for i in action.milestone_ids if i in nodes), None)
            nodes[action.id] = RoadmapNodeOut(
                id=action.id,
                title=action.title,
                kind="record",
                parent_id=parent,
                target_id=action.id,
                target_type=action.type,
                persisted=False,
            )
            values[action.id] = float(action.completed)
            children[parent].append(action.id)
            represented.add(action.id)
    targets = {n.target_id for n in nodes.values() if n.target_id}
    # A Todo preparing a represented topic is supporting practice, not a second outcome unit.
    leaf_topics = {
        n.target_id
        for n in nodes.values()
        if n.target_type == "study_topic" and not children[n.id] and n.progress_bearing
    }
    relevant = {n.target_id for n in nodes.values() if n.target_id and n.progress_bearing}
    for project_id in targets:
        relevant.update(UUID(i) for i in _cache["project_requirements"].get(project_id, {}))
    aliases = {
        lk.from_id: lk.to_id
        for lk in _cache["preparation"]
        if lk.to_id in leaf_topics
        and lk.from_id in relevant
        and entities.get(lk.from_id)
        and entities[lk.from_id].type == "todo"
    }
    evidence_values = dict(values)
    groups = defaultdict(set)
    for task, topic in aliases.items():
        groups[topic].add(task)
    for topic, tasks in groups.items():
        states = [evidence_values.get(i) for i in {topic, *tasks}]
        values[topic] = sum(states) / len(states) if None not in states else None
    cache = {}

    def requirements(i, path=()):
        if i in path or len(path) > 32:
            return {str(i): None}
        if i in cache:
            return cache[i]
        n = nodes[i]
        if not n.progress_bearing:
            return {}
        kids = children[i]
        req = {}
        for c in kids:
            req.update(requirements(c, (*path, i)))
        if n.target_id in _cache["project_requirements"] and not kids:
            req[str(n.target_id)] = values.get(n.target_id)
        elif n.completion_gate or not kids:
            key = aliases.get(n.target_id, n.target_id) or n.id
            req[str(key)] = values.get(key, None if n.missing or n.target_id else 0.0)
        if (
            n.kind == "milestone"
            and not n.completion_gate
            and n.target_id
            and values.get(n.target_id) == 1
        ):
            req = {key: 1.0 for key in req}
        cache[i] = req
        return req

    roots = children[None] + [
        i for i, n in nodes.items() if n.parent_id and n.parent_id not in nodes
    ]
    roots.sort(
        key=lambda i: (
            nodes[i].kind not in {"period", "phase", "child_goal"},
            nodes[i].position,
            str(i),
        )
    )
    _cache["groups"][goal_id] = [(requirements(i), nodes[i].weight) for i in roots]
    _cache["supports"][goal_id] = {t for topic, tasks in groups.items() for t in {topic, *tasks}}
    _cache["overrides"][goal_id] = {
        key
        for i, n in nodes.items()
        if n.kind == "milestone"
        and not n.completion_gate
        and n.target_id
        and values.get(n.target_id) == 1
        for key in requirements(i)
    }
    from app.modules.goal.progress_aggregation import aggregate

    fraction, known, contributions = aggregate(goal_id, _cache)
    for i, n in nodes.items():
        req = requirements(i)
        n.percent = (
            round(sum(req.values()) / len(req) * 100) if req and None not in req.values() else None
        )
        n.completed = n.percent == 100
    percent = round(fraction * 100) if fraction is not None and not truncated else None
    for n in nodes.values():
        if n.target_id in contributions:
            value = contributions[n.target_id]
            n.percent = round(value * 100) if value is not None else None
            n.completed = n.percent == 100
    for n in nodes.values():
        if children[n.id]:
            req = requirements(n.id)
            changed = {k: contributions.get(UUID(k), v) for k, v in req.items()}
            n.percent = (
                round(sum(changed.values()) / len(changed) * 100)
                if changed and None not in changed.values()
                else None
            )
            n.completed = n.percent == 100

    def has_work(i, path=()):
        if i in path or len(path) > 32:
            return False
        return any(
            nodes[c].target_type in {"todo", "study_topic", "project", "goal"}
            or has_work(c, (*path, i))
            for c in children[i]
        )

    result = RoadmapOut(
        goal_id=goal_id,
        nodes=list(nodes.values()),
        percent=percent,
        scope_count=len(_cache["root_units"].get(goal_id, [])),
        completed_scope_count=sum(v == 1 for v, _ in _cache["root_units"].get(goal_id, [])),
        completed_requirements=sum(v == 1 for v in known.values()),
        unplanned_count=sum(n.kind == "phase" and not has_work(n.id) for n in nodes.values()),
        total_requirements=len(known),
        known_requirements=sum(v is not None for v in known.values()),
        truncated=truncated,
        warnings=["Bağlı kayıtlardan bazıları eksik; ilerleme bilinmiyor"]
        if None in known.values()
        else [],
    )
    _cache["computed"][goal_id] = result
    return result


async def legacy_read(db, goal_id, *, work=None, _cache=None, stack=()):
    from app.modules.goal import service
    from app.modules.goal.work import load_work

    if work is None:
        goal = await service.get_goal(db, goal_id)
        if not goal:
            raise ValueError("Hedef bulunamadı")
        work = (await load_work(db, [goal]))[goal_id]
    nodes = [
        RoadmapNodeOut(
            id=m.id,
            title=m.title,
            kind="milestone",
            persisted=False,
            target_id=m.id,
            target_type="goal_milestone",
            percent=m.progress_percent,
            completed=m.completed,
            position=p,
        )
        for p, m in enumerate(work.milestones)
    ]
    for a in work.actions:
        nodes.append(
            RoadmapNodeOut(
                id=a.id,
                title=a.title,
                kind="record",
                persisted=False,
                parent_id=a.milestone_ids[0] if a.milestone_ids else None,
                target_id=a.id,
                target_type=a.type,
                percent=100 if a.completed else 0,
                completed=a.completed,
            )
        )
    percent = work.progress_percent
    total, completed = work.total_count, work.completed_count
    if _cache is not None:
        actions = {a.id: a for a in work.actions}
        assigned = {i for m in work.milestones for i in m.action_ids}
        groups = []
        for m in work.milestones:
            req = {
                str(i): 1.0 if m.manual_completed else _cache["values"].get(i)
                for i in m.action_ids
                if i in actions
            }
            groups.append((req or {str(m.id): float(m.completed)}, 1))
        groups.extend(
            ({str(a.id): _cache["values"].get(a.id)}, 1)
            for a in work.actions
            if a.id not in assigned
        )
        for child in _cache["goals"].values():
            if child.parent_goal_id == goal_id:
                state = await read(db, child.id, _cache=_cache, stack=(*stack, goal_id))
                nodes.append(
                    RoadmapNodeOut(
                        id=child.id,
                        title=child.title,
                        kind="child_goal",
                        target_id=child.id,
                        target_type="goal",
                        percent=state.percent,
                        completed=state.percent == 100,
                        persisted=False,
                    )
                )
                groups.append(
                    (
                        {str(child.id): state.percent / 100 if state.percent is not None else None},
                        float(child.weight),
                    )
                )
        _cache["groups"][goal_id] = groups
        _cache["supports"][goal_id] = {a.id for a in work.actions}
        _cache["overrides"][goal_id] = {
            str(i) for m in work.milestones if m.manual_completed for i in m.action_ids
        }
        from app.modules.goal.progress_aggregation import aggregate

        fraction, known, contributions = aggregate(goal_id, _cache)
        for n in nodes:
            if n.target_id in contributions:
                value = contributions[n.target_id]
                n.percent = round(value * 100) if value is not None else None
                n.completed = n.percent == 100
        percent = round(fraction * 100) if fraction is not None and not work.truncated else None
        total, completed = len(known), sum(v == 1 for v in known.values())
    result = RoadmapOut(
        goal_id=goal_id,
        nodes=nodes,
        percent=percent,
        scope_count=len(_cache["root_units"].get(goal_id, [])) if _cache else work.total_count,
        completed_scope_count=sum(v == 1 for v, _ in _cache["root_units"].get(goal_id, []))
        if _cache
        else work.completed_count,
        completed_requirements=completed,
        total_requirements=total,
        known_requirements=sum(v is not None for v in known.values()) if _cache else total,
        legacy=True,
        truncated=work.truncated,
    )
    if _cache is not None:
        _cache["computed"][goal_id] = result
    return result
