from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import EntityBacked
from app.db import Base


class NoteFolder(EntityBacked, Base):
    """Obsidian benzeri, ic ice yerlesebilen not klasoru.

    Klasorler de entity-backed'tir: tasima/silme hareketleri event akimina
    girer, yedeklenir ve ileride graf/arama kapsamına güvenle alinabilir.
    """

    __tablename__ = "note_folder"
    __table_args__ = (
        CheckConstraint("parent_id is null or parent_id <> id", name="note_folder_no_self_ck"),
    )
    ENTITY_TYPE = "note_folder"

    id: Mapped[uuid.UUID] = EntityBacked._entity_pk()
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("note_folder.id", ondelete="SET NULL"), nullable=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


class Note(EntityBacked, Base):
    """Yerel hizli not (Faz 21). PK entity.id'ye FK (kural 1).

    Baslik Entity.title'da yasar (body'den turetilir); arsivleme/silme
    Entity yasam dongusunden gelir. Not govdesi Markdown'dir; ekler ayni
    yerel/yedeklenebilir kaydin parcasidir.
    """

    __tablename__ = "note"
    __table_args__ = (
        CheckConstraint(
            "project_id is null or journal_day is not null",
            name="note_project_journal_day_ck",
        ),
        CheckConstraint(
            "default_view in ('page', 'canvas')",
            name="note_default_view_ck",
        ),
        UniqueConstraint(
            "project_id", "journal_day", name="note_project_journal_day_uniq"
        ),
    )
    ENTITY_TYPE = "note"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE"), primary_key=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("project.id", ondelete="SET NULL"), nullable=True
    )
    folder_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("note_folder.id", ondelete="SET NULL"), nullable=True
    )
    journal_day: Mapped[date | None] = mapped_column(Date, nullable=True)
    trashed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    trashed_from_archive: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    source_bookmark_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("bookmark.id", ondelete="SET NULL"), nullable=True
    )
    #: Notun yerel fotograf/ses/Excalidraw ekleri. Icerik base64 olarak ayni satirda
    #: tutulur; boylece mevcut JSON yedek/geri-yukleme akisi ekleri de tasir.
    #:
    #: ESKI temsil: icerik artik `NoteAttachment` satirinda ve dosya sisteminde
    #: yasar. Bu kolon donusum tamamlanana kadar okunur (bkz. service.py).
    attachments: Mapped[list[dict]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    #: Excalidraw sahnesi ayni entity-backed notta yasar. Markdown ile tuval
    #: birbirinden kopuk iki belge degil, ayni notun iki gorunumudur.
    canvas_state: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    default_view: Mapped[str] = mapped_column(
        Text, nullable=False, default="page", server_default="page"
    )


class NoteAttachment(Base):
    """Not ekinin METADATA'si (1:N destek tablosu).

    Kural 1 istisnasi: ek bagimsiz aranabilir/linklenebilir bir nesne degil,
    tek bir notu olcen destek satiridir (`bookmark_highlight`, `plan_slot` ile
    ayni sinif). `id` bilincli olarak eski JSONB kaydinin id'sini KORUR; boylece
    indirme URL'leri (`/notes/{note}/attachments/{id}`) donusumden sonra da
    ayni kalir.

    Binary ICERIK burada degil: `data/attachments/<sha256>` altinda durur.
    Dosya adi yalnizca `sha256`'dan turetilir -- istemciden gelen `name`
    hicbir zaman yol olarak kullanilmaz.
    """

    __tablename__ = "note_attachment"
    __table_args__ = (Index("ix_note_attachment_note_id", "note_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    note_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("note.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    mime: Mapped[str] = mapped_column(String(128), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    #: Icerigin sha256'si; dosya adi da budur (content-addressed, dedup'li).
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
