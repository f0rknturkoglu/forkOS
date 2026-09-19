from __future__ import annotations

import asyncio
from datetime import datetime

from app.core.heartbeat import WORKER_HEARTBEAT_KEY, heartbeat_is_fresh
from app.db import SessionLocal
from app.modules.system.models import Setting


async def check() -> bool:
    async with SessionLocal() as session:
        heartbeat = await session.get(Setting, WORKER_HEARTBEAT_KEY)
    if heartbeat is None or not isinstance(heartbeat.value, dict):
        return False
    raw = heartbeat.value.get("at")
    if not isinstance(raw, str):
        return False
    try:
        observed = datetime.fromisoformat(raw)
    except ValueError:
        return False
    return heartbeat_is_fresh(observed)


if __name__ == "__main__":
    raise SystemExit(0 if asyncio.run(check()) else 1)
