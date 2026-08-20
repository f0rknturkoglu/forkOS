from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select

from app.core import runs
from app.core.models import SourceRun
from app.db import SessionLocal
from app.modules.opportunity import service
from app.sources.announcements import SOURCES
from app.sources.forkjob_port import forkjob_sources


@dataclass
class NativeJob:
    raw: Any

    def __getattr__(self, name: str) -> Any:
        values = {
            "external_id": self.raw.external_id,
            "job_id": self.raw.external_id,
            "title": self.raw.title,
            "url": self.raw.url,
            "company": self.raw.extra.get("organization"),
            "location": self.raw.extra.get("location"),
            "description": self.raw.summary or self.raw.extra.get("description"),
            "salary": self.raw.extra.get("compensation"),
            "kind": self.raw.extra.get("kind", "job"),
            "published_at": self.raw.published_at,
        }
        if name in values:
            return values[name]
        if name == "work_mode":
            return type("Mode", (), {"value": self.raw.extra.get("remote") or "unknown"})()
        raise AttributeError(name)

    def to_row(self) -> dict[str, Any]:
        return {
            "title": self.raw.title,
            "url": self.raw.url,
            "published_at": self.raw.published_at.isoformat() if self.raw.published_at else None,
            **self.raw.extra,
        }


async def poll_source(source) -> int:
    async with SessionLocal() as session:
        run = await runs.start_run(session, source.id)
        try:
            raw_items = await source.fetch()
            payloads = [NativeJob(raw) for raw in raw_items]
            added = await service.ingest_jobs(session, payloads, source.id)
            status = runs.OK if raw_items else runs.EMPTY
            await runs.finish_run(session, run, status=status, items_found=added)
            await session.commit()
            if status == runs.EMPTY:
                await runs.check_stalled(session, source.id)
                await session.commit()
            return added
        except Exception as exc:
            await runs.finish_run(session, run, status=runs.ERROR, error=str(exc))
            await session.commit()
            return 0


async def poll_opportunities(*, limit: int = 4) -> int:
    """Only poll the stalest slice; complete syncs must be explicit."""
    sources = [*forkjob_sources(), *SOURCES]
    async with SessionLocal() as session:
        latest = dict(
            (
                await session.execute(
                    select(SourceRun.source, func.max(SourceRun.started_at))
                    .where(SourceRun.source.in_([source.id for source in sources]))
                    .group_by(SourceRun.source)
                )
            ).all()
        )
    sources.sort(key=lambda source: (latest.get(source.id) is not None, latest.get(source.id)))
    return sum([await poll_source(source) for source in sources[:limit]])


async def poll_named_source(source_id: str) -> int:
    source = next((item for item in [*forkjob_sources(), *SOURCES] if item.id == source_id), None)
    if source is None:
        raise KeyError(source_id)
    return await poll_source(source)
