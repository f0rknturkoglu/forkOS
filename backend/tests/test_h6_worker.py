"""H6 worker entegrasyonu: tek iş, açılış telafisi, eski üreticilerin yokluğu."""

from __future__ import annotations

import pathlib

import pytest

from app.worker import jobs, main


def _scheduler_source() -> str:
    return pathlib.Path("app/worker/main.py").read_text(encoding="utf-8")


def test_single_h6_scheduler_job() -> None:
    """§170: ritüeller/son tarihler AYRI işler değildir; tek tur vardır."""
    source = _scheduler_source()
    assert 'id="proactivity_tick"' in source
    assert "minutes=1" in source
    # Tek tur: dakikada bir "bakılacak bir şey var mı?" kontrolü.
    assert source.count("proactivity_tick") >= 1
    assert "max_instances=1" in source
    assert "coalesce=True" in source


def test_legacy_proactive_producers_are_retired() -> None:
    """§149: aynı mantıksal durum için İKİ üretici kalmaz."""
    source = _scheduler_source()
    assert "morning_digest" not in source
    assert "deadline_ladder" not in source
    assert not pathlib.Path("app/worker/digest.py").exists()
    # Eski merdiven ve rung yardımcıları da kaldırıldı.
    opportunity = pathlib.Path("app/modules/opportunity/service.py").read_text(encoding="utf-8")
    assert "def deadline_ladder" not in opportunity
    assert "def deadline_rung" not in opportunity
    assert "DEADLINE_LADDER_DAYS" not in opportunity


def test_startup_uses_the_same_service_after_source_refresh() -> None:
    """§89/§172: açılış telafisi AYNI servisi çağırır ve kaynaklardan SONRA gelir."""
    source = _scheduler_source()
    assert '("proactivity_catch_up", proactivity_catch_up)' in source
    order = source.index('("critical_catch_up", critical_catch_up)')
    assert order < source.index('("proactivity_catch_up", proactivity_catch_up)')
    assert '("catch_up_feeds", catch_up)' in source
    assert source.index('("catch_up_feeds", catch_up)') < source.index(
        '("proactivity_catch_up", proactivity_catch_up)'
    )


async def test_tick_job_swallows_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    """§171: tur hatası worker döngüsünü düşürmez."""
    from app.modules.proactivity import service as proactivity_service

    async def boom(*args: object, **kwargs: object) -> object:
        raise RuntimeError("tur çöktü")

    monkeypatch.setattr(proactivity_service, "tick", boom)
    assert await jobs.proactivity_tick() == 0


async def test_catch_up_job_uses_catch_up_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """Açılış telafisi ayrı bir implementasyon DEĞİL; aynı servis + bayrak."""
    from app.modules.proactivity import service as proactivity_service

    seen: dict[str, object] = {}

    class _Result:
        delivered = 2

    async def fake_tick(session: object, *, catch_up: bool = False) -> object:
        seen["catch_up"] = catch_up
        return _Result()

    monkeypatch.setattr(proactivity_service, "tick", fake_tick)
    assert await jobs.proactivity_catch_up() == 2
    assert seen["catch_up"] is True


def test_no_second_startup_loop_was_added() -> None:
    """§89: mevcut açılış sırası kullanılır; ikinci bir döngü eklenmez."""
    source = _scheduler_source()
    assert source.count("def _startup_tasks(") == 1
    assert source.count("await run_startup(scheduler)") == 1
    assert source.count("asyncio.Event().wait()") == 1


def test_worker_module_has_no_h6_network_calls() -> None:
    """§157: H6 yeni bir dış ağ çağrısı getirmez."""
    for path in ("app/modules/proactivity/service.py", "app/modules/proactivity/rules.py"):
        source = pathlib.Path(path).read_text(encoding="utf-8")
        for forbidden in ("httpx", "requests.get", "aiohttp", "socket."):
            assert forbidden not in source


def test_worker_main_imports_are_used() -> None:
    """Ölü import bırakılmaz: emekli işlerin kalıntısı yok."""
    source = _scheduler_source()
    for name in ("deadline_ladder", "morning_digest", "digest"):
        assert f"import {name}" not in source
        assert "from app.worker.digest" not in source


def test_main_module_exposes_the_worker_entrypoint() -> None:
    assert hasattr(main, "main")
    assert hasattr(main, "RSS_POLL_TICK_MINUTES")


# ---------------------------------------------------------------------------
# H6.1/D — startup sırası: bayat durumdan proaktif üretim YOK
# ---------------------------------------------------------------------------


async def test_scheduled_tick_waits_for_source_refresh_and_catch_up() -> None:
    """D1: kaynak tazeleme + H6 telafisi bitmeden dakikalık tur ÇALIŞMAZ."""
    events: list[str] = []

    class FakeScheduler:
        def add_job(self, func: object, *args: object, **kwargs: object) -> None:
            events.append(f"register:{kwargs.get('id')}")

    async def source_refresh() -> None:
        events.append("source_refresh")

    async def feeds() -> None:
        events.append("feeds")

    async def proactivity_catch_up() -> None:
        events.append("proactivity_catch_up")

    await main.run_startup(
        FakeScheduler(),  # type: ignore[arg-type]
        tasks=[
            ("source_refresh", source_refresh),
            ("catch_up_feeds", feeds),
            ("proactivity_catch_up", proactivity_catch_up),
        ],
    )

    assert events == [
        "source_refresh",
        "feeds",
        "proactivity_catch_up",
        "register:proactivity_tick",
    ]
    # Tur KAYDI zincirin SONUNDA: kaynak tazeleme sırasında tur yok.
    assert events.index("register:proactivity_tick") > events.index("source_refresh")
    assert events.index("proactivity_catch_up") > events.index("source_refresh")


async def test_startup_chain_continues_after_a_failing_task() -> None:
    """Bir açılış görevi çökse de zincir devam eder ve tur yine kaydedilir."""
    events: list[str] = []

    class FakeScheduler:
        def add_job(self, func: object, *args: object, **kwargs: object) -> None:
            events.append("registered")

    async def boom() -> None:
        raise RuntimeError("kaynak çöktü")

    async def ok() -> None:
        events.append("ok")

    await main.run_startup(
        FakeScheduler(),  # type: ignore[arg-type]
        tasks=[("boom", boom), ("ok", ok)],
    )

    assert events == ["ok", "registered"]


def test_production_chain_orders_catch_up_after_refresh() -> None:
    """Üretim zinciri: H6 telafisi kaynak tazelemeden SONRA gelir."""
    names = [name for name, _ in main._startup_tasks()]
    assert "proactivity_catch_up" in names
    assert names.index("critical_catch_up") < names.index("proactivity_catch_up")
    assert names.index("catch_up_feeds") < names.index("proactivity_catch_up")
    # Eski mükerrer üreticiler zincirde YOK.
    assert "morning_digest" not in names
    assert "deadlines" not in names
