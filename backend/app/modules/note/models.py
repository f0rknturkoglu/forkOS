from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import EntityBacked
from app.db import Base


class Note(EntityBacked, Base):
    """Yerel hizli not (Faz 21). PK entity.id'ye FK (kural 1).

    Baslik Entity.title'da yasar (body'den turetilir); arsivleme/silme
    Entity yasam dongusunden gelir. Klasor agaci/WYSIWYG/attachment YOK --
    not minimal kalir.
    """

    __tablename__ = "note"
    __table_args__ = (
        CheckConstraint(
            "project_id is null or journal_day is not null",
            name="note_project_journal_day_ck",
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
    journal_day: Mapped[date | None] = mapped_column(Date, nullable=True)
    #: Notun yerel fotograf/ses ekleri. Icerik base64 olarak ayni satirda
    #: tutulur; boylece mevcut JSON yedek/geri-yukleme akisi ekleri de tasir.
    attachments: Mapped[list[dict]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
