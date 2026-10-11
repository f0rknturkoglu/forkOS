"""Operasyonel veri saklama (retention).

`event` BURADA DEGIL ve olmayacak: o kisisel aktivite hafizasi, budanmaz.
Burada yalnizca yeniden uretilebilir operasyonel kayitlar var.

Esikler `source_run` gecmisinden turetilen saglik kararlarini bozmayacak
sekilde secildi. Bu kararlar sunlara bakar:

  - devre kesici (circuit_states): ardisik hata sayisi
  - sessiz olum alarmi (check_stalled/check_failing): son N kosu
  - kapsam kuculmesi (previous_seen_count): onceki `ok` kosu
  - yeniden sahiplenme butcesi (_attempt_counts): batch ici kosu sayisi

Bu yuzden "her kaynak icin son N kosu her durumda kalir" kurali esiklerden
bagimsizdir; kaynak yillarca kosmasa bile son gorunumu korunur.

Politika:

  source_run
    ok / empty            : 30 gun
    partial/error/...     : 90 gun  (devre kesici ve kapsam karsilastirmasi
                                     daha uzun gecmis ister)
    her kaynak icin       : en az son 20 kosu HER DURUMDA kalir
  source_sync_batch
    opportunity terminal (completed / completed_with_errors) : 60 gun
    media historical batches and runs            : ASLA silinmez
    aktif (queued / running)                     : ASLA silinmez
  notification
    okunmus/kapatilmis, importance < 3           : 90 gun
    okunmus/kapatilmis, importance >= 3          : 180 gun
    okunmamis VE kapatilmamis                    : ASLA silinmez
  proactivity_run
    terminal (resolved/cancelled/dismissed/failed) : 90 gun
    aktif (candidate/deferred/digest_queued/snoozed)
    ve teslim edilmis (delivered) kosular          : ASLA silinmez

      `delivered` neden SINIRSIZ kalir (H6.1 karari: KEEP)?
      Cunku `logical_trigger_key` TEK SEFERLIK kosunun kimligidir: satir
      budanirsa ayni esik (or. ayni son tarihin T-3 basamagi) yeniden
      uretilebilir hale gelir ve kullanici AYNI seyi ikinci kez alir. Satir
      ayrica cooldown muhasebesini (`last_delivered_at`, `delivery_count`) ve
      "neden o gun durtuldu" sorusunun cevabini tasir. Bu yuzden teslim
      edilmis kosular H6'nin idempotans invariantinin PARCASIDIR; budama
      yalnizca terminal durumlarla sinirlidir.

Budama `created_at`e gore yapilir. Silinen bir bildirimin `dedup_key`i
yeniden uretilebilir hale gelir; bu yalnizca kosulu hala gecerli olan kalici
sorunlarda (or. bir medya saglayicisi hala cokuyor) 90 gunde bir tekrar
bildirim demektir -- spam degil, "hala bozuk" hatirlatmasidir.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Notification, SourceRun, SourceSyncBatch

#: Sorunsuz kosular (`ok`, `empty`) bu kadar gun tutulur.
SOURCE_RUN_OK_DAYS = 30
#: Geri kalan kosular (partial/error/abandoned) bu kadar gun tutulur.
SOURCE_RUN_PROBLEM_DAYS = 90
#: Esikten bagimsiz korunan kosu sayisi (kaynak basina).
SOURCE_RUN_KEEP_PER_SOURCE = 20
_SOURCE_RUN_OK_STATUSES = ("ok", "empty")

#: Terminal batch'ler bu kadar gun tutulur. Aktif batch asla silinmez.
SOURCE_SYNC_BATCH_DAYS = 60
SOURCE_SYNC_BATCH_TERMINAL_STATUSES = ("completed", "completed_with_errors")

#: Okunmus/kapatilmis bildirimler bu kadar gun tutulur.
NOTIFICATION_DAYS = 90
#: Acil bildirimler (importance >= 3) daha uzun tutulur.
NOTIFICATION_CRITICAL_DAYS = 180
NOTIFICATION_CRITICAL_IMPORTANCE = 3


async def prune_source_runs(session: AsyncSession, *, now: datetime | None = None) -> int:
    """Eski `source_run` satirlarini sil; her kaynagin son N kosusu kalir."""
    moment = now or datetime.now(UTC)
    ok_cutoff = moment - timedelta(days=SOURCE_RUN_OK_DAYS)
    problem_cutoff = moment - timedelta(days=SOURCE_RUN_PROBLEM_DAYS)

    ranked = (
        select(
            SourceRun.id.label("id"),
            SourceRun.started_at.label("started_at"),
            SourceRun.status.label("status"),
            func.row_number()
            .over(
                partition_by=SourceRun.source,
                order_by=(SourceRun.started_at.desc(), SourceRun.id.desc()),
            )
            .label("rank"),
        )
        .subquery()
    )
    archived_sources = select(SourceSyncBatch.source_ids).where(SourceSyncBatch.scope == "media")
    # Preserve both attached and detached historical Media runs.
    media_sources = {source for ids in (await session.execute(archived_sources)).scalars() for source in ids}
    doomed = select(ranked.c.id).where(
        ranked.c.id.not_in(select(SourceRun.id).where(SourceRun.batch_id.in_(
            select(SourceSyncBatch.id).where(SourceSyncBatch.scope == "media")))),
        ranked.c.id.not_in(select(SourceRun.id).where(SourceRun.source.in_(media_sources))),
        ranked.c.id.not_in(select(SourceRun.id).where(SourceRun.source.like("media:%"))),
        ranked.c.rank > SOURCE_RUN_KEEP_PER_SOURCE,
        or_(
            and_(
                ranked.c.status.in_(_SOURCE_RUN_OK_STATUSES),
                ranked.c.started_at < ok_cutoff,
            ),
            and_(
                ranked.c.status.not_in(_SOURCE_RUN_OK_STATUSES),
                ranked.c.started_at < problem_cutoff,
            ),
        ),
    )
    result = await session.execute(delete(SourceRun).where(SourceRun.id.in_(doomed)))
    return result.rowcount or 0


async def prune_source_sync_batches(
    session: AsyncSession, *, now: datetime | None = None
) -> int:
    """Opportunity terminal batches only; active and historical Media records remain."""
    moment = now or datetime.now(UTC)
    cutoff = moment - timedelta(days=SOURCE_SYNC_BATCH_DAYS)
    result = await session.execute(
        delete(SourceSyncBatch).where(
            SourceSyncBatch.scope == "opportunity",
            SourceSyncBatch.status.in_(SOURCE_SYNC_BATCH_TERMINAL_STATUSES),
            func.coalesce(SourceSyncBatch.finished_at, SourceSyncBatch.created_at) < cutoff,
        )
    )
    return result.rowcount or 0


async def prune_notifications(session: AsyncSession, *, now: datetime | None = None) -> int:
    """Okunmus/kapatilmis eski bildirimleri sil; okunmamis olanlar kalir."""
    moment = now or datetime.now(UTC)
    cutoff = moment - timedelta(days=NOTIFICATION_DAYS)
    critical_cutoff = moment - timedelta(days=NOTIFICATION_CRITICAL_DAYS)
    handled = Notification.read_at.is_not(None) | Notification.dismissed_at.is_not(None)
    critical = Notification.importance >= NOTIFICATION_CRITICAL_IMPORTANCE
    result = await session.execute(
        delete(Notification).where(
            handled,
            or_(
                and_(critical, Notification.created_at < critical_cutoff),
                and_(~critical, Notification.created_at < cutoff),
            ),
        )
    )
    return result.rowcount or 0


async def prune_operational(session: AsyncSession, *, now: datetime | None = None) -> dict[str, int]:
    """Operasyonel budamanin tamami; sonuclar tablo adiyla doner.

    Commit CAGIRMAZ: cagiran taraf (maintenance / worker) tek transaction
    icinde istedigi gibi davranabilsin.
    """
    return {
        "source_run": await prune_source_runs(session, now=now),
        "source_sync_batch": await prune_source_sync_batches(session, now=now),
        "notification": await prune_notifications(session, now=now),
        "proactivity_run": await prune_proactivity_runs(session, now=now),
    }


async def prune_proactivity_runs(session: AsyncSession, *, now: datetime | None = None) -> int:
    """H6 kosu gecmisi: YALNIZCA terminal kosular budanir.

    Bekleyen (ertelenmis/digest kuyrugunda) veya teslim edilmis kosular
    silinmez: "neden simdi durtuldu" sorusunun cevabi ve cooldown muhasebesi
    bu satirlara baglidir.
    """
    from app.modules.proactivity.models import ProactivityRun
    from app.modules.proactivity.service import RUN_RETENTION_DAYS

    moment = now or datetime.now(UTC)
    cutoff = moment - timedelta(days=RUN_RETENTION_DAYS)
    result = await session.execute(
        delete(ProactivityRun).where(
            ProactivityRun.created_at < cutoff,
            ProactivityRun.state.in_(("resolved", "cancelled", "dismissed", "failed")),
        )
    )
    return int(result.rowcount or 0)
