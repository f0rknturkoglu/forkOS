from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import create_entity
from app.core.events import log_event
from app.core.models import Entity
from app.modules.pomodoro.models import PomodoroSession
from app.modules.pomodoro.schemas import (
    PomodoroManual,
    PomodoroOut,
    PomodoroStart,
    PomodoroStats,
)
from app.modules.study.models import StudyTopic

KINDS = {"focus", "short_break", "long_break"}


async def _out(session: AsyncSession, pomo: PomodoroSession) -> PomodoroOut:
    context = await session.get(Entity, pomo.context_entity_id) if pomo.context_entity_id else None
    return PomodoroOut(
        id=pomo.id,
        started_at=pomo.started_at,
        ended_at=pomo.ended_at,
        planned_min=pomo.planned_min,
        actual_min=pomo.actual_min,
        kind=pomo.kind,
        context_entity_id=pomo.context_entity_id,
        context_title=context.title if context else None,
        topic=pomo.topic,
        interrupted=pomo.interrupted,
        paused_at=pomo.paused_at,
        paused_s=pomo.paused_s,
    )


async def start(session: AsyncSession, data: PomodoroStart) -> PomodoroOut:
    if data.kind not in KINDS:
        raise ValueError("gecersiz pomodoro turu")
    active = (
        await session.execute(select(PomodoroSession).where(PomodoroSession.ended_at.is_(None)))
    ).scalar_one_or_none()
    if active is not None:
        raise RuntimeError("aktif pomodoro zaten var")
    context = await session.get(Entity, data.context_entity_id) if data.context_entity_id else None
    if data.context_entity_id and context is None:
        raise ValueError("baglam entity bulunamadi")
    label = data.topic or (context.title if context else None) or data.kind.replace("_", " ")
    entity = await create_entity(
        session, type=PomodoroSession.ENTITY_TYPE, title=f"Pomodoro: {label}", search_text=label
    )
    pomo = PomodoroSession(
        id=entity.id,
        planned_min=data.planned_min,
        kind=data.kind,
        context_entity_id=data.context_entity_id,
        topic=data.topic,
    )
    session.add(pomo)
    await session.commit()
    await session.refresh(pomo)
    return await _out(session, pomo)


async def active(session: AsyncSession) -> PomodoroOut | None:
    pomo = (
        (
            await session.execute(
                select(PomodoroSession)
                .where(PomodoroSession.ended_at.is_(None))
                .order_by(PomodoroSession.started_at.desc())
            )
        )
        .scalars()
        .first()
    )
    return await _out(session, pomo) if pomo else None


async def stop(session: AsyncSession, pomo_id: uuid.UUID, interrupted: bool) -> PomodoroOut | None:
    pomo = await session.get(PomodoroSession, pomo_id)
    if pomo is None:
        return None
    if pomo.ended_at is None:
        ended = datetime.now(UTC)
        pomo.ended_at = ended
        # Duraklamada gecen sure calisma degil: hem birikmis paused_s hem de
        # duraklatilmisken durdurulduysa su anki duraklama dusuluyor.
        pomo.paused_s = _paused_total(pomo, ended)
        pomo.paused_at = None
        elapsed = max(0, int((ended - pomo.started_at).total_seconds() - pomo.paused_s) // 60)
        # Tamamlanan seans planlanan sureyi yazar (sayac zaten sifira indi);
        # yarida kesilen gercekten calisilan kadarini.
        pomo.actual_min = min(elapsed, pomo.planned_min) if interrupted else pomo.planned_min
        pomo.interrupted = interrupted
        context = (
            await session.get(Entity, pomo.context_entity_id) if pomo.context_entity_id else None
        )
        verb = "pomodoro.interrupted" if interrupted else "pomodoro.completed"
        payload = (
            {"minutes": pomo.actual_min, "planned": pomo.planned_min}
            if interrupted
            else {
                "minutes": pomo.actual_min,
                "topic": pomo.topic or (context.title if context else None),
                "context_type": context.type if context else None,
            }
        )
        await log_event(
            session,
            verb=verb,
            entity_id=pomo.id,
            entity_type=PomodoroSession.ENTITY_TYPE,
            payload=payload,
        )
        if pomo.kind == "focus" and pomo.context_entity_id:
            topic = await session.get(StudyTopic, pomo.context_entity_id)
            if topic is not None:
                topic.last_studied_at = ended
        await session.commit()
    return await _out(session, pomo)


def _range_start(value: str) -> datetime:
    today = date.today()
    if value == "day":
        start = today
    elif value == "month":
        start = today.replace(day=1)
    else:
        start = today - timedelta(days=today.weekday())
    return datetime.combine(start, time.min, tzinfo=UTC)


async def stats(session: AsyncSession, value: str = "week") -> PomodoroStats:
    row = (
        await session.execute(
            select(
                func.coalesce(func.sum(PomodoroSession.actual_min), 0),
                func.count(PomodoroSession.id),
                func.count(PomodoroSession.id).filter(PomodoroSession.interrupted.is_(True)),
            ).where(
                PomodoroSession.started_at >= _range_start(value),
                PomodoroSession.ended_at.is_not(None),
                PomodoroSession.kind == "focus",
            )
        )
    ).one()
    return PomodoroStats(minutes=int(row[0]), sessions=int(row[1]), interrupted=int(row[2]))


def _paused_total(pomo: PomodoroSession, at: datetime) -> int:
    """Birikmis duraklama + (duraklatilmissa) su ana kadarki duraklama."""
    open_pause = int((at - pomo.paused_at).total_seconds()) if pomo.paused_at else 0
    return pomo.paused_s + max(0, open_pause)


async def pause(session: AsyncSession, pomo_id: uuid.UUID) -> PomodoroOut | None:
    """Sayaci durdurur. Bitmis ya da zaten durakli seans degismez (idempotent)."""
    pomo = await session.get(PomodoroSession, pomo_id)
    if pomo is None:
        return None
    if pomo.ended_at is None and pomo.paused_at is None:
        pomo.paused_at = datetime.now(UTC)
        await session.commit()
    return await _out(session, pomo)


async def resume(session: AsyncSession, pomo_id: uuid.UUID) -> PomodoroOut | None:
    pomo = await session.get(PomodoroSession, pomo_id)
    if pomo is None:
        return None
    if pomo.ended_at is None and pomo.paused_at is not None:
        pomo.paused_s = _paused_total(pomo, datetime.now(UTC))
        pomo.paused_at = None
        await session.commit()
    return await _out(session, pomo)


async def add_manual(session: AsyncSession, data: PomodoroManual) -> PomodoroOut:
    """Sayac calistirilmadan yapilan isi gecmise isler.

    Tamamlanmis kaydedilir ve `pomodoro.completed` yazar -- yani emek
    haritasina da girer; elle islenen is de istatistige dahildir.
    """
    if data.kind not in KINDS:
        raise ValueError("gecersiz pomodoro turu")
    context = await session.get(Entity, data.context_entity_id) if data.context_entity_id else None
    if data.context_entity_id and context is None:
        raise ValueError("baglam entity bulunamadi")

    started = data.started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=UTC)
    if started > datetime.now(UTC):
        raise ValueError("gelecege seans islenemez")

    label = data.topic or (context.title if context else None) or data.kind.replace("_", " ")
    entity = await create_entity(
        session, type=PomodoroSession.ENTITY_TYPE, title=f"Pomodoro: {label}", search_text=label
    )
    pomo = PomodoroSession(
        id=entity.id,
        started_at=started,
        ended_at=started + timedelta(minutes=data.minutes),
        planned_min=data.minutes,
        actual_min=data.minutes,
        kind=data.kind,
        context_entity_id=data.context_entity_id,
        topic=data.topic,
    )
    session.add(pomo)
    await log_event(
        session,
        verb="pomodoro.completed",
        entity_id=entity.id,
        entity_type=PomodoroSession.ENTITY_TYPE,
        payload={"minutes": data.minutes, "topic": data.topic, "manual": True},
    )
    await session.commit()
    await session.refresh(pomo)
    return await _out(session, pomo)


async def delete(session: AsyncSession, pomo_id: uuid.UUID) -> bool:
    """Seansi siler. `event` kayitlari kalir -- append-only (kural 3)."""
    entity = await session.get(Entity, pomo_id)
    if entity is None:
        return False
    await session.delete(entity)   # pomodoro_session PK'si entity'ye FK: cascade
    await log_event(
        session,
        verb="pomodoro.deleted",
        entity_type=PomodoroSession.ENTITY_TYPE,
        payload={"title": entity.title},
    )
    await session.commit()
    return True


async def recent(session: AsyncSession, *, limit: int = 20) -> list[PomodoroOut]:
    """Son seanslar -- silme ve gozden gecirme icin."""
    rows = (
        (
            await session.execute(
                select(PomodoroSession)
                .where(PomodoroSession.ended_at.is_not(None))
                .order_by(PomodoroSession.started_at.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return [await _out(session, pomo) for pomo in rows]
