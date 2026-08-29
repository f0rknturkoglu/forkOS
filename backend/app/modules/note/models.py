from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Text
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
    ENTITY_TYPE = "note"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE"), primary_key=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
