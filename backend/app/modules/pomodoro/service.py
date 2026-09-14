from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import create_entity
from app.core.events import log_event
from app.core.models import Entity
from app.core.time import local_day_bounds, local_today
from app.modules.learning.models import StudyTopic
from app.modules.pomodoro.models import PomodoroSession
from app.modules.pomodoro.schemas import (
    PomodoroAnalytics,
    PomodoroContextStat,
    PomodoroDailyPoint,
    PomodoroManual,
    PomodoroOut,
    PomodoroStart,
    PomodoroStats,
)

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
        context_type=context.type if context else None,
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
            {
                "minutes": pomo.actual_min,
                "planned": pomo.planned_min,
                "context_entity_id": (
                    str(pomo.context_entity_id) if pomo.context_entity_id else None
                ),
                "context_type": context.type if context else None,
            }
            if interrupted
            else {
                "minutes": pomo.actual_min,
                "topic": pomo.topic or (context.title if context else None),
                "context_entity_id": (
                    str(pomo.context_entity_id) if pomo.context_entity_id else None
                ),
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
            # Baglam bir konu ya da bir kaynak olabilir. Kaynak baglaminda seans
            # suresi KONUNUN (ve atalarinin) icine yazilir; boylece alt kaynak
            # calisilinca ust konular "stale" gorunmez.
            from app.modules.learning import service as learning_service
            from app.modules.learning.models import LearningResource

            topic_id = None
            resource = await session.get(LearningResource, pomo.context_entity_id)
            if resource is not None:
                topic_id = resource.topic_id
            else:
                topic = await session.get(StudyTopic, pomo.context_entity_id)
                if topic is not None:
                    topic_id = topic.id
            if topic_id is not None:
                await learning_service.touch_topic_chain(session, topic_id, at=ended)
        await session.commit()
    return await _out(session, pomo)


def _range_start(value: str) -> datetime:
    today = local_today()
    if value == "day":
        start = today
    elif value == "month":
        start = today.replace(day=1)
    else:
        start = today - timedelta(days=today.weekday())
    return local_day_bounds(start)[0]


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


async def analytics(session: AsyncSession, value: str = "week") -> PomodoroAnalytics:
    """Odak sayfasinin gunluk seri ve baglam dagilimini tek sorgudan uretir."""
    today = local_today()
    if value == "week":
        requested_start = today - timedelta(days=today.weekday())
    elif value == "month":
        requested_start = today.replace(day=1)
    else:
        requested_start = None

    statement = (
        select(
            PomodoroSession.started_at,
            PomodoroSession.actual_min,
            PomodoroSession.interrupted,
            PomodoroSession.context_entity_id,
            PomodoroSession.topic,
            Entity.title,
            Entity.type,
        )
        .outerjoin(Entity, Entity.id == PomodoroSession.context_entity_id)
        .where(
            PomodoroSession.ended_at.is_not(None),
            PomodoroSession.kind == "focus",
        )
        .order_by(PomodoroSession.started_at.asc())
    )
    if requested_start is not None:
        statement = statement.where(
            PomodoroSession.started_at >= local_day_bounds(requested_start)[0]
        )

    rows = (await session.execute(statement)).all()
    start = requested_start or (local_today(rows[0].started_at) if rows else today)

    daily_values: dict = {}
    context_values: dict = {}
    total_minutes = 0
    interrupted = 0
    for row in rows:
        day = local_today(row.started_at)
        minutes = int(row.actual_min or 0)
        total_minutes += minutes
        interrupted += int(row.interrupted)

        day_value = daily_values.setdefault(day, {"minutes": 0, "sessions": 0, "interrupted": 0})
        day_value["minutes"] += minutes
        day_value["sessions"] += 1
        day_value["interrupted"] += int(row.interrupted)

        title = row.title or row.topic or "Bağımsız"
        key = str(row.context_entity_id) if row.context_entity_id else f"topic:{title.casefold()}"
        context_value = context_values.setdefault(
            key,
            {
                "context_entity_id": row.context_entity_id,
                "title": title,
                "context_type": row.type,
                "minutes": 0,
                "sessions": 0,
            },
        )
        context_value["minutes"] += minutes
        context_value["sessions"] += 1

    display_end = start + timedelta(days=6) if value == "week" else today
    daily: list[PomodoroDailyPoint] = []
    cursor = start
    while cursor <= display_end:
        value_for_day = daily_values.get(cursor, {"minutes": 0, "sessions": 0, "interrupted": 0})
        daily.append(PomodoroDailyPoint(date=cursor, **value_for_day))
        cursor += timedelta(days=1)

    contexts = [
        PomodoroContextStat(
            **context_value,
            share=round((context_value["minutes"] / total_minutes) * 100, 1)
            if total_minutes
            else 0,
        )
        for context_value in sorted(
            context_values.values(), key=lambda item: (-item["minutes"], item["title"])
        )
    ]
    sessions = len(rows)
    return PomodoroAnalytics(
        range=value,
        start_date=start,
        end_date=display_end,
        minutes=total_minutes,
        sessions=sessions,
        completed=sessions - interrupted,
        interrupted=interrupted,
        daily=daily,
        contexts=contexts,
    )


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
        payload={
            "minutes": data.minutes,
            "topic": data.topic,
            "manual": True,
            "context_entity_id": (str(pomo.context_entity_id) if pomo.context_entity_id else None),
            "context_type": context.type if context else None,
        },
    )
    await session.commit()
    await session.refresh(pomo)
    return await _out(session, pomo)


async def delete(session: AsyncSession, pomo_id: uuid.UUID) -> bool:
    """Seansi siler. `event` kayitlari kalir -- append-only (kural 3)."""
    entity = await session.get(Entity, pomo_id)
    if entity is None:
        return False
    await session.delete(entity)  # pomodoro_session PK'si entity'ye FK: cascade
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


#: Odak seansina baglam olabilecek entity tipleri.
#: Liste burada durur cunku "neye odaklanilir" pomodoro'nun kararidir;
#: modul basina import etmek yerine entity tipiyle suzulur (tek sorgu).
#: Firsat (is ilani) BILEREK yok -- ilanin kendisine odaklanilmaz; ona
#: hazirlanan gorev zaten listede (todo -> prepares_for).
#: Medya (media_item) VAR: "Su kitabi 50 dakika oku" gercek bir odak seansidir
#: ve seans suresi medya tuketimine aktarilabilir.
FOCUS_CONTEXT_TYPES = ["todo", "study_topic", "learning_resource", "project", "media_item"]


async def contexts(session: AsyncSession, query: str | None = None, limit: int = 40) -> list[dict]:
    """Baglam secicisinin adaylari: en son dokunulanlar once.

    Kapanmis gorevler listeye girmez -- bitmis bir ise odaklanilmaz. Diger
    tiplerde boyle bir durum kavrami olmadigi icin suzme yapilmaz.
    """
    from sqlalchemy import func, or_

    from app.core.search import match_clause, rank_expr
    from app.modules.media.models import MediaItem
    from app.modules.todo.models import Todo

    stmt = (
        select(
            Entity.id,
            Entity.type,
            Entity.title,
            MediaItem.kind,
            MediaItem.cover_path,
            MediaItem.cover_url,
        )
        .outerjoin(Todo, Todo.id == Entity.id)
        .outerjoin(MediaItem, MediaItem.id == Entity.id)
        .where(Entity.type.in_(FOCUS_CONTEXT_TYPES), Entity.archived_at.is_(None))
        .where(or_(Entity.type != "todo", Todo.status.in_(["open", "doing"])))
    )
    text_query = (query or "").strip()
    if text_query:
        # Arama varken siralama ALAKAYA gore olmali: global aramanin trigram
        # esiği "rebase" icin "Release"i de yakaliyor; en son guncellenene
        # gore dizersek gercek eslesme listenin dibinde kaliyor.
        stmt = stmt.where(match_clause(text_query)).order_by(
            (func.lower(Entity.title) == text_query.casefold()).desc(),
            rank_expr(text_query).desc(),
            Entity.updated_at.desc(),
        )
    else:
        stmt = stmt.order_by(Entity.updated_at.desc())
    rows = (await session.execute(stmt.limit(limit))).all()
    return [
        {
            "id": id_,
            "type": type_,
            "title": title,
            "kind": kind,
            # Yerel onbellek varsa onu, yoksa uzak kapak adresini ver; arayuz
            # ayni kurallari (mediaCoverUrl) uygular.
            "cover_url": cover_path or cover_url,
        }
        for id_, type_, title, kind, cover_path, cover_url in rows
    ]
