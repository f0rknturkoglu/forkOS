from __future__ import annotations

import re
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity import archive_entity, create_entity, delete_entity, touch_entity
from app.core.events import log_event
from app.core.links import link
from app.core.models import Entity
from app.modules.note.models import Note
from app.modules.note.schemas import NoteIn, NoteOut, NoteUpdate

#: Body'den turetilen baslik siniri -- liste satirlarinda tasmaz.
MAX_TITLE = 60


def derive_title(body: str) -> str:
    """Kullanici baslik vermedi; body'den guvenli kisa baslik turet.

    Ilk satir, fazla bosluklar silinmis, 60 karakterde kirpilir. Bos
    cikarsa "Not" -- liste hicbir zaman bos baslik gostermez.
    """
    first = body.strip().splitlines()[0] if body.strip() else ""
    collapsed = re.sub(r"\s+", " ", first).strip()
    if not collapsed:
        return "Not"
    return collapsed[:MAX_TITLE].rstrip() or "Not"


def _out(note: Note, title: str, created_at, updated_at) -> NoteOut:
    # created/updated Entity'de yasar (modul tablosunda kolon yok).
    return NoteOut(
        id=note.id,
        title=title,
        body=note.body,
        pinned=note.pinned,
        project_id=note.project_id,
        journal_day=note.journal_day,
        created_at=created_at,
        updated_at=updated_at,
    )


async def create(
    session: AsyncSession,
    data: NoteIn,
    *,
    project_id: uuid.UUID | None = None,
    journal_day: date | None = None,
) -> NoteOut:
    if (project_id is None) != (journal_day is None):
        raise ValueError("proje gunlugu icin project_id ve journal_day birlikte gerekli")
    entity = await create_entity(session, type=Note.ENTITY_TYPE,
                                 title=derive_title(data.body), search_text=data.body)
    note = Note(
        id=entity.id,
        body=data.body,
        pinned=data.pinned,
        project_id=project_id,
        journal_day=journal_day,
    )
    session.add(note)
    if data.relate_to is not None:
        # Ayni transaction: iliski kurulamazsa not da olusmaz (Faz 29).
        target = await session.get(Entity, data.relate_to)
        if target is None:
            raise ValueError("iliskilendirilecek kayit bulunamadi")
        await link(session, note.id, data.relate_to, "notes_about")
    await log_event(session, verb="note.created", entity_id=note.id, entity_type="note",
                    payload={"pinned": data.pinned,
                             "relate_to": str(data.relate_to) if data.relate_to else None,
                             "project_id": str(project_id) if project_id else None,
                             "journal_day": journal_day.isoformat() if journal_day else None})
    await session.commit()
    return _out(note, entity.title, entity.created_at, entity.updated_at)


async def list_notes(session: AsyncSession, *, include_archived: bool = False) -> list[NoteOut]:
    stmt = (
        select(Note, Entity.title, Entity.created_at, Entity.updated_at)
        .join(Entity, Entity.id == Note.id)
        .order_by(Note.pinned.desc(), Entity.updated_at.desc())
    )
    if not include_archived:
        stmt = stmt.where(Entity.archived_at.is_(None))
    rows = (await session.execute(stmt)).all()
    return [_out(note, title, created, updated) for note, title, created, updated in rows]


async def get(session: AsyncSession, note_id: uuid.UUID) -> NoteOut | None:
    row = (await session.execute(
        select(Note, Entity.title, Entity.created_at, Entity.updated_at)
        .join(Entity, Entity.id == Note.id)
        .where(Note.id == note_id)
    )).first()
    if row is None:
        return None
    return _out(row[0], row[1], row[2], row[3])


async def update(session: AsyncSession, note_id: uuid.UUID, data: NoteUpdate) -> NoteOut | None:
    note = await session.get(Note, note_id)
    if note is None:
        return None
    entity = await session.get(Entity, note_id)
    values = data.model_dump(exclude_unset=True)
    body_changed = "body" in values and values["body"] != note.body
    pinned_changed = "pinned" in values and values["pinned"] != note.pinned
    if body_changed:
        note.body = values["body"]
        await touch_entity(session, note_id, title=derive_title(note.body),
                           search_text=note.body)
    if pinned_changed:
        note.pinned = values["pinned"]
        await log_event(session, verb="note.pinned", entity_id=note_id,
                        entity_type="note", payload={"pinned": note.pinned})
    if body_changed:
        # Faz 34: body + pinned ayni PATCH'te degisse IKI event de yazilir;
        # hicbiri degismediyse hicbir event uretilmez.
        changed = [field for field in ("body",) if field in values]
        await log_event(session, verb="note.updated", entity_id=note_id,
                        entity_type="note", payload={
                            "changed_fields": changed,
                            "project_id": str(note.project_id) if note.project_id else None,
                            "journal_day": (
                                note.journal_day.isoformat() if note.journal_day else None
                            ),
                        })
    await session.commit()
    if entity is not None:
        # touch_entity updated_at'i SQL ifadesiyle atar; flush sonrasi expire
        # olur, senkron erisim async'te patlar. Async refresh ile yukle.
        await session.refresh(entity)
    title = entity.title if entity else derive_title(note.body)
    return _out(note, title, entity.created_at if entity else None,
                entity.updated_at if entity else None)


async def archive(session: AsyncSession, note_id: uuid.UUID) -> bool:
    if await session.get(Note, note_id) is None:
        return False
    await archive_entity(session, note_id)
    await log_event(session, verb="note.archived", entity_id=note_id,
                    entity_type="note", payload={})
    await session.commit()
    return True


async def delete(session: AsyncSession, note_id: uuid.UUID) -> bool:
    entity = await session.get(Entity, note_id)
    if entity is None or entity.type != Note.ENTITY_TYPE:
        return False
    title = entity.title
    note = await session.get(Note, note_id)
    project_id = note.project_id if note else None
    journal_day = note.journal_day if note else None
    if not await delete_entity(session, note_id):
        return False
    await log_event(session, verb="note.deleted", entity_type="note",
                    payload={
                        "title": title,
                        "project_id": str(project_id) if project_id else None,
                        "journal_day": journal_day.isoformat() if journal_day else None,
                    })
    await session.commit()
    return True
