"""Worker isleri.

Burada SADECE zamanlama ve sirayla calistirma var. Cekme mantigi modulun
kendisinde (app/modules/rss/service.py) -- boylece "simdi yenile" butonu ve
worker ayni kodu kullanir, ileride scraper katmani VPS'e tasinabilir (kural 5).
"""
from __future__ import annotations

import asyncio
import logging

from app.db import SessionLocal
from app.modules.rss import service as rss

log = logging.getLogger("worker.jobs")

# Ayni anda kac feed cekilsin. Local makinede agresif olmaya gerek yok.
CONCURRENCY = 4


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
