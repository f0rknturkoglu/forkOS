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
    prune_stale_opportunities,
)
from app.modules.system.maintenance import run_maintenance
from app.worker.jobs import (
    catch_up,
    catch_up_media,
    consume_source_sync_batches,
    critical_catch_up,
    nightly_backup,
    poll_feeds,
    poll_media,
    poll_opportunities,
    proactivity_catch_up,
    proactivity_tick,
    record_worker_heartbeat,
    sync_calendar,
    sync_github,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("worker")

#: Zamanlayicinin RSS turu (dakika). GERCEK cadence `rss.interval_minutes`
#: ayarindan gelir; bu yalnizca "ne siklikta bakariz" degeridir ve taze
#: feed'ler `due_feeds` tarafindan elenir. Kisa tutulur ki ayar degisikligi
#: worker yeniden baslatilmadan etkili olsun.
RSS_POLL_TICK_MINUTES = 5


async def maintenance_job() -> None:
    """Gunde bir kez: operasyonel saklama + RSS + gorsel onbellegi.

    Gun kapisi ve idempotanslik `run_maintenance` icinde.
    """
    async with SessionLocal() as session:
        await run_maintenance(session)


async def prune_opportunities_job() -> None:
    async with SessionLocal() as session:
        await prune_stale_opportunities(session)


async def backfill_opportunity_skill_matches() -> None:
    async with SessionLocal() as session:
        updated = await backfill_skill_match_ratios(session)
        if updated:
            log.info("CV eslesme cache'i tamamlandi: %d ilan", updated)


async def main() -> None:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        poll_feeds,
        "interval",
        minutes=RSS_POLL_TICK_MINUTES,
        jitter=60,  # feed'ler ayni saniyede yigilmasin
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

    scheduler.add_job(maintenance_job, "cron", hour=4, id="maintenance")

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

    scheduler.add_job(
        sync_calendar,
        "interval",
        minutes=60,
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

    await run_startup(scheduler)
    await asyncio.Event().wait()


async def run_startup(scheduler: AsyncIOScheduler, *, tasks: list | None = None) -> None:
    """Aciliş zinciri + H6 turunun KAYDI (H6.1/D).

    KRITIK SIRA: `proactivity_tick` ancak kaynak tazeleme ve H6 telafisi
    TAMAMLANDIKTAN SONRA kaydedilir. Aksi halde dakikalik tur, startup
    surerken (or. 3 dakikalik kaynak cekimi) BAYAT operasyonel durum uzerinden
    aday uretip bildirim gonderebilirdi. Zamanlayici zaten calisiyor olsa da
    kaydedilmeyen is CALISMAZ -- bu yuzden kapi tek satirlik ve aciktir.
    """
    chain = tasks if tasks is not None else _startup_tasks()
    for task_name, task_fn in chain:
        try:
            await task_fn()
        except Exception:
            log.exception(
                "startup gorevi basarisiz oldu (%s) -- diger gorevler devam ediyor", task_name
            )

    # TEK proaktif is: ritüel/son tarih/proje kararlari bu turun ICINDE verilir
    # (dakikada bir "bakilacak bir sey var mi?" kontrolu). Kullaniciya giden
    # cadence H6 politikasindadir, zamanlayicida DEGIL.
    scheduler.add_job(
        proactivity_tick,
        "interval",
        minutes=1,
        id="proactivity_tick",
        max_instances=1,
        coalesce=True,
    )
    log.info("proaktif tur kaydedildi (kaynak tazeleme + H6 telafisi tamamlandi)")


def _startup_tasks() -> list:
    return [
        ("heartbeat", record_worker_heartbeat),
        ("maintenance", maintenance_job),
        ("backfill_opportunity_skill_matches", backfill_opportunity_skill_matches),
        # Kritik kaynaklar once: aciliş tanıtımında YLSY/OSYM tazelenir.
        ("critical_catch_up", critical_catch_up),
        ("catch_up_feeds", catch_up),
        ("catch_up_media", catch_up_media),
        # Kaynaklar tazelendikten SONRA: H6 telafisi guncel duruma bakar.
        ("proactivity_catch_up", proactivity_catch_up),
        ("sync_calendar", sync_calendar),
        ("sync_github", sync_github),
        ("nightly_backup", nightly_backup),
    ]


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("worker durduruldu")
