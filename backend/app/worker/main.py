"""Local-only worker.

Makine kapaliyken calismaz. Bu yuzden ACILISTA hemen bir catch-up turu atar --
"her sabah make up" ritualinin isi gormesini saglayan sey budur.
"""
from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.worker.jobs import catch_up, poll_feeds, prune_old_items

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("worker")


async def main() -> None:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        poll_feeds, "interval",
        minutes=settings.rss_default_interval_minutes,
        jitter=300,                      # feed'ler ayni saniyede yigilmasin
        id="poll_feeds", max_instances=1, coalesce=True,
    )
    scheduler.add_job(prune_old_items, "cron", hour=4, id="prune")
    scheduler.start()
    log.info("worker basladi -- interval=%ddk, retention=%dgun",
             settings.rss_default_interval_minutes, settings.rss_retention_days)

    try:
        await catch_up()
    except Exception:
        log.exception("catch-up basarisiz -- zamanlanmis turlar devam ediyor")

    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("worker durduruldu")
