"""H6 PART-0 sertleştirmesi: eşzamanlı tur + sınırlı tarama != çözülme."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Notification
from app.db import SessionLocal
from app.modules.proactivity import rules, service
from app.modules.proactivity.models import ProactivityRun
from tests.h5_fixtures import make_todo

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# 0.1 — eşzamanlı değerlendirme: teslim edilmiş koşu GERİYE DÜŞEMEZ
# ---------------------------------------------------------------------------


async def test_concurrent_ticks_do_not_regress_a_delivered_run(
    db_session: AsyncSession,
) -> None:
    """İki bağımsız transaction aynı bekleyen koşuyu işlerse lifecycle bozulmaz.

    Gerçek iki oturum kullanılır; ikinci transaction birincinin commit'ini
    bekler ve yarış DB seviyesinde gerçekleşir.
    """
    await service.configure(db_session, enabled=True, quiet_hours_start="14:00", quiet_hours_end="16:00")
    # T-6 → rung 7; pencere açıldığında da rung DEĞİŞMEZ (tek mantıksal teslim).
    await make_todo(db_session, title="Yarış", due_at=NOW + timedelta(days=6))
    await db_session.commit()
    await service.tick(db_session, now=NOW)  # kuit → deferred
    runs = list((await db_session.execute(select(ProactivityRun))).scalars())
    assert len(runs) == 1, [(item.logical_trigger_key, item.state) for item in runs]
    run = runs[0]
    pending_key = run.logical_trigger_key
    assert run.state == "deferred"

    # Pencereyi kapat: bir sonraki tur teslim edecek.
    await service.configure(db_session, digest_time="00:05")
    await db_session.commit()
    moment = NOW + timedelta(hours=3)

    async def evaluate() -> None:
        async with SessionLocal() as session:
            await service.tick(session, now=moment)

    await asyncio.gather(evaluate(), evaluate())

    async with SessionLocal() as session:
        all_runs = list((await session.execute(select(ProactivityRun))).scalars())
        notifications = list((await session.execute(select(Notification))).scalars())
    # Bekleyen kosu takip edilir: zaman ilerledikce YENI basamak acilabilir,
    # ama BEKLEYEN kosunun lifecycle'i bozulmamali.
    refreshed = next(item for item in all_runs if item.logical_trigger_key == pending_key)

    assert len(notifications) == 1, "tek mantıksal teslim = tek bildirim"
    assert refreshed.state == "delivered", "teslim edilmiş koşu geriye düşemez"
    assert refreshed.delivery_count == 1
    assert refreshed.notification_id == notifications[0].id
    assert "DUPLICATE_TRIGGER" not in (refreshed.reason_codes or [])


async def test_sequential_repeat_tick_is_harmless(db_session: AsyncSession) -> None:
    """Tekrar turlar teslim edilmiş koşuyu değiştirmez (regresyon tabanı)."""
    await service.configure(db_session, enabled=True)
    await make_todo(db_session, title="Tekrar", due_at=NOW + timedelta(days=2, hours=1))
    await db_session.commit()

    await service.tick(db_session, now=NOW)
    await service.tick(db_session, now=NOW + timedelta(minutes=1))

    async with SessionLocal() as session:
        runs = list((await session.execute(select(ProactivityRun))).scalars())
        notifications = list((await session.execute(select(Notification))).scalars())
    assert len(runs) == 1
    assert runs[0].state == "delivered"
    assert runs[0].delivery_count == 1
    assert len(notifications) == 1


# ---------------------------------------------------------------------------
# 0.2 — bilinen koşul yeniden doğrulaması TAM kimlikle yapılır
# ---------------------------------------------------------------------------


async def test_known_condition_outside_scan_bound_is_not_resolved(
    db_session: AsyncSession,
) -> None:
    """Tarama sınırı yüzünden görünmeyen koşul ÇÖZÜLMÜŞ sayılamaz.

    `MAX_DEADLINE_ROWS` sınırı ADAY KEŞFİ içindir; bilinen bir koşulun
    yeniden doğrulamasını etkilememelidir.
    """
    target = await make_todo(db_session, title="Bilinen koşul", due_at=NOW + timedelta(days=2, hours=1))
    await service.seed_rules(db_session)
    await db_session.commit()
    rule = next(
        item
        for item in await service.list_rules(db_session)
        if item.kind == "deadline_staircase"
    )

    first = await rules.evaluate_rule(db_session, rule, now=NOW)  # type: ignore[arg-type]
    key = next(item.logical_trigger_key for item in first if item.subject_id == target.id)

    # Sınırdan fazla, DAHA YAKIN son tarih ekle: hedef artık ilk 200'de değil.
    for index in range(rules.MAX_DEADLINE_ROWS + 5):
        await make_todo(
            db_session,
            title=f"Yakın {index:03d}",
            due_at=NOW + timedelta(minutes=30 + index),
        )
    await db_session.commit()

    # Kosul GERCEKTEN var ama tarama sinirinin disinda: karar "belirsiz" olmali,
    # "yok" DEGIL.
    assert (
        await rules.revalidate(db_session, rule=rule, logical_trigger_key=key, now=NOW)
        == "indeterminate"
    )
    status, row = await rules.resolve_identity(
        db_session, rules.identity_of_key(key)  # type: ignore[arg-type]
    )
    assert status == "indeterminate"
    assert row is None


async def test_deleted_known_condition_is_resolved(db_session: AsyncSession) -> None:
    target = await make_todo(db_session, title="Silinecek", due_at=NOW + timedelta(days=2, hours=1))
    await service.seed_rules(db_session)
    await db_session.commit()
    rule = next(
        item
        for item in await service.list_rules(db_session)
        if item.kind == "deadline_staircase"
    )
    first = await rules.evaluate_rule(db_session, rule, now=NOW)  # type: ignore[arg-type]
    key = next(item.logical_trigger_key for item in first if item.subject_id == target.id)

    from app.modules.todo.models import Todo

    row = await db_session.get(Todo, target.id)
    assert row is not None
    row.status = "done"
    await db_session.commit()

    assert (
        await rules.revalidate(db_session, rule=rule, logical_trigger_key=key, now=NOW)
        == "not_found"
    )


async def test_changed_revision_is_stale(db_session: AsyncSession) -> None:
    from app.modules.todo.models import Todo

    target = await make_todo(db_session, title="Kayacak", due_at=NOW + timedelta(days=2, hours=1))
    await service.seed_rules(db_session)
    await db_session.commit()
    rule = next(
        item
        for item in await service.list_rules(db_session)
        if item.kind == "deadline_staircase"
    )
    first = await rules.evaluate_rule(db_session, rule, now=NOW)  # type: ignore[arg-type]
    key = next(item.logical_trigger_key for item in first if item.subject_id == target.id)

    row = await db_session.get(Todo, target.id)
    assert row is not None
    row.due_at = NOW + timedelta(days=9)
    await db_session.commit()

    assert (
        await rules.revalidate(db_session, rule=rule, logical_trigger_key=key, now=NOW)
        == "not_found"
    )


async def test_delivered_run_cannot_be_regressed_by_a_duplicate_attempt(
    db_session: AsyncSession,
) -> None:
    """Mükerrer teslim denemesi teslim edilmiş koşuyu GERİYE DÜŞÜREMEZ.

    Yarışın tam zamanlaması deterministik üretilemez; bu test yarışın
    ULAŞTIĞI dalı doğrudan çalıştırır: bildirim zaten varsa hiçbir lifecycle
    yazımı yapılmamalıdır.
    """
    await service.configure(db_session, enabled=True)
    await make_todo(db_session, title="Mükerrer", due_at=NOW + timedelta(days=2, hours=1))
    await db_session.commit()
    await service.tick(db_session, now=NOW)

    run = (await db_session.execute(select(ProactivityRun))).scalar_one()
    assert run.state == "delivered"
    before = (
        run.state,
        run.delivery_count,
        run.notification_id,
        list(run.reason_codes or []),
    )

    # Aynı koşuyu yeniden teslim etmeye çalış: bildirim dedup'ı tutar.
    rule = next(
        item
        for item in await service.list_rules(db_session)
        if item.kind == "deadline_staircase"
    )
    from app.modules.proactivity import policy

    decision = policy.InterventionDecision("surface", ["DEADLINE_3D"], "test")
    await service._deliver_now(
        db_session,
        run=run,
        rule=rule,
        candidate=service._candidate_for(rule, run),
        decision=decision,
        now=NOW + timedelta(minutes=1),
        result=service.TickResult(),
    )
    await db_session.commit()

    refreshed = (
        await db_session.execute(select(ProactivityRun).where(ProactivityRun.id == run.id))
    ).scalar_one()
    assert (
        refreshed.state,
        refreshed.delivery_count,
        refreshed.notification_id,
        list(refreshed.reason_codes or []),
    ) == before
    assert refreshed.state == "delivered"
    assert "DUPLICATE_TRIGGER" not in (refreshed.reason_codes or [])
