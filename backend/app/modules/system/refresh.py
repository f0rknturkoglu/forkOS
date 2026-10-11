from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import source_sync
from app.core.events import log_event
from app.db import SessionLocal
from app.modules.system.models import Setting

STATUS_KEY = "system.manual_refresh"
STALE_AFTER = timedelta(hours=1)

#: Manuel yenileme kapsamlari.
#: critical -- yalnizca resmi/hizli kaynaklar (YLSY, OSYM, YOK, ATS panolari).
#: standard -- varsayilan: opt-in/yavas kaynaklar haric her sey + medya.
#: full     -- katalogun tamami, opt-in dahil (kullanici acikca isterse).
REFRESH_SCOPES = ("critical", "standard", "full")
DEFAULT_SCOPE = "standard"


def _default_status() -> dict[str, Any]:
    return {
        "status": "idle",
        "scope": DEFAULT_SCOPE,
        "batch_id": None,
        "started_at": None,
        "finished_at": None,
        "results": {},
        "errors": [],
    }


def _is_running(started_at: Any, *, now: datetime | None = None) -> bool:
    """Calisan bir yenileme var mi?

    Kalp atisi bu kadar sure once basladiysa surec olmustur (API yeniden
    yuklendi, container yeniden basladi); `running` durumunda takili kalip
    butonu kilitlemesin diye bayat kabul edilir ve yeniden baslatilabilir.
    """
    if not isinstance(started_at, str):
        return False
    try:
        moment = datetime.fromisoformat(started_at)
    except ValueError:
        return False
    return moment >= (now or datetime.now(UTC)) - STALE_AFTER


async def status(session: AsyncSession) -> dict[str, Any]:
    row = await session.get(Setting, STATUS_KEY)
    value = row.value if row and isinstance(row.value, dict) else _default_status()
    merged = {**_default_status(), **value}
    if merged.get("status") == "running" and not _is_running(merged.get("started_at")):
        # Bayat `running`: kilidi ac ama gecmisi silme (ne oldugu gorunur kalsin).
        merged["status"] = "interrupted"
    return merged


async def queue(
    session: AsyncSession, *, scope: str = DEFAULT_SCOPE
) -> tuple[dict[str, Any], bool]:
    from app.sources.base import (
        SourceClass,
        is_general_refresh_source,
        is_runnable,
        order_by_class,
        source_class,
        source_estimated_seconds,
    )
    from app.sources.catalog import opportunity_sources

    if scope not in REFRESH_SCOPES:
        scope = DEFAULT_SCOPE

    current = await status(session)
    if current["status"] == "running":
        # Ayni yenilemenin cift baslatilmasi engellenir.
        return current, False

    everything = [source for source in opportunity_sources() if is_runnable(source)]
    if scope == "critical":
        selected = [
            source for source in everything if source_class(source) is SourceClass.CRITICAL
        ]
    elif scope == "full":
        selected = list(everything)
    else:
        # Standart: critical once, sonra normal. Opt-in/yavas kaynaklar
        # (eures, linkedin) buraya GIRMEZ; yalnizca kullanici acikca secince kosar.
        selected = [source for source in everything if is_general_refresh_source(source)]
    opportunity_sources = order_by_class(selected)

    opportunity_ids = [source.id for source in opportunity_sources]
    batch, newly_queued = await source_sync.create_or_extend_batch(
        session,
        opportunity_ids,
        scope="opportunity",
    )
    value = {
        "status": "running",
        "scope": scope,
        "batch_id": str(batch.id),
        "started_at": datetime.now(UTC).isoformat(),
        "finished_at": None,
        "results": {
            "opportunity_sources": batch.total_sources,
            "opportunity_sources_queued": len(newly_queued),
            "opportunity_estimated_seconds": sum(
                source_estimated_seconds(source) for source in opportunity_sources
            ),
        },
        "errors": [],
    }
    row = await session.get(Setting, STATUS_KEY)
    if row is None:
        session.add(Setting(key=STATUS_KEY, value=value))
    else:
        row.value = value
    await log_event(
        session,
        verb="system.refresh.started",
        entity_type="system",
        payload={"opportunity_sources": batch.total_sources, "scope": scope},
    )
    await session.commit()
    return value, True


async def run() -> None:
    from app.modules.proactivity import service as proactivity_service
    from app.modules.rss import service as rss_service
    from app.worker.jobs import drain_source_sync_batches, sync_calendar, sync_github

    results: dict[str, int] = {}
    errors: list[str] = []

    async def execute(name: str, action) -> None:
        try:
            results[name] = await action()
        except Exception as exc:  # Her bölüm diğerlerini engellemeden raporlanır.
            errors.append(f"{name}: {type(exc).__name__}: {exc}"[:500])

    await execute("sources", drain_source_sync_batches)
    await execute("rss", lambda: rss_service.refresh_all(ignore_interval=True))
    await execute("calendar", sync_calendar)
    await execute("github", sync_github)

    async def proactivity() -> int:
        # Tek proaktif sahip H6'dir: elle yenileme de onu tetikler, ikinci bir
        # son tarih merdiveni CALISTIRMAZ (yinelenen bildirim olmaz).
        async with SessionLocal() as session:
            result = await proactivity_service.tick(session, catch_up=True)
            return result.delivered

    await execute("proactivity", proactivity)

    async with SessionLocal() as session:
        row = await session.get(Setting, STATUS_KEY)
        previous = row.value if row and isinstance(row.value, dict) else {}
        value = {
            **_default_status(),
            **previous,
            "status": "completed_with_errors" if errors else "completed",
            "finished_at": datetime.now(UTC).isoformat(),
            "results": {**(previous.get("results") or {}), **results},
            "errors": errors,
        }
        if row is None:
            session.add(Setting(key=STATUS_KEY, value=value))
        else:
            row.value = value
        await log_event(
            session,
            verb="system.refresh.completed",
            entity_type="system",
            payload={"results": value["results"], "errors": errors},
        )
        await session.commit()
