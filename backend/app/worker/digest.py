"""Sabah ozeti.

Gunu tek bildirimle acar: bugun ne var, ne bekliyor. Bildirim altyapisi
zaten idempotent (`dedup_key`), o yuzden worker gun icinde birkac kez
yeniden baslasa da ayni gun icin ikinci bir ozet dusmez -- "her sabah
make up" ritualinin kacan turlari telafi etmesi bu sayede zararsiz.

Sayilar okunur; hicbir sey yazilmaz (bildirimin kendisi disinda).
"""
from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.modules.opportunity.service import notify

log = logging.getLogger("worker.digest")


async def _scalar(session: AsyncSession, sql: str, **params) -> int:
    return int((await session.execute(text(sql), params)).scalar() or 0)


async def collect(session: AsyncSession) -> dict[str, int]:
    """Ozetin satirlari. Her biri tek sayi -- bildirim govdesi kisa kalmali."""
    start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    return {
        "due_today": await _scalar(
            session,
            "select count(*) from todo where status in ('open','doing') "
            "and due_at >= :start and due_at < :end",
            start=start, end=end,
        ),
        "overdue": await _scalar(
            session,
            "select count(*) from todo where status in ('open','doing') and due_at < :start",
            start=start,
        ),
        "planned": await _scalar(
            session,
            "select count(*) from plan_slot where day = :today",
            today=date.today(),
        ),
        "deadlines": await _scalar(
            session,
            "select count(*) from deadline_v where due_at >= now() "
            "and due_at < now() + interval '7 days'",
        ),
        "inbox": await _scalar(
            session,
            "select count(*) from bookmark where collection = 'inbox'",
        ),
        "unread": await _scalar(
            session,
            "select count(*) from feed_item where read_at is null",
        ),
    }


def compose(stats: dict[str, int]) -> tuple[str, str]:
    """(baslik, govde). Sifir olan satir yazilmaz -- ozet sifir listesi degil."""
    head: list[str] = []
    if stats["due_today"]:
        head.append(f"{stats['due_today']} görev bugün")
    if stats["overdue"]:
        head.append(f"{stats['overdue']} gecikmiş")
    if stats["planned"]:
        head.append(f"{stats['planned']} blok planlı")
    title = "Bugün: " + (" · ".join(head) if head else "planında bir şey yok")

    tail: list[str] = []
    if stats["deadlines"]:
        tail.append(f"{stats['deadlines']} son tarih bu hafta")
    if stats["inbox"]:
        tail.append(f"{stats['inbox']} gelen kutusunda")
    if stats["unread"]:
        tail.append(f"{stats['unread']} okunmamış yazı")
    return title, " · ".join(tail) if tail else "Bekleyen yığın yok."


async def morning_digest() -> None:
    async with SessionLocal() as session:
        stats = await collect(session)
        title, body = compose(stats)
        await notify(
            session,
            kind="digest.morning",
            title=title,
            body=body,
            # Gunde bir: ayni gun ikinci kez calissa da yeni bildirim dusmez.
            dedup_key=f"digest:morning:{date.today().isoformat()}",
            importance=2 if stats["overdue"] or stats["deadlines"] else 1,
        )
        await session.commit()
    log.info("sabah ozeti: %s — %s", title, body)
