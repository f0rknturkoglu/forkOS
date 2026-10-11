"""Canonical planning projection for H7 approval freshness; no domain mutations."""

import hashlib
import json

from sqlalchemy import select

from app.core.time import local_today
from app.modules.todo.models import PlanSlot


async def planning_fingerprint(session, todo_id):
    rows = (
        await session.execute(
            select(PlanSlot.id, PlanSlot.day, PlanSlot.start_min, PlanSlot.duration_min)
            .where(PlanSlot.entity_id == todo_id, PlanSlot.day >= local_today())
            .order_by(PlanSlot.day, PlanSlot.id)
        )
    ).all()
    state = [[str(row.id), row.day.isoformat(), row.start_min, row.duration_min] for row in rows]
    return hashlib.sha256(json.dumps(state, separators=(",", ":")).encode()).hexdigest()
