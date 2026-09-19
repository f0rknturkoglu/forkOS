"""Local-only worker.

Makine kapaliyken calismaz. Bu yuzden ACILISTA hemen bir catch-up turu atar --
"her sabah make up" ritualinin isi gormesini saglayan sey budur.
"""

from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.core.heartbeat import HEARTBEAT_INTERVAL_MINUTES
from app.db import SessionLocal
from app.modules.opportunity.service import (
    backfill_skill_match_ratios,
    deadline_ladder,
    prune_stale_opportunities,
)
from app.worker.digest import morning_digest
from app.worker.jobs import (
    catch_up,
    catch_up_media,
    consume_source_sync_batches,
    critical_catch_up,
    nightly_backup,
    poll_feeds,
    poll_media,
    poll_opportunities,
    prune_old_items,
    record_worker_heartbeat,
    sync_calendar,
    sync_github,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("worker")


async def main() -> None:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        poll_feeds,
        "interval",
        minutes=settings.rss_default_interval_minutes,
        jitter=300,  # feed'ler ayni saniyede yigilmasin
        id="poll_feeds",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        sync_github,
        "interval",
        hours=3,
        id="sync_github",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(nightly_backup, "cron", hour=3, id="nightly_backup")
    scheduler.add_job(prune_old_items, "cron", hour=4, id="prune")

    async def prune_opportunities_job() -> None:
        async with SessionLocal() as session:
            await prune_stale_opportunities(session)

    scheduler.add_job(prune_opportunities_job, "cron", hour=4, minute=30, id="prune_opportunities")
    scheduler.add_job(
        poll_opportunities,
        "interval",
        minutes=15,
        jitter=60,
        id="poll_opportunities",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        consume_source_sync_batches,
        "interval",
        minutes=1,
        id="source_sync_queue",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        poll_media,
        "interval",
        hours=1,
        id="poll_media",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        record_worker_heartbeat,
        "interval",
        minutes=HEARTBEAT_INTERVAL_MINUTES,
        id="worker_heartbeat",
        max_instances=1,
        coalesce=True,
    )

    async def deadlines() -> None:
        async with SessionLocal() as session:
            await deadline_ladder(session)

    async def backfill_opportunity_skill_matches() -> None:
        async with SessionLocal() as session:
            updated = await backfill_skill_match_ratios(session)
            if updated:
                log.info("CV eslesme cache'i tamamlandi: %d ilan", updated)

    scheduler.add_job(deadlines, "cron", hour=8, id="deadline_ladder")
    # Son tarih merdiveninden HEMEN SONRA: ozet o turun bildirimlerini de sayar.
    scheduler.add_job(morning_digest, "cron", hour=8, minute=5, id="morning_digest")
    scheduler.add_job(
        sync_calendar,
        "interval",
        minutes=30,
        id="sync_calendar",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    log.info(
        "worker basladi -- interval=%ddk, retention=%dgun",
        settings.rss_default_interval_minutes,
        settings.rss_retention_days,
    )

    startup_tasks = [
        ("heartbeat", record_worker_heartbeat),
        ("backfill_opportunity_skill_matches", backfill_opportunity_skill_matches),
        # Kritik kaynaklar once: aciliş tanıtımında YLSY/OSYM tazelenir.
        ("critical_catch_up", critical_catch_up),
        ("catch_up_feeds", catch_up),
        ("catch_up_media", catch_up_media),
        ("deadlines", deadlines),
        ("morning_digest", morning_digest),
        ("sync_calendar", sync_calendar),
        ("sync_github", sync_github),
        ("nightly_backup", nightly_backup),
    ]
    for task_name, task_fn in startup_tasks:
        try:
            await task_fn()
        except Exception:
            log.exception(
                "startup gorevi basarisiz oldu (%s) -- diger gorevler devam ediyor", task_name
            )

    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("worker durduruldu")
