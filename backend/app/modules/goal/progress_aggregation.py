"""Scoped equal-stage progress. A canonical requirement belongs to its first stage only."""

from collections import defaultdict
from uuid import UUID


def aggregate(goal_id, cache):
    groups = cache["groups"]
    values = cache["values"]
    scope, seen = set(), set()

    def collect(gid, depth=0):
        if gid in seen or depth > 12:
            return
        seen.add(gid)
        for requirements, _ in groups.get(gid, []):
            for key in requirements:
                identity = UUID(key)
                if identity in groups:
                    collect(identity, depth + 1)
                else:
                    scope.add(identity)
        scope.update(cache["supports"].get(gid, set()))

    collect(goal_id)
    containers = {
        parent
        for child, parent in cache.get("task_parents", {}).items()
        if child in scope and parent in scope
    }
    topics = {
        i for i in scope if cache["entities"].get(i) and cache["entities"][i].type == "study_topic"
    }
    aliases = {}
    for lk in sorted(cache["preparation"], key=lambda r: (str(r.from_id), str(r.to_id))):
        if lk.from_id in scope and lk.from_id not in containers and lk.to_id in topics:
            aliases.setdefault(lk.from_id, lk.to_id)
    sources = defaultdict(set)
    for task, topic in aliases.items():
        sources[topic].update({task, topic})
    known, used, contributions = {}, set(), {}

    def scoped(gid, stack=()):
        if gid in stack or len(stack) >= 12:
            return None
        units = []
        for req, weight in groups.get(gid, []):
            results = []
            for key, value in req.items():
                identity = UUID(key)
                if identity in containers:
                    continue
                if identity in groups and groups[identity]:
                    fraction = scoped(identity, (*stack, gid))
                    if fraction is not False:
                        results.append(fraction)
                        contributions[identity] = fraction
                    continue
                canonical = aliases.get(identity, identity)
                if canonical in used:
                    continue
                used.add(canonical)
                if canonical in sources and key not in cache["overrides"].get(gid, set()):
                    states = [values.get(i) for i in sources[canonical]]
                    value = sum(states) / len(states) if None not in states else None
                known[str(canonical)] = value
                results.append(value)
            if results:
                units.append((sum(results) / len(results) if None not in results else None, weight))
        if gid == goal_id:
            cache["root_units"][goal_id] = units
        if not units:
            return False  # only duplicate requirements; excluded from denominator
        return (
            sum(v * w for v, w in units) / sum(w for _, w in units)
            if all(v is not None for v, _ in units)
            else None
        )

    fraction = scoped(goal_id)
    return None if fraction is False else fraction, known, contributions
