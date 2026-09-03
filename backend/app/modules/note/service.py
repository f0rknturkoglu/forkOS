from __future__ import annotations

import base64
import binascii
import re
import uuid
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from app.core import refs as ref_svc
from app.core import tags as tag_svc
from app.core.entity import archive_entity, create_entity, delete_entity, touch_entity
from app.core.events import log_event
from app.core.links import link
from app.core.models import Entity, Link
from app.modules.note.models import Note
from app.modules.note.schemas import NoteIn, NoteOut, NoteUpdate

#: Body'den turetilen baslik siniri -- liste satirlarinda tasmaz.
MAX_TITLE = 60
MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024
ALLOWED_ATTACHMENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "audio/webm",
    "audio/ogg",
    "audio/mpeg",
    "audio/mp4",
    "audio/wav",
    "audio/x-wav",
    "audio/x-m4a",
}


#: Baslik satirindaki markdown isaretleri -- listede ham gorunmesinler.
_MARKDOWN_PREFIX = re.compile(r"^\s*(?:#{1,6}\s+|[-*+]\s+(?:\[[ xX]\]\s+)?|\d{1,3}[.)]\s+|>\s?)")
_MARKDOWN_EMPHASIS = re.compile(r"(\*\*|__|~~|[*_`])")


def derive_title(body: str) -> str:
    """Kullanici baslik vermedi; body'den guvenli kisa baslik turet.

    Ilk anlamli satir, markdown isaretleri temizlenmis, 60 karakterde
    kirpilir. "# Baslik" listede "# Baslik" diye gorunmemeli -- notlar artik
    markdown (Faz 35). Bos cikarsa "Not".
    """
    for raw in (body or "").splitlines():
        line = _MARKDOWN_PREFIX.sub("", raw)
        line = _MARKDOWN_EMPHASIS.sub("", line)
        collapsed = re.sub(r"\s+", " ", line).strip()
        if collapsed:
            return collapsed[:MAX_TITLE].rstrip() or "Not"
    return "Not"


def _out(
    note: Note,
    title: str,
    created_at,
    updated_at,
    tags: list[str] | None = None,
    unresolved: list[str] | None = None,
    links: list[dict] | None = None,
    attachments: list[dict] | None = None,
) -> NoteOut:
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
        tags=tags or [],
        unresolved_links=unresolved or [],
        resolved_links=links or [],
        attachments=[
            _attachment_out(note.id, item)
            for item in (attachments if attachments is not None else (note.attachments or []))
        ],
    )


def _attachment_out(note_id: uuid.UUID, item: dict) -> dict:
    return {
        "id": item["id"],
        "name": item["name"],
        "mime": item["mime"],
        "size": item["size"],
        "url": f"/api/notes/{note_id}/attachments/{item['id']}",
    }


async def _attachments_metadata(
    session: AsyncSession, note_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[dict]]:
    """Notlarin ek METADATA'sini (veri olmadan) tek sorguda toplar.

    JSONB icindeki base64 `data` alani listeleme icin gereksiz; dosya icerigi
    yalnizca /attachments/{id} indirme ucunda decode edilir. Bos liste donerse
    bos sozluk (ek sorgu atilmaz).
    """
    if not note_ids:
        return {}
    rows = (
        await session.execute(
            sa_text(
                """
                select n.id,
                  coalesce((
                    select jsonb_agg(jsonb_build_object(
                      'id', a->>'id', 'name', a->>'name',
                      'mime', a->>'mime', 'size', (a->>'size')::int
                    ))
                    from jsonb_array_elements(n.attachments) a
                  ), '[]'::jsonb) as meta
                from note n
                where n.id = any(:ids)
                """
            ),
            {"ids": note_ids},
        )
    ).all()
    return {row.id: list(row.meta) for row in rows}


def prepare_attachment(filename: str | None, mime: str | None, content: bytes) -> dict:
    """Yuklenen eki dogrula ve yedeklenebilir JSON nesnesine cevir."""
    content_type = (mime or "").split(";", 1)[0].lower().strip()
    if content_type not in ALLOWED_ATTACHMENT_TYPES:
        raise ValueError("yalnızca fotoğraf ve ses dosyaları destekleniyor")
    if not content:
        raise ValueError("boş dosya yüklenemez")
    if len(content) > MAX_ATTACHMENT_BYTES:
        raise ValueError("ek boyutu 25 MB sınırını aşıyor")
    safe_name = Path(filename or "ek").name.strip()[:180] or "ek"
    return {
        "id": str(uuid.uuid4()),
        "name": safe_name,
        "mime": content_type,
        "size": len(content),
        "data": base64.b64encode(content).decode("ascii"),
    }


async def add_attachment(
    session: AsyncSession,
    note_id: uuid.UUID,
    *,
    filename: str | None,
    mime: str | None,
    content: bytes,
) -> dict | None:
    note = await session.get(Note, note_id)
    if note is None:
        return None
    item = prepare_attachment(filename, mime, content)
    note.attachments = [*(note.attachments or []), item]
    await touch_entity(session, note_id)
    await log_event(
        session,
        verb="note.attachment_added",
        entity_id=note_id,
        entity_type="note",
        payload={"attachment_id": item["id"], "mime": item["mime"], "size": item["size"]},
    )
    await session.commit()
    return _attachment_out(note_id, item)


async def attachment_content(
    session: AsyncSession, note_id: uuid.UUID, attachment_id: uuid.UUID
) -> tuple[bytes, str, str] | None:
    note = await session.get(Note, note_id)
    if note is None:
        return None
    item = next(
        (row for row in (note.attachments or []) if row.get("id") == str(attachment_id)),
        None,
    )
    if item is None:
        return None
    try:
        content = base64.b64decode(item["data"], validate=True)
    except (KeyError, ValueError, binascii.Error):
        return None
    return content, item["mime"], item["name"]


async def delete_attachment(
    session: AsyncSession, note_id: uuid.UUID, attachment_id: uuid.UUID
) -> bool:
    note = await session.get(Note, note_id)
    if note is None:
        return False
    before = note.attachments or []
    after = [row for row in before if row.get("id") != str(attachment_id)]
    if len(after) == len(before):
        return False
    note.attachments = after
    await touch_entity(session, note_id)
    await log_event(
        session,
        verb="note.attachment_deleted",
        entity_id=note_id,
        entity_type="note",
        payload={"attachment_id": str(attachment_id)},
    )
    await session.commit()
    return True


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
    # Govdedeki [[wikilink]] ve #etiketler ayni transaction'da yazilir.
    await session.flush()
    synced = await ref_svc.sync_refs(session, note.id, data.body, extra_tags=data.tags)
    await log_event(session, verb="note.created", entity_id=note.id, entity_type="note",
                    payload={"pinned": data.pinned,
                             "relate_to": str(data.relate_to) if data.relate_to else None,
                             "project_id": str(project_id) if project_id else None,
                             "journal_day": journal_day.isoformat() if journal_day else None})
    await session.commit()
    return _out(note, entity.title, entity.created_at, entity.updated_at,
                synced["tags"], synced["unresolved"], synced["links"])


async def list_notes(
    session: AsyncSession,
    *,
    include_archived: bool = False,
    about: uuid.UUID | None = None,
) -> list[NoteOut]:
    """`about` verilirse yalnizca o kayda `notes_about` ile bagli notlar.

    Bagli notlari cagiran tarafta tek tek cekmek yerine tek sorgu -- konu
    detayi acilirken N+1 olmasin.
    """
    # attachments JSONB'i (base64 veri icerir) listelemede YUKLEME -- boyutu
    # 25MB'a cikabilen veriyi RAM'e tasiyip atmak yerine yalnizca metadata
    # SQL'de cikarilir. Detay cagrisi (get) tam satiri yukler, orasi yeter.
    stmt = (
        select(Note, Entity.title, Entity.created_at, Entity.updated_at)
        .join(Entity, Entity.id == Note.id)
        .options(defer(Note.attachments))
        .order_by(Note.pinned.desc(), Entity.updated_at.desc())
    )
    if about is not None:
        stmt = stmt.join(Link, Link.from_id == Note.id).where(
            Link.to_id == about, Link.relation == "notes_about"
        )
    if not include_archived:
        stmt = stmt.where(Entity.archived_at.is_(None))
    rows = (await session.execute(stmt)).all()
    note_ids = [note.id for note, _, _, _ in rows]
    tags = await tag_svc.tags_for(session, note_ids)
    per_note = {note.id: ref_svc.parse_wikilinks(note.body) for note, _, _, _ in rows}
    resolved = await ref_svc.resolve_titles(
        session, list({t for targets in per_note.values() for t in targets})
    )
    attachments_by_note = await _attachments_metadata(session, note_ids)
    out: list[NoteOut] = []
    for note, title, created, updated in rows:
        targets = per_note[note.id]
        out.append(
            _out(
                note, title, created, updated, tags.get(note.id, []),
                [t for t in targets if t not in resolved],
                [
                    {"target": t, "id": resolved[t][0], "type": resolved[t][1]}
                    for t in targets
                    if t in resolved
                ],
                attachments=attachments_by_note.get(note.id),
            )
        )
    return out


async def get(session: AsyncSession, note_id: uuid.UUID) -> NoteOut | None:
    row = (await session.execute(
        select(Note, Entity.title, Entity.created_at, Entity.updated_at)
        .join(Entity, Entity.id == Note.id)
        .where(Note.id == note_id)
    )).first()
    if row is None:
        return None
    note = row[0]
    tags = (await tag_svc.tags_for(session, [note_id])).get(note_id, [])
    targets = ref_svc.parse_wikilinks(note.body)
    resolved = await ref_svc.resolve_titles(session, targets)
    return _out(
        note, row[1], row[2], row[3], tags,
        [t for t in targets if t not in resolved],
        [
            {"target": t, "id": resolved[t][0], "type": resolved[t][1]}
            for t in targets
            if t in resolved
        ],
    )


async def update(session: AsyncSession, note_id: uuid.UUID, data: NoteUpdate) -> NoteOut | None:
    note = await session.get(Note, note_id)
    if note is None:
        return None
    entity = await session.get(Entity, note_id)
    values = data.model_dump(exclude_unset=True)
    old_body = note.body
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
    # Govde ya da elle etiket degistiyse baglar/etiketler yeniden turetilir.
    synced = None
    if body_changed or "tags" in values:
        extra = values.get("tags")
        if extra is None:
            # Yalnizca govde degisti: elle eklenmis (ESKI govdede gecmeyen)
            # etiketler korunur; govdeden silinen #etiket ise gercekten gider.
            current = (await tag_svc.tags_for(session, [note_id])).get(note_id, [])
            was_inline = {t.casefold() for t in ref_svc.parse_tags(old_body)}
            extra = [t for t in current if t.casefold() not in was_inline]
        synced = await ref_svc.sync_refs(session, note_id, note.body, extra_tags=extra)
    await session.commit()
    if entity is not None:
        # touch_entity updated_at'i SQL ifadesiyle atar; flush sonrasi expire
        # olur, senkron erisim async'te patlar. Async refresh ile yukle.
        await session.refresh(entity)
    title = entity.title if entity else derive_title(note.body)
    if synced is None:
        tags = (await tag_svc.tags_for(session, [note_id])).get(note_id, [])
        return _out(note, title, entity.created_at if entity else None,
                    entity.updated_at if entity else None, tags)
    return _out(note, title, entity.created_at if entity else None,
                entity.updated_at if entity else None,
                synced["tags"], synced["unresolved"], synced["links"])


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
