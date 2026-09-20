"""H6 teslimi: kısa metin, sınırlar, dedup anahtarları, dış kanal yok."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Notification
from app.db import SessionLocal
from app.modules.proactivity import delivery, service

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


class _Insight:
    def __init__(self, text: str) -> None:
        self.text = text


class _Loop:
    def __init__(self, title: str, detail: str | None = None) -> None:
        self.title = title
        self.detail = detail


def test_facts_are_bounded_and_deduplicated() -> None:
    items = [_Insight("bir"), _Insight("iki"), _Insight("üç"), _Insight("dört"), _Insight("bir")]
    facts = delivery.compose_facts(items)
    assert facts == ["bir", "iki", "üç"]
    assert len(facts) <= delivery.MAX_SURFACE_FACTS


def test_fact_lines_are_clipped_and_flattened() -> None:
    long_text = "çok   uzun\nbir metin " * 40
    line = delivery.fact_line(_Insight(long_text))
    assert line is not None
    assert len(line) <= delivery.MAX_FACT_CHARS
    assert "\n" not in line


def test_fact_line_handles_dicts_and_loops() -> None:
    assert delivery.fact_line({"title": "YLSY", "detail": "3 gün"}) == "YLSY — 3 gün"
    assert delivery.fact_line(_Loop("forkjob", "sonraki adım yok")) == "forkjob — sonraki adım yok"
    assert delivery.fact_line(None) is None
    assert delivery.fact_line(_Insight("   ")) is None


async def test_surface_creates_one_notification_with_episode_key(
    db_session: AsyncSession,
) -> None:
    notification_id = await delivery.deliver_run(
        db_session,
        run_id=1,
        logical_trigger_key="deadline:v1:abc:2026-09-23:3d",
        delivery_count=0,
        title="YLSY — 3 gün kaldı",
        facts=["YLSY için son tarih 3 gün içinde"],
        importance=2,
        now=NOW,
    )
    await db_session.commit()

    rows = list((await db_session.execute(select(Notification))).scalars())
    assert len(rows) == 1
    assert notification_id == rows[0].id
    assert rows[0].dedup_key == "proactivity:deadline:v1:abc:2026-09-23:3d:1"
    assert rows[0].kind == "proactivity"
    assert rows[0].body is not None and rows[0].body.startswith("• ")


async def test_same_episode_never_duplicates_a_notification(db_session: AsyncSession) -> None:
    first = await delivery.deliver_run(
        db_session,
        run_id=1,
        logical_trigger_key="deadline:v1:abc:2026-09-23:3d",
        delivery_count=0,
        title="t",
        facts=["f"],
        importance=2,
        now=NOW,
    )
    await db_session.commit()
    second = await delivery.deliver_run(
        db_session,
        run_id=1,
        logical_trigger_key="deadline:v1:abc:2026-09-23:3d",
        delivery_count=0,
        title="t",
        facts=["f"],
        importance=2,
        now=NOW,
    )
    await db_session.commit()

    assert first is not None
    assert second is None
    assert len(list((await db_session.execute(select(Notification))).scalars())) == 1


async def test_next_episode_is_a_new_notification(db_session: AsyncSession) -> None:
    """§72/§73: cooldown sonrası YENİ teslim meşrudur (sonsuz dedup değil)."""
    for count in (0, 1):
        await delivery.deliver_run(
            db_session,
            run_id=1,
            logical_trigger_key="project_stalled:v1:proj",
            delivery_count=count,
            title="forkjob",
            facts=["kayıtlı hareket yok"],
            importance=1,
            now=NOW,
        )
    await db_session.commit()
    keys = {
        row.dedup_key for row in (await db_session.execute(select(Notification))).scalars()
    }
    assert keys == {
        "proactivity:project_stalled:v1:proj:1",
        "proactivity:project_stalled:v1:proj:2",
    }


async def test_digest_is_one_notification_for_many_candidates(db_session: AsyncSession) -> None:
    notification_id, delivered_ids = await delivery.deliver_digest(
        db_session,
        entries=[
            delivery.DigestEntry(run_id=index + 1, title=f"Kayıt {index}", facts=[f"{index} gün kaldı"])
            for index in range(4)
        ],
        now=NOW,
    )
    await db_session.commit()
    assert delivered_ids == [1, 2, 3, 4]

    rows = list((await db_session.execute(select(Notification))).scalars())
    assert len(rows) == 1
    assert notification_id == rows[0].id
    assert rows[0].kind == "proactivity.digest"
    # Parti kimliği üye kümesine bağlıdır (deterministik, restart-safe).
    assert rows[0].dedup_key.startswith("proactivity:digest:2026-09-21:")
    assert len(rows[0].dedup_key.split(":")[-1]) == 12
    assert rows[0].importance == 1
    assert rows[0].body is not None
    assert rows[0].body.count("•") == 4


async def test_digest_is_bounded(db_session: AsyncSession) -> None:
    _, delivered_ids = await delivery.deliver_digest(
        db_session,
        entries=[
            delivery.DigestEntry(run_id=index + 1, title=f"Kayıt {index}", facts=["x"])
            for index in range(40)
        ],
        now=NOW,
    )
    await db_session.commit()
    row = (await db_session.execute(select(Notification))).scalar_one()
    assert row.body is not None
    assert row.body.count("•") <= delivery.MAX_DIGEST_ITEMS
    # Yalnizca GERCEKTEN gosterilen uyeler teslim edildi sayilir (§C).
    assert delivered_ids == list(range(1, delivery.MAX_DIGEST_ITEMS + 1))


async def test_empty_digest_writes_nothing(db_session: AsyncSession) -> None:
    assert await delivery.deliver_digest(db_session, entries=[], now=NOW) == (None, [])
    await db_session.commit()
    assert list((await db_session.execute(select(Notification))).scalars()) == []


async def test_delivery_never_uses_an_external_channel() -> None:
    """§194: H6 yalnızca forkOS Notification üretir; dış push YOK."""
    import pathlib

    source = pathlib.Path("app/modules/proactivity/delivery.py").read_text(encoding="utf-8")
    for forbidden in ("httpx", "requests", "smtplib", "urllib", "webhook", "ntfy", "apprise"):
        assert forbidden not in source


async def test_notification_bodies_stay_concise(db_session: AsyncSession) -> None:
    """§82: bildirim bir dikkat artefaktıdır, H5 paketinin dökümü DEĞİL."""
    await delivery.deliver_run(
        db_session,
        run_id=1,
        logical_trigger_key="k:v1:concise",
        delivery_count=0,
        title="Başlık",
        facts=[f"olgu {index}" for index in range(10)],
        importance=2,
        now=NOW,
    )
    await db_session.commit()
    row = (await db_session.execute(select(Notification))).scalar_one()
    assert row.body is not None
    assert row.body.count("•") <= delivery.MAX_SURFACE_FACTS


async def test_pruning_never_touches_pending_runs(db_session: AsyncSession) -> None:
    """§92: bekleyen/teslim edilmiş koşular yaştan bağımsız korunur."""
    from app.core.retention import prune_proactivity_runs
    from app.modules.proactivity.models import ProactivityRun

    await service.seed_rules(db_session)
    rule = (await service.list_rules(db_session))[0]
    old = datetime(2025, 1, 1, tzinfo=UTC)
    for key, state in (
        ("k:v1:pending", "deferred"),
        ("k:v1:delivered", "delivered"),
        ("k:v1:resolved", "resolved"),
        ("k:v1:cancelled", "cancelled"),
    ):
        db_session.add(
            ProactivityRun(
                rule_id=rule.id,
                logical_trigger_key=key,
                state=state,
                reason_codes=[],
                triggered_at=old,
                created_at=old,
            )
        )
    await db_session.commit()

    removed = await prune_proactivity_runs(db_session, now=NOW)
    await db_session.commit()

    remaining = {
        run.logical_trigger_key
        for run in (await db_session.execute(select(ProactivityRun))).scalars()
    }
    assert removed == 2
    assert remaining == {"k:v1:pending", "k:v1:delivered"}


async def test_digest_batch_identity_is_membership_based(db_session: AsyncSession) -> None:
    """§C3: parti kimliği ÜYE KÜMESİNE bağlıdır — aynı küme tekrar teslim edilmez."""
    first = [delivery.DigestEntry(run_id=index, title=f"K{index}", facts=["x"]) for index in (1, 2, 3)]
    other = [delivery.DigestEntry(run_id=index, title=f"K{index}", facts=["x"]) for index in (4, 5)]

    id_first, delivered_first = await delivery.deliver_digest(db_session, entries=first, now=NOW)
    await db_session.commit()
    id_repeat, delivered_repeat = await delivery.deliver_digest(db_session, entries=first, now=NOW)
    await db_session.commit()
    id_other, delivered_other = await delivery.deliver_digest(db_session, entries=other, now=NOW)
    await db_session.commit()

    assert id_first is not None
    # Aynı yığın: YENİ bildirim yok, ama üyeler gerçekten gösterildi sayılır.
    assert id_repeat == id_first
    assert delivered_repeat == [1, 2, 3]
    # Farklı yığın (kalan birikim): yeni bildirim.
    assert id_other is not None and id_other != id_first
    assert delivered_other == [4, 5]
    assert len(list((await db_session.execute(select(Notification))).scalars())) == 2
