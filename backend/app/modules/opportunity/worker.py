from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, or_, select

from app.core import runs
from app.core.models import SourceRun
from app.db import SessionLocal
from app.modules.opportunity import service
from app.modules.opportunity import sync as sync_service
from app.sources.announcements import SOURCES
from app.sources.base import FetchOutcome, normalize_fetch, source_class, source_timeout_seconds
from app.sources.forkjob_port import forkjob_sources

log = logging.getLogger("worker.opportunity")

#: Kaynak basina ust sinif tekrar deneme (ilk deneme haric).
MAX_SOURCE_RETRIES = 2
RETRY_BACKOFF_BASE = 1.0
RETRY_BACKOFF_CAP = 20.0

#: Kapanma bekleme suresi (gun) kaynak sinifina gore.
CLOSE_GRACE_DAYS = {"critical": 1, "normal": 3, "slow_optin": 14}

#: Kapsam koruma: yeni kosu, onceki TAM kosunun gordugu kayit sayisinin bu
#: oranindan azini gorduyse kaynak daralmis sayilir (sayfalama/yardimci feed
#: bozulmustur) ve kapanma taramasi YAPILMAZ. Kucuk kaynaklarda yanlis pozitif
#: olmamasi icin bir de mutlak taban vardir.
SWEEP_SCOPE_MIN_BASELINE = 10
SWEEP_SCOPE_MIN_RATIO = 0.5

#: Ayni kaynagi ayni anda iki kez kosmamak icin surec-ici kilitler.
_SOURCE_LOCKS: dict[str, asyncio.Lock] = {}


def _lock_for(source_id: str) -> asyncio.Lock:
    return _SOURCE_LOCKS.setdefault(source_id, asyncio.Lock())


def _error_message(exc: Exception) -> str:
    detail = str(exc).strip()
    return f"{type(exc).__name__}: {detail}" if detail else type(exc).__name__


@dataclass
class NativeJob:
    raw: Any

    def __getattr__(self, name: str) -> Any:
        deadline_at = self.raw.extra.get("deadline_at")
        if isinstance(deadline_at, str):
            try:
                deadline_at = datetime.fromisoformat(deadline_at)
            except ValueError:
                deadline_at = None
        values = {
            "external_id": self.raw.external_id,
            "job_id": self.raw.external_id,
            "title": self.raw.title,
            "url": self.raw.url,
            "company": self.raw.extra.get("organization"),
            "location": self.raw.extra.get("location"),
            "description": self.raw.summary or self.raw.extra.get("description"),
            "salary": self.raw.extra.get("compensation"),
            "kind": self.raw.extra.get("kind", "job"),
            "published_at": self.raw.published_at,
            "deadline_at": deadline_at,
        }
        if name in values:
            return values[name]
        if name == "work_mode":
            return type("Mode", (), {"value": self.raw.extra.get("remote") or "unknown"})()
        raise AttributeError(name)

    def to_row(self) -> dict[str, Any]:
        return {
            "title": self.raw.title,
            "url": self.raw.url,
            "published_at": self.raw.published_at.isoformat() if self.raw.published_at else None,
            **self.raw.extra,
        }


async def _fetch_with_retries(source, limit: float) -> FetchOutcome:
    """Sert sure butcesi icinde getir; gecici hatalarda sinirli tekrar dene.

    Butce asildiginda `TimeoutError` yukselir -- kaynak iptal edilir, kardes
    kaynaklar etkilenmez. Tekrar denemeler ayni butceden yer; boylece toplam
    sure `timeout_seconds`i asla asmaz.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + limit
    attempt = 0
    while True:
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise TimeoutError(f"{source.id} exceeded {limit:.0f}s budget")
        try:
            return normalize_fetch(await asyncio.wait_for(source.fetch(), timeout=remaining))
        except Exception as exc:
            kind = runs.classify_error(exc)
            if attempt >= MAX_SOURCE_RETRIES or not runs.is_retryable(kind):
                raise
            delay = min(RETRY_BACKOFF_BASE * (2**attempt), RETRY_BACKOFF_CAP)
            delay = min(delay, max(remaining / 2, 0.05))
            attempt += 1
            log.info("source %s transient %s; retry %d in %.1fs", source.id, kind, attempt, delay)
            await asyncio.sleep(delay)


async def _scope_shrank(session, source_id: str, *, run_id: int, seen: int) -> int | None:
    """Onceki TAM kosuya gore kaynak daralmis mi? Daralan taban sayisini dondur.

    `partial` isareti koymayan ama sayfalamasi sessizce bozulan kaynaklari
    yakalayan guvenlik agi: 100 kayit goren bir feed bir gun 12 kayit gorurse
    bu bir kapsam degisikligidir, "12 ilan kapandi" degil.
    """
    baseline = await runs.previous_seen_count(session, source_id, exclude_run_id=run_id)
    if not baseline or baseline < SWEEP_SCOPE_MIN_BASELINE:
        return None
    if seen >= baseline * SWEEP_SCOPE_MIN_RATIO:
        return None
    return baseline


async def _sweep_missing(source, payloads: list) -> None:
    """Kosu `ok` ve en az bir item urettiyse gorunmeyenleri kademeli kapat.

    Bos/hata kosusunda ASLA cagrilmaz: basarisiz kaynak ilan kapatamaz.
    """
    from app.modules.opportunity.models import OpportunitySourceObservation

    external_ids = {str(item.external_id) for item in payloads if getattr(item, "external_id", None)}
    urls = {item.url for item in payloads if getattr(item, "url", None)}
    conditions = []
    if external_ids:
        conditions.append(OpportunitySourceObservation.external_id.in_(external_ids))
    if urls:
        conditions.append(OpportunitySourceObservation.canonical_url.in_(urls))
    if not conditions:
        return
    async with SessionLocal() as session:
        seen = list(
            (
                await session.execute(
                    select(OpportunitySourceObservation.opportunity_id).where(
                        OpportunitySourceObservation.source == source.id, or_(*conditions)
                    )
                )
            ).scalars()
        )
        grace = CLOSE_GRACE_DAYS[source_class(source).value]
        await service.sweep_missing_opportunities(
            session,
            source_label=source.id,
            seen_opportunity_ids=list(set(seen)),
            grace_days=grace,
        )


async def _fail_reserved_run(
    run_id: int, *, batch_id, error: str, error_kind: str, status: str = runs.ERROR
) -> None:
    async with SessionLocal() as session:
        run = await session.get(SourceRun, run_id)
        if run is not None:
            await runs.finish_run(session, run, status=status, error=error, error_kind=error_kind)
        if batch_id is not None:
            await sync_service.finish_batch_source(session, batch_id, status=status)
        await session.commit()


async def poll_source(source, *, batch_id=None, timeout: float | None = None) -> int:
    """Tek kaynagi kos; sert timeout, sinirli tekrar ve devre kesici ile.

    Kaynak basina kilitle ayni kaynak iki kez kosmaz; rezervasyon yarisinda
    kaybeden kosum `abandoned` yazip sessizce cekilir.
    """
    limit = float(timeout) if timeout is not None else source_timeout_seconds(source)
    async with _lock_for(source.id):
        return await _poll_source_locked(source, batch_id=batch_id, limit=limit)


async def _poll_source_locked(source, *, batch_id, limit: float) -> int:
    source_id = source.id
    async with SessionLocal() as session:
        state = await runs.circuit_state(session, source_id)
        run = await runs.start_run(session, source_id, batch_id=batch_id)
        run_id = run.id
        if state["open"]:
            log.info("source %s circuit open; skipping", source_id)
            await runs.finish_run(
                session,
                run,
                status=runs.ERROR,
                error=(
                    f"circuit open after {state['consecutive_failures']} consecutive failures"
                ),
                error_kind="circuit_open",
            )
            if batch_id is not None:
                await sync_service.finish_batch_source(session, batch_id, status=runs.ERROR)
            await session.commit()
            return 0
        duplicate = await runs.has_live_claim(
            session, source_id, exclude_run_id=run_id, lease=timedelta(seconds=limit)
        )
        if duplicate:
            log.info("source %s already running elsewhere; skipping duplicate", source_id)
            await runs.finish_run(
                session, run, status=runs.ABANDONED, error="duplicate concurrent claim"
            )
            await session.commit()
            return 0
        await session.commit()

    try:
        result = await _fetch_with_retries(source, limit)
    except Exception as exc:
        message = _error_message(exc)
        kind = runs.classify_error(exc)
        log.warning("source %s failed (%s): %s", source_id, kind, message)
        await _fail_reserved_run(run_id, batch_id=batch_id, error=message, error_kind=kind)
        await _run_health_check(source, status=runs.ERROR, error_kind=kind)
        return 0

    payloads = [NativeJob(raw) for raw in result.items]
    detail = result.detail
    partial = result.partial
    added = 0
    try:
        async with SessionLocal() as session:
            run = await session.get(SourceRun, run_id)
            if run is None:
                return 0
            if payloads and not partial:
                baseline = await _scope_shrank(
                    session, source_id, run_id=run_id, seen=len(payloads)
                )
                if baseline is not None:
                    partial = True
                    detail = (
                        f"kapsam daralmasi: {len(payloads)} kayit goruldu, "
                        f"onceki tam kosu {baseline} kayit gordu"
                    )
            status = _outcome_status(partial=partial, seen=len(payloads))
            if payloads:
                added = await service.ingest_jobs(session, payloads, source_id)
            await runs.finish_run(
                session,
                run,
                status=status,
                items_found=added,
                items_seen=len(payloads),
                error=detail or None,
                error_kind="partial" if partial and detail else None,
            )
            if batch_id is not None:
                await sync_service.finish_batch_source(
                    session, batch_id, status=status, items_found=added
                )
            await session.commit()
    except Exception as exc:
        message = _error_message(exc)
        kind = runs.classify_error(exc)
        log.warning("source %s ingest failed (%s): %s", source_id, kind, message)
        await _fail_reserved_run(run_id, batch_id=batch_id, error=message, error_kind=kind)
        await _run_health_check(source, status=runs.ERROR, error_kind=kind)
        return 0

    # Kapanma taramasi YALNIZ guvenilir tam kosumda: `partial`/`empty` kosusunda
    # "gorunmeyen" kayit aslinda taranmamis olabilir.
    if payloads and not partial:
        await _sweep_missing(source, payloads)
    await _run_health_check(source, status=_outcome_status(partial=partial, seen=len(payloads)))
    return added


def _outcome_status(*, partial: bool, seen: int) -> str:
    """Adapter sonucunu `source_run.status` degerine cevirir.

    Semantik: complete=`ok`, kismi tarama=`partial`, teknik olarak tamamlanmis
    ama bos=`empty`, guvenilir sonuc yok=`error` (worker'in hata dalinda).
    """
    if partial:
        return runs.PARTIAL
    return runs.OK if seen else runs.EMPTY


async def _run_health_check(source, *, status: str, error_kind: str | None = None) -> None:
    """Kosum sonucuna gore (empty/error serisi) saglik alarmini uretir."""
    async with SessionLocal() as session:
        await runs.check_source_health(
            session,
            source.id,
            status=status,
            label=getattr(source, "label", "") or source.id,
            error_kind=error_kind,
        )
        await session.commit()


async def poll_opportunities(*, limit: int = 4) -> int:
    """Her adapter'ın kendi aralığına göre yalnızca süresi gelenleri çek."""
    sources = [*forkjob_sources(), *SOURCES]
    async with SessionLocal() as session:
        latest = dict(
            (
                await session.execute(
                    select(SourceRun.source, func.max(SourceRun.started_at))
                    .where(SourceRun.source.in_([source.id for source in sources]))
                    .group_by(SourceRun.source)
                )
            ).all()
        )
    due = select_due_sources(sources, latest)[:limit]
    return sum(await asyncio.gather(*(poll_source(source) for source in due)))


def select_due_sources(sources, latest: dict[str, datetime], *, now: datetime | None = None):
    current = now or datetime.now(UTC)

    def due_at(source):
        last_run = latest.get(source.id)
        if last_run is None:
            return datetime.min.replace(tzinfo=UTC)
        return last_run + timedelta(minutes=source.interval_minutes)

    return sorted(
        (source for source in sources if due_at(source) <= current),
        key=due_at,
    )


async def poll_named_source(source_id: str, *, batch_id=None) -> int:
    source = next(
        (
            item
            for item in [*forkjob_sources(include_opt_in=True), *SOURCES]
            if item.id == source_id
        ),
        None,
    )
    if source is None:
        # Bilinmeyen kaynak batch'i sonsuza kadar `running` birakmamali: terminal
        # bir hata kosumu yazip cekiliriz.
        if batch_id is None:
            raise KeyError(source_id)
        async with SessionLocal() as session:
            run = await runs.start_run(session, source_id, batch_id=batch_id)
            await runs.finish_run(
                session,
                run,
                status=runs.ERROR,
                error=f"unknown source: {source_id}",
                error_kind="unknown",
            )
            await sync_service.finish_batch_source(session, batch_id, status=runs.ERROR)
            await session.commit()
        return 0
    return await poll_source(source, batch_id=batch_id)
