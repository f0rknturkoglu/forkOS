from __future__ import annotations

import os
from datetime import UTC, date, datetime, timedelta
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import UUID

from sqlalchemy import Integer, cast, func, or_, select, text
from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core import contributions
from app.core.entity import (
    archive_entity,
    create_entity,
    delete_entity,
    restore_entity,
    touch_entity,
)
from app.core.events import log_event
from app.core.links import link
from app.core.models import Entity, Event, Link
from app.core.time import local_day_bounds, local_today, streak_stats
from app.modules.bookmark.models import Bookmark
from app.modules.learning.models import Course, LearningResource, StudyArea, StudyTopic
from app.modules.learning.review import next_review
from app.modules.pomodoro.models import PomodoroSession
from app.modules.todo.models import PlanSlot, Todo
from app.modules.todo.schemas import TodoIn

#: Recursive CTE'lerde derinlik tavani. Bozuk (cycle'li) veri bile sorguyu
#: kilitleyemez: en fazla bu kadar iner.
MAX_DEPTH = 32

#: `stale` varsayilan esigi -- LearningWidget ayni degeri kullanir.
DEFAULT_STALE_DAYS = 21

#: Ice aktarmada ilerleme/oturum bilgisi olmayan, ama panoda "yeni" sayilan
#: konu esigi (weak: mastery bunun altindaysa zayif).
WEAK_MASTERY = 40

#: Ayni konuda `forgot` bu kadar biriktiyse konu zayif sayilir.
WEAK_FORGOT_COUNT = 3

#: PATCH govdesinde alan "verilmedi" ile "null verildi" ayrilmali.
_UNSET = object()


class LearningCommandError(ValueError):
    """Is kurali ihlali -- router 422 dondurur."""


class LearningNotFoundError(LearningCommandError):
    """Kayit yok -- router 404 dondurur."""


# ---------------------------------------------------------------------------
# Yardimcilar: normalizasyon, arama metni, URL
# ---------------------------------------------------------------------------


def _clean(value: str) -> str:
    """Fazla bosluklari sadelestirir (baslik/etiket arama anahtari icin)."""
    return " ".join(value.split())


def _norm(value: str) -> str:
    """Turkce-duyarli eslesme anahtari: `casefold` + bosluk sadeleştirme.

    `lower()` yerine `casefold` cunku `İ`/`I` ve `ß` gibi durumlarda
    `lower()` iki farkli basligi ayni anahtara indirebiliyor.
    """
    return _clean(value).casefold()


def _tracking_param(name: str) -> bool:
    lowered = name.lower()
    return lowered.startswith("utm_") or lowered in {"fbclid", "gclid", "mc_cid", "mc_eid"}


def canonical_url(url: str | None) -> str | None:
    """Dedupe anahtari: sema/host kucuk harf, fragment ve izleme parametreleri atilir.

    `https://Site.com/a/?utm_source=x#bolum` -> `https://site.com/a`
    """
    if not url:
        return None
    value = url.strip()
    if not value:
        return None
    parts = urlsplit(value)
    if not parts.scheme or not parts.netloc:
        return value
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()
    if scheme == "http" and netloc.endswith(":80"):
        netloc = netloc[:-3]
    if scheme == "https" and netloc.endswith(":443"):
        netloc = netloc[:-4]
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not _tracking_param(k)]
    path = parts.path.rstrip("/")
    return urlunsplit((scheme, netloc, path, urlencode(query), ""))


def _topic_search_text(title: str) -> str:
    return _clean(title)


def _area_search_text(title: str) -> str:
    return _clean(title)


def _resource_search_text(title: str, url: str | None, note: str | None, kind: str) -> str:
    return " ".join(filter(None, [_clean(title), url, note, kind]))


def _course_search_text(
    title: str, platform: str | None, url: str | None, notes: str | None
) -> str:
    return " ".join(filter(None, [_clean(title), platform, url, notes]))


def _kind_for_url(url: str | None) -> str:
    """Yer iminden gelen kaynagin turu: video siteleri video, digerleri link."""
    host = (urlsplit(url).netloc.lower() if url else "")
    if any(host.endswith(site) for site in ("youtube.com", "youtu.be", "vimeo.com")):
        return "video"
    return "link"


def _due_at(day: date) -> datetime:
    """Verilen yerel gunun basi (UTC) -- 'tekrar zamani geldi' siniri."""
    return local_day_bounds(day)[0]


def _today_end() -> datetime:
    """Bugunun sonu (yarinin basi): `next_review_at < bu` ise bugun tekrar edilir."""
    return local_day_bounds(local_today())[1]


def _is_due(value: datetime | None) -> bool:
    return value is not None and value < _today_end()


# ---------------------------------------------------------------------------
# Dogrulama
# ---------------------------------------------------------------------------


async def _validate_parent(
    session: AsyncSession,
    area_id: UUID,
    parent_id: UUID | None,
    topic_id: UUID | None = None,
) -> None:
    """`parent_id` kuralini uygular: ayni alan, kendisi degil, soyundan degil.

    Descendant cycle kontrolu ancestor zinciri uzerinden yapilir (recursive CTE,
    derinlik sinirli): yeni parent'in atalari arasinda `topic_id` varsa konu
    kendi altina tasiniyor demektir.
    """
    if parent_id is None:
        return
    if topic_id is not None and parent_id == topic_id:
        raise LearningCommandError("konu kendi ebeveyni olamaz")
    parent = await session.get(StudyTopic, parent_id)
    if parent is None:
        raise LearningCommandError("ebeveyn konu bulunamadi")
    if parent.area_id != area_id:
        raise LearningCommandError("ebeveyn konu ayni alanda olmali")
    if topic_id is None:
        return
    ancestors = (
        await session.execute(
            text(
                """with recursive chain as (
                    select id, parent_id, 1 as depth from study_topic where id = :pid
                    union all
                    select t.id, t.parent_id, c.depth + 1
                      from study_topic t join chain c on t.id = c.parent_id
                     where c.depth < :limit)
                select id from chain"""
            ),
            {"pid": parent_id, "limit": MAX_DEPTH},
        )
    ).scalars().all()
    if topic_id in set(ancestors):
        raise LearningCommandError("konu kendi alt agacinin altina tasinamaz")


async def _validate_entities(
    session: AsyncSession, ids: list[UUID], *, expected: tuple[str, ...], label: str
) -> None:
    if not ids:
        return
    rows = (
        await session.execute(select(Entity.id, Entity.type).where(Entity.id.in_(set(ids))))
    ).all()
    found = {row[0]: row[1] for row in rows}
    missing = [str(i) for i in set(ids) if i not in found]
    if missing:
        raise LearningCommandError(f"{label} bulunamadi: {', '.join(missing)}")
    wrong = sorted({found[i] for i in set(ids) if found[i] not in expected})
    if wrong:
        raise LearningCommandError(f"{label} tipi {expected} olmali: {wrong}")


# ---------------------------------------------------------------------------
# Cikti yardimcilari
# ---------------------------------------------------------------------------


def topic_out(topic: StudyTopic, title: str) -> dict:
    return {
        "id": topic.id,
        "title": title,
        "area_id": topic.area_id,
        "parent_id": topic.parent_id,
        "status": topic.status,
        "confidence": topic.confidence,
        "target_min": topic.target_min,
        "position": topic.position,
        "mastery": topic.mastery,
        "last_studied_at": topic.last_studied_at,
        "interval_days": topic.interval_days,
        "ease": topic.ease,
        "review_count": topic.review_count,
        "last_reviewed_at": topic.last_reviewed_at,
        "next_review_at": topic.next_review_at,
    }


def resource_out(
    item: LearningResource,
    title: str,
    bookmark_title: str | None = None,
    bookmark_url: str | None = None,
) -> dict:
    """Yer imine bagli kaynakta baslik/url BOOKMARK'tan okunur (taze gosterim)."""
    return {
        "id": item.id,
        "topic_id": item.topic_id,
        "title": bookmark_title or title,
        "url": bookmark_url or item.url,
        "kind": item.kind,
        "position": item.position,
        "completed_at": item.completed_at,
        "note": item.note,
        "estimated_min": item.estimated_min,
        "last_opened_at": item.last_opened_at,
        "source": item.source,
        "bookmark_id": item.bookmark_id,
        "course_id": item.course_id,
    }


def _resource_select():
    """Kaynak + entity basligi + (varsa) yer imi basligi/url'i tek sorguda."""
    bookmark_entity = aliased(Entity)
    return (
        select(
            LearningResource,
            Entity.title,
            bookmark_entity.title,
            Bookmark.url,
        )
        .join(Entity, Entity.id == LearningResource.id)
        .outerjoin(Bookmark, Bookmark.id == LearningResource.bookmark_id)
        .outerjoin(bookmark_entity, bookmark_entity.id == Bookmark.id)
    )


def _resource_row_out(row) -> dict:
    item, title, bookmark_title, bookmark_url = row
    return resource_out(item, title, bookmark_title, bookmark_url)


# ---------------------------------------------------------------------------
# Kurslar
# ---------------------------------------------------------------------------


def _course_row_out(
    course: Course,
    title: str,
    *,
    area_ids: list[UUID],
    topic_ids: list[UUID],
    resource_count: int,
    archived: bool,
) -> dict:
    return {
        "id": course.id,
        "title": title,
        "platform": course.platform,
        "url": course.url,
        "status": course.status,
        "progress_pct": course.progress_pct,
        "started_at": course.started_at,
        "completed_at": course.completed_at,
        "certificate_entity_id": course.certificate_entity_id,
        "notes": course.notes,
        "archived": archived,
        "area_ids": area_ids,
        "topic_ids": topic_ids,
        "resource_count": resource_count,
    }


async def _course_links(session: AsyncSession, course_ids: list[UUID]) -> dict[UUID, dict]:
    """Kurs -> (alan, konu) baglari ve kaynak sayisi; kurs basina sorgu YOK."""
    if not course_ids:
        return {}
    links = (
        await session.execute(
            select(Link.from_id, Link.to_id, Entity.type)
            .join(Entity, Entity.id == Link.to_id)
            .where(
                Link.from_id.in_(course_ids),
                Link.relation == "references",
                Entity.type.in_(("study_area", "study_topic")),
            )
        )
    ).all()
    counts = dict(
        (
            await session.execute(
                select(LearningResource.course_id, func.count())
                .where(LearningResource.course_id.in_(course_ids))
                .group_by(LearningResource.course_id)
            )
        ).all()
    )
    out: dict[UUID, dict] = {}
    for course_id in course_ids:
        out[course_id] = {"area_ids": [], "topic_ids": [], "resource_count": int(counts.get(course_id, 0))}
    for from_id, to_id, entity_type in links:
        bucket = out.get(from_id)
        if bucket is None:
            continue
        bucket["area_ids" if entity_type == "study_area" else "topic_ids"].append(to_id)
    return out


async def _sync_course_links(
    session: AsyncSession,
    course_id: UUID,
    *,
    area_ids: list[UUID] | None,
    topic_ids: list[UUID] | None,
) -> None:
    """`references` baglarini (kurs -> alan/konu) istenen hale getirir."""
    if area_ids is None and topic_ids is None:
        return
    if area_ids:
        await _validate_entities(session, area_ids, expected=("study_area",), label="alan")
    if topic_ids:
        await _validate_entities(session, topic_ids, expected=("study_topic",), label="konu")
    if area_ids is not None:
        await session.execute(
            sa_delete(Link).where(
                Link.from_id == course_id,
                Link.relation == "references",
                Link.to_id.in_(select(StudyArea.id)),
            )
        )
    if topic_ids is not None:
        await session.execute(
            sa_delete(Link).where(
                Link.from_id == course_id,
                Link.relation == "references",
                Link.to_id.in_(select(StudyTopic.id)),
            )
        )
    for target in (area_ids or []) + (topic_ids or []):
        await link(session, course_id, target, "references")


def _sync_course_state(
    course: Course, *, progress_given: bool, status_given: bool
) -> None:
    """Tarih/durum semantiginin TEK noktasi.

    `progress_pct == 100` ile `status == 'done'` birbirini tutar: yuzde 100
    verilirse durum done olur; done'dan cikilirsa yuzde tavana yapisik kalamaz
    (99'a iner). `in_progress` ilk geciste `started_at` yazar, done'dan cikis
    `completed_at`i temizler.
    """
    today = local_today()
    if progress_given and course.progress_pct == 100:
        course.status = "done"
    if status_given and course.status != "done" and course.progress_pct == 100:
        course.progress_pct = 99
    if course.status == "done":
        course.progress_pct = 100
        if course.started_at is None:
            course.started_at = today
        if course.completed_at is None:
            course.completed_at = today
    elif course.status == "in_progress":
        course.completed_at = None
        if course.started_at is None:
            course.started_at = today
    elif course.status == "planned":
        course.started_at = None
        course.completed_at = None
    else:  # dropped: baslamis olabilir, bitmis degil
        course.completed_at = None


async def list_courses(
    session: AsyncSession, *, include_archived: bool = False, area_id: UUID | None = None
) -> list[dict]:
    stmt = (
        select(Course, Entity.title, Entity.archived_at)
        .join(Entity, Entity.id == Course.id)
        .order_by(Entity.updated_at.desc())
    )
    if not include_archived:
        stmt = stmt.where(Entity.archived_at.is_(None))
    if area_id is not None:
        stmt = stmt.where(
            Course.id.in_(
                select(Link.from_id).where(
                    Link.to_id == area_id, Link.relation == "references"
                )
            )
        )
    rows = (await session.execute(stmt)).all()
    extra = await _course_links(session, [course.id for course, _, _ in rows])
    return [
        _course_row_out(
            course,
            title,
            archived=archived_at is not None,
            **extra.get(course.id, {"area_ids": [], "topic_ids": [], "resource_count": 0}),
        )
        for course, title, archived_at in rows
    ]


async def get_course(session: AsyncSession, course_id: UUID) -> dict | None:
    row = (
        await session.execute(
            select(Course, Entity.title, Entity.archived_at)
            .join(Entity, Entity.id == Course.id)
            .where(Course.id == course_id)
        )
    ).first()
    if row is None:
        return None
    course, title, archived_at = row
    extra = await _course_links(session, [course.id])
    return _course_row_out(
        course,
        title,
        archived=archived_at is not None,
        **extra.get(course.id, {"area_ids": [], "topic_ids": [], "resource_count": 0}),
    )


async def create_course(session: AsyncSession, data) -> dict:
    values = data.model_dump(exclude={"area_ids", "topic_ids"})
    title = values.pop("title")
    if values.get("certificate_entity_id") is not None:
        await _validate_entities(
            session,
            [values["certificate_entity_id"]],
            expected=("document", "note"),
            label="sertifika",
        )
    entity = await create_entity(
        session,
        type=Course.ENTITY_TYPE,
        title=title,
        search_text=_course_search_text(
            title, values.get("platform"), values.get("url"), values.get("notes")
        ),
    )
    course = Course(id=entity.id, **values)
    _sync_course_state(course, progress_given=True, status_given=True)
    session.add(course)
    await _sync_course_links(session, course.id, area_ids=data.area_ids, topic_ids=data.topic_ids)
    await log_event(
        session,
        verb="course.created",
        entity_id=course.id,
        entity_type=Course.ENTITY_TYPE,
        payload={"title": title, "status": course.status},
    )
    if course.status == "in_progress":
        await log_event(
            session,
            verb="course.started",
            entity_id=course.id,
            entity_type=Course.ENTITY_TYPE,
            payload={"title": title, "status": course.status},
        )
    await session.commit()
    return await get_course(session, course.id)


async def patch_course(session: AsyncSession, course_id: UUID, data) -> dict | None:
    course = await session.get(Course, course_id)
    if course is None:
        return None
    values = data.model_dump(exclude_unset=True)
    title = values.pop("title", None)
    archived = values.pop("archived", None)
    area_ids = values.pop("area_ids", None)
    topic_ids = values.pop("topic_ids", None)
    certificate = values.pop("certificate_entity_id", _UNSET)
    old_status, old_progress = course.status, course.progress_pct
    if certificate is not _UNSET and certificate is not None:
        # PHASE 3: sertifika yalnızca belge olabilir. `note` artık canlı bir
        # forkOS tipi değildir (bilgi Vault'ta yaşar), bu yüzden kabul edilmez.
        await _validate_entities(
            session, [certificate], expected=("document",), label="sertifika"
        )
    for key, value in values.items():
        setattr(course, key, value)
    if certificate is not _UNSET:
        course.certificate_entity_id = certificate
    _sync_course_state(
        course,
        progress_given="progress_pct" in data.model_fields_set,
        status_given="status" in data.model_fields_set,
    )
    await touch_entity(
        session,
        course.id,
        title=title,
        search_text=_course_search_text(
            title or "", course.platform, course.url, course.notes
        ),
    )
    await _sync_course_links(session, course.id, area_ids=area_ids, topic_ids=topic_ids)
    if archived is True:
        await archive_entity(session, course.id)
    elif archived is False:
        await restore_entity(session, course.id)
    if course.status != old_status:
        verb = {
            "done": "course.completed",
            "in_progress": "course.started" if old_status in ("planned", "dropped") else "course.reopened",
            "planned": "course.reopened",
        }.get(course.status)
        if verb is not None:
            await log_event(
                session,
                verb=verb,
                entity_id=course.id,
                entity_type=Course.ENTITY_TYPE,
                payload={"title": title or "", "from": old_status, "to": course.status},
            )
    if course.progress_pct != old_progress:
        await log_event(
            session,
            verb="course.progressed",
            entity_id=course.id,
            entity_type=Course.ENTITY_TYPE,
            payload={"from_pct": old_progress, "to_pct": course.progress_pct},
        )
    await session.commit()
    return await get_course(session, course.id)


async def delete_course(session: AsyncSession, course_id: UUID) -> bool:
    """Kursu siler. `event` kalir -- append-only (kural 3)."""
    if await session.get(Course, course_id) is None:
        return False
    entity = await session.get(Entity, course_id)
    title = entity.title if entity else ""
    if not await delete_entity(session, course_id):
        return False
    await log_event(
        session, verb="course.deleted", entity_type=Course.ENTITY_TYPE, payload={"title": title}
    )
    await session.commit()
    return True


# ---------------------------------------------------------------------------
# Calisma alanlari
# ---------------------------------------------------------------------------


async def create_area(session: AsyncSession, data) -> dict:
    entity = await create_entity(
        session, type="study_area", title=data.title, search_text=_area_search_text(data.title)
    )
    area = StudyArea(id=entity.id, color=data.color, active=True, position=data.position)
    session.add(area)
    await log_event(
        session,
        verb="study.area_created",
        entity_id=area.id,
        entity_type="study_area",
        payload={"area_id": str(area.id), "title": data.title},
    )
    await session.commit()
    return {
        "id": area.id,
        "title": data.title,
        "color": area.color,
        "active": area.active,
        "position": area.position,
        "archived_at": None,
    }


_STATS_SQL = """
select a.id, e.title, a.color, a.active, a.position, e.archived_at,
       (select count(*) from study_topic t where t.area_id = a.id) as topic_count,
       (select count(*) from study_topic t where t.area_id = a.id and t.status = 'done')
         as done_count,
       (select count(*) from learning_resource r join study_topic t on t.id = r.topic_id
          where t.area_id = a.id) as resource_count,
       (select count(*) from learning_resource r join study_topic t on t.id = r.topic_id
          where t.area_id = a.id and r.completed_at is not null) as resource_done,
       (select coalesce(sum(p.actual_min), 0) from pomodoro_session p
          join study_topic t on t.id = p.context_entity_id
         where t.area_id = a.id and p.kind = 'focus' and p.ended_at is not null)
         as focus_minutes,
       (select count(*) from study_topic t
         where t.area_id = a.id
           and (t.last_studied_at is null or t.last_studied_at < :cutoff)) as stale_count,
       (select max(t.last_studied_at) from study_topic t where t.area_id = a.id)
         as last_studied_at
  from study_area a join entity e on e.id = a.id
 order by a.position, e.title
"""


async def list_areas(session: AsyncSession, *, include_stats: bool = False) -> list[dict]:
    if not include_stats:
        rows = (
            await session.execute(
                select(StudyArea, Entity.title, Entity.archived_at)
                .join(Entity, Entity.id == StudyArea.id)
                .order_by(StudyArea.position, Entity.title)
            )
        ).all()
        return [
            {
                "id": area.id,
                "title": title,
                "color": area.color,
                "active": area.active,
                "position": area.position,
                "archived_at": archived_at,
            }
            for area, title, archived_at in rows
        ]
    cutoff = datetime.now(UTC) - timedelta(days=DEFAULT_STALE_DAYS)
    rows = (await session.execute(text(_STATS_SQL), {"cutoff": cutoff})).mappings().all()
    return [dict(row) for row in rows]


async def get_area(session: AsyncSession, area_id: UUID) -> dict | None:
    row = (
        await session.execute(
            select(StudyArea, Entity.title, Entity.archived_at)
            .join(Entity, Entity.id == StudyArea.id)
            .where(StudyArea.id == area_id)
        )
    ).first()
    if row is None:
        return None
    area, title, archived_at = row
    return {
        "id": area.id,
        "title": title,
        "color": area.color,
        "active": area.active,
        "position": area.position,
        "archived_at": archived_at,
    }


async def patch_area(session: AsyncSession, area_id: UUID, data) -> dict | None:
    area = await session.get(StudyArea, area_id)
    if area is None:
        return None
    values = data.model_dump(exclude_unset=True)
    title = values.pop("title", None)
    archived = values.pop("archived", None)
    old_active = area.active
    for key, value in values.items():
        setattr(area, key, value)
    await touch_entity(
        session,
        area.id,
        title=title,
        search_text=_area_search_text(title) if title is not None else None,
    )
    if archived is not None:
        # Arsiv = pasif: stale/agac sorgulari kapanan alanin konularini gostermez.
        area.active = not archived
        if archived:
            await archive_entity(session, area.id)
        else:
            await restore_entity(session, area.id)
        await log_event(
            session,
            verb="study.area_archived" if archived else "study.area_reopened",
            entity_id=area.id,
            entity_type="study_area",
            payload={
                "area_id": str(area.id),
                "title": title or "",
                "archived": archived,
            },
        )
    elif area.active != old_active:
        await log_event(
            session,
            verb="study.area_reopened" if area.active else "study.area_archived",
            entity_id=area.id,
            entity_type="study_area",
            payload={"area_id": str(area.id), "title": title or "", "active": area.active},
        )
    await session.commit()
    return await get_area(session, area_id)


async def delete_area(session: AsyncSession, area_id: UUID) -> bool:
    """Alani ve altindaki tum konulari siler."""
    area = await session.get(StudyArea, area_id)
    if area is None:
        return False
    entity = await session.get(Entity, area_id)
    title = entity.title if entity else ""
    if not await delete_entity(session, area_id):
        return False
    await log_event(
        session,
        verb="study.area_deleted",
        entity_type="study_area",
        payload={"area_id": str(area_id), "title": title},
    )
    await session.commit()
    return True


# ---------------------------------------------------------------------------
# Konular
# ---------------------------------------------------------------------------


async def create_topic(session: AsyncSession, data) -> dict:
    if await session.get(StudyArea, data.area_id) is None:
        raise LearningCommandError("alan bulunamadi")
    await _validate_parent(session, data.area_id, data.parent_id)
    entity = await create_entity(
        session,
        type="study_topic",
        title=data.title,
        search_text=_topic_search_text(data.title),
    )
    topic = StudyTopic(id=entity.id, **data.model_dump(exclude={"title"}))
    session.add(topic)
    await log_event(
        session,
        verb="study.topic_created",
        entity_id=topic.id,
        entity_type="study_topic",
        payload={"topic_id": str(topic.id), "area_id": str(topic.area_id), "title": data.title},
    )
    if topic.status == "in_progress":
        await log_event(
            session,
            verb="study.topic_started",
            entity_id=topic.id,
            entity_type="study_topic",
            payload={"topic_id": str(topic.id), "area_id": str(topic.area_id), "title": data.title},
        )
    await session.commit()
    return topic_out(topic, data.title)


async def patch_topic(session: AsyncSession, topic_id: UUID, data) -> dict | None:
    topic = await session.get(StudyTopic, topic_id)
    if topic is None:
        return None
    values = data.model_dump(exclude_unset=True)
    title = values.pop("title", None)
    parent_given = "parent_id" in values
    new_parent = values.get("parent_id")
    if parent_given:
        await _validate_parent(session, topic.area_id, new_parent, topic_id=topic_id)
    old_status, old_confidence, old_mastery = topic.status, topic.confidence, topic.mastery
    old_parent = topic.parent_id
    for key, value in values.items():
        setattr(topic, key, value)
    if title is not None:
        await touch_entity(
            session, topic.id, title=title, search_text=_topic_search_text(title)
        )
    else:
        await touch_entity(session, topic.id)
    entity = await session.get(Entity, topic.id)
    label = entity.title if entity else ""
    base = {"topic_id": str(topic.id), "area_id": str(topic.area_id), "title": label}

    if title is not None:
        await log_event(
            session, verb="study.topic_renamed", entity_id=topic.id,
            entity_type="study_topic", payload={**base, "title": title},
        )
    if parent_given and topic.parent_id != old_parent:
        await log_event(
            session,
            verb="study.topic_moved",
            entity_id=topic.id,
            entity_type="study_topic",
            payload={
                **base,
                "from_parent_id": str(old_parent) if old_parent else None,
                "to_parent_id": str(topic.parent_id) if topic.parent_id else None,
            },
        )
    if topic.confidence != old_confidence:
        await log_event(
            session,
            verb="study.confidence_changed",
            entity_id=topic.id,
            entity_type="study_topic",
            payload={**base, "from": old_confidence, "to": topic.confidence},
        )
    if topic.mastery != old_mastery:
        await log_event(
            session,
            verb="study.mastery_changed",
            entity_id=topic.id,
            entity_type="study_topic",
            payload={**base, "from": old_mastery, "to": topic.mastery},
        )
    if topic.status != old_status:
        if topic.status == "done":
            # Ogrenilen konu tazeleme kuyruguna girer: ilk tekrar bugun.
            topic.next_review_at = datetime.now(UTC)
            await log_event(
                session,
                verb="study.topic_completed",
                entity_id=topic.id,
                entity_type="study_topic",
                payload={**base, "total_minutes": (await _topic_metrics(session, topic.id))["minutes"]},
            )
        elif topic.status == "in_progress":
            await log_event(
                session,
                verb="study.topic_started" if old_status == "not_started" else "study.topic_reopened",
                entity_id=topic.id,
                entity_type="study_topic",
                payload={**base, "from": old_status, "to": topic.status},
            )
        elif old_status == "done":
            await log_event(
                session,
                verb="study.topic_reopened",
                entity_id=topic.id,
                entity_type="study_topic",
                payload={**base, "from": old_status, "to": topic.status},
            )
    await session.commit()
    return topic_out(topic, label)


async def move_topic(session: AsyncSession, topic_id: UUID, data) -> dict | None:
    topic = await session.get(StudyTopic, topic_id)
    if topic is None:
        return None
    await _validate_parent(session, topic.area_id, data.parent_id, topic_id=topic_id)
    old_parent = topic.parent_id
    topic.parent_id = data.parent_id
    if data.position is not None:
        topic.position = data.position
    entity = await session.get(Entity, topic.id)
    label = entity.title if entity else ""
    await touch_entity(session, topic.id)
    await log_event(
        session,
        verb="study.topic_moved",
        entity_id=topic.id,
        entity_type="study_topic",
        payload={
            "topic_id": str(topic.id),
            "area_id": str(topic.area_id),
            "title": label,
            "from_parent_id": str(old_parent) if old_parent else None,
            "to_parent_id": str(topic.parent_id) if topic.parent_id else None,
        },
    )
    await session.commit()
    return topic_out(topic, label)


async def delete_topic(session: AsyncSession, topic_id: UUID) -> bool:
    """Konuyu (ve alt konularini) siler. `event` kalir -- append-only."""
    topic = await session.get(StudyTopic, topic_id)
    if topic is None:
        return False
    entity = await session.get(Entity, topic_id)
    title = entity.title if entity else ""
    if not await delete_entity(session, topic_id):
        return False
    await log_event(
        session,
        verb="study.topic_deleted",
        entity_type="study_topic",
        payload={"topic_id": str(topic_id), "area_id": str(topic.area_id), "title": title},
    )
    await session.commit()
    return True


def _subtree_cte(alias: str = "subtree") -> str:
    """Derinlik sinirli alt agac CTE'si -- bozuk veri bile sonsuz donmez."""
    return f"""{alias} as (
    select id, 1 as depth from study_topic where id = :id
    union all
    select t.id, s.depth + 1 from study_topic t join {alias} s on t.parent_id = s.id
     where s.depth < :limit)"""


async def _topic_metrics(session: AsyncSession, topic_id: UUID) -> dict:
    """Alt agac (kendi + cocuklar) kaynak sayaclari + odak dakikalari (tek sorgu)."""
    week_start = _due_at(local_today() - timedelta(days=local_today().weekday()))
    row = (
        (
            await session.execute(
                text(
                    f"""with recursive {_subtree_cte()}
                    select
                      (select count(*) from learning_resource r
                        where r.topic_id in (select id from subtree)) as total,
                      (select count(*) from learning_resource r
                        where r.topic_id in (select id from subtree)
                          and r.completed_at is not null) as done,
                      (select coalesce(sum(p.actual_min), 0) from pomodoro_session p
                        where p.context_entity_id in (select id from subtree)
                          and p.kind = 'focus' and p.ended_at is not null) as minutes,
                      (select count(*) from pomodoro_session p
                        where p.context_entity_id in (select id from subtree)
                          and p.kind = 'focus' and p.ended_at is not null) as sessions,
                      (select coalesce(sum(p.actual_min), 0) from pomodoro_session p
                        where p.context_entity_id in (select id from subtree)
                          and p.kind = 'focus' and p.ended_at is not null
                          and p.started_at >= :week_start) as week_minutes,
                      (select max(t.last_studied_at) from study_topic t
                        where t.id in (select id from subtree)) as last_studied_at"""
                ),
                {"id": topic_id, "limit": MAX_DEPTH, "week_start": week_start},
            )
        )
        .mappings()
        .one()
    )
    total, done = int(row["total"]), int(row["done"])
    return {
        "total": total,
        "done": done,
        "pct": round(done * 100 / total) if total else 0,
        "minutes": int(row["minutes"]),
        "sessions": int(row["sessions"]),
        "week_minutes": int(row["week_minutes"]),
        "last_studied_at": row["last_studied_at"],
    }


async def topic_progress(session: AsyncSession, topic_id: UUID) -> dict:
    if await session.get(StudyTopic, topic_id) is None:
        raise LearningNotFoundError("konu bulunamadi")
    metrics = await _topic_metrics(session, topic_id)
    return {"total": metrics["total"], "done": metrics["done"], "pct": metrics["pct"]}




async def _ancestors(session: AsyncSession, topic_id: UUID) -> list[dict]:
    rows = (
        await session.execute(
            text(
                """with recursive chain as (
                    select id, parent_id, 1 as depth from study_topic where id = :id
                    union all
                    select t.id, t.parent_id, c.depth + 1
                      from study_topic t join chain c on t.id = c.parent_id
                     where c.depth < :limit)
                select c.id, e.title, c.depth from chain c
                  join entity e on e.id = c.id
                 order by c.depth desc"""
            ),
            {"id": topic_id, "limit": MAX_DEPTH},
        )
    ).all()
    # depth 1 = konunun kendisi; atalar kokten ebeveyne siralanir.
    return [{"id": row[0], "title": row[1]} for row in rows if row[2] > 1]


async def _open_todo(session: AsyncSession, topic_id: UUID) -> dict | None:
    row = (
        await session.execute(
            select(Todo, PlanSlot.day)
            .join(Link, Link.from_id == Todo.id)
            .join(Entity, Entity.id == Todo.id)
            .outerjoin(PlanSlot, PlanSlot.entity_id == Todo.id)
            .where(
                Link.to_id == topic_id,
                Link.relation == "prepares_for",
                Todo.status.in_(("open", "doing")),
            )
            .order_by(PlanSlot.day.asc().nullslast(), Entity.created_at.desc())
            .limit(1)
        )
    ).first()
    if row is None:
        return None
    todo, plan_day = row
    return {
        "id": todo.id,
        "title": (await session.get(Entity, todo.id)).title,
        "status": todo.status,
        "plan_day": plan_day,
        "priority": todo.priority,
        "due_at": todo.due_at,
    }


async def _deck_count(session: AsyncSession, topic_id: UUID) -> int:
    from app.modules.flashcard.service import STUDY_RELATIONS

    return int(
        (
            await session.execute(
                select(func.count())
                .select_from(Link)
                .join(Entity, Entity.id == Link.from_id)
                .where(
                    Link.to_id == topic_id,
                    Link.relation.in_(STUDY_RELATIONS),
                    Entity.type == "flashcard_deck",
                )
            )
        ).scalar_one()
    )


def review_block(topic: StudyTopic) -> dict:
    return {
        "interval_days": topic.interval_days,
        "ease": topic.ease,
        "review_count": topic.review_count,
        "last_reviewed_at": topic.last_reviewed_at,
        "next_review_at": topic.next_review_at,
        "mastery": topic.mastery,
        "due": _is_due(topic.next_review_at),
    }


async def get_topic(session: AsyncSession, topic_id: UUID) -> dict | None:
    row = (
        await session.execute(
            select(StudyTopic, Entity.title)
            .join(Entity, Entity.id == StudyTopic.id)
            .where(StudyTopic.id == topic_id)
        )
    ).first()
    if row is None:
        return None
    topic, title = row
    metrics = await _topic_metrics(session, topic_id)
    resources = [
        _resource_row_out(row)
        for row in (
            await session.execute(
                _resource_select()
                .where(LearningResource.topic_id == topic_id)
                .order_by(LearningResource.position, Entity.created_at, LearningResource.id)
            )
        ).all()
    ]
    return {
        "topic": topic_out(topic, title),
        "ancestors": await _ancestors(session, topic_id),
        "resources": resources,
        "progress": {"total": metrics["total"], "done": metrics["done"], "pct": metrics["pct"]},
        "stats": {
            "minutes": metrics["minutes"],
            "sessions": metrics["sessions"],
            "week_minutes": metrics["week_minutes"],
            "last_studied_at": metrics["last_studied_at"],
        },
        "open_todo": await _open_todo(session, topic_id),
        "flashcard_deck_count": await _deck_count(session, topic_id),
        "review": review_block(topic),
    }


async def topic_impact(session: AsyncSession, topic_id: UUID) -> dict | None:
    """Silme onayi: alt agacta ne var (sabit sorgu)."""
    if await session.get(StudyTopic, topic_id) is None:
        return None
    row = (
        (
            await session.execute(
                text(
                    f"""with recursive {_subtree_cte()}
                    select
                      (select count(*) from subtree) as topics,
                      (select count(*) from learning_resource r
                        where r.topic_id in (select id from subtree)) as resources,
                      (select count(*) from link l
                        where l.from_id in (select id from subtree)
                           or l.to_id in (select id from subtree)) as links,
                      (select count(*) from plan_slot s
                        where s.entity_id in (select id from subtree)) as plan_slots,
                      (select count(*) from link l
                        where l.to_id in (select id from subtree)
                          and l.relation = 'prepares_for') as todos"""
                ),
                {"id": topic_id, "limit": MAX_DEPTH},
            )
        )
        .mappings()
        .one()
    )
    return {key: int(value) for key, value in row.items()}


# ---------------------------------------------------------------------------
# Agac (tree)
# ---------------------------------------------------------------------------


def _children_map(nodes: dict[UUID, dict]) -> dict[UUID | None, list[UUID]]:
    children: dict[UUID | None, list[UUID]] = {}
    for node_id, node in nodes.items():
        parent = node["parent_id"]
        if parent == node_id or parent not in nodes:
            parent = None
        children.setdefault(parent, []).append(node_id)
    for bucket in children.values():
        bucket.sort(key=lambda nid: (nodes[nid]["position"], nodes[nid]["title"]))
    return children


async def _load_area_graph(session: AsyncSession, area_id: UUID) -> dict | None:
    """Alanin TUM dugumleri + kaynaklari + odak dakikalari. 4 sorgu, konu sayisindan bagimsiz."""
    area_row = (
        await session.execute(
            select(StudyArea, Entity.title, Entity.archived_at)
            .join(Entity, Entity.id == StudyArea.id)
            .where(StudyArea.id == area_id)
        )
    ).first()
    if area_row is None:
        return None
    area, area_title, area_archived = area_row

    topic_rows = (
        await session.execute(
            select(StudyTopic, Entity.title)
            .join(Entity, Entity.id == StudyTopic.id)
            .where(StudyTopic.area_id == area_id, Entity.archived_at.is_(None))
        )
    ).all()

    resources: dict[UUID, list[dict]] = {}
    for row in (
        await session.execute(
            _resource_select()
            .join(StudyTopic, StudyTopic.id == LearningResource.topic_id)
            .where(StudyTopic.area_id == area_id)
            .order_by(LearningResource.position, Entity.created_at, LearningResource.id)
        )
    ).all():
        out = _resource_row_out(row)
        resources.setdefault(out["topic_id"], []).append(out)

    focus: dict[UUID, tuple[int, int]] = {
        context_entity_id: (int(minutes), int(sessions))
        for context_entity_id, minutes, sessions in (
            await session.execute(
                select(
                    PomodoroSession.context_entity_id,
                    func.coalesce(func.sum(PomodoroSession.actual_min), 0),
                    func.count(PomodoroSession.id),
                )
                .where(
                    PomodoroSession.kind == "focus",
                    PomodoroSession.ended_at.is_not(None),
                    PomodoroSession.context_entity_id.in_(
                        select(StudyTopic.id).where(StudyTopic.area_id == area_id)
                    ),
                )
                .group_by(PomodoroSession.context_entity_id)
            )
        ).all()
    }

    nodes: dict[UUID, dict] = {}
    for topic, title in topic_rows:
        direct = resources.get(topic.id, [])
        minutes, sessions = focus.get(topic.id, (0, 0))
        nodes[topic.id] = {
            **topic_out(topic, title),
            "depth": 0,
            "path": [],
            "child_count": 0,
            "resource_total": len(direct),
            "resource_done": sum(1 for r in direct if r["completed_at"] is not None),
            "focus_minutes": minutes,
            "focus_sessions": sessions,
            "resources": direct,
        }
    return {
        "area": area,
        "area_title": area_title,
        "area_archived": area_archived,
        "nodes": nodes,
        "resources": resources,
    }


def _annotate(nodes: dict[UUID, dict]) -> tuple[list[UUID], int]:
    """Derinlik/yol/cocuk sayisi + alt agac toplamlari. Dongu verisi guvenli."""
    children = _children_map(nodes)
    orphan_count = sum(
        1
        for node in nodes.values()
        if node["parent_id"] is not None and node["parent_id"] not in nodes
    )
    ordered: list[UUID] = []
    seen: set[UUID] = set()

    def walk(node_id: UUID, depth: int, path: list[UUID]) -> None:
        if node_id in seen or depth > 64:
            return
        seen.add(node_id)
        node = nodes[node_id]
        node["depth"] = depth
        node["path"] = path
        ordered.append(node_id)
        for child in children.get(node_id, []):
            walk(child, depth + 1, path + [node_id])

    roots = children.get(None, [])
    for root in roots:
        walk(root, 0, [])
    # Dongu iceren (bozuk) kayitlar da gorunsun: onlari kok gibi ele al.
    for node_id in nodes:
        if node_id not in seen:
            orphan_count += 1
            walk(node_id, 0, [])
    # Cocuklar once: alt agac toplamlari tek gecisi ile yukari yayilir.
    for node_id in sorted(ordered, key=lambda nid: -nodes[nid]["depth"]):
        node = nodes[node_id]
        parent = node["parent_id"] if node["parent_id"] in nodes else None
        if parent is None or parent == node_id:
            continue
        parent_node = nodes[parent]
        parent_node["child_count"] += 1
        parent_node["resource_total"] += node["resource_total"]
        parent_node["resource_done"] += node["resource_done"]
        parent_node["focus_minutes"] += node["focus_minutes"]
        parent_node["focus_sessions"] += node["focus_sessions"]
    return ordered, orphan_count


def _filter_nodes(nodes: dict[UUID, dict], ordered: list[UUID], *, q, status) -> list[UUID]:
    keep = list(ordered)
    if status:
        keep = [nid for nid in keep if nodes[nid]["status"] == status]
    if q:
        needle = _norm(q)
        matched = {nid for nid in nodes if needle in _norm(nodes[nid]["title"])}
        # Arama sonucu dali acar: eslesenlerin atalari da gorunur.
        for nid in list(matched):
            matched.update(nodes[nid]["path"])
        keep = [nid for nid in keep if nid in matched]
    return keep


def _area_out_from_graph(graph: dict, nodes: dict[UUID, dict]) -> dict:
    area = graph["area"]
    all_nodes = list(nodes.values())
    cutoff = datetime.now(UTC) - timedelta(days=DEFAULT_STALE_DAYS)
    return {
        "id": area.id,
        "title": graph["area_title"],
        "color": area.color,
        "active": area.active,
        "position": area.position,
        "archived_at": graph["area_archived"],
        "topic_count": len(all_nodes),
        "done_count": sum(1 for n in all_nodes if n["status"] == "done"),
        "resource_count": sum(len(v) for v in graph["resources"].values()),
        "resource_done": sum(
            1 for v in graph["resources"].values() for r in v if r["completed_at"] is not None
        ),
        "focus_minutes": sum(int(n["focus_minutes"]) for n in all_nodes),
        "stale_count": sum(
            1
            for n in all_nodes
            if n["last_studied_at"] is None or n["last_studied_at"] < cutoff
        ),
        "last_studied_at": max(
            (n["last_studied_at"] for n in all_nodes if n["last_studied_at"] is not None),
            default=None,
        ),
    }


async def area_tree(
    session: AsyncSession,
    area_id: UUID,
    *,
    q: str | None = None,
    status: str | None = None,
    include_resources: bool = False,
) -> dict | None:
    graph = await _load_area_graph(session, area_id)
    if graph is None:
        return None
    nodes = graph["nodes"]
    ordered, orphan_count = _annotate(nodes)
    keep = _filter_nodes(nodes, ordered, q=q, status=status)
    keep_set = set(keep)
    roots = [
        nid
        for nid in keep
        if nodes[nid]["parent_id"] is None or nodes[nid]["parent_id"] not in keep_set
    ]
    payload = []
    for nid in keep:
        node = nodes[nid]
        payload.append(
            {
                **{k: node[k] for k in (
                    "id",
                    "title",
                    "parent_id",
                    "depth",
                    "position",
                    "status",
                    "confidence",
                    "mastery",
                    "target_min",
                    "last_studied_at",
                    "next_review_at",
                    "path",
                    "resource_total",
                    "resource_done",
                    "focus_minutes",
                    "focus_sessions",
                    "child_count",
                )},
                "review_due": _is_due(node["next_review_at"]),
                "progress_pct": (
                    round(node["resource_done"] * 100 / node["resource_total"])
                    if node["resource_total"]
                    else 0
                ),
                "resources": node["resources"] if include_resources else None,
            }
        )
    return {
        "area": _area_out_from_graph(graph, nodes),
        "nodes": payload,
        "totals": {
            "topics": len(keep),
            "done": sum(1 for nid in keep if nodes[nid]["status"] == "done"),
            "in_progress": sum(1 for nid in keep if nodes[nid]["status"] == "in_progress"),
            "review_due": sum(1 for nid in keep if _is_due(nodes[nid]["next_review_at"])),
            "resource_total": sum(nodes[nid]["resource_total"] for nid in roots),
            "resource_done": sum(nodes[nid]["resource_done"] for nid in roots),
            "focus_minutes": sum(nodes[nid]["focus_minutes"] for nid in roots),
            "focus_sessions": sum(nodes[nid]["focus_sessions"] for nid in roots),
        },
        "orphan_count": orphan_count,
    }


async def tree(session: AsyncSession, area_id: UUID) -> list[dict]:
    """`GET /study/topics?area_id=` -- eski (ic ice) sekil, yol DEGISMEDI.

    Yeni duz agac (`/study/areas/{id}/tree`) ile AYNI grafikten uretilir;
    ikinci bir sorgu yolu yok.
    """
    graph = await _load_area_graph(session, area_id)
    if graph is None:
        raise LearningNotFoundError("alan bulunamadi")
    nodes = graph["nodes"]
    ordered, _orphan = _annotate(nodes)
    by_parent: dict[UUID | None, list[UUID]] = {}
    for nid in ordered:
        parent = nodes[nid]["parent_id"]
        if parent == nid or parent not in nodes:
            parent = None
        by_parent.setdefault(parent, []).append(nid)

    def build(parent: UUID | None) -> list[dict]:
        out = []
        for nid in by_parent.get(parent, []):
            node = nodes[nid]
            out.append(
                {
                    **{k: node[k] for k in (
                        "id",
                        "title",
                        "area_id",
                        "parent_id",
                        "status",
                        "confidence",
                        "target_min",
                        "position",
                        "mastery",
                        "last_studied_at",
                        "interval_days",
                        "ease",
                        "review_count",
                        "last_reviewed_at",
                        "next_review_at",
                    )},
                    "progress": {
                        "total": node["resource_total"],
                        "done": node["resource_done"],
                        "pct": (
                            round(node["resource_done"] * 100 / node["resource_total"])
                            if node["resource_total"]
                            else 0
                        ),
                    },
                    "children": build(nid),
                }
            )
        return out

    return build(None)


async def stale(
    session: AsyncSession,
    *,
    days: int = DEFAULT_STALE_DAYS,
    limit: int = 20,
    offset: int = 0,
    area_id: UUID | None = None,
    include_done: bool = False,
) -> dict:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    conditions = [
        Entity.archived_at.is_(None),
        StudyArea.active.is_(True),
        or_(StudyTopic.last_studied_at.is_(None), StudyTopic.last_studied_at < cutoff),
    ]
    if not include_done:
        conditions.append(StudyTopic.status != "done")
    if area_id is not None:
        conditions.append(StudyTopic.area_id == area_id)
    base = (
        select(StudyTopic, Entity.title)
        .join(Entity, Entity.id == StudyTopic.id)
        .join(StudyArea, StudyArea.id == StudyTopic.area_id)
        .where(*conditions)
    )
    total = (
        await session.execute(
            select(func.count())
            .select_from(StudyTopic)
            .join(Entity, Entity.id == StudyTopic.id)
            .join(StudyArea, StudyArea.id == StudyTopic.area_id)
            .where(*conditions)
        )
    ).scalar_one()
    rows = (
        await session.execute(
            base.order_by(
                StudyTopic.last_studied_at.asc().nullsfirst(), Entity.title
            ).limit(limit).offset(offset)
        )
    ).all()
    return {
        "items": [topic_out(topic, title) for topic, title in rows],
        "total": int(total),
        "limit": limit,
        "offset": offset,
    }


# ---------------------------------------------------------------------------
# Tekrar (SRS)
# ---------------------------------------------------------------------------


async def touch_topic_chain(
    session: AsyncSession, topic_id: UUID, *, at: datetime | None = None
) -> int:
    """Konunun kendisi + TUM atalarinin `last_studied_at`ini yazar.

    Pomodoro bir kaynak baglaminda bitince cagrilir: alt konu calisilinca
    ust konular "stale" gorunmez. `commit` ETMEZ -- cagiran commit eder.
    """
    moment = at or datetime.now(UTC)
    result = await session.execute(
        text(
            """with recursive chain as (
                select id, parent_id, 1 as depth from study_topic where id = :id
                union all
                select t.id, t.parent_id, c.depth + 1
                  from study_topic t join chain c on t.id = c.parent_id
                 where c.depth < :limit)
            update study_topic set last_studied_at = :at
             where id in (select id from chain)"""
        ),
        {"id": topic_id, "limit": MAX_DEPTH, "at": moment},
    )
    return int(result.rowcount or 0)


def _review_row(topic: StudyTopic, title: str, area_title: str) -> dict:
    return {
        "id": topic.id,
        "title": title,
        "area_id": topic.area_id,
        "area_title": area_title,
        "status": topic.status,
        "next_review_at": topic.next_review_at,
        "mastery": topic.mastery,
        "interval_days": topic.interval_days,
        "review_count": topic.review_count,
        "last_reviewed_at": topic.last_reviewed_at,
        "confidence": topic.confidence,
        "last_studied_at": topic.last_studied_at,
    }


async def topic_review_queue(
    session: AsyncSession, *, window_days: int = 14, limit: int = 50
) -> dict:
    """`GET /api/study/review` govdesi.

    today modulu "tekrar zamani gelen konular" onerisini buradan alir;
    `due_today` + `overdue` listeleri konu ozeti tasir (id, title, area_id,
    area_title, next_review_at, mastery).
    """
    today = local_today()
    day_start = _due_at(today)
    day_end = _today_end()
    window_end = _due_at(today + timedelta(days=max(1, window_days)))
    area_entity = aliased(Entity)
    rows = (
        await session.execute(
            select(StudyTopic, Entity.title, area_entity.title)
            .join(Entity, Entity.id == StudyTopic.id)
            .join(StudyArea, StudyArea.id == StudyTopic.area_id)
            .join(area_entity, area_entity.id == StudyArea.id)
            .where(Entity.archived_at.is_(None), StudyArea.active.is_(True))
        )
    ).all()
    forgotten = dict(
        (
            await session.execute(
                text(
                    "select entity_id, count(*) from event"
                    " where verb = 'study.reviewed' and payload->>'grade' = 'forgot'"
                    " group by entity_id having count(*) >= :threshold"
                ),
                {"threshold": WEAK_FORGOT_COUNT},
            )
        ).all()
    )

    buckets: dict[str, list[dict]] = {
        "due_today": [], "overdue": [], "upcoming": [], "new_topics": [], "weak": []
    }
    for topic, title, area_title in rows:
        row = _review_row(topic, title, area_title or "")
        due = topic.next_review_at
        if due is not None and due < day_start:
            buckets["overdue"].append(row)
        elif due is not None and due < day_end:
            buckets["due_today"].append(row)
        elif due is not None and due < window_end:
            buckets["upcoming"].append(row)
        elif due is None and topic.review_count == 0 and topic.status == "in_progress":
            buckets["new_topics"].append(row)
        if (topic.mastery is not None and topic.mastery < WEAK_MASTERY) or topic.id in forgotten:
            buckets["weak"].append(row)

    buckets["overdue"].sort(key=lambda r: r["next_review_at"])
    buckets["due_today"].sort(key=lambda r: r["next_review_at"])
    buckets["upcoming"].sort(key=lambda r: r["next_review_at"])
    buckets["new_topics"].sort(key=lambda r: (r["last_studied_at"] is None, r["title"]))
    buckets["weak"].sort(key=lambda r: (r["mastery"] is None, r["mastery"] or 0, r["title"]))
    return {name: items[:limit] for name, items in buckets.items()}


async def review_topic(session: AsyncSession, topic_id: UUID, data) -> dict | None:
    topic = await session.get(StudyTopic, topic_id)
    if topic is None:
        return None
    interval, ease = next_review(topic.interval_days, topic.ease, data.grade)
    now = datetime.now(UTC)
    topic.interval_days = interval
    topic.ease = ease
    topic.review_count += 1
    topic.last_reviewed_at = now
    # Aralik 0 ise konu bugun tekrar kuyrugunda kalir; aksi halde hedef gunun basi.
    topic.next_review_at = now if interval == 0 else _due_at(local_today() + timedelta(days=interval))
    entity = await session.get(Entity, topic.id)
    label = entity.title if entity else ""
    if data.mastery is not None and data.mastery != topic.mastery:
        old_mastery = topic.mastery
        topic.mastery = data.mastery
        await log_event(
            session,
            verb="study.mastery_changed",
            entity_id=topic.id,
            entity_type="study_topic",
            payload={
                "topic_id": str(topic.id),
                "area_id": str(topic.area_id),
                "title": label,
                "from": old_mastery,
                "to": topic.mastery,
            },
        )
    await log_event(
        session,
        verb="study.reviewed",
        entity_id=topic.id,
        entity_type="study_topic",
        payload={
            "topic_id": str(topic.id),
            "area_id": str(topic.area_id),
            "title": label,
            "grade": data.grade,
            "interval_days": interval,
            "ease": ease,
        },
    )
    await session.commit()
    return review_block(topic)


# ---------------------------------------------------------------------------
# Istatistik
# ---------------------------------------------------------------------------

#: `range` -> geriye kac gun (None = tum zamanlar).
_RANGES = {"week": 7, "month": 30, "90d": 90, "year": 365, "all": None}


async def study_stats(session: AsyncSession, *, value: str = "week") -> dict:
    days = _RANGES.get(value, 7)
    start = None if days is None else datetime.now(UTC) - timedelta(days=days)
    start_day = None if days is None else local_today() - timedelta(days=days)
    focus_filter = [
        PomodoroSession.kind == "focus",
        PomodoroSession.ended_at.is_not(None),
    ]
    if start is not None:
        focus_filter.append(PomodoroSession.started_at >= start)
    row = (
        await session.execute(
            select(
                func.coalesce(func.sum(PomodoroSession.actual_min), 0),
                func.count(PomodoroSession.id),
            ).where(*focus_filter)
        )
    ).one()
    focus_minutes, focus_sessions = int(row[0]), int(row[1])

    async def count_events(verb: str) -> int:
        stmt = select(func.count()).select_from(Event).where(Event.verb == verb)
        if start is not None:
            stmt = stmt.where(Event.occurred_at >= start)
        return int((await session.execute(stmt)).scalar_one())

    by_area = [
        {"area_id": area_id, "title": title, "minutes": int(minutes)}
        for area_id, title, minutes in (
            await session.execute(
                select(StudyTopic.area_id, Entity.title, func.coalesce(func.sum(PomodoroSession.actual_min), 0))
                .join(PomodoroSession, PomodoroSession.context_entity_id == StudyTopic.id)
                .join(Entity, Entity.id == StudyTopic.area_id)
                .where(*focus_filter)
                .group_by(StudyTopic.area_id, Entity.title)
                .order_by(func.coalesce(func.sum(PomodoroSession.actual_min), 0).desc())
            )
        ).all()
    ]
    by_topic = [
        {"topic_id": topic_id, "title": title, "minutes": int(minutes)}
        for topic_id, title, minutes in (
            await session.execute(
                select(StudyTopic.id, Entity.title, func.coalesce(func.sum(PomodoroSession.actual_min), 0))
                .join(PomodoroSession, PomodoroSession.context_entity_id == StudyTopic.id)
                .join(Entity, Entity.id == StudyTopic.id)
                .where(*focus_filter)
                .group_by(StudyTopic.id, Entity.title)
                .order_by(func.coalesce(func.sum(PomodoroSession.actual_min), 0).desc())
                .limit(10)
            )
        ).all()
    ]
    planned_stmt = select(func.coalesce(func.sum(PlanSlot.duration_min), 0)).where(
        PlanSlot.entity_id.in_(select(StudyTopic.id))
    )
    if start_day is not None:
        planned_stmt = planned_stmt.where(PlanSlot.day >= start_day)
    planned_minutes = int((await session.execute(planned_stmt)).scalar_one())

    course_rows = dict(
        (
            await session.execute(select(Course.status, func.count()).group_by(Course.status))
        ).all()
    )
    delta_stmt = select(
        func.coalesce(
            func.sum(
                cast(Event.payload["to"].astext, Integer)
                - cast(Event.payload["from"].astext, Integer)
            ),
            0,
        )
    ).where(Event.verb == "study.confidence_changed")
    if start is not None:
        delta_stmt = delta_stmt.where(Event.occurred_at >= start)
    confidence_delta = int((await session.execute(delta_stmt)).scalar_one())

    active = await contributions.active_days(session, since=start_day)
    streak, _longest = streak_stats(active, today=local_today())

    return {
        "focus_minutes": focus_minutes,
        "focus_sessions": focus_sessions,
        "topics_done": await count_events("study.topic_completed"),
        "topics_started": await count_events("study.topic_started"),
        "resources_done": await count_events("learning.resource_completed"),
        "reviews_done": await count_events("study.reviewed"),
        "active_days": len(active),
        "streak_days": streak,
        "by_area": by_area,
        "by_topic": by_topic,
        "planned_minutes": planned_minutes,
        "actual_minutes": focus_minutes,
        "courses": {
            "total": sum(int(v) for v in course_rows.values()),
            "done": int(course_rows.get("done", 0)),
            "in_progress": int(course_rows.get("in_progress", 0)),
        },
        "flashcards_reviewed": await count_events("flashcard.reviewed"),
        "confidence_delta": confidence_delta,
    }


# ---------------------------------------------------------------------------
# Kaynaklar
# ---------------------------------------------------------------------------


async def list_resources(session: AsyncSession, topic_id: UUID) -> list[dict]:
    if await session.get(StudyTopic, topic_id) is None:
        raise LearningNotFoundError("konu bulunamadi")
    rows = (
        await session.execute(
            _resource_select()
            .where(LearningResource.topic_id == topic_id)
            .order_by(LearningResource.position, Entity.created_at, LearningResource.id)
        )
    ).all()
    return [_resource_row_out(row) for row in rows]


async def get_resource(session: AsyncSession, resource_id: UUID) -> dict | None:
    """Tek kaynak (deep-link) + `last_opened_at` damgasi."""
    row = (
        await session.execute(_resource_select().where(LearningResource.id == resource_id))
    ).first()
    if row is None:
        return None
    item = row[0]
    item.last_opened_at = datetime.now(UTC)
    await session.commit()
    return _resource_row_out(row)


async def _next_position(session: AsyncSession, topic_id: UUID) -> int:
    return int(
        (
            await session.execute(
                select(func.coalesce(func.max(LearningResource.position), -1) + 1).where(
                    LearningResource.topic_id == topic_id
                )
            )
        ).scalar_one()
    )


async def create_resource(session: AsyncSession, topic_id: UUID, data) -> dict:
    if await session.get(StudyTopic, topic_id) is None:
        raise LearningNotFoundError("konu bulunamadi")
    values = data.model_dump()
    title = values.pop("title")
    entity = await create_entity(
        session,
        type=LearningResource.ENTITY_TYPE,
        title=title,
        search_text=_resource_search_text(title, values.get("url"), values.get("note"), values["kind"]),
    )
    item = LearningResource(id=entity.id, topic_id=topic_id, **values)
    session.add(item)
    # Konu -> kaynak bagi: RelatedPanel ve graf kaynagi konunun altinda gosterir.
    await link(session, topic_id, item.id, "learns_from")
    await log_event(
        session,
        verb="learning.resource_added",
        entity_id=item.id,
        entity_type=LearningResource.ENTITY_TYPE,
        payload={
            "topic_id": str(topic_id),
            "kind": item.kind,
            "title": title,
            "source": item.source,
        },
    )
    await session.commit()
    return resource_out(item, title)


async def attach_bookmark(session: AsyncSession, topic_id: UUID, bookmark_id: UUID) -> dict:
    """Yer imini KOPYALAMADAN ogrenme kaynagina baglar (partial unique ile idempotent)."""
    topic = await session.get(StudyTopic, topic_id)
    if topic is None:
        raise LearningNotFoundError("konu bulunamadi")
    bookmark = await session.get(Bookmark, bookmark_id)
    if bookmark is None:
        raise LearningCommandError("yer imi bulunamadi")
    existing = (
        await session.execute(
            _resource_select().where(
                LearningResource.topic_id == topic_id,
                LearningResource.bookmark_id == bookmark_id,
            )
        )
    ).first()
    if existing is not None:
        return _resource_row_out(existing)
    bookmark_title = (await session.get(Entity, bookmark.id)).title
    entity = await create_entity(
        session,
        type=LearningResource.ENTITY_TYPE,
        title=bookmark_title,
        search_text=_resource_search_text(bookmark_title, bookmark.url, bookmark.note, "link"),
    )
    item = LearningResource(
        id=entity.id,
        topic_id=topic_id,
        bookmark_id=bookmark.id,
        url=bookmark.url,
        kind=_kind_for_url(bookmark.url),
        position=await _next_position(session, topic_id),
        source="bookmark",
    )
    session.add(item)
    await link(session, topic_id, item.id, "learns_from")
    await log_event(
        session,
        verb="learning.resource_added",
        entity_id=item.id,
        entity_type=LearningResource.ENTITY_TYPE,
        payload={
            "topic_id": str(topic_id),
            "kind": item.kind,
            "title": bookmark_title,
            "source": "bookmark",
        },
    )
    await session.commit()
    row = (
        await session.execute(_resource_select().where(LearningResource.id == item.id))
    ).first()
    return _resource_row_out(row)


async def patch_resource(session: AsyncSession, resource_id: UUID, data) -> dict | None:
    item = await session.get(LearningResource, resource_id)
    if item is None:
        return None
    values = data.model_dump(exclude_unset=True)
    title = values.pop("title", None)
    completed = values.pop("completed", None)
    if item.bookmark_id is not None and (title is not None or "url" in values):
        # Baslik/url yer iminden okunur; burada degistirmek sessizce ezilirdi.
        raise LearningCommandError("yer imine bagli kaynagin basligi/url'i yer iminden gelir")
    for key, value in values.items():
        setattr(item, key, value)
    if completed is not None:
        was_done = item.completed_at is not None
        item.completed_at = datetime.now(UTC) if completed else None
        if completed != was_done:
            await log_event(
                session,
                verb="learning.resource_completed" if completed else "learning.resource_reopened",
                entity_id=item.id,
                entity_type=LearningResource.ENTITY_TYPE,
                payload={"topic_id": str(item.topic_id)},
            )
    if title is not None:
        await touch_entity(
            session,
            item.id,
            title=title,
            search_text=_resource_search_text(title, item.url, item.note, item.kind),
        )
    else:
        entity = await session.get(Entity, item.id)
        label = entity.title if entity else ""
        await touch_entity(
            session,
            item.id,
            search_text=_resource_search_text(label, item.url, item.note, item.kind),
        )
    entity = await session.get(Entity, item.id)
    label = entity.title if entity else ""
    changed = [key for key in values]
    await log_event(
        session,
        verb="learning.resource_updated",
        entity_id=item.id,
        entity_type=LearningResource.ENTITY_TYPE,
        payload={"topic_id": str(item.topic_id), "title": label, "fields": changed},
    )
    await session.commit()
    row = (
        await session.execute(_resource_select().where(LearningResource.id == item.id))
    ).first()
    return _resource_row_out(row)


async def delete_resource(session: AsyncSession, resource_id: UUID) -> bool:
    item = await session.get(LearningResource, resource_id)
    if item is None:
        return False
    entity = await session.get(Entity, resource_id)
    title = entity.title if entity else ""
    if not await delete_entity(session, resource_id):
        return False
    await log_event(
        session,
        verb="learning.resource_deleted",
        entity_type=LearningResource.ENTITY_TYPE,
        payload={"topic_id": str(item.topic_id), "title": title},
    )
    await session.commit()
    return True


# ---------------------------------------------------------------------------
# Todo koprusu (Faz 6)
# ---------------------------------------------------------------------------


async def create_todo_for_topic(
    session: AsyncSession, topic_id: UUID, data=None
) -> dict:
    """Konudan gorev uretir + `prepares_for` bagini TEK transaction'da yazar.

    Idempotent: konunun ACIK (`open`/`doing`) gorevi varsa yenisi acilmaz,
    `{created: false, todo: ...}` doner. `force=true` ikinci gorevi uretir.
    """
    from app.modules.todo import service as todo_service

    topic = await session.get(StudyTopic, topic_id)
    if topic is None:
        raise LearningNotFoundError("konu bulunamadi")
    force = bool(getattr(data, "force", False)) if data else False
    if not force:
        existing = (
            await session.execute(
                select(Todo.id)
                .join(Link, Link.from_id == Todo.id)
                .join(Entity, Entity.id == Todo.id)
                .where(
                    Link.to_id == topic_id,
                    Link.relation == "prepares_for",
                    Todo.status.in_(("open", "doing")),
                )
                .order_by(Entity.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if existing is not None:
            return {"created": False, "todo": await todo_service.get(session, existing)}
    title = (await session.get(Entity, topic_id)).title
    extra = data.model_dump(exclude_unset=True, exclude={"force"}) if data else {}
    todo = await todo_service.create(
        session,
        TodoIn(title=title, description="çalışma konusu", **extra),
        commit=False,
    )
    await link(session, todo.id, topic_id, "prepares_for")
    await session.commit()
    return {"created": True, "todo": todo}


# ---------------------------------------------------------------------------
# Ice aktarma (preview + apply)
# ---------------------------------------------------------------------------


class _SeedNode:
    __slots__ = ("node", "title", "parent", "depth", "path", "position", "status", "target_min")

    def __init__(
        self, node, title: str, parent: int | None, depth: int, path: str, position: int
    ) -> None:
        self.node = node
        self.title = title
        self.parent = parent
        self.depth = depth
        self.path = path
        #: Acik `position` verilmediyse kardes sirasi (0,1,2...) yazilir.
        self.position = node.position if node.position is not None else position
        self.status = node.status
        self.target_min = node.target_min


def _flatten_seeds(topics: list, prefix: str | None) -> list[_SeedNode]:
    flat: list[_SeedNode] = []

    def walk(nodes: list, parent: int | None, depth: int, parent_path: str) -> None:
        for position, node in enumerate(nodes):
            title = node.title
            if prefix:
                title = title[len(prefix):] if title.startswith(prefix) else title
            title = _clean(title)
            path = f"{parent_path} / {title}" if parent_path else title
            index = len(flat)
            flat.append(_SeedNode(node, title, parent, depth, path, position))
            walk(node.children, index, depth + 1, path)

    walk(topics, None, 1, "")
    return flat


def _common_prefix(titles: list[str]) -> str | None:
    """Tum basliklarin ortak onegini (ayiriciya kadar) bulur."""
    if len(titles) < 2:
        return None
    shared = os.path.commonprefix(titles)
    for separator in (" - ", " – ", " — ", ": ", "-", ":", "_"):
        index = shared.rfind(separator)
        if index >= 3:
            return shared[: index + len(separator)]
    return None


async def _resolve_import_area(session: AsyncSession, data, *, create: bool) -> dict:
    if data.area_id is not None:
        area = await session.get(StudyArea, data.area_id)
        if area is None:
            raise LearningCommandError("alan bulunamadi")
        title = (await session.get(Entity, area.id)).title
        return {"area_id": area.id, "title": title, "exists": True}
    wanted = _norm(data.area or "")
    rows = (
        await session.execute(select(StudyArea.id, Entity.title).join(Entity, Entity.id == StudyArea.id))
    ).all()
    for area_id, title in rows:
        if _norm(title) == wanted:
            return {"area_id": area_id, "title": title, "exists": True}
    if not create:
        return {"area_id": None, "title": _clean(data.area or ""), "exists": False}
    entity = await create_entity(
        session, type="study_area", title=_clean(data.area or ""), search_text=_area_search_text(data.area or "")
    )
    session.add(StudyArea(id=entity.id, active=True, position=0))
    await session.flush()
    await log_event(
        session,
        verb="study.area_created",
        entity_id=entity.id,
        entity_type="study_area",
        payload={"area_id": str(entity.id), "title": _clean(data.area or "")},
    )
    return {"area_id": entity.id, "title": _clean(data.area or ""), "exists": False}


async def _import_state(session: AsyncSession, area_id: UUID):
    """Alandaki mevcut konular + kaynaklar: (parent, norm baslik) -> id eslemesi."""
    rows = (
        await session.execute(
            select(StudyTopic.id, StudyTopic.parent_id, StudyTopic.status, StudyTopic.target_min,
                   StudyTopic.position, Entity.title)
            .join(Entity, Entity.id == StudyTopic.id)
            .where(StudyTopic.area_id == area_id)
        )
    ).all()
    topics: dict[tuple[UUID | None, str], dict] = {}
    by_id: dict[UUID, dict] = {}
    for topic_id, parent_id, status, target_min, position, title in rows:
        entry = {
            "id": topic_id,
            "parent_id": parent_id,
            "status": status,
            "target_min": target_min,
            "position": position,
            "title": title,
            "resources": {},
            "resource_count": 0,
        }
        topics[(_norm(title), parent_id)] = entry
        by_id[topic_id] = entry
    if by_id:
        for resource_id, topic_id, title, url, kind, note, estimated_min in (
            await session.execute(
                select(
                    LearningResource.id,
                    LearningResource.topic_id,
                    Entity.title,
                    LearningResource.url,
                    LearningResource.kind,
                    LearningResource.note,
                    LearningResource.estimated_min,
                )
                .join(Entity, Entity.id == LearningResource.id)
                .where(LearningResource.topic_id.in_(list(by_id)))
                .order_by(LearningResource.position, Entity.created_at, LearningResource.id)
            )
        ).all():
            entry = by_id[topic_id]
            entry["resource_count"] += 1
            key = canonical_url(url) or _norm(title)
            entry["resources"][key] = {
                "id": resource_id,
                "title": title,
                "url": url,
                "kind": kind,
                "note": note,
                "estimated_min": estimated_min,
            }
    return topics, by_id


def _classify(
    flat: list[_SeedNode],
    known: dict[tuple[UUID | None, str], dict],
    *,
    update_existing: bool,
) -> dict:
    """Preview siniflandirmasi: hangisi olusacak/guncellenecek/eslesecek."""
    creates, updates, matches, conflicts = [], [], [], []
    resources_new = resources_duplicate = 0
    resolved: list[UUID | None] = [None] * len(flat)
    seen: set[tuple[int | None, str]] = set()
    for index, seed in enumerate(flat):
        sibling_key = (seed.parent, _norm(seed.title))
        if sibling_key in seen:
            conflicts.append(
                {"path": seed.path, "reason": "ayni ebeveyn altinda yinelenen konu basligi"}
            )
        seen.add(sibling_key)
        # Ebeveyn bu yuklemede yeni olusuyorsa cocuk da zorunlu olarak yenidir.
        parent_id = resolved[seed.parent] if seed.parent is not None else None
        existed = None
        if seed.parent is None or resolved[seed.parent] is not None:
            existed = known.get((_norm(seed.title), parent_id))
        if existed is None:
            creates.append(
                {
                    "path": seed.path,
                    "title": seed.title,
                    "status": seed.status,
                    "resources": len(seed.node.resources),
                }
            )
            resources_new += len(seed.node.resources)
            continue
        resolved[index] = existed["id"]
        changes: list[str] = []
        if existed["status"] != seed.status:
            changes.append("status")
        if existed["target_min"] != seed.target_min:
            changes.append("target_min")
        if existed["position"] != seed.position:
            changes.append("position")
        for resource in seed.node.resources:
            key = canonical_url(resource.url) or _norm(resource.title)
            current = existed["resources"].get(key)
            if current is None:
                resources_new += 1
                continue
            resources_duplicate += 1
            if not update_existing:
                continue
            for field, value in (
                ("url", resource.url),
                ("kind", resource.kind),
                ("note", resource.note),
                ("estimated_min", resource.estimated_min),
            ):
                if value is not None and current[field] != value:
                    changes.append(f"resource:{field}")
        entry = {
            "path": seed.path,
            "title": seed.title,
            "status": seed.status,
            "resources": len(seed.node.resources),
            "changes": sorted(set(changes)),
        }
        if changes and update_existing:
            updates.append(entry)
        else:
            matches.append(entry)
    return {
        "creates": creates,
        "updates": updates,
        "matches": matches,
        "conflicts": conflicts,
        "resources_new": resources_new,
        "resources_duplicate": resources_duplicate,
    }


async def import_preview(session: AsyncSession, data) -> dict:
    """Hicbir sey YAZMAZ; ne olacagini soyler (agac + sayaclar)."""
    area = await _resolve_import_area(session, data, create=False)
    all_titles = [node.title for node in _flatten_seeds(data.topics, None)]
    prefix = _common_prefix(all_titles)
    flat = _flatten_seeds(data.topics, prefix if data.strip_common_prefix else None)
    if area["area_id"] is None:
        known: dict = {}
    else:
        known, _by_id = await _import_state(session, area["area_id"])
    result = _classify(flat, known, update_existing=data.update_existing)
    return {
        "area": {"id": area["area_id"], "title": area["title"], "exists": area["exists"]},
        "creates": result["creates"],
        "updates": result["updates"],
        "matches": result["matches"],
        "resources_new": result["resources_new"],
        "resources_duplicate": result["resources_duplicate"],
        "conflicts": result["conflicts"],
        "invalid": [],
        "suggested_prefix": prefix,
        "totals": {
            "nodes": len(flat),
            "depth": max((seed.depth for seed in flat), default=0),
            "creates": len(result["creates"]),
            "updates": len(result["updates"]),
            "matches": len(result["matches"]),
        },
    }


async def import_topics(session: AsyncSession, data) -> dict:
    """Konu agacini JSON'dan kurar/gunceller. ATOMIK: tek commit, hata -> rollback.

    `update_existing` eslesen konuda status/target_min/position, eslesen
    kaynakta url/kind/note/estimated_min tazeler. `prune` SILMEZ: agacta
    olmayan konu/kaynaklari arsivler ve sayisini dondurur.
    """
    counters = {
        "topics_created": 0,
        "topics_matched": 0,
        "topics_updated": 0,
        "resources_created": 0,
        "resources_skipped": 0,
        "resources_updated": 0,
        "topics_archived": 0,
        "resources_archived": 0,
    }
    try:
        area = await _resolve_import_area(session, data, create=True)
        area_id = area["area_id"]
        all_titles = [node.title for node in _flatten_seeds(data.topics, None)]
        prefix = _common_prefix(all_titles)
        flat = _flatten_seeds(data.topics, prefix if data.strip_common_prefix else None)
        known, by_id = await _import_state(session, area_id)
        visited: set[UUID] = set()
        created_ids: list[UUID | None] = [None] * len(flat)
        entries: list[dict | None] = [None] * len(flat)

        for index, seed in enumerate(flat):
            parent_id = created_ids[seed.parent] if seed.parent is not None else None
            entry = None
            if seed.parent is None or created_ids[seed.parent] is not None:
                entry = known.get((_norm(seed.title), parent_id))
            if entry is None:
                entity = await create_entity(
                    session,
                    type="study_topic",
                    title=seed.title,
                    search_text=_topic_search_text(seed.title),
                )
                session.add(
                    StudyTopic(
                        id=entity.id,
                        area_id=area_id,
                        parent_id=parent_id,
                        status=seed.status,
                        target_min=seed.target_min,
                        position=seed.position,
                    )
                )
                await session.flush()
                topic_id = entity.id
                entry = {
                    "id": topic_id,
                    "parent_id": parent_id,
                    "status": seed.status,
                    "target_min": seed.target_min,
                    "position": seed.position,
                    "title": seed.title,
                    "resources": {},
                    "resource_count": 0,
                }
                known[(_norm(seed.title), parent_id)] = entry
                by_id[topic_id] = entry
                counters["topics_created"] += 1
                await log_event(
                    session,
                    verb="study.topic_created",
                    entity_id=topic_id,
                    entity_type="study_topic",
                    payload={
                        "topic_id": str(topic_id),
                        "area_id": str(area_id),
                        "title": seed.title,
                    },
                )
            else:
                topic_id = entry["id"]
                counters["topics_matched"] += 1
                if data.update_existing:
                    changed = (
                        entry["status"] != seed.status
                        or entry["target_min"] != seed.target_min
                        or entry["position"] != seed.position
                    )
                    if changed:
                        topic = await session.get(StudyTopic, topic_id)
                        topic.status = seed.status
                        topic.target_min = seed.target_min
                        topic.position = seed.position
                        counters["topics_updated"] += 1
            created_ids[index] = topic_id
            entries[index] = entry
            visited.add(topic_id)
            position = entry["resource_count"]
            for resource in seed.node.resources:
                key = canonical_url(resource.url) or _norm(resource.title)
                current = entry["resources"].get(key) if entry is not None else None
                if current is not None:
                    counters["resources_skipped"] += 1
                    if data.update_existing:
                        item = await session.get(LearningResource, current["id"])
                        changed = (
                            (resource.url is not None and item.url != resource.url)
                            or item.kind != resource.kind
                            or (resource.note is not None and item.note != resource.note)
                            or (
                                resource.estimated_min is not None
                                and item.estimated_min != resource.estimated_min
                            )
                        )
                        if changed:
                            if resource.url is not None:
                                item.url = resource.url
                            item.kind = resource.kind
                            if resource.note is not None:
                                item.note = resource.note
                            if resource.estimated_min is not None:
                                item.estimated_min = resource.estimated_min
                            await touch_entity(
                                session,
                                item.id,
                                search_text=_resource_search_text(
                                    current["title"], item.url, item.note, item.kind
                                ),
                            )
                            counters["resources_updated"] += 1
                    continue
                entity = await create_entity(
                    session,
                    type=LearningResource.ENTITY_TYPE,
                    title=resource.title,
                    search_text=_resource_search_text(
                        resource.title, resource.url, resource.note, resource.kind
                    ),
                )
                session.add(
                    LearningResource(
                        id=entity.id,
                        topic_id=topic_id,
                        url=resource.url,
                        kind=resource.kind,
                        position=position,
                        note=resource.note,
                        estimated_min=resource.estimated_min,
                        source="import",
                    )
                )
                await link(session, topic_id, entity.id, "learns_from")
                position += 1
                counters["resources_created"] += 1
                if entry is not None:
                    entry["resources"][key] = {"id": entity.id, "title": resource.title}
                    entry["resource_count"] += 1

        if data.prune:
            for topic_id, entry in by_id.items():
                if topic_id in visited:
                    continue
                await archive_entity(session, topic_id)
                counters["topics_archived"] += 1
                for resource in entry["resources"].values():
                    if resource["id"] is None:
                        continue
                    await archive_entity(session, resource["id"])
                    counters["resources_archived"] += 1
            # Ziyaret edilen konularda agacta olmayan kaynaklar da arsivlenir.
            for seed_index, seed in enumerate(flat):
                topic_id = created_ids[seed_index]
                if topic_id is None:
                    continue
                entry = entries[seed_index]
                if entry is None:
                    continue
                wanted = {
                    canonical_url(resource.url) or _norm(resource.title)
                    for resource in seed.node.resources
                }
                for key, resource in entry["resources"].items():
                    if key in wanted or resource["id"] is None:
                        continue
                    await archive_entity(session, resource["id"])
                    counters["resources_archived"] += 1

        await log_event(
            session,
            verb="learning.imported",
            entity_id=area_id,
            entity_type="study_area",
            payload={
                "area_id": str(area_id),
                "area": area["title"],
                "area_id_created": not area["exists"],
                "update_existing": data.update_existing,
                "prune": data.prune,
                **counters,
            },
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return {"area_id": area_id, "area_title": area["title"], **counters}


__all__ = [
    "attach_bookmark",
    "canonical_url",
    "create_todo_for_topic",
    "review_topic",
    "topic_review_queue",
    "touch_topic_chain",
]
