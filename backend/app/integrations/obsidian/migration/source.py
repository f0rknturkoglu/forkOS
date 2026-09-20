"""forkOS notlarinin SALT-OKUNUR anlik goruntusu ve kaynak parmak izi.

Migration bu modulun dondurdugu veriyi geri YAZMAZ. Oturum
`REPEATABLE READ, READ ONLY` transaction icinde acilir (PHASE 9): kaynak
veritabani migration boyunca tek bir tutarli snapshot olarak okunur ve
yanlislikla yazma girisimi PostgreSQL tarafindan reddedilir.

Parmak izi (`source_fingerprint`) migration'in kaynagi degistirmedigini
kanitlayan sozlesmedir: once/sonra ayni cikmak ZORUNDADIR.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import tags as tag_service
from app.core.models import Entity, Link
from app.core.refs import parse_wikilinks, resolve_titles
from app.db import SessionLocal
from app.modules.bookmark.models import Bookmark
from app.modules.note import storage as attachment_storage
from app.modules.note.models import Note, NoteAttachment, NoteFolder
from app.modules.project.models import Project

#: Legacy JSONB eki ile yeni `note_attachment` satiri ayni id'yi tasiyabilir.
BLOB_GENERATION = "blob"
LEGACY_GENERATION = "legacy"


class AttachmentUnavailable(Exception):
    """Ek icerigi okunamadi (eksik blob, bozuk base64, tutmayan ozet/boyut)."""


@dataclass(frozen=True)
class SourceAttachment:
    """Bir not ekini iki depolama kusagindan da temsil eder."""

    attachment_id: str
    name: str
    mime: str
    size: int
    generation: str
    #: Yalnizca `blob` kusagi: icerigin sha256'si (dosya adi da budur).
    sha256: str | None = None
    #: Yalnizca `legacy` kusagi: `note.attachments` JSONB girdisinin AYNISI.
    legacy_raw: dict[str, Any] | None = None


@dataclass(frozen=True)
class SourceRelation:
    relation: str
    target_id: uuid.UUID
    target_type: str
    target_title: str


@dataclass(frozen=True)
class SourceNote:
    note_id: uuid.UUID
    title: str
    body: str
    pinned: bool
    project_id: uuid.UUID | None
    folder_id: uuid.UUID | None
    journal_day: date | None
    source_bookmark_id: uuid.UUID | None
    trashed_at: datetime | None
    trashed_from_archive: bool
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None
    canvas_state: dict[str, Any]
    default_view: str
    attachments: tuple[SourceAttachment, ...] = ()
    tags: tuple[str, ...] = ()
    relations: tuple[SourceRelation, ...] = ()

    @property
    def state(self) -> str:
        """`trashed` arsivden baskindir (PHASE 2)."""
        if self.trashed_at is not None:
            return "trashed"
        if self.archived_at is not None:
            return "archived"
        return "active"

    @property
    def body_sha256(self) -> str:
        return hashlib.sha256((self.body or "").encode("utf-8")).hexdigest()

    @property
    def has_canvas(self) -> bool:
        return bool(self.canvas_state)


@dataclass(frozen=True)
class SourceFolder:
    folder_id: uuid.UUID
    title: str
    parent_id: uuid.UUID | None
    position: int


@dataclass(frozen=True)
class SourceBookmark:
    bookmark_id: uuid.UUID
    url: str
    title: str


@dataclass
class SourceSnapshot:
    notes: tuple[SourceNote, ...]
    folders: dict[uuid.UUID, SourceFolder]
    projects: dict[uuid.UUID, str]
    bookmarks: dict[uuid.UUID, SourceBookmark]
    #: Govdedeki wikilink metni -> (entity id, entity tipi). `core/refs.py`
    #: cozumlemesi (arsivliler haric, ayni baslikta son guncellenen kazanir).
    title_resolution: dict[str, tuple[uuid.UUID, str]] = field(default_factory=dict)
    fingerprint: str = ""

    @property
    def notes_by_id(self) -> dict[uuid.UUID, SourceNote]:
        return {note.note_id: note for note in self.notes}


@asynccontextmanager
async def read_only_session() -> AsyncIterator[AsyncSession]:
    """Tutarli snapshot veren salt-okunur transaction (PHASE 9).

    `SET TRANSACTION` transaction'in ILK komutudur; sonrasinda her yazma
    girisimi `ReadOnlySqlTransaction` ile reddedilir.
    """
    async with SessionLocal() as session:
        await session.execute(
            text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        )
        try:
            yield session
        finally:
            await session.rollback()


def read_attachment_bytes(attachment: SourceAttachment) -> bytes:
    """Ekin GERCEK baytlarini dondur; okunamiyorsa `AttachmentUnavailable`."""
    if attachment.generation == BLOB_GENERATION:
        if not attachment.sha256:
            raise AttachmentUnavailable("blob ozeti eksik")
        data = attachment_storage.read_blob(attachment.sha256)
        if data is None:
            raise AttachmentUnavailable(f"blob bulunamadi: {attachment.sha256[:12]}")
        actual = hashlib.sha256(data).hexdigest()
        if actual != attachment.sha256:
            raise AttachmentUnavailable("blob icerigi sha256 ile tutmuyor")
        if attachment.size and len(data) != attachment.size:
            raise AttachmentUnavailable(
                f"blob boyutu tutmuyor: {len(data)} != {attachment.size}"
            )
        return data

    raw = attachment.legacy_raw or {}
    encoded = raw.get("data")
    if not isinstance(encoded, str) or not encoded:
        raise AttachmentUnavailable("legacy ek verisi (base64) yok")
    try:
        data = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise AttachmentUnavailable("legacy base64 cozulemedi") from exc
    if attachment.size and len(data) != attachment.size:
        raise AttachmentUnavailable(
            f"legacy ek boyutu tutmuyor: {len(data)} != {attachment.size}"
        )
    return data


def _dedupe_attachments(
    legacy: list[SourceAttachment], stored: list[SourceAttachment]
) -> tuple[SourceAttachment, ...]:
    """Ayni id iki kusakta varsa YENI kusak (blob) kazanir; sira korunur."""
    order: list[str] = []
    by_id: dict[str, SourceAttachment] = {}
    for item in legacy:
        if item.attachment_id not in by_id:
            order.append(item.attachment_id)
        by_id[item.attachment_id] = item
    for item in stored:
        if item.attachment_id not in by_id:
            order.append(item.attachment_id)
        by_id[item.attachment_id] = item
    return tuple(by_id[aid] for aid in order)


def _legacy_attachment(item: Any) -> SourceAttachment | None:
    if not isinstance(item, dict):
        return None
    raw_id = str(item.get("id") or "").strip()
    if not raw_id:
        return None
    try:
        size = int(item.get("size") or 0)
    except (TypeError, ValueError):
        size = 0
    return SourceAttachment(
        attachment_id=raw_id,
        name=str(item.get("name") or "ek"),
        mime=str(item.get("mime") or "application/octet-stream"),
        size=size,
        generation=LEGACY_GENERATION,
        legacy_raw=dict(item),
    )


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _fingerprint_line(parts: list[Any]) -> str:
    return _canonical(parts)


def source_fingerprint(snapshot: SourceSnapshot) -> str:
    """Migration ile ilgili TUM kaynak verinin deterministik ozeti (PHASE 23)."""
    digest = hashlib.sha256()
    for note in sorted(snapshot.notes, key=lambda n: str(n.note_id)):
        digest.update(
            _fingerprint_line(
                [
                    "note",
                    str(note.note_id),
                    note.title,
                    note.body_sha256,
                    len(note.body or ""),
                    note.state,
                    note.pinned,
                    str(note.project_id) if note.project_id else None,
                    str(note.folder_id) if note.folder_id else None,
                    note.journal_day.isoformat() if note.journal_day else None,
                    str(note.source_bookmark_id) if note.source_bookmark_id else None,
                    note.trashed_from_archive,
                    note.created_at.isoformat() if note.created_at else None,
                    note.updated_at.isoformat() if note.updated_at else None,
                    note.archived_at.isoformat() if note.archived_at else None,
                    note.default_view,
                    _canonical(note.canvas_state or {}),
                ]
            ).encode()
        )
        for attachment in sorted(note.attachments, key=lambda a: a.attachment_id):
            digest.update(
                _fingerprint_line(
                    [
                        "attachment",
                        str(note.note_id),
                        attachment.attachment_id,
                        attachment.name,
                        attachment.mime,
                        attachment.size,
                        attachment.generation,
                        attachment.sha256,
                        _canonical(attachment.legacy_raw) if attachment.legacy_raw else None,
                    ]
                ).encode()
            )
        for tag in sorted(note.tags, key=str.casefold):
            digest.update(_fingerprint_line(["tag", str(note.note_id), tag]).encode())
        for relation in sorted(
            note.relations, key=lambda r: (r.relation, str(r.target_id))
        ):
            digest.update(
                _fingerprint_line(
                    ["link", str(note.note_id), relation.relation, str(relation.target_id)]
                ).encode()
            )
    for folder in sorted(snapshot.folders.values(), key=lambda f: str(f.folder_id)):
        digest.update(
            _fingerprint_line(
                [
                    "folder",
                    str(folder.folder_id),
                    folder.title,
                    str(folder.parent_id) if folder.parent_id else None,
                    folder.position,
                ]
            ).encode()
        )
    return f"sha256:{digest.hexdigest()}"


async def load_snapshot(session: AsyncSession) -> SourceSnapshot:
    """Kaynak notlari, klasorleri, ekleri, etiketleri ve iliskileri oku."""
    note_rows = (
        await session.execute(
            select(
                Note,
                Entity.title,
                Entity.created_at,
                Entity.updated_at,
                Entity.archived_at,
            )
            .join(Entity, Entity.id == Note.id)
            .order_by(Note.id)
        )
    ).all()

    note_ids = [note.id for note, *_ in note_rows]

    project_titles = {
        row[0]: row[1]
        for row in (
            await session.execute(
                select(Project.id, Entity.title).join(Entity, Entity.id == Project.id)
            )
        ).all()
    }

    folders = {
        row[0]: SourceFolder(folder_id=row[0], title=row[1] or "", parent_id=row[2], position=row[3])
        for row in (
            await session.execute(
                select(NoteFolder.id, Entity.title, NoteFolder.parent_id, NoteFolder.position)
                .join(Entity, Entity.id == NoteFolder.id)
                .order_by(NoteFolder.position, Entity.title)
            )
        ).all()
    }

    stored_attachments: dict[uuid.UUID, list[SourceAttachment]] = {}
    if note_ids:
        for row in (
            await session.execute(
                select(NoteAttachment).where(NoteAttachment.note_id.in_(note_ids))
            )
        ).scalars():
            stored_attachments.setdefault(row.note_id, []).append(
                SourceAttachment(
                    attachment_id=str(row.id),
                    name=row.name,
                    mime=row.mime,
                    size=row.size,
                    generation=BLOB_GENERATION,
                    sha256=row.sha256,
                )
            )

        tag_map = await tag_service.tags_for(session, note_ids)

        relation_map: dict[uuid.UUID, list[SourceRelation]] = {}
        for from_id, relation, to_id, to_type, to_title in (
            await session.execute(
                select(Link.from_id, Link.relation, Link.to_id, Entity.type, Entity.title)
                .join(Entity, Entity.id == Link.to_id)
                .where(Link.from_id.in_(note_ids))
                .order_by(Link.from_id, Link.relation, Link.to_id)
            )
        ).all():
            relation_map.setdefault(from_id, []).append(
                SourceRelation(
                    relation=relation,
                    target_id=to_id,
                    target_type=to_type,
                    target_title=to_title or "",
                )
            )
    else:
        tag_map, relation_map = {}, {}

    bookmark_ids = {n.source_bookmark_id for n, *_ in note_rows if n.source_bookmark_id}
    bookmarks: dict[uuid.UUID, SourceBookmark] = {}
    if bookmark_ids:
        for row in (
            await session.execute(
                select(Bookmark.id, Bookmark.url, Entity.title)
                .join(Entity, Entity.id == Bookmark.id)
                .where(Bookmark.id.in_(bookmark_ids))
            )
        ).all():
            bookmarks[row[0]] = SourceBookmark(
                bookmark_id=row[0], url=row[1] or "", title=row[2] or ""
            )

    notes: list[SourceNote] = []
    for note, title, created_at, updated_at, archived_at in note_rows:
        legacy = [
            item
            for item in (_legacy_attachment(entry) for entry in (note.attachments or []))
            if item is not None
        ]
        notes.append(
            SourceNote(
                note_id=note.id,
                title=title or "",
                body=note.body or "",
                pinned=bool(note.pinned),
                project_id=note.project_id,
                folder_id=note.folder_id,
                journal_day=note.journal_day,
                source_bookmark_id=note.source_bookmark_id,
                trashed_at=note.trashed_at,
                trashed_from_archive=bool(note.trashed_from_archive),
                created_at=created_at,
                updated_at=updated_at,
                archived_at=archived_at,
                canvas_state=note.canvas_state or {},
                default_view=note.default_view,
                attachments=_dedupe_attachments(
                    legacy, stored_attachments.get(note.id, [])
                ),
                tags=tuple(tag_map.get(note.id, [])),
                relations=tuple(relation_map.get(note.id, [])),
            )
        )

    snapshot = SourceSnapshot(
        notes=tuple(notes),
        folders=folders,
        projects=project_titles,
        bookmarks=bookmarks,
    )
    snapshot.title_resolution = await _resolve_wikilink_titles(session, notes)
    snapshot.fingerprint = source_fingerprint(snapshot)
    return snapshot


async def _resolve_wikilink_titles(
    session: AsyncSession, notes: list[SourceNote]
) -> dict[str, tuple[uuid.UUID, str]]:
    """Tum not govdelerindeki wikilink hedeflerini TEK sorguda cozer."""
    targets: dict[str, None] = {}
    for note in notes:
        for target in parse_wikilinks(note.body):
            targets.setdefault(target, None)
    if not targets:
        return {}
    return await resolve_titles(session, list(targets))
