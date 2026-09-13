from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import select, text

from app.core import runs as run_svc
from app.core.models import Event, Notification, SourceRun
from app.core.source_sync import reconcile_stale_runs
from app.db import engine
from app.modules.opportunity.models import Opportunity
from app.modules.opportunity.service import ingest_jobs
from app.sources.base import FetchOutcome, RawItem
from app.sources.forkjob_core.models import WorkMode


@dataclass
class _MockJob:
    title: str
    url: str
    company: str
    location: str
    description: str
    external_id: str | None = None
    work_mode: WorkMode = WorkMode.REMOTE
    salary: str | None = None
    kind: str = "job"

    def to_row(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "company": self.company,
            "location": self.location,
            "description": self.description,
            "external_id": self.external_id,
            "forkjob": {
                "country": "ES",
                "region": "EU",
                "score": 60,
            },
        }


async def test_check_stalled_notifies_and_deduplicates_streak():
    source = f"test-stalled-{uuid.uuid4().hex[:8]}"
    label = f"Label-{source}"

    async with engine.begin() as conn:
        # 1. Henüz 2 boş koşu varken stalled tetiklenmemeli
        await conn.execute(
            text(
                "insert into source_run (source, status, started_at, finished_at) "
                "values (:s, 'empty', now() - interval '20 minutes', now()), "
                "       (:s, 'empty', now() - interval '10 minutes', now())"
            ),
            {"s": source},
        )

    from app.db import SessionLocal

    async with SessionLocal() as session:
        alerted = await run_svc.check_stalled(session, source, label=label)
        await session.commit()
        assert alerted is False

    # 2. 3. boş koşu geldiğinde tam olarak tetiklenmeli ve notification tablosuna yazmalı
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "insert into source_run (source, status, started_at, finished_at) "
                "values (:s, 'empty', now(), now())"
            ),
            {"s": source},
        )

    async with SessionLocal() as session:
        alerted = await run_svc.check_stalled(session, source, label=label)
        await session.commit()
        assert alerted is True

        # Notification tablosu kontrolü (Kural 6)
        notifications = list(
            (
                await session.execute(
                    select(Notification).where(Notification.kind == "source_stalled")
                )
            ).scalars().all()
        )
        assert any(label in n.title or label in n.body for n in notifications)

        # Event tablosu kontrolü
        events = list(
            (
                await session.execute(
                    select(Event).where(
                        Event.verb == "source.stalled",
                        Event.payload["source"].astext == source,
                    )
                )
            ).scalars().all()
        )
        assert len(events) == 1

    # 3. 4. boş koşu (aynı streak devam ediyor) tekrar bildirim ve event atmamalı
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "insert into source_run (source, status, started_at, finished_at) "
                "values (:s, 'empty', now(), now())"
            ),
            {"s": source},
        )

    async with SessionLocal() as session:
        alerted = await run_svc.check_stalled(session, source, label=label)
        await session.commit()
        assert alerted is False

        # Event sayısı hala 1 olmalı
        events = list(
            (
                await session.execute(
                    select(Event).where(
                        Event.verb == "source.stalled",
                        Event.payload["source"].astext == source,
                    )
                )
            ).scalars().all()
        )
        assert len(events) == 1


async def test_reconcile_stale_runs_dynamic_timeout():
    now = datetime.now(UTC)
    std_source = f"test:std:{uuid.uuid4().hex[:6]}"
    eures_source = "jobhunter:eures"

    async with engine.begin() as conn:
        # Standart kaynak: 25 dakika önce başladı (15dk eşiğini aştı -> abandoned olmalı)
        await conn.execute(
            text(
                "insert into source_run (source, status, started_at) "
                "values (:s, 'running', :t)"
            ),
            {"s": std_source, "t": now - timedelta(minutes=25)},
        )
        # EURES: 25 dakika önce başladı (15dk eşiğini aştı ama 60dk eşiğinde -> running kalmalı)
        await conn.execute(
            text(
                "insert into source_run (source, status, started_at) "
                "values (:s, 'running', :t)"
            ),
            {"s": eures_source, "t": now - timedelta(minutes=25)},
        )

    from app.db import SessionLocal

    async with SessionLocal() as session:
        # Standart 15dk eşiği ile uzlaşma
        cutoff = now - timedelta(minutes=15)
        reconciled = await reconcile_stale_runs(session, older_than=cutoff)
        await session.commit()
        assert reconciled >= 1

        # Standart kaynak terk edildi
        std_row = (
            await session.execute(
                select(SourceRun).where(SourceRun.source == std_source)
            )
        ).scalar_one()
        assert std_row.status == "abandoned"

        # EURES hala koşuyor olmalı!
        eures_row = (
            await session.execute(
                select(SourceRun)
                .where(SourceRun.source == eures_source)
                .order_by(SourceRun.id.desc())
            )
        ).scalars().first()
        assert eures_row.status == "running"


async def test_ingest_jobs_deduplicates_same_source_url():
    test_url = f"https://example.com/jobs/{uuid.uuid4().hex}"
    source = "test-board"

    job1 = _MockJob(
        title="Backend Dev",
        url=test_url,
        company="Acme Corp",
        location="Remote",
        description="Python async developer",
        external_id="ext-original-1",
    )

    from app.db import SessionLocal

    async with SessionLocal() as session:
        added = await ingest_jobs(session, [job1], source_label=source)
        await session.commit()
        assert added == 1

        opps = (
            await session.execute(
                select(Opportunity).where(Opportunity.url == test_url)
            )
        ).scalars().all()
        assert len(opps) == 1
        assert opps[0].organization == "Acme Corp"

    # İkinci geliş: Aynı URL, aynı kaynak, farklı veya None external_id
    job2 = _MockJob(
        title="Backend Dev (Senior)",
        url=test_url,
        company="Acme Corp",
        location="Madrid",
        description="Updated python async developer",
        external_id=None,
    )

    async with SessionLocal() as session:
        added = await ingest_jobs(session, [job2], source_label=source)
        await session.commit()
        # İkinci geliş yeni kayıt açmamalı (added == 0)
        assert added == 0

        # Veritabanında hala tek kayıt olmalı
        opps = (
            await session.execute(
                select(Opportunity).where(Opportunity.url == test_url)
            )
        ).scalars().all()
        assert len(opps) == 1
        assert opps[0].country == "ES"


# ---------------------------------------------------------------------------
# Hata siniflandirma / devre kesici / timeout / kapanma tespiti
# ---------------------------------------------------------------------------


@dataclass
class _FakeSource:
    id: str
    interval_minutes: int = 60
    timeout_seconds: float = 5.0
    result: list | None = None
    exc: Exception | None = None
    sleep: float = 0.0
    #: Doluysa `result` yerine bu sonuc doner (partial/complete ayrimi icin).
    outcome: FetchOutcome | None = None

    async def fetch(self) -> list | FetchOutcome:
        if self.sleep:
            await asyncio.sleep(self.sleep)
        if self.exc is not None:
            raise self.exc
        if self.outcome is not None:
            return self.outcome
        return list(self.result or [])


def _raw_item(tag: str) -> RawItem:
    return RawItem(
        external_id=f"ext-{tag}",
        title="Backend Dev",
        url=f"https://example.com/jobs/{tag}",
        summary="python async developer",
        extra={"organization": "Acme", "location": "Remote", "remote": "remote", "kind": "job"},
    )


@pytest.mark.no_database
def test_classify_error_kinds():
    import socket
    import ssl

    assert run_svc.classify_error(TimeoutError("boom")) == "timeout"
    assert run_svc.classify_error(socket.gaierror("Name or service not known")) == "dns"
    assert run_svc.classify_error(ssl.SSLError("certificate verify failed")) == "tls"
    assert run_svc.classify_error(RuntimeError("HTTP 403 (blocked) for https://x")) == "http_403"
    assert run_svc.classify_error(RuntimeError("HTTP 404 for https://x")) == "http_404"
    assert run_svc.classify_error(RuntimeError("HTTP 429 for https://x")) == "http_429"
    assert run_svc.classify_error(RuntimeError("HTTP 503 for https://x")) == "http_5xx"
    assert run_svc.classify_error(json.JSONDecodeError("x", "y", 0)) == "parser"
    assert run_svc.classify_error(RuntimeError("weird failure")) == "unknown"


@pytest.mark.no_database
def test_sanitize_error_never_leaks_credentials_or_tokens():
    dirty = (
        "ProxyError: http://fork:s3cret@proxy.local:8080/ failed "
        "&token=abc123XYZ Bearer sk-live-999"
    )

    clean = run_svc.sanitize_error(dirty)

    assert "s3cret" not in clean
    assert "abc123XYZ" not in clean
    assert "sk-live-999" not in clean
    assert "fork:***@proxy.local:8080" in clean


async def test_finish_run_sanitizes_secret_and_records_kind():
    from app.db import SessionLocal

    async with SessionLocal() as session:
        run = await run_svc.start_run(session, "osym")
        await run_svc.finish_run(
            session,
            run,
            status=run_svc.ERROR,
            error="ProxyError: http://user:s3cret@proxy:8080/?api_key=abc123XYZ",
        )
        await session.commit()

        assert run.error is not None
        assert "s3cret" not in run.error
        assert "abc123XYZ" not in run.error
        assert run_svc.error_kind_of(run) in run_svc.ERROR_KINDS


async def test_per_source_timeout_does_not_block_siblings(monkeypatch: pytest.MonkeyPatch):
    from app.db import SessionLocal
    from app.modules.opportunity import worker

    monkeypatch.setattr(worker, "MAX_SOURCE_RETRIES", 0)
    slow = _FakeSource("osym", timeout_seconds=0.2, sleep=5.0, result=[_raw_item("slow")])
    fast = _FakeSource("ylsy", result=[_raw_item("fast")])

    started = time.monotonic()
    results = await asyncio.gather(worker.poll_source(slow), worker.poll_source(fast))
    elapsed = time.monotonic() - started

    assert results == [0, 1]
    assert elapsed < 3
    async with SessionLocal() as session:
        rows = {row.source: row for row in (await session.execute(select(SourceRun))).scalars()}
    assert rows["osym"].status == "error"
    assert run_svc.error_kind_of(rows["osym"]) == "timeout"
    assert rows["ylsy"].status == "ok"


async def test_circuit_breaker_skips_source_after_consecutive_failures():
    from app.db import SessionLocal
    from app.modules.opportunity import worker

    now = datetime.now(UTC)
    async with engine.begin() as conn:
        for step in range(run_svc.CIRCUIT_FAILURE_THRESHOLD):
            await conn.execute(
                text(
                    "insert into source_run (source, status, started_at, finished_at) "
                    "values ('osym', 'error', :t, :t)"
                ),
                {"t": now - timedelta(minutes=step + 1)},
            )

    async with SessionLocal() as session:
        state = await run_svc.circuit_state(session, "osym")
    assert state["open"] is True
    assert state["consecutive_failures"] == run_svc.CIRCUIT_FAILURE_THRESHOLD
    assert state["retry_at"] is not None

    called = {"fetch": False}
    source = _FakeSource("osym")

    async def boom() -> list:
        called["fetch"] = True
        raise AssertionError("devre acikken aga cikilmamali")

    source.fetch = boom  # type: ignore[method-assign]
    assert await worker.poll_source(source) == 0
    assert called["fetch"] is False

    async with SessionLocal() as session:
        run = (
            await session.execute(
                select(SourceRun).where(SourceRun.source == "osym").order_by(SourceRun.id.desc())
            )
        ).scalars().first()
    assert run is not None
    assert run.status == "error"
    assert run_svc.error_kind_of(run) == "circuit_open"


async def test_empty_and_error_are_distinct_and_only_ok_sweeps(
    monkeypatch: pytest.MonkeyPatch,
):
    from app.db import SessionLocal
    from app.modules.opportunity import service, worker

    monkeypatch.setattr(worker, "MAX_SOURCE_RETRIES", 0)
    calls: list[dict] = []

    async def fake_sweep(session, **kwargs):
        calls.append(kwargs)
        return {"missing": 0, "likely_closed": 0, "closed": 0}

    monkeypatch.setattr(service, "sweep_missing_opportunities", fake_sweep)

    ok = _FakeSource("ylsy", result=[_raw_item("ok")])
    empty = _FakeSource("osym", result=[])
    failing = _FakeSource("yok-msc", exc=RuntimeError("HTTP 500 for https://x"))
    await asyncio.gather(
        worker.poll_source(ok), worker.poll_source(empty), worker.poll_source(failing)
    )

    async with SessionLocal() as session:
        rows = {
            row.source: row
            for row in (await session.execute(select(SourceRun).order_by(SourceRun.id))).scalars()
        }
    assert rows["ylsy"].status == "ok" and rows["ylsy"].items_found == 1
    assert rows["osym"].status == "empty"
    assert rows["yok-msc"].status == "error"
    assert run_svc.error_kind_of(rows["yok-msc"]) == "http_5xx"
    # Hata ve bos kosumlar kapanma taramasini TETIKLEMEZ.
    assert len(calls) == 1
    assert calls[0]["source_label"] == "ylsy"
    assert calls[0]["grace_days"] == 1  # ylsy = critical


async def test_sweep_grace_transitions_and_reopen():
    from app.db import SessionLocal
    from app.modules.opportunity import service
    from app.modules.opportunity.models import OpportunitySourceObservation

    source = f"test-close-{uuid.uuid4().hex[:8]}"
    url = f"https://example.com/close/{uuid.uuid4().hex}"
    job = _MockJob(
        title="Closing Job",
        url=url,
        company="Acme",
        location="Remote",
        description="python",
        external_id="close-1",
    )

    async with SessionLocal() as session:
        await ingest_jobs(session, [job], source_label=source)
        await session.commit()
        opp_id = (
            await session.execute(select(Opportunity.id).where(Opportunity.url == url))
        ).scalar_one()

    async with SessionLocal() as session:
        result = await service.sweep_missing_opportunities(
            session, source_label=source, seen_opportunity_ids=[opp_id], grace_days=1
        )
        assert result == {"missing": 0, "likely_closed": 0, "closed": 0}

    async with SessionLocal() as session:
        result = await service.sweep_missing_opportunities(
            session, source_label=source, seen_opportunity_ids=[], grace_days=1
        )
        assert result["missing"] == 1
        opp = (
            await session.execute(select(Opportunity).where(Opportunity.id == opp_id))
        ).scalar_one()
        assert opp.source_status == "missing"

    async with SessionLocal() as session:
        result = await service.sweep_missing_opportunities(
            session,
            source_label=source,
            seen_opportunity_ids=[],
            grace_days=1,
            now=datetime.now(UTC) + timedelta(days=1, minutes=1),
        )
        assert result["likely_closed"] == 1

    async with SessionLocal() as session:
        result = await service.sweep_missing_opportunities(
            session,
            source_label=source,
            seen_opportunity_ids=[],
            grace_days=1,
            now=datetime.now(UTC) + timedelta(days=2, minutes=2),
        )
        assert result["closed"] == 1
        opp = (
            await session.execute(select(Opportunity).where(Opportunity.id == opp_id))
        ).scalar_one()
        assert opp.status == "closed"

    # Kaynakta tekrar gorununce yeniden acilir.
    async with SessionLocal() as session:
        await ingest_jobs(session, [job], source_label=source)
        await session.commit()
        observation = (
            await session.execute(
                select(OpportunitySourceObservation).where(
                    OpportunitySourceObservation.source == source
                )
            )
        ).scalar_one()
        assert observation.source_status == "active"


# ---------------------------------------------------------------------------
# Faz 1: complete / partial / empty / error semantigi
# ---------------------------------------------------------------------------


async def test_partial_run_keeps_items_and_never_sweeps(monkeypatch: pytest.MonkeyPatch):
    """Yardimci parca bozuldugunda ana sonuclar korunur ve kapanma taramasi YAPILMAZ."""
    from app.db import SessionLocal
    from app.modules.opportunity import service, worker

    monkeypatch.setattr(worker, "MAX_SOURCE_RETRIES", 0)
    calls: list[dict] = []

    async def fake_sweep(session, **kwargs):
        calls.append(kwargs)
        return {"missing": 0, "likely_closed": 0, "closed": 0}

    monkeypatch.setattr(service, "sweep_missing_opportunities", fake_sweep)

    source = _FakeSource(
        "ylsy",
        outcome=FetchOutcome(
            items=[_raw_item("partial")],
            partial=True,
            detail="rss: RuntimeError",
        ),
    )
    added = await worker.poll_source(source)

    assert added == 1
    async with SessionLocal() as session:
        run = (
            await session.execute(select(SourceRun).where(SourceRun.source == "ylsy"))
        ).scalars().one()
    assert run.status == "partial"
    assert run.items_seen == 1 and run.items_found == 1
    assert run.error_kind == "partial"
    assert calls == [], "partial kosum kapanma taramasi tetiklememeli"


async def test_scope_shrink_is_partial_and_does_not_close_listings(
    monkeypatch: pytest.MonkeyPatch,
):
    """Sayfalamasi sessizce bozulan kaynak 'kalan ilanlar kapandi' diyemez."""
    from app.db import SessionLocal
    from app.modules.opportunity import service, worker

    monkeypatch.setattr(worker, "MAX_SOURCE_RETRIES", 0)
    calls: list[dict] = []

    async def fake_sweep(session, **kwargs):
        calls.append(kwargs)
        return {"missing": 0, "likely_closed": 0, "closed": 0}

    monkeypatch.setattr(service, "sweep_missing_opportunities", fake_sweep)

    # Onceki TAM kosu 100 kayit gormustu.
    async with SessionLocal() as session:
        await run_svc.finish_run(
            session,
            await run_svc.start_run(session, "ylsy"),
            status="ok",
            items_found=100,
            items_seen=100,
        )
        await session.commit()

    source = _FakeSource("ylsy", result=[_raw_item(f"shrink-{index}") for index in range(12)])
    await worker.poll_source(source)

    async with SessionLocal() as session:
        run = (
            await session.execute(
                select(SourceRun).where(SourceRun.source == "ylsy").order_by(SourceRun.id.desc())
            )
        ).scalars().first()
    assert run.status == "partial"
    assert "kapsam daralmasi" in (run.error or "")
    assert calls == [], "daralan kapsamda kapanma taramasi yapilmamali"


async def test_small_source_shrink_is_not_flagged(monkeypatch: pytest.MonkeyPatch):
    """Kucuk kaynaklarda dalgalanma yanlis 'partial' uretmemeli."""
    from app.db import SessionLocal
    from app.modules.opportunity import service, worker

    monkeypatch.setattr(worker, "MAX_SOURCE_RETRIES", 0)

    async def fake_sweep(session, **kwargs):
        return {"missing": 0, "likely_closed": 0, "closed": 0}

    monkeypatch.setattr(service, "sweep_missing_opportunities", fake_sweep)

    async with SessionLocal() as session:
        await run_svc.finish_run(
            session,
            await run_svc.start_run(session, "ylsy"),
            status="ok",
            items_found=8,
            items_seen=8,
        )
        await session.commit()

    await worker.poll_source(_FakeSource("ylsy", result=[_raw_item("few")]))

    async with SessionLocal() as session:
        run = (
            await session.execute(
                select(SourceRun).where(SourceRun.source == "ylsy").order_by(SourceRun.id.desc())
            )
        ).scalars().first()
    assert run.status == "ok"


async def test_parser_and_network_failures_are_errors_not_empty(monkeypatch: pytest.MonkeyPatch):
    """Parser/ag hatasi 'bos' sayilamaz: iki durum farkli bildirimler uretir."""
    from app.db import SessionLocal
    from app.modules.opportunity import worker

    monkeypatch.setattr(worker, "MAX_SOURCE_RETRIES", 0)

    broken_parser = _FakeSource("yok-msc", exc=RuntimeError("HTML selector parse failed"))
    offline = _FakeSource("osym", exc=OSError("connection refused"))

    await asyncio.gather(
        worker.poll_source(broken_parser),
        worker.poll_source(offline),
    )

    async with SessionLocal() as session:
        rows = {row.source: row for row in (await session.execute(select(SourceRun))).scalars()}
    assert rows["yok-msc"].status == "error"
    assert run_svc.error_kind_of(rows["yok-msc"]) == "parser"
    assert rows["osym"].status == "error"
    assert rows["osym"].status != "empty"


async def test_error_streak_produces_a_notification():
    """Ust uste hata veren kaynak icin 'empty' degil 'failing' bildirimi uretilir."""
    from app.core.models import Notification
    from app.db import SessionLocal

    source = f"test-failing-{uuid.uuid4().hex[:8]}"
    async with SessionLocal() as session:
        alerts: list[bool] = []
        for _ in range(run_svc.ERROR_STREAK_ALERT + 1):
            await run_svc.finish_run(
                session,
                await run_svc.start_run(session, source),
                status=run_svc.ERROR,
                error="TimeoutError: slow",
                error_kind="timeout",
            )
            alerts.append(
                await run_svc.check_source_health(
                    session, source, status=run_svc.ERROR, error_kind="timeout"
                )
            )
        await session.commit()
        rows = list(
            (
                await session.execute(
                    select(Notification).where(Notification.kind == "source_failing")
                )
            ).scalars()
        )
    # Alarm seri tamamlandiginda BIR KEZ uretilir, sonraki hatalarda tekrarlamaz.
    assert alerts == [False, False, True, False]
    assert len(rows) == 1
    assert source in (rows[0].body or "")
    assert "timeout" in (rows[0].body or "")


async def test_error_streak_is_not_broken_by_partial_runs():
    """`partial` bir saglikli kosumdur: hata serisini sifirlar, alarm uretmez."""
    from app.db import SessionLocal

    source = f"test-partial-{uuid.uuid4().hex[:8]}"
    async with SessionLocal() as session:
        for _ in range(run_svc.ERROR_STREAK_ALERT):
            await run_svc.finish_run(
                session, await run_svc.start_run(session, source), status=run_svc.ERROR
            )
        await run_svc.finish_run(
            session, await run_svc.start_run(session, source), status=run_svc.PARTIAL
        )
        assert not await run_svc.check_source_health(
            session, source, status=run_svc.PARTIAL
        )


async def test_ylsy_keeps_main_results_when_helper_feed_breaks(monkeypatch: pytest.MonkeyPatch):
    """Ana YLSY listesi alindiysa yardimci RSS bozulunca sonuc kaybolmaz."""
    from app.sources import announcements
    from app.sources.announcements import YlsySource

    source = YlsySource("ylsy", "https://yyegm.meb.gov.tr/www/duyurular/kategori/2", (), "scholarship")
    ajax_payload = {
        "data": [
            {
                "BASLIK": "2026 YLSY Kurum Tercih Islemleri Basladi",
                "LINK": "/www/kurum-tercihi/icerik/1",
                "ISLEMSAAT": "01/09/2026",
                "SIRAID": 7,
            }
        ],
        "recordsFiltered": 1,
        "recordsTotal": 1,
    }

    class _Response:
        def __init__(self, url: str, *, json_payload=None, content: bytes = b"", text: str = ""):
            self.url = url
            self._json = json_payload
            self.content = content
            self.text = text

        def json(self):
            return self._json

    async def fake_request(client, method, url, **kwargs):
        if url == announcements._YLSY_AJAX_URL:
            return _Response(url, json_payload=ajax_payload)
        if url == announcements._YLSY_RSS_URL:
            raise RuntimeError("HTTP 503 for rss")
        return _Response(url, text="<html></html>")

    monkeypatch.setattr(announcements, "_request_with_retry", fake_request)

    outcome = await source.fetch()

    assert outcome.partial is True
    assert "rss" in outcome.detail
    titles = [item.title for item in outcome.items]
    assert titles == ["2026 YLSY Kurum Tercih Islemleri Basladi"]
