from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from app.db import SessionLocal
from app.modules.system.models import Setting


async def check() -> bool:
    async with SessionLocal() as session:
        heartbeat = await session.get(Setting, "worker.heartbeat")
    if heartbeat is None or not isinstance(heartbeat.value, dict):
        return False
    raw = heartbeat.value.get("at")
    if not isinstance(raw, str):
        return False
    try:
        observed = datetime.fromisoformat(raw)
    except ValueError:
        return False
    return observed >= datetime.now(UTC) - timedelta(minutes=3)


if __name__ == "__main__":
    raise SystemExit(0 if asyncio.run(check()) else 1)
