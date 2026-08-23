"""Forkjob collection engine bridged into forkOS' SourceAdapter contract.

The upstream persistence/CLI/web layers are intentionally absent. Every ATS
and portal scraper produces RawItem values; PostgreSQL lifecycle, events,
notifications and health tracking stay native to forkOS.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.sources.base import RawItem
from app.sources.forkjob_core.config import load_config
from app.sources.forkjob_core.models import Job
from app.sources.forkjob_core.registry import Registry
from app.sources.forkjob_core.score import score_job
from app.sources.forkjob_core.scrapers.base import ScrapeBatch
from app.sources.forkjob_core.scrapers.index import get_scraper, unavailable_reason
from app.sources.forkjob_core.scrapers.registry import LayerBSource, load_registry_b
from app.sources.forkjob_core.sources.adapters import build_adapter
from app.sources.forkjob_core.sources.base import HttpClient

SCORING = load_config()


def job_to_raw(job: Job) -> RawItem:
    score_job(job, SCORING)
    row = job.to_row()
    return RawItem(
        external_id=job.external_id or job.job_id,
        title=job.title,
        url=job.url,
        summary=job.description,
        published_at=job.posted_at,
        extra={
            "organization": job.company,
            "location": job.location,
            "city": job.city,
            "country": job.country,
            "remote": job.work_mode.value,
            "compensation": job.salary,
            "department": job.department,
            "language": job.language,
            "forkjob": row,
        },
    )


@dataclass
class AtsBoardSource:
    company: Any
    interval_minutes: int = 360

    @property
    def id(self) -> str:
        return f"jobhunter:{self.company.source}"

    async def fetch(self) -> list[RawItem]:
        adapter = build_adapter(self.company)
        if adapter is None:
            raise RuntimeError(f"ATS adapter missing: {self.company.ats}")
        async with HttpClient() as client:
            return [job_to_raw(job) for job in await adapter.collect(client)]


@dataclass
class PortalSource:
    portal: LayerBSource
    interval_minutes: int = 720

    @property
    def id(self) -> str:
        return f"jobhunter:{self.portal.key}"

    async def fetch(self) -> list[RawItem]:
        scraper = get_scraper(self.portal)
        if scraper is None:
            raise RuntimeError(unavailable_reason(self.portal.key))
        result = await scraper.collect()
        if isinstance(result, ScrapeBatch):
            if result.succeeded == 0 and result.errors:
                raise RuntimeError("; ".join(result.errors))
            jobs = result.jobs
        else:
            jobs = result
        return [job_to_raw(job) for job in jobs]


def forkjob_sources(*, include_opt_in: bool = False) -> list[AtsBoardSource | PortalSource]:
    ats = [AtsBoardSource(company) for company in Registry.load().enabled()]
    portals = load_registry_b().sources
    layer_b = [
        PortalSource(source)
        for source in portals
        if source.enabled or (include_opt_in and source.key == "linkedin")
    ]
    return [*ats, *layer_b]
