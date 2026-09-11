from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import EntityBacked
from app.db import Base


class Course(EntityBacked, Base):
    __tablename__ = "course"
    ENTITY_TYPE = "course"
    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE"), primary_key=True
    )
    platform: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="planned")
    progress_pct: Mapped[int] = mapped_column(SmallInteger, default=0)
    started_at: Mapped[date | None] = mapped_column(Date)
    completed_at: Mapped[date | None] = mapped_column(Date)
    certificate_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="SET NULL")
    )
    notes: Mapped[str | None] = mapped_column(Text)

class StudyArea(EntityBacked, Base):
    __tablename__ = "study_area"
    ENTITY_TYPE = "study_area"
    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE"), primary_key=True
    )
    color: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    position: Mapped[int] = mapped_column(Integer, default=0)


class StudyTopic(EntityBacked, Base):
    __tablename__ = "study_topic"
    ENTITY_TYPE = "study_topic"
    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE"), primary_key=True
    )
    area_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("study_area.id", ondelete="CASCADE")
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("study_topic.id", ondelete="CASCADE")
    )
    status: Mapped[str] = mapped_column(Text, default="not_started")
    confidence: Mapped[int | None] = mapped_column(SmallInteger)
    target_min: Mapped[int | None] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(Integer, default=0)
    last_studied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    #: Kullanici beyani (1-100). "Tamamlandi" demek DEGIL: ne kadar oturdugunu
    #: kullanici soyler, kaynak ilerlemesi ayri alanlardan turer (tek yuzde yok).
    mastery: Mapped[int | None] = mapped_column(SmallInteger)
    #: SRS (bkz. review.py). `next_review_at` null ise konu tekrar kuyrugunda degil.
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ease: Mapped[float] = mapped_column(Float, nullable=False, default=2.5)
    review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LearningResource(EntityBacked, Base):
    """Bir konunun altindaki ogrenme materyali (URL, video, kitap bolumu...).

    Tamamlanma isareti `completed_at`; konunun ilerleme yuzdesi bu satirlardan
    (alt konular dahil) hesaplanir -- ayri bir yuzde kolonu TUTULMAZ ki
    kaynaklarla ilerleme birbirinden kaymasin.

    `bookmark_id` doluysa kaynak bir yer imine baglidir: baslik/url KOPYALANMAZ,
    okuma yolunda bookmark'tan taze okunur (yer imi degisince gosterim bayatlamaz).
    """

    __tablename__ = "learning_resource"
    ENTITY_TYPE = "learning_resource"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE"), primary_key=True
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("study_topic.id", ondelete="CASCADE")
    )
    url: Mapped[str | None] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text, default="link")
    position: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(Text)
    #: Yer iminden gelen kaynak (source='bookmark'); silinirse bag kopar, kaynak kalir.
    bookmark_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("bookmark.id", ondelete="SET NULL")
    )
    #: Kurs kaynagi ise bagli kurs (source='import'/'manual').
    course_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("course.id", ondelete="SET NULL")
    )
    source: Mapped[str] = mapped_column(Text, nullable=False, default="manual")
    estimated_min: Mapped[int | None] = mapped_column(Integer)
    last_opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
