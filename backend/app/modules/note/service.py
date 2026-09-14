from __future__ import annotations

import base64
import binascii
import json
import re
import uuid
from datetime import date
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy import text as sa_text
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from app.core import refs as ref_svc
from app.core import tags as tag_svc
from app.core.entity import (
    archive_entity,
    create_entity,
    delete_entity,
    restore_entity,
    touch_entity,
)
from app.core.events import log_event
from app.core.links import link
from app.core.models import Entity, Link
from app.modules.note.models import Note, NoteFolder
from app.modules.note.schemas import (
    NoteFolderIn,
    NoteFolderOut,
    NoteFolderUpdate,
    NoteIn,
    NoteOut,
    NoteUpdate,
)

#: Body'den turetilen baslik siniri -- liste satirlarinda tasmaz.
MAX_TITLE = 60
MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024
EXCALIDRAW_MIME = "application/vnd.excalidraw+json"
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
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "application/pdf",
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/zip",
    "application/x-zip-compressed",
    "application/vnd.oasis.opendocument.text",
    "application/vnd.oasis.opendocument.spreadsheet",
    "application/vnd.oasis.opendocument.presentation",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/octet-stream",
    EXCALIDRAW_MIME,
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
    archived_at=None,
    tags: list[str] | None = None,
    unresolved: list[str] | None = None,
    links: list[dict] | None = None,
    attachments: list[dict] | None = None,
    canvas_state: dict | None = None,
) -> NoteOut:
    # created/updated Entity'de yasar (modul tablosunda kolon yok).
    return NoteOut(
        id=note.id,
        title=title,
        body=note.body,
        pinned=note.pinned,
        project_id=note.project_id,
        folder_id=note.folder_id,
        journal_day=note.journal_day,
        archived_at=archived_at,
        trashed_at=note.trashed_at,
        source_bookmark_id=note.source_bookmark_id,
        created_at=created_at,
        updated_at=updated_at,
        tags=tags or [],
        unresolved_links=unresolved or [],
        resolved_links=links or [],
        attachments=[
            _attachment_out(note.id, item)
            for item in (attachments if attachments is not None else (note.attachments or []))
        ],
        canvas_state=(canvas_state if canvas_state is not None else (note.canvas_state or {})),
        default_view=note.default_view,
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
    safe_name = Path(filename or "ek").name.strip()[:180] or "ek"
    content_type = (mime or "").split(";", 1)[0].lower().strip()
    is_drawing = Path(safe_name).suffix.lower() == ".excalidraw"
    if is_drawing:
        try:
            drawing = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("geçerli bir Excalidraw dosyası seçin") from exc
        if not isinstance(drawing, dict) or drawing.get("type") != "excalidraw" or not isinstance(drawing.get("elements"), list):
            raise ValueError("geçerli bir Excalidraw dosyası seçin")
        content_type = EXCALIDRAW_MIME
    if content_type not in ALLOWED_ATTACHMENT_TYPES:
        raise ValueError(
            "bu dosya türü desteklenmiyor; görsel, ses, video, PDF, metin, "
            "ofis belgesi, zip veya Excalidraw seçin"
        )
    if not content:
        raise ValueError("boş dosya yüklenemez")
    if len(content) > MAX_ATTACHMENT_BYTES:
        raise ValueError("ek boyutu 25 MB sınırını aşıyor")
    return {
        "id": str(uuid.uuid4()),
        "name": safe_name,
        "mime": content_type,
        "size": len(content),
        "data": base64.b64encode(content).decode("ascii"),
    }


async def _folder_exists(session: AsyncSession, folder_id: uuid.UUID | None) -> bool:
    return folder_id is None or await session.get(NoteFolder, folder_id) is not None


async def _assert_valid_parent(
    session: AsyncSession,
    *,
    folder_id: uuid.UUID | None,
    parent_id: uuid.UUID | None,
) -> None:
    if parent_id is None:
        return
    if folder_id == parent_id:
        raise ValueError("klasör kendi içine taşınamaz")
    if await session.get(NoteFolder, parent_id) is None:
        raise ValueError("üst klasör bulunamadı")
    current = parent_id
    visited: set[uuid.UUID] = set()
    while current is not None and current not in visited:
        if current == folder_id:
            raise ValueError("klasör kendi alt klasörüne taşınamaz")
        visited.add(current)
        parent = await session.get(NoteFolder, current)
        current = parent.parent_id if parent else None


async def list_folders(session: AsyncSession) -> list[NoteFolderOut]:
    counts = (
        select(Note.folder_id, func.count(Note.id).label("note_count"))
        .where(Note.folder_id.is_not(None))
        .group_by(Note.folder_id)
        .subquery()
    )
    rows = (
        await session.execute(
            select(
                NoteFolder,
                Entity.title,
                Entity.created_at,
                Entity.updated_at,
                func.coalesce(counts.c.note_count, 0),
            )
            .join(Entity, Entity.id == NoteFolder.id)
            .outerjoin(counts, counts.c.folder_id == NoteFolder.id)
            .where(Entity.archived_at.is_(None))
            .order_by(NoteFolder.position, Entity.title)
        )
    ).all()
    return [
        NoteFolderOut(
            id=folder.id,
            name=title,
            parent_id=folder.parent_id,
            position=folder.position,
            note_count=note_count,
            created_at=created_at,
            updated_at=updated_at,
        )
        for folder, title, created_at, updated_at, note_count in rows
    ]


async def create_folder(session: AsyncSession, data: NoteFolderIn) -> NoteFolderOut:
    name = data.name.strip()
    if not name:
        raise ValueError("klasör adı boş olamaz")
    await _assert_valid_parent(session, folder_id=None, parent_id=data.parent_id)
    max_position = (
        await session.execute(
            select(func.coalesce(func.max(NoteFolder.position), -1)).where(
                NoteFolder.parent_id == data.parent_id
            )
        )
    ).scalar_one()
    entity = await create_entity(
        session, type=NoteFolder.ENTITY_TYPE, title=name, search_text=name
    )
    folder = NoteFolder(
        id=entity.id, parent_id=data.parent_id, position=int(max_position) + 1
    )
    session.add(folder)
    await log_event(
        session,
        verb="note.folder_created",
        entity_id=folder.id,
        entity_type=NoteFolder.ENTITY_TYPE,
        payload={"parent_id": str(data.parent_id) if data.parent_id else None},
    )
    await session.commit()
    return NoteFolderOut(
        id=folder.id,
        name=name,
        parent_id=folder.parent_id,
        position=folder.position,
        note_count=0,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


async def update_folder(
    session: AsyncSession, folder_id: uuid.UUID, data: NoteFolderUpdate
) -> NoteFolderOut | None:
    folder = await session.get(NoteFolder, folder_id)
    entity = await session.get(Entity, folder_id)
    if folder is None or entity is None:
        return None
    values = data.model_dump(exclude_unset=True)
    if "parent_id" in values:
        await _assert_valid_parent(
            session, folder_id=folder_id, parent_id=values["parent_id"]
        )
        folder.parent_id = values["parent_id"]
    if "position" in values and values["position"] is not None:
        folder.position = values["position"]
    if "name" in values and values["name"] is not None:
        name = values["name"].strip()
        if not name:
            raise ValueError("klasör adı boş olamaz")
        await touch_entity(session, folder_id, title=name, search_text=name)
    else:
        await touch_entity(session, folder_id)
    await log_event(
        session,
        verb="note.folder_updated",
        entity_id=folder_id,
        entity_type=NoteFolder.ENTITY_TYPE,
        payload={"changed_fields": sorted(values)},
    )
    await session.commit()
    await session.refresh(entity)
    count = (
        await session.execute(
            select(func.count(Note.id)).where(Note.folder_id == folder_id)
        )
    ).scalar_one()
    return NoteFolderOut(
        id=folder.id,
        name=entity.title,
        parent_id=folder.parent_id,
        position=folder.position,
        note_count=count,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


async def delete_folder(session: AsyncSession, folder_id: uuid.UUID) -> bool:
    folder = await session.get(NoteFolder, folder_id)
    entity = await session.get(Entity, folder_id)
    if folder is None or entity is None:
        return False
    title = entity.title
    # Alt klasorleri ve notlari silmek yerine bir ust seviyeye tasir.
    await session.execute(
        sql_update(NoteFolder)
        .where(NoteFolder.parent_id == folder_id)
        .values(parent_id=folder.parent_id)
    )
    await session.execute(
        sql_update(Note).where(Note.folder_id == folder_id).values(folder_id=None)
    )
    await log_event(
        session,
        verb="note.folder_deleted",
        entity_id=folder_id,
        entity_type=NoteFolder.ENTITY_TYPE,
        payload={"title": title},
    )
    await delete_entity(session, folder_id)
    await session.commit()
    return True


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
    source_bookmark_id: uuid.UUID | None = None,
) -> NoteOut:
    if project_id is not None and journal_day is None:
        raise ValueError("proje gunlugu icin journal_day gerekli")
    if not await _folder_exists(session, data.folder_id):
        raise ValueError("not klasörü bulunamadı")
    entity = await create_entity(session, type=Note.ENTITY_TYPE,
                                 title=derive_title(data.body), search_text=data.body)
    note = Note(
        id=entity.id,
        body=data.body,
        pinned=data.pinned,
        project_id=project_id,
        folder_id=data.folder_id,
        journal_day=journal_day,
        source_bookmark_id=source_bookmark_id,
        canvas_state=data.canvas_state,
        default_view=data.default_view,
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
                             "folder_id": str(data.folder_id) if data.folder_id else None,
                             "journal_day": journal_day.isoformat() if journal_day else None,
                             "source_bookmark_id": str(source_bookmark_id) if source_bookmark_id else None})
    await session.commit()
    return _out(note, entity.title, entity.created_at, entity.updated_at, entity.archived_at,
                synced["tags"], synced["unresolved"], synced["links"])


async def list_notes(
    session: AsyncSession,
    *,
    include_archived: bool = False,
    about: uuid.UUID | None = None,
    scope: str = "active",
) -> list[NoteOut]:
    """`about` verilirse yalnizca o kayda `notes_about` ile bagli notlar.

    Bagli notlari cagiran tarafta tek tek cekmek yerine tek sorgu -- konu
    detayi acilirken N+1 olmasin.
    """
    # Buyuk JSONB alanlarini listelemede YUKLEME. Ek metadata'si ayri SQL ile
    # gelir; tuval ise secili notun detay cagrisi ile yuklenir.
    stmt = (
        select(Note, Entity.title, Entity.created_at, Entity.updated_at, Entity.archived_at)
        .join(Entity, Entity.id == Note.id)
        .options(defer(Note.attachments), defer(Note.canvas_state))
        .order_by(Note.pinned.desc(), Entity.updated_at.desc())
    )
    if about is not None:
        stmt = stmt.join(Link, Link.from_id == Note.id).where(
            Link.to_id == about, Link.relation == "notes_about"
        )
    if scope == "trash":
        stmt = stmt.where(Note.trashed_at.is_not(None))
    elif scope == "archive":
        stmt = stmt.where(Note.trashed_at.is_(None), Entity.archived_at.is_not(None))
    elif include_archived:
        stmt = stmt.where(Note.trashed_at.is_(None))
    else:
        stmt = stmt.where(Note.trashed_at.is_(None), Entity.archived_at.is_(None))
    rows = (await session.execute(stmt)).all()
    note_ids = [note.id for note, _, _, _, _ in rows]
    tags = await tag_svc.tags_for(session, note_ids)
    per_note = {note.id: ref_svc.parse_wikilinks(note.body) for note, _, _, _, _ in rows}
    resolved = await ref_svc.resolve_titles(
        session, list({t for targets in per_note.values() for t in targets})
    )
    attachments_by_note = await _attachments_metadata(session, note_ids)
    out: list[NoteOut] = []
    for note, title, created, updated, archived_at in rows:
        targets = per_note[note.id]
        out.append(
            _out(
                note, title, created, updated, archived_at, tags.get(note.id, []),
                [t for t in targets if t not in resolved],
                [
                    {"target": t, "id": resolved[t][0], "type": resolved[t][1]}
                    for t in targets
                    if t in resolved
                ],
                attachments=attachments_by_note.get(note.id),
                canvas_state={},
            )
        )
    return out


async def get(session: AsyncSession, note_id: uuid.UUID) -> NoteOut | None:
    row = (await session.execute(
        select(Note, Entity.title, Entity.created_at, Entity.updated_at, Entity.archived_at)
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
        note, row[1], row[2], row[3], row[4], tags,
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
    canvas_changed = "canvas_state" in values and values["canvas_state"] is not None and values["canvas_state"] != note.canvas_state
    view_changed = "default_view" in values and values["default_view"] is not None and values["default_view"] != note.default_view
    folder_changed = "folder_id" in values and values["folder_id"] != note.folder_id
    if body_changed:
        note.body = values["body"]
        await touch_entity(session, note_id, title=derive_title(note.body),
                           search_text=note.body)
    if pinned_changed:
        note.pinned = values["pinned"]
        await log_event(session, verb="note.pinned", entity_id=note_id,
                        entity_type="note", payload={"pinned": note.pinned})
    if canvas_changed:
        note.canvas_state = values["canvas_state"]
    if view_changed:
        note.default_view = values["default_view"]
    if folder_changed:
        if not await _folder_exists(session, values["folder_id"]):
            raise ValueError("not klasörü bulunamadı")
        previous_folder = note.folder_id
        note.folder_id = values["folder_id"]
        await log_event(
            session,
            verb="note.moved",
            entity_id=note_id,
            entity_type="note",
            payload={
                "from_folder_id": str(previous_folder) if previous_folder else None,
                "to_folder_id": str(note.folder_id) if note.folder_id else None,
            },
        )
    content_changed = body_changed or canvas_changed or view_changed or folder_changed or "tags" in values
    if content_changed and not body_changed:
        await touch_entity(session, note_id)
    if content_changed:
        # Markdown, tuval ve gorunum tercihleri ayni not guncellemesidir.
        changed = [
            field
            for field, changed_now in (
                ("body", body_changed),
                ("canvas_state", canvas_changed),
                ("default_view", view_changed),
                ("folder_id", folder_changed),
                ("tags", "tags" in values),
            )
            if changed_now
        ]
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
                    entity.updated_at if entity else None,
                    entity.archived_at if entity else None, tags)
    return _out(note, title, entity.created_at if entity else None,
                entity.updated_at if entity else None,
                entity.archived_at if entity else None,
                synced["tags"], synced["unresolved"], synced["links"])


async def archive(session: AsyncSession, note_id: uuid.UUID) -> bool:
    note = await session.get(Note, note_id)
    if note is None or note.trashed_at is not None:
        return False
    await archive_entity(session, note_id)
    await log_event(session, verb="note.archived", entity_id=note_id,
                    entity_type="note", payload={})
    await session.commit()
    return True


async def delete(session: AsyncSession, note_id: uuid.UUID) -> bool:
    """Notu geri alinabilir cop kutusuna tasir."""
    note = await session.get(Note, note_id)
    entity = await session.get(Entity, note_id)
    if note is None or entity is None or entity.type != Note.ENTITY_TYPE:
        return False
    if note.trashed_at is not None:
        return True
    note.trashed_from_archive = entity.archived_at is not None
    note.trashed_at = func.now()
    await archive_entity(session, note_id)
    await log_event(session, verb="note.trashed", entity_id=note_id,
                    entity_type="note", payload={"title": entity.title})
    await session.commit()
    return True


async def restore_from_trash(session: AsyncSession, note_id: uuid.UUID) -> bool:
    note = await session.get(Note, note_id)
    if note is None or note.trashed_at is None:
        return False
    return_to_archive = note.trashed_from_archive
    note.trashed_at = None
    note.trashed_from_archive = False
    if return_to_archive:
        await touch_entity(session, note_id)
    else:
        await restore_entity(session, note_id)
    await log_event(session, verb="note.restored", entity_id=note_id,
                    entity_type="note", payload={
                        "from": "trash",
                        "to": "archive" if return_to_archive else "active",
                    })
    await session.commit()
    return True


async def restore_archive(session: AsyncSession, note_id: uuid.UUID) -> bool:
    note = await session.get(Note, note_id)
    entity = await session.get(Entity, note_id)
    if note is None or entity is None or note.trashed_at is not None or entity.archived_at is None:
        return False
    await restore_entity(session, note_id)
    await log_event(session, verb="note.archive_restored", entity_id=note_id,
                    entity_type="note", payload={})
    await session.commit()
    return True


async def permanently_delete(
    session: AsyncSession, note_id: uuid.UUID, *, allow_active: bool = False
) -> bool:
    entity = await session.get(Entity, note_id)
    note = await session.get(Note, note_id)
    if (
        entity is None
        or entity.type != Note.ENTITY_TYPE
        or note is None
        or (note.trashed_at is None and not allow_active)
    ):
        return False
    title = entity.title
    project_id = note.project_id
    journal_day = note.journal_day
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


async def ensure_daily_note(session: AsyncSession, journal_day: date) -> NoteOut:
    row = (await session.execute(
        select(Note, Entity.title, Entity.created_at, Entity.updated_at, Entity.archived_at)
        .join(Entity, Entity.id == Note.id)
        .where(Note.project_id.is_(None), Note.journal_day == journal_day)
    )).first()
    if row is not None:
        note, title, created_at, updated_at, archived_at = row
        if note.trashed_at is not None:
            note.trashed_at = None
            await restore_entity(session, note.id)
            await log_event(session, verb="note.restored", entity_id=note.id,
                            entity_type="note", payload={"from": "daily_ensure"})
            await session.commit()
            entity = await session.get(Entity, note.id)
            archived_at = entity.archived_at if entity else None
        elif archived_at is not None:
            await restore_entity(session, note.id)
            await log_event(session, verb="note.archive_restored", entity_id=note.id,
                            entity_type="note", payload={"from": "daily_ensure"})
            await session.commit()
            entity = await session.get(Entity, note.id)
            archived_at = entity.archived_at if entity else None
        tags = (await tag_svc.tags_for(session, [note.id])).get(note.id, [])
        return _out(note, title, created_at, updated_at, archived_at, tags)
    return await create(
        session,
        NoteIn(body=f"# {journal_day.isoformat()}\n\n## Bugünün odağı\n\n## Görevler\n\n## Notlar\n"),
        journal_day=journal_day,
    )
