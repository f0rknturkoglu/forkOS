from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import EntityBacked
from app.db import Base


class Document(EntityBacked, Base):
    __tablename__ = "document"
    ENTITY_TYPE = "document"
    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE"), primary_key=True
    )
    drive_file_id: Mapped[str] = mapped_column(Text, unique=True)
    folder_id: Mapped[str | None] = mapped_column(Text)
    mime: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)
    web_view_link: Mapped[str | None] = mapped_column(Text)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    drive_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
