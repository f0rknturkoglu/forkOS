"""Worker isleri.

Burada SADECE zamanlama ve sirayla calistirma var. Cekme mantigi modulun
kendisinde (app/modules/rss/service.py) -- boylece "simdi yenile" butonu ve
worker ayni kodu kullanir, ileride scraper katmani VPS'e tasinabilir (kural 5).
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import time
from datetime import UTC, datetime, timedelta

from app.core import source_sync
from app.core.heartbeat import WORKER_HEARTBEAT_KEY
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
        heartbeat = await session.get(Setting, WORKER_HEARTBEAT_KEY)
        value = {"at": datetime.now(UTC).isoformat()}
        if heartbeat is None:
            session.add(Setting(key=WORKER_HEARTBEAT_KEY, value=value))
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


#: Acilista kuyruga alinacak kritik kaynak sayisi (sinirli tutulur).
CRITICAL_CATCH_UP_LIMIT = 12


async def critical_catch_up(*, limit: int = CRITICAL_CATCH_UP_LIMIT) -> int:
    """Acilista kritik kaynaklari kalici yenileme kuyrugunun basina koy.

    Local-only mimaride makine kapaliyken gecen sure kritik YLSY/OSYM
    kaynaklari icin telafi edilmelidir, ama acilis da bloklanmamali: yalniz
    `critical` sinif kuyruga girer, sayisi sinirlidir ve cekimi mevcut
    worker/API drain'i yapar (ilerleme UI'da gorunur, lease/devre kesici
    guvenlikleri aynen gecerli).
    """
    from app.modules.opportunity.worker import critical_source_ids

    ids = critical_source_ids()[:limit]
    if not ids:
        return 0
    async with SessionLocal() as session:
        batch, newly_queued = await source_sync.create_or_extend_batch(session, ids)
        await session.commit()
    log.info(
        "critical_catch_up: %d kritik kaynak kuyruga alindi (batch %s)",
        len(newly_queued),
        batch.id,
    )
    return len(newly_queued)


DRAIN_HEARTBEAT_KEY = "source_sync.drain"
#: Bir drain bu kadar saniye kalp atmazsa olu sayilir; API okuma tarafi
#: kuyrugu devralmak icin yeni bir drain baslatir.
DRAIN_HEARTBEAT_STALE = timedelta(seconds=90)
#: Kaynak sinifinin sert timeout'una eklenen kiralama payi.
LEASE_GRACE = timedelta(seconds=30)


def _source_catalog() -> list:
    from app.sources.announcements import SOURCES
    from app.sources.forkjob_port import forkjob_sources

    return [*forkjob_sources(include_opt_in=True), *SOURCES]


_LEASE_CACHE: tuple[float, dict[str, timedelta]] | None = None
_LEASE_CACHE_SECONDS = 300.0


def _lease_map() -> dict[str, timedelta]:
    """Kaynak basina kiralama: sert timeout + pay (kisa sureli onbellekli)."""
    global _LEASE_CACHE

    from app.sources.base import source_timeout_seconds

    now = time.monotonic()
    if _LEASE_CACHE is None or now - _LEASE_CACHE[0] > _LEASE_CACHE_SECONDS:
        _LEASE_CACHE = (
            now,
            {
                source.id: timedelta(seconds=source_timeout_seconds(source)) + LEASE_GRACE
                for source in _source_catalog()
            },
        )
    return _LEASE_CACHE[1]


async def touch_drain_heartbeat(session, *, batch_id=None) -> None:
    value = {
        "owner": f"{socket.gethostname()}:{os.getpid()}",
        "batch_id": str(batch_id) if batch_id else None,
        "at": datetime.now(UTC).isoformat(),
    }
    row = await session.get(Setting, DRAIN_HEARTBEAT_KEY)
    if row is None:
        session.add(Setting(key=DRAIN_HEARTBEAT_KEY, value=value))
    else:
        row.value = value


async def drain_heartbeat(session) -> datetime | None:
    row = await session.get(Setting, DRAIN_HEARTBEAT_KEY)
    value = row.value if row is not None and isinstance(row.value, dict) else None
    at = (value or {}).get("at")
    if not isinstance(at, str):
        return None
    try:
        return datetime.fromisoformat(at)
    except ValueError:
        return None


async def drain_is_alive(session, *, now: datetime | None = None) -> bool:
    """Kalp atisi taze bir drain var mi? API okumasi buna gore devralir."""
    at = await drain_heartbeat(session)
    return at is not None and at >= (now or datetime.now(UTC)) - DRAIN_HEARTBEAT_STALE


#: Taze olusturulmus bir batch'i GET okumasi hemen devralmasin: POST'un kendi
#: arka plan gorevi once baslasin. Bu sureden eski, tuketicisi olmayan batch
#: (olmus drain) okuma sirasinda devralinir.
AUTO_DRAIN_GRACE = timedelta(seconds=30)


def batch_waiting_too_long(batch: dict, *, now: datetime | None = None) -> bool:
    reference = batch.get("started_at") or batch.get("created_at")
    if isinstance(reference, str):
        try:
            reference = datetime.fromisoformat(reference)
        except ValueError:
            return False
    if not isinstance(reference, datetime):
        return False
    return reference <= (now or datetime.now(UTC)) - AUTO_DRAIN_GRACE


async def reclaim_stale_source_runs(session, *, now: datetime | None = None) -> int:
    """API tarafi uzlastirma: sinif bazli lease ile kirli kosumlari geri al.

    Worker kapaliyken `running` kalan batch'ler burada `queued`a doner; commit
    cagirana aittir.
    """
    moment = now or datetime.now(UTC)
    return await source_sync.reconcile_stale_runs(
        session,
        older_than=moment - source_sync.DEFAULT_LEASE,
        leases=_lease_map(),
        now=moment,
    )


async def _consume_source_sync_batch(*, limit: int = CONCURRENCY) -> tuple[int, int]:
    """Kuyruktan bir dilim tüket; (işlenen kaynak, eklenen kayıt) döndür."""
    async with SessionLocal() as session:
        # Her dilim once kirli sahiplikleri geri alir: drain olduyse bile is
        # yeniden sahiplenilebilir hale gelir.
        await reclaim_stale_source_runs(session)
        batch, pending = await source_sync.claim_pending_sources(session, limit=limit)
        if batch is not None:
            # Kalp atisi YALNIZ aktif bir batch varken yazilir: tek islevi
            # "bu kuyrugun sahibi hala yasiyor" sorusunu yanitlamak
            # (bkz. drain_is_alive) ve o soru yalniz aktif batch varken
            # sorulur. Kuyruk bosken her dakika kosulsuz UPDATE+COMMIT
            # yaziliyordu -- idle worker artik hic yazmiyor.
            await touch_drain_heartbeat(session, batch_id=batch.id)
            await session.commit()

    if batch is None or not pending:
        return 0, 0
    semaphore = asyncio.Semaphore(CONCURRENCY)

    async def one(source_id: str) -> int:
        async with semaphore:
            if batch.scope == "media":
                return await poll_media_source(source_id, batch_id=batch.id)
            return await poll_named_source(source_id, batch_id=batch.id)

    total = sum(await asyncio.gather(*(one(source_id) for source_id in pending)))
    async with SessionLocal() as session:
        await touch_drain_heartbeat(session, batch_id=batch.id)
        await session.commit()
    log.info(
        "consume_source_sync_batches: %d kaynak, %d yeni fırsat",
        len(pending),
        total,
    )
    return len(pending), total


async def consume_source_sync_batches(*, limit: int = CONCURRENCY) -> int:
    """API'nin kalıcı kuyruğundan tek bir sınırlı dilim tüket."""
    _, total = await _consume_source_sync_batch(limit=limit)
    return total


async def drain_source_sync_batches(*, limit: int = CONCURRENCY) -> int:
    """Worker kapalıyken manuel yenilemenin oluşturduğu kuyruğu tamamen tüket.

    Baslangicta terk edilmis sahiplikleri geri alir (crash sonrasi devam) ve
    kuyruk bosalana kadar dilim dilim tuketir. Batch her zaman terminal bir
    duruma (`completed` / `completed_with_errors`) ulasir.
    """
    total = 0
    while True:
        processed, added = await _consume_source_sync_batch(limit=limit)
        total += added
        if processed == 0:
            async with SessionLocal() as session:
                await touch_drain_heartbeat(session)
                await session.commit()
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
