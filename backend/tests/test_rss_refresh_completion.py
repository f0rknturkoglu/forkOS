"""Manual refresh acknowledges durable ingestion before cache invalidation."""
import asyncio
import inspect

from fastapi import BackgroundTasks

from app.db import SessionLocal
from app.modules.rss import service
from app.modules.rss.router import refresh_all


async def test_refresh_all_response_waits_for_ingestion(monkeypatch):
    started, finish = asyncio.Event(), asyncio.Event()
    async def due(db, **kwargs):
        return [object()]
    async def refresh():
        started.set()
        await finish.wait()
        return 3
    monkeypatch.setattr(service, "due_feeds", due)
    monkeypatch.setattr(service, "refresh_all", refresh)
    async with SessionLocal() as db:
        kwargs = {"session": db}
        if "background" in inspect.signature(refresh_all).parameters:
            kwargs["background"] = BackgroundTasks()
        task = asyncio.create_task(refresh_all(**kwargs))
        try:
            await asyncio.sleep(0)
            assert not task.done(), "Response arrived before durable feed ingestion"
            await asyncio.wait_for(started.wait(), 1)
            finish.set()
            assert await task == {"started": 1, "added": 3}
        finally:
            finish.set()
            await task
