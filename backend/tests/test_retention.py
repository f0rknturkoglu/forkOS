"""Operasyonel saklama (retention) sinirlari.

Bu esikler `source_run` gecmisinden turetilen saglik kararlarini besler;
yanlis budama devre kesiciyi veya sessiz olum alarmini sessizce bozar.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, text

from app.core import retention
from app.core.models import Event, Notification, SourceRun, SourceSyncBatch
from app.db import SessionLocal


def _run(source: str, status: str, *, days: int, now: datetime) -> SourceRun:
    return SourceRun(source=source, status=status, started_at=now - timedelta(days=days))


async def test_source_run_prune_keeps_last_runs_of_each_source() -> None:
    """Esikten eski olsa bile son 20 kosu kaynak basina kalir."""
    now = datetime.now(UTC)
    async with SessionLocal() as session:
        # Ilk 5 kosu esikten eski, kalan 20 taze.
        for index in range(25):
            session.add(_run("busy", "ok", days=40 if index < 5 else 1, now=now))
        # Tek kosusu olan ve yillarca kosmamis kaynak: son gorunumu kaybolmamali.
        session.add(_run("lonely", "ok", days=400, now=now))
        await session.commit()

        removed = await retention.prune_source_runs(session, now=now)
        await session.commit()

        counts = dict(
            (
                await session.execute(
                    select(SourceRun.source, func.count()).group_by(SourceRun.source)
                )
            ).all()
        )

    assert removed == 5
    assert counts == {"busy": 20, "lonely": 1}


async def test_source_run_prune_keeps_problem_runs_longer() -> None:
    """30 gun / 90 gun ayrimi gercekten uygulanir.

    Her kaynakta 20 taze kosu var; test edilen kosu 21. siralara dusuyor,
    yani "son 20 kalir" kurali onu koruyamaz.
    """
    now = datetime.now(UTC)
    async with SessionLocal() as session:
        for source, status, days in (
            ("recent-problem", "error", 40),      # 90 gun penceresi: kalir
            ("old-problem", "abandoned", 100),    # 90 gunu gecti: gider
            ("old-ok", "ok", 40),                 # 30 gunu gecti: gider
        ):
            session.add(_run(source, status, days=days, now=now))
            for _ in range(20):
                session.add(_run(source, "ok", days=1, now=now))
        await session.commit()

        removed = await retention.prune_source_runs(session, now=now)
        await session.commit()

        remaining = {
            source: dict(
                (
                    await session.execute(
                        select(SourceRun.status, func.count())
                        .where(SourceRun.source == source)
                        .group_by(SourceRun.status)
                    )
                ).all()
            )
            for source in ("recent-problem", "old-problem", "old-ok")
        }

    assert removed == 2
    assert remaining["recent-problem"] == {"ok": 20, "error": 1}
    assert remaining["old-problem"] == {"ok": 20}
    assert remaining["old-ok"] == {"ok": 20}


async def test_source_sync_batch_prune_never_touches_active_batches() -> None:
    """Aktif batch silinirse ilerleme UI'i ve drain devralmasi bozulur."""
    now = datetime.now(UTC)
    stale = now - timedelta(days=100)
    doomed = SourceSyncBatch(status="completed", created_at=stale, finished_at=stale)
    async with SessionLocal() as session:
        session.add_all(
            [
                doomed,
                SourceSyncBatch(
                    status="completed_with_errors", created_at=stale, finished_at=stale
                ),
                # Aktif kalan batch'ler: yas ne olursa olsun dokunulmaz.
                SourceSyncBatch(status="running", created_at=stale, started_at=stale),
                SourceSyncBatch(status="queued", created_at=stale),
                # Yasi buyuk ama yeni bitmis: created_at'e gore silinmemeli.
                SourceSyncBatch(
                    status="completed", created_at=stale, finished_at=now - timedelta(days=1)
                ),
                SourceSyncBatch(
                    status="completed",
                    created_at=now - timedelta(days=10),
                    finished_at=now - timedelta(days=10),
                ),
            ]
        )
        await session.flush()
        # Silinecek batch'e bagli, kendi esigi icinde KALAN bir kosu: FK
        # ON DELETE SET NULL olmali, silme patlamamali.
        survivor = _run("survivor", "ok", days=1, now=now)
        survivor.batch_id = doomed.id
        session.add(survivor)
        await session.commit()

        removed = await retention.prune_source_sync_batches(session, now=now)
        await session.commit()

        remaining = dict(
            (
                await session.execute(
                    select(SourceSyncBatch.status, func.count()).group_by(
                        SourceSyncBatch.status
                    )
                )
            ).all()
        )
        # ORM kimlik haritasi bayat olabilir (expire_on_commit=False):
        # FK'nin gercekten SET NULL yaptigini DB'den oku.
        orphan_batch_id = (
            await session.execute(
                text("select batch_id from source_run where id = :id"),
                {"id": survivor.id},
            )
        ).scalar_one_or_none()

    assert removed == 2
    assert remaining == {"running": 1, "queued": 1, "completed": 2}
    assert orphan_batch_id is None


async def test_notification_prune_keeps_unread_and_urgent() -> None:
    """Okunmamis bildirim asla silinmez; acil olanlar daha uzun kalir."""
    now = datetime.now(UTC)

    def _notification(key: str, *, created_days: int, read_days: int | None = None,
                      importance: int = 1, dismissed: bool = False) -> Notification:
        created = now - timedelta(days=created_days)
        handled = now - timedelta(days=read_days) if read_days is not None else None
        return Notification(
            kind="test",
            title=key,
            body=None,
            entity_id=None,
            importance=importance,
            dedup_key=key,
            created_at=created,
            read_at=None if dismissed else handled,
            dismissed_at=handled if dismissed else None,
        )

    async with SessionLocal() as session:
        session.add_all(
            [
                _notification("read-old", created_days=100, read_days=100),
                _notification("dismissed-old", created_days=100, read_days=100, dismissed=True),
                _notification("urgent-read", created_days=100, read_days=100, importance=3),
                _notification("urgent-ancient", created_days=200, read_days=200, importance=3),
                _notification("unread-ancient", created_days=400),
                _notification("read-fresh", created_days=10, read_days=10),
            ]
        )
        await session.commit()

        removed = await retention.prune_notifications(session, now=now)
        await session.commit()

        keys = set(
            (await session.execute(select(Notification.dedup_key))).scalars()
        )

    assert removed == 3
    assert keys == {"urgent-read", "unread-ancient", "read-fresh"}


async def test_prune_operational_reports_every_table() -> None:
    """Tek cagriyla uc tablo birlikte budanir (maintenance'in girdisi)."""
    now = datetime.now(UTC)
    async with SessionLocal() as session:
        session.add(_run("keeper", "ok", days=1, now=now))
        # Kaynak basina son 20 kosu korunur: esikten eski kosunun gitmesi icin
        # onunde 20 taze kosu olmali.
        session.add(_run("gone", "ok", days=400, now=now))
        for _ in range(20):
            session.add(_run("gone", "ok", days=1, now=now))
        session.add(
            SourceSyncBatch(
                status="completed",
                created_at=now - timedelta(days=100),
                finished_at=now - timedelta(days=100),
            )
        )
        await session.commit()

        summary = await retention.prune_operational(session, now=now)
        await session.commit()

    assert summary["source_run"] == 1
    assert summary["source_sync_batch"] == 1
    assert summary["notification"] == 0
    # H6 kosu gecmisi de ayni gunluk bakim adiminda budanir (ayri zamanlayici YOK).
    assert summary["proactivity_run"] == 0
    assert set(summary) == {
        "source_run",
        "source_sync_batch",
        "notification",
        "proactivity_run",
    }


async def test_retention_never_prunes_events() -> None:
    """`event` kisisel aktivite hafizasi: hicbir saklama kurali dokunmaz."""
    now = datetime.now(UTC)
    async with SessionLocal() as session:
        await session.execute(
            text(
                "insert into event (verb, payload, occurred_at) "
                "values ('bookmark.saved', '{}'::jsonb, :at)"
            ),
            {"at": now - timedelta(days=2000)},
        )
        await session.commit()

        await retention.prune_operational(session, now=now)
        await session.commit()

        events = (await session.execute(select(func.count()).select_from(Event))).scalar_one()

    assert events == 1
