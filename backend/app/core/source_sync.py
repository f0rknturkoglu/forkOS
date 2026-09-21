from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import runs as run_svc
from app.core.events import log_event
from app.core.models import SourceRun, SourceSyncBatch

ACTIVE_STATUSES = ("queued", "running")

#: Bir kaynak bir batch icinde en fazla bu kadar kez sahiplenilir. Butcesini
#: asan (surekli coken) kaynak "error" yazilir ki batch asla `running` kalmasin.
MAX_CLAIM_ATTEMPTS = 3

#: Reconcile icin varsayilan kiralama tavani (kaynak bazli lease verilmezse).
DEFAULT_LEASE = timedelta(minutes=15)


def batch_out(batch: SourceSyncBatch) -> dict:
    total = batch.total_sources or 0
    return {
        "id": str(batch.id),
        "scope": batch.scope,
        "status": batch.status,
        "source_ids": batch.source_ids,
        "total_sources": total,
        "completed_sources": batch.completed_sources,
        "ok_sources": batch.ok_sources,
        "partial_sources": batch.partial_sources,
        "empty_sources": batch.empty_sources,
        "error_sources": batch.error_sources,
        "items_found": batch.items_found,
        "progress_pct": int(batch.completed_sources * 100 / total) if total else 0,
        "created_at": batch.created_at,
        "started_at": batch.started_at,
        "finished_at": batch.finished_at,
    }


async def create_or_extend_batch(
    session: AsyncSession, source_ids: list[str], *, scope: str = "opportunity"
) -> tuple[SourceSyncBatch, list[str]]:
    ids = list(dict.fromkeys(source_ids))
    # A row lock cannot serialize the empty-table case. Scope-level transaction
    # advisory locking keeps creation and extension in one PostgreSQL critical section.
    await session.execute(
        text(
            "select pg_advisory_xact_lock("
            "hashtext('forkos.source_sync_batch'), hashtext(:scope))"
        ),
        {"scope": scope},
    )
    batch = (
        await session.execute(
            select(SourceSyncBatch)
            .where(
                SourceSyncBatch.scope == scope,
                SourceSyncBatch.status.in_(ACTIVE_STATUSES),
            )
            .order_by(SourceSyncBatch.created_at.desc())
            .limit(1)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if batch is None:
        batch = SourceSyncBatch(
            scope=scope, status="queued", source_ids=ids, total_sources=len(ids)
        )
        session.add(batch)
        await session.flush()
        await log_event(
            session,
            verb="source_sync.queued",
            entity_type="source_sync",
            payload={"batch_id": str(batch.id), "scope": scope, "total_sources": len(ids)},
        )
        return batch, ids
    existing = set(batch.source_ids or [])
    added = [source_id for source_id in ids if source_id not in existing]
    if added:
        batch.source_ids = [*(batch.source_ids or []), *added]
        batch.total_sources += len(added)
        await log_event(
            session,
            verb="source_sync.sources_added",
            entity_type="source_sync",
            payload={"batch_id": str(batch.id), "scope": scope, "count": len(added)},
        )
    return batch, added


async def claim_pending_batch(session: AsyncSession) -> SourceSyncBatch | None:
    batch = (
        await session.execute(
            select(SourceSyncBatch)
            .where(SourceSyncBatch.status.in_(ACTIVE_STATUSES))
            .order_by(SourceSyncBatch.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
    ).scalar_one_or_none()
    if batch is None:
        return None
    if batch.status == "queued":
        batch.status = "running"
        batch.started_at = datetime.now(UTC)
        await log_event(
            session,
            verb="source_sync.started",
            entity_type="source_sync",
            payload={"batch_id": str(batch.id), "scope": batch.scope},
        )
    await session.commit()
    return batch


async def claim_pending_sources(
    session: AsyncSession, *, limit: int
) -> tuple[SourceSyncBatch | None, list[str]]:
    """En eski batch satırını kilitleyip source_run rezervasyonlarını atomik yaz."""
    batch = (
        await session.execute(
            select(SourceSyncBatch)
            .where(SourceSyncBatch.status.in_(ACTIVE_STATUSES))
            .order_by(SourceSyncBatch.created_at)
            .limit(1)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if batch is None:
        await session.commit()
        return None, []
    if batch.status == "queued":
        batch.status = "running"
        batch.started_at = datetime.now(UTC)
        await log_event(
            session,
            verb="source_sync.started",
            entity_type="source_sync",
            payload={"batch_id": str(batch.id), "scope": batch.scope},
        )
    pending = await pending_source_ids(session, batch)
    if not pending:
        # Tuketilecek is kalmadi: butcesini asmis (surekli terk edilmis)
        # kaynaklari terminal hataya cevir, sonra sayaclari tazele. Batch
        # tamamlanabiliyorsa burada terminal olur — worker olmese bile
        # `running` kalmaz.
        await _fail_exhausted_sources(session, batch)
        await _recompute_batch(session, batch)
        await session.commit()
        return batch, []
    reserved = pending[:limit]
    for source_id in reserved:
        session.add(
            SourceRun(source=source_id, status="running", batch_id=batch.id)
        )
    await session.commit()
    return batch, reserved


async def _attempt_counts(
    session: AsyncSession, pairs: set[tuple[uuid.UUID, str]]
) -> dict[tuple[uuid.UUID, str], int]:
    """(batch_id, source) basina toplam kosum sayisi -- tek sorgu."""
    if not pairs:
        return {}
    batch_ids = {batch_id for batch_id, _ in pairs}
    sources = {source for _, source in pairs}
    rows = await session.execute(
        select(SourceRun.batch_id, SourceRun.source, func.count())
        .where(
            SourceRun.batch_id.in_(batch_ids),
            SourceRun.source.in_(sources),
        )
        .group_by(SourceRun.batch_id, SourceRun.source)
    )
    return {
        (batch_id, source): count
        for batch_id, source, count in rows
        if batch_id is not None
    }


async def pending_source_ids(session: AsyncSession, batch: SourceSyncBatch) -> list[str]:
    rows = list(
        (
            await session.execute(
                select(SourceRun)
                .where(SourceRun.batch_id == batch.id)
                .order_by(SourceRun.started_at.desc(), SourceRun.id.desc())
            )
        ).scalars()
    )
    latest: dict[str, SourceRun] = {}
    for row in rows:
        latest.setdefault(row.source, row)
    finished = {"ok", "empty", "error"}
    claimed = await _attempt_counts(
        session, {(batch.id, source_id) for source_id in batch.source_ids}
    )
    return [
        source_id
        for source_id in batch.source_ids
        if (source_id not in latest or latest[source_id].status not in finished | {"running"})
        and claimed.get((batch.id, source_id), 0) < MAX_CLAIM_ATTEMPTS
    ]


async def reconcile_stale_runs(
    session: AsyncSession,
    *,
    older_than: datetime | None = None,
    long_running_sources: tuple[str, ...] = ("jobhunter:eures",),
    long_older_than: datetime | None = None,
    leases: dict[str, timedelta] | None = None,
    now: datetime | None = None,
) -> int:
    """Sahiplenilip terk edilmis kosumlari geri al.

    Iki kip vardir:
      - `leases` verilirse her kaynak icin `started_at + lease < now` esigine
        gore calisir (kaynak sinifinin sert timeout'u + pay). API tarafi bunu
        kullanir; worker kapaliyken de kirli kosumlar geri alinir.
      - `leases` verilmezse eski davranis korunur: `older_than` esigi ve EURES
        gibi uzun suren kaynaklar icin `long_older_than`.

    Butcesini asan (MAX_CLAIM_ATTEMPTS kez sahiplenilip yine takilan) kaynak
    `abandoned` yerine `error` yazilir; boylece batch terminal duruma ulasir.
    """
    moment = now or datetime.now(UTC)
    default_cutoff = older_than or (moment - DEFAULT_LEASE)
    long_cutoff = long_older_than or (moment - timedelta(minutes=60))

    def cutoff_for(source: str) -> datetime:
        if leases is not None and source in leases:
            return moment - leases[source]
        if source in long_running_sources:
            return long_cutoff
        return default_cutoff

    running = list(
        (
            await session.execute(
                select(SourceRun.id, SourceRun.source, SourceRun.batch_id, SourceRun.started_at)
                .where(SourceRun.status == "running")
            )
        ).all()
    )
    stale = [row for row in running if row.started_at < cutoff_for(row.source)]
    if not stale:
        return 0

    claimed = await _attempt_counts(
        session, {(row.batch_id, row.source) for row in stale if row.batch_id is not None}
    )
    abandon_ids: list[int] = []
    fail_ids: list[int] = []
    batches: set[uuid.UUID] = set()
    for row in stale:
        attempts = claimed.get((row.batch_id, row.source), 1) if row.batch_id else 1
        if row.batch_id and attempts >= MAX_CLAIM_ATTEMPTS:
            fail_ids.append(row.id)
            batches.add(row.batch_id)
        else:
            abandon_ids.append(row.id)
            if row.batch_id:
                batches.add(row.batch_id)

    if abandon_ids:
        await session.execute(
            update(SourceRun)
            .where(SourceRun.id.in_(abandon_ids))
            .values(
                status="abandoned",
                finished_at=moment,
                error="claim lease expired; requeued",
            )
        )
    if fail_ids:
        await session.execute(
            update(SourceRun)
            .where(SourceRun.id.in_(fail_ids))
            .values(
                status="error",
                finished_at=moment,
                error=f"claim lease expired after {MAX_CLAIM_ATTEMPTS} attempts; giving up",
            )
        )
    for batch_id in batches:
        batch = (
            await session.execute(
                select(SourceSyncBatch).where(SourceSyncBatch.id == batch_id)
            )
        ).scalar_one_or_none()
        if batch is None or batch.status not in ACTIVE_STATUSES:
            continue
        await _recompute_batch(session, batch)
        if batch.status != "running":
            continue
        # Drain olmus: batch `queued`a doner ve bir sonraki tuketici devam eder.
        still_running = (
            await session.execute(
                select(SourceRun.id)
                .where(SourceRun.batch_id == batch.id, SourceRun.status == "running")
                .limit(1)
            )
        ).scalar_one_or_none()
        if still_running is None:
            batch.status = "queued"
    return len(abandon_ids) + len(fail_ids)


async def _fail_exhausted_sources(session: AsyncSession, batch: SourceSyncBatch) -> int:
    """Butcesini asmis kaynaklarin son kosumunu `error` yaz.

    Surekli coken bir kaynak `abandoned` kaldigi surece `_recompute_batch`
    onu saymaz ve batch sonsuza kadar `running` kalirdi. Bu, terminal
    garantisinin son halkasi.
    """
    rows = list(
        (
            await session.execute(
                select(SourceRun)
                .where(SourceRun.batch_id == batch.id)
                .order_by(SourceRun.started_at.desc(), SourceRun.id.desc())
            )
        ).scalars()
    )
    latest: dict[str, SourceRun] = {}
    for row in rows:
        if row.source in batch.source_ids:
            latest.setdefault(row.source, row)
    claimed = await _attempt_counts(
        session, {(batch.id, source_id) for source_id in batch.source_ids}
    )
    moment = datetime.now(UTC)
    changed = 0
    for source_id in batch.source_ids:
        row = latest.get(source_id)
        if row is None or row.status in ("ok", "empty", "error"):
            continue
        if claimed.get((batch.id, source_id), 0) >= MAX_CLAIM_ATTEMPTS:
            row.status = "error"
            row.finished_at = moment
            row.error = f"claim attempts exhausted ({MAX_CLAIM_ATTEMPTS}); giving up"
            changed += 1
    return changed


async def _recompute_batch(session: AsyncSession, batch: SourceSyncBatch) -> None:
    """Batch sayaclarini source_run gecmisinden yeniden turet.

    Yalnizca terminal durumlar (ok/empty/error) sayilir; `abandoned` ve
    `running` is bekleyen is demektir. Tum kaynaklar terminal oldugunda batch
    `completed` / `completed_with_errors` olur.
    """
    rows = list(
        (
            await session.execute(
                select(SourceRun)
                .where(
                    SourceRun.batch_id == batch.id,
                    # `partial` de tamamlanmis bir kosumdur: sayilmazsa batch
                    # sonsuza kadar `running` kalir.
                    SourceRun.status.in_(("ok", "partial", "empty", "error")),
                )
                .order_by(SourceRun.started_at.desc(), SourceRun.id.desc())
            )
        ).scalars()
    )
    latest: dict[str, SourceRun] = {}
    for row in rows:
        if row.source in batch.source_ids:
            latest.setdefault(row.source, row)
    batch.completed_sources = len(latest)
    batch.ok_sources = sum(row.status == "ok" for row in latest.values())
    batch.partial_sources = sum(row.status == "partial" for row in latest.values())
    batch.empty_sources = sum(row.status == "empty" for row in latest.values())
    batch.error_sources = sum(row.status == "error" for row in latest.values())
    batch.items_found = sum(row.items_found for row in latest.values())
    if batch.completed_sources >= batch.total_sources and batch.status in ACTIVE_STATUSES:
        batch.status = "completed_with_errors" if batch.error_sources else "completed"
        batch.finished_at = datetime.now(UTC)
        await log_event(
            session,
            verb="source_sync.completed",
            entity_type="source_sync",
            payload={
                "batch_id": str(batch.id),
                "scope": batch.scope,
                "count": batch.items_found,
                "errors": batch.error_sources,
            },
        )


async def finish_batch_source(
    session: AsyncSession,
    batch_id: uuid.UUID,
    *,
    status: str,
    items_found: int = 0,
) -> None:
    batch = (
        await session.execute(
            select(SourceSyncBatch).where(SourceSyncBatch.id == batch_id).with_for_update()
        )
    ).scalar_one_or_none()
    if batch is None or batch.status not in ACTIVE_STATUSES:
        return
    await _recompute_batch(session, batch)


async def current_status(session: AsyncSession, *, scope: str = "opportunity") -> dict:
    base_scope = SourceSyncBatch.scope == scope
    last_completed = (
        await session.execute(
            select(SourceSyncBatch)
            .where(base_scope, ~SourceSyncBatch.status.in_(ACTIVE_STATUSES))
            .order_by(SourceSyncBatch.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    batch = (
        await session.execute(
            select(SourceSyncBatch)
            .where(base_scope, SourceSyncBatch.status.in_(ACTIVE_STATUSES))
            .order_by(SourceSyncBatch.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if batch is None:
        return {
            "active": None,
            "last_completed": batch_out(last_completed) if last_completed else None,
            "sources": [],
            "running": [],
        }
    rows = list(
        (
            await session.execute(
                select(SourceRun)
                .where(SourceRun.batch_id == batch.id)
                .order_by(SourceRun.started_at.desc())
            )
        ).scalars()
    )
    latest: dict[str, SourceRun] = {}
    for row in rows:
        latest.setdefault(row.source, row)

    def visible_status(source_id: str) -> str:
        row = latest.get(source_id)
        return "queued" if row is None or row.status == "abandoned" else row.status

    sources = [
        {
            "source": source_id,
            "status": visible_status(source_id),
            "started_at": latest[source_id].started_at if source_id in latest else None,
            "finished_at": latest[source_id].finished_at if source_id in latest else None,
            "items_found": latest[source_id].items_found if source_id in latest else 0,
            #: Kolon ham metin tasiyabilir (media senkronu, eski satirlar);
            #: `/sources/sync` her zaman temizlenmis metni gosterir.
            "error": (
                run_svc.error_message_of(latest[source_id]) if source_id in latest else None
            ),
        }
        for source_id in batch.source_ids
    ]
    return {
        "active": batch_out(batch),
        "last_completed": batch_out(last_completed) if last_completed else None,
        "sources": sources,
        "running": [row for row in sources if row["status"] == "running"],
    }


async def history(
    session: AsyncSession, limit: int = 10, *, scope: str = "opportunity"
) -> list[dict]:
    rows = (
        await session.execute(
            select(SourceSyncBatch)
            .where(
                SourceSyncBatch.scope == scope,
                ~SourceSyncBatch.status.in_(ACTIVE_STATUSES),
            )
            .order_by(SourceSyncBatch.created_at.desc())
            .limit(limit)
        )
    ).scalars()
    return [batch_out(batch) for batch in rows]
