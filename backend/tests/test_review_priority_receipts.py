"""Review oncelik makbuzlari.

Kanitlanan sozlesmeler: makbuzda GERCEK Todo id'leri, plan gunu = donem sonu,
3 oncelik siniri, bos baslik atlama, makbuzsuz eski kayitlarin okunabilirligi
ve mevcut drop/carry_over/reschedule davranisinin korunmasi.

Makbuz `Review.decisions["_receipts"]` altinda yasar; `decisions` semasi
degismedigi icin eski kayitlar da aynen okunur.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import date

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import create_entity
from app.core.models import Entity
from app.core.time import local_datetime
from app.db import SessionLocal
from app.modules.review import service as review_service
from app.modules.review.models import Review
from app.modules.review.schemas import ReviewIn, ReviewOut
from app.modules.todo import service as todo_service
from app.modules.todo.models import PlanSlot, Todo
from app.modules.todo.schemas import TodoIn

#: 2026-01-05 Pazartesi: haftalik donem sinirlari testte kaymasin.
PERIOD_START = date(2026, 1, 5)


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def _review(session: AsyncSession, decisions: dict) -> ReviewOut:
    return await review_service.create(
        session, ReviewIn(kind="weekly", period_start=PERIOD_START, decisions=decisions)
    )


async def _todo_count(session: AsyncSession) -> int:
    return int((await session.execute(select(func.count()).select_from(Todo))).scalar_one())


async def _todo_title(session: AsyncSession, todo_id: uuid.UUID) -> str | None:
    return (await session.execute(select(Entity.title).where(Entity.id == todo_id))).scalar_one()


async def _slot_days(session: AsyncSession, todo_id: uuid.UUID) -> list[date]:
    return list(
        (
            await session.execute(select(PlanSlot.day).where(PlanSlot.entity_id == todo_id))
        ).scalars()
    )


async def test_priority_receipts_store_real_todo_ids(db_session: AsyncSession) -> None:
    created = await _review(db_session, {"priorities": ["ALES denemesi", "forkjob UI"]})

    receipts = created.decisions["_receipts"]["priorities"]
    assert [item["title"] for item in receipts] == ["ALES denemesi", "forkjob UI"]
    assert len({item["todo_id"] for item in receipts}) == 2

    for item in receipts:
        todo_id = uuid.UUID(item["todo_id"])
        assert await db_session.get(Todo, todo_id) is not None
        assert await _todo_title(db_session, todo_id) == item["title"]


async def test_priority_receipts_record_scheduled_day(db_session: AsyncSession) -> None:
    created = await _review(db_session, {"priorities": ["Planlanan oncelik"]})

    receipt = created.decisions["_receipts"]["priorities"][0]
    assert receipt["scheduled_day"] == created.period_end.isoformat()
    assert await _slot_days(db_session, uuid.UUID(receipt["todo_id"])) == [created.period_end]


async def test_priority_receipts_are_bounded_to_three(db_session: AsyncSession) -> None:
    created = await _review(
        db_session, {"priorities": [f"Oncelik {index}" for index in range(5)]}
    )

    receipts = created.decisions["_receipts"]["priorities"]
    assert [item["title"] for item in receipts] == ["Oncelik 0", "Oncelik 1", "Oncelik 2"]
    assert await _todo_count(db_session) == 3


async def test_review_without_receipts_still_reads(db_session: AsyncSession) -> None:
    entity = await create_entity(
        db_session, type=Review.ENTITY_TYPE, title="Eski review", search_text=""
    )
    db_session.add(
        Review(
            id=entity.id,
            kind="weekly",
            period_start=PERIOD_START,
            period_end=date(2026, 1, 12),
            stats={},
            decisions={"priorities": ["Eski oncelik"]},
        )
    )
    await db_session.commit()

    listed = await review_service.list_reviews(db_session, None, 10)

    assert [item.decisions for item in listed] == [{"priorities": ["Eski oncelik"]}]


async def test_blank_priority_is_skipped(db_session: AsyncSession) -> None:
    created = await _review(db_session, {"priorities": ["", {"title": ""}]})

    assert created.decisions["_receipts"] == {"priorities": []}
    assert await _todo_count(db_session) == 0


async def test_existing_decision_behaviour_is_preserved(db_session: AsyncSession) -> None:
    dropped = await todo_service.create(db_session, TodoIn(title="Dusecek gorev"))
    carried = await todo_service.create(db_session, TodoIn(title="Tasinacak gorev"))
    moved = await todo_service.create(db_session, TodoIn(title="Ertelenecek gorev"))
    moved_day = date(2026, 1, 8)

    created = await _review(
        db_session,
        {
            "drop": [str(dropped.id)],
            "carry_over": [str(carried.id)],
            "reschedule": [{"id": str(moved.id), "day": moved_day.isoformat()}],
            "priorities": ["Korunan oncelik"],
        },
    )

    dropped_todo = await db_session.get(Todo, dropped.id)
    assert dropped_todo is not None and dropped_todo.status == "dropped"

    assert await _slot_days(db_session, carried.id) == [created.period_end]
    assert await _slot_days(db_session, dropped.id) == []

    moved_todo = await db_session.get(Todo, moved.id)
    assert moved_todo is not None
    assert moved_todo.due_at == local_datetime(moved_day, 17 * 60)
    assert await _slot_days(db_session, moved.id) == [moved_day]

    # `priorities` karari oldugu gibi kalir; makbuz AYRI anahtarda yasar.
    assert created.decisions["priorities"] == ["Korunan oncelik"]
    assert [
        item["title"] for item in created.decisions["_receipts"]["priorities"]
    ] == ["Korunan oncelik"]
