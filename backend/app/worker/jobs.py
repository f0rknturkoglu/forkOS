"""Worker isleri.

Burada SADECE zamanlama ve sirayla calistirma var. Cekme mantigi modulun
kendisinde (app/modules/rss/service.py) -- boylece "simdi yenile" butonu ve
worker ayni kodu kullanir, ileride scraper katmani VPS'e tasinabilir (kural 5).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from app.core import source_sync
from app.db import SessionLocal
from app.modules.calendar.service import sync_google
from app.modules.media.sync import poll_media_source, poll_media_sources
from app.modules.opportunity.worker import (
    poll_named_source,
)
from app.modules.opportunity.worker import (
    poll_opportunities as _poll_opportunities,
)
from app.modules.project.github import sync as sync_github_service
from app.modules.rss import service as rss
from app.modules.system.backup import backup_if_stale
from app.modules.system.models import Setting

log = logging.getLogger("worker.jobs")

# Ayni anda kac feed cekilsin. Local makinede agresif olmaya gerek yok.
CONCURRENCY = 4


async def record_worker_heartbeat() -> None:
    async with SessionLocal() as session:
        heartbeat = await session.get(Setting, "worker.heartbeat")
        value = {"at": datetime.now(UTC).isoformat()}
        if heartbeat is None:
            session.add(Setting(key="worker.heartbeat", value=value))
        else:
            heartbeat.value = value
        await session.commit()


async def poll_feeds(*, ignore_interval: bool = False) -> int:
    """Suresi gelmis feed'leri ceker. Doner: eklenen toplam item sayisi."""
    async with SessionLocal() as session:
        feeds = await rss.due_feeds(session, interval_minutes=0 if ignore_interval else None)

    if not feeds:
        log.info("poll_feeds: suresi gelen feed yok")
        return 0

    log.info("poll_feeds: %d feed", len(feeds))
    semaphore = asyncio.Semaphore(CONCURRENCY)

    async def run_one(feed_id) -> int:
        # Her feed kendi session'inda: biri patlarsa digerleri etkilenmez.
        async with semaphore, SessionLocal() as session:
            feed = await session.get(rss.Feed, feed_id)
            if feed is None:
                return 0
            try:
                status, added = await rss.poll_feed(session, feed)
            except Exception:
                log.exception("feed cekilemedi: %s", feed.url)
                return 0
            log.info("  %-8s +%-3d %s", status, added, feed.url)
            return added

    total = sum(await asyncio.gather(*(run_one(f.id) for f in feeds)))
    log.info("poll_feeds bitti: %d yeni item", total)
    return total


async def catch_up() -> int:
    """Acilista bekleyen TUM aktif feed'leri hemen cek.

    Local-only mimarinin telafisi burasi: makine kapaliyken kacirilan turlar
    "sabah make up" ile tek seferde kapanir.
    """
    log.info("catch-up turu basliyor")
    return await poll_feeds(ignore_interval=True)


async def prune_old_items() -> int:
    """Okunmamis + kaydedilmemis feed_item'lari retention suresi sonrasi sil."""
    async with SessionLocal() as session:
        removed = await rss.prune_items(session)
    log.info("prune_old_items: %d item silindi", removed)
    return removed


async def poll_opportunities(*, limit: int = 4) -> int:
    total = await _poll_opportunities(limit=limit)
    log.info("poll_opportunities: %d yeni firsat", total)
    return total


async def consume_source_sync_batches(*, limit: int = CONCURRENCY) -> int:
    """API'nin kalıcı kuyruğunu worker sürecinde, sınırlı eşzamanlılıkla tüket."""
    async with SessionLocal() as session:
        await source_sync.reconcile_stale_runs(
            session, older_than=datetime.now(UTC) - timedelta(minutes=15)
        )
        await session.commit()
        batch, pending = await source_sync.claim_pending_sources(session, limit=limit)

    if batch is None or not pending:
        return 0
    semaphore = asyncio.Semaphore(CONCURRENCY)

    async def one(source_id: str) -> int:
        async with semaphore:
            if batch.scope == "media":
                return await poll_media_source(source_id, batch_id=batch.id)
            return await poll_named_source(source_id, batch_id=batch.id)

    total = sum(await asyncio.gather(*(one(source_id) for source_id in pending)))
    log.info(
        "consume_source_sync_batches: %d kaynak, %d yeni fırsat",
        len(pending),
        total,
    )
    return total


async def poll_media() -> int:
    total = await poll_media_sources()
    log.info("poll_media: %d değişiklik", total)
    return total


async def catch_up_media() -> int:
    total = await poll_media_sources(ignore_interval=False)
    log.info("catch_up_media: %d değişiklik", total)
    return total


async def sync_calendar() -> int:
    async with SessionLocal() as session:
        try:
            changed = await sync_google(session)
        except RuntimeError:
            log.info("sync_calendar: Google bağlı değil")
            return 0
    log.info("sync_calendar: %d etkinlik güncellendi", changed)
    return changed


async def sync_github() -> int:
    async with SessionLocal() as session:
        try:
            changed = await sync_github_service(session)
        except RuntimeError:
            log.info("sync_github: GitHub bağlı değil")
            return 0
    log.info("sync_github: %d commit işlendi", changed)
    return changed


async def nightly_backup() -> str | None:
    async with SessionLocal() as session:
        path = await backup_if_stale(session)
    if path:
        log.info("nightly_backup: %s", path)
        return str(path)
    return None
