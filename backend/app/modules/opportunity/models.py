from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import EntityBacked
from app.db import Base


class Opportunity(EntityBacked, Base):
    __tablename__ = "opportunity"
    ENTITY_TYPE = "opportunity"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE"), primary_key=True
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(Text)
    organization: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    # Kesif / duyuru yasam dongusu. Izinli kume ture baglidir (lifecycle.py):
    # job -> discovered|shortlisted|dismissed|archived|closed
    # duyuru -> new|reviewed|watching|action_required|applied|completed|expired|archived
    # Basvuru hatti ARTIK BURADA TUTULMAZ; application.status'tadir.
    status: Mapped[str] = mapped_column(Text, default="discovered")
    priority: Mapped[int] = mapped_column(SmallInteger, default=2)
    found_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    location: Mapped[str | None] = mapped_column(Text)
    remote: Mapped[str | None] = mapped_column(Text)
    compensation: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text, default="manual")
    external_id: Mapped[str | None] = mapped_column(Text)
    raw: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    # Kanonik kural-tabanli uygunluk skoru: -1..100. -1 = elendi (kill kelimesi).
    # null = henuz hesaplanmadi. raw.forkjob.score aciklama/log icin korunur.
    score: Mapped[float | None] = mapped_column(Float)
    score_source: Mapped[str | None] = mapped_column(Text)
    score_computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    skill_match_ratio: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)
    trashed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trashed_from_status: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(Text)  # TR | EU | OTHER | UNKNOWN
    follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    # 0075 oncesi tek alan. Bilinmeyen eski bicimleri korur; yeni yazma YOK.
    legacy_evaluation: Mapped[dict[str, Any]] = mapped_column("evaluation", JSONB, default=dict)
    legacy_evaluated_at: Mapped[datetime | None] = mapped_column(
        "evaluated_at", DateTime(timezone=True)
    )
    candidate_evaluation: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    candidate_evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deep_evaluation: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    deep_evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # ── Kaynak gozlemi ve kapanma (job + duyuru) ───────────────────────
    # active | missing | likely_closed | closed
    source_status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    missing_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # ── Duyuruya ozel alanlar (job kayitlari bunlari kullanmaz) ────────
    official: Mapped[bool | None] = mapped_column(Boolean)
    # YLSY ana kilavuz -> universite/kurum kontenjani hiyerarsisi.
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("opportunity.id", ondelete="SET NULL")
    )
    stage: Mapped[str | None] = mapped_column(Text)
    application_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    application_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    exam_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    guide_url: Mapped[str | None] = mapped_column(Text)
    apply_url: Mapped[str | None] = mapped_column(Text)
    quota_total: Mapped[int | None] = mapped_column(Integer)
    fields: Mapped[list[str]] = mapped_column(JSONB, default=list)


class OpportunitySourceObservation(Base):
    """Bir ilanin kaynak bazli gozlemi.

    Destek tablosu: bagimsiz aranabilir/linklenebilir bir nesne degil, tek bir
    opportunity'yi kaynak karsisinda olcen satirdir. Bu yuzden PK'si entity.id'ye
    FK DEGILDIR (AGENTS.md kural 1 istisnasi; tests/test_migrations.py listesi).
    `opportunity.raw.forkjob` icindeki first_seen/last_seen tek kaynak icin
    yeterliydi; coklu kaynak birlestirmede kaynak bazli gorunurluk kayboluyordu.
    """

    __tablename__ = "opportunity_source_observation"
    __table_args__ = (
        UniqueConstraint("opportunity_id", "source", name="opportunity_source_observation_uniq"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("opportunity.id", ondelete="CASCADE")
    )
    source: Mapped[str] = mapped_column(Text, nullable=False)
    external_id: Mapped[str | None] = mapped_column(Text)
    canonical_url: Mapped[str | None] = mapped_column(Text)
    payload_hash: Mapped[str | None] = mapped_column(Text)
    # active | missing | likely_closed | closed
    source_status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_successful_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    enrichment: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class OpportunityRequirement(Base):
    __tablename__ = "opportunity_requirement"
    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("opportunity.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(Text)
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(Text, default="missing")
    document_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="SET NULL")
    )
    note: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, default=0)


class Application(EntityBacked, Base):
    """Basvuru kaydi (1:1). PK entity FK; snapshots basvuru anindaki hali saklar."""

    __tablename__ = "application"
    ENTITY_TYPE = "application"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE"), primary_key=True
    )
    cv_document_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="SET NULL")
    )
    cv_title: Mapped[str | None] = mapped_column(Text)
    cv_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cover_letter: Mapped[str | None] = mapped_column(Text)
    company_research: Mapped[str | None] = mapped_column(Text)
    salary_expectation: Mapped[str | None] = mapped_column(Text)
    posting_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    package: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    note: Mapped[str | None] = mapped_column(Text)
    # Basvuru hatti: preparing|applied|interview|offer|accepted|rejected|withdrawn|closed
    # Tek hakikat kaynagi lifecycle.APPLICATION_FLOW; kesif durumu (opportunity.status)
    # ile karistirilmaz.
    status: Mapped[str] = mapped_column(Text, nullable=False, default="applied")
    status_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ApplicationHistory(Base):
    """Durum gecis gecmisi — append-only (kural 3 ile birlikte)."""

    __tablename__ = "application_history"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("opportunity.id", ondelete="CASCADE")
    )
    from_status: Mapped[str | None] = mapped_column(Text)
    to_status: Mapped[str] = mapped_column(Text, nullable=False)
    #: 'discovery' (kesif/duyuru dongusu) | 'application' (basvuru hatti).
    scope: Mapped[str] = mapped_column(Text, nullable=False, default="application")
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    note: Mapped[str | None] = mapped_column(Text)


class Interview(Base):
    __tablename__ = "interview"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("opportunity.id", ondelete="CASCADE")
    )
    stage: Mapped[str] = mapped_column(Text, nullable=False, default="genel")
    mode: Mapped[str | None] = mapped_column(Text)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_min: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str | None] = mapped_column(Text)
    salary_stated: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, default=0)
    # Preparation/practice/debrief artifacts, not a second interview lifecycle.
    intelligence: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class CareerStory(EntityBacked, Base):
    """Mülakatta tekrar kullanılabilen, kaynak sınıflı STAR+R hikâyesi."""

    __tablename__ = "career_story"
    __table_args__ = (
        CheckConstraint(
            "provenance in ('existing', 'supported', 'derived-unverified', 'user-cannot-confirm')",
            name="ck_career_story_provenance",
        ),
    )
    ENTITY_TYPE = "career_story"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE"), primary_key=True
    )
    situation: Mapped[str | None] = mapped_column(Text)
    task: Mapped[str | None] = mapped_column(Text)
    action: Mapped[str | None] = mapped_column(Text)
    result: Mapped[str | None] = mapped_column(Text)
    reflection: Mapped[str | None] = mapped_column(Text)
    provenance: Mapped[str] = mapped_column(Text, nullable=False, default="existing")
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)


class CareerConnection(EntityBacked, Base):
    """LinkedIn disari aktarimindan gelen, tamamen yerel profesyonel baglanti."""

    __tablename__ = "career_connection"
    __table_args__ = (UniqueConstraint("identity_key", name="career_connection_identity_key_uniq"),)
    ENTITY_TYPE = "career_connection"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE"), primary_key=True
    )
    identity_key: Mapped[str] = mapped_column(Text, nullable=False)
    first_name: Mapped[str | None] = mapped_column(Text)
    last_name: Mapped[str | None] = mapped_column(Text)
    profile_url: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    company: Mapped[str | None] = mapped_column(Text)
    normalized_company: Mapped[str | None] = mapped_column(Text)
    position: Mapped[str | None] = mapped_column(Text)
    connected_on: Mapped[date | None] = mapped_column(Date)
