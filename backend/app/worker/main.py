"""Local-only worker.

Makine kapaliyken calismaz. Bu yuzden ACILISTA hemen bir catch-up turu atar --
"her sabah make up" ritualinin isi gormesini saglayan sey budur.
"""

from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.db import SessionLocal
from app.modules.opportunity.service import deadline_ladder
from app.worker.digest import morning_digest
from app.worker.jobs import (
    catch_up,
    nightly_backup,
    poll_feeds,
    poll_opportunities,
    prune_old_items,
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
    scheduler.add_job(
        poll_opportunities,
        "interval",
        hours=2,
        jitter=600,
        id="poll_opportunities",
        max_instances=1,
        coalesce=True,
    )

    async def deadlines() -> None:
        async with SessionLocal() as session:
            await deadline_ladder(session)

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

    try:
        await catch_up()
        await deadlines()
        await morning_digest()
        await sync_calendar()
        await sync_github()
        await nightly_backup()
    except Exception:
        log.exception("catch-up basarisiz -- zamanlanmis turlar devam ediyor")

    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("worker durduruldu")
