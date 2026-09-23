"""A3: sınırlı, kaynağa bağlanabilen EPİZODİK oturum devri destek tabloları.

Bu tablolar `source_run`, `agent_session` ve `agent_session_source` gibi
operasyonel destek kayıtlarıdır: bağımsız aranabilir veya linklenebilir entity
değildir. Kanonik bilgi f0rknbrain Vault'unda ve forkOS operasyonel
tablolarında kalır.

Epistemik sınır (A3 sözleşmesi §7): burada saklanan her satır
"önceki oturumda şöyle konuşuldu/sonuçlandı" anlamına gelen TARİHSEL bir
iddiadır. "Şu an doğru" anlamına GELMEZ; Todo, proje durumu, H2 hafızası,
Vault bilgisi veya H7 yetkilendirmesi değildir.

Ham transkript invariantı (§5): hiçbir tabloda ham `user_message`, ham
`assistant_response`, `conversation_history` veya tam transkript kolonu
YOKTUR ve olmayacaktır. Yalnız model tarafından türetilmiş, karakterle
sınırlı ifadeler ile bunların kökenini doğrulayan digest saklanır.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AgentSessionEpisode(Base):
    """Bir Hermes oturumunun mühürlenmiş epizodik devri (oturum başına tek satır)."""

    __tablename__ = "agent_session_episode"
    __table_args__ = (
        UniqueConstraint("session_id", name="uq_agent_session_episode_session"),
        CheckConstraint(
            "status in ('draft', 'sealed', 'sealed_degraded', 'sealed_empty')",
            name="ck_agent_session_episode_status",
        ),
        CheckConstraint(
            "turn_count >= 0 and item_count >= 0", name="ck_agent_session_episode_counts"
        ),
        CheckConstraint(
            "(status = 'draft') = (sealed_at is null)", name="ck_agent_session_episode_sealed_at"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agent_session.id", ondelete="CASCADE"), nullable=False
    )
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")
    scope_project: Mapped[str | None] = mapped_column(String(64))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sealed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    turn_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    degraded_reasons: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class AgentSessionEpisodeTurn(Base):
    """Gözlemlenen tek tur: köken digest'i ve o turda teslim edilen kaynak bağı.

    `delivered_refs` A3'ün KENDİ teslim defteridir: A2 kaynak tablosu yeniden
    teslimatta `turn_id`'yi ezdiği ve devamlılık yolunda hiç yazmadığı için
    "bu turda tam olarak hangi kaynak teslim edildi" sorusu oradan deterministik
    cevaplanamaz (§9). Defter yalnız A3'ün kendi tablosudur; A1/A2 tabloları
    salt okunur kullanılır.
    """

    __tablename__ = "agent_session_episode_turn"
    __table_args__ = (
        UniqueConstraint("episode_id", "turn_key", name="uq_agent_session_episode_turn_identity"),
        CheckConstraint(
            "status in ('pending', 'extracted', 'degraded')",
            name="ck_agent_session_episode_turn_status",
        ),
        CheckConstraint(
            "item_count >= 0 and item_count <= 6", name="ck_agent_session_episode_turn_items"
        ),
        CheckConstraint(
            "status <> 'extracted' or turn_digest is not null",
            name="ck_agent_session_episode_turn_digest",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    episode_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agent_session_episode.id", ondelete="CASCADE"), nullable=False
    )
    turn_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agent_session_turn.id", ondelete="CASCADE")
    )
    turn_key: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    turn_digest: Mapped[str | None] = mapped_column(String(64))
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delivered_refs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    degraded_reasons: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    delivered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    semantic_memory_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class AgentSessionEpisodeItem(Base):
    """Türetilmiş tek epizodik ifade.

    `text` model tarafından yeniden yazılmış sınırlı bir ifadedir; ham metin
    DEĞİLDİR. Doğrulamada kullanılan `source_excerpt` KALICI OLARAK SAKLANMAZ
    (§5/§6): yalnız istek belleğinde yaşar ve grounding kapısından geçmek için
    kullanılır.
    """

    __tablename__ = "agent_session_episode_item"
    __table_args__ = (
        CheckConstraint(
            "kind in ('topic', 'outcome', 'open_thread', 'session_decision', 'next_focus', 'reference')",
            name="ck_agent_session_episode_item_kind",
        ),
        CheckConstraint(
            "evidence_class in ('turn_derived', 'canonical_supported', 'observed_during_session')",
            name="ck_agent_session_episode_item_evidence",
        ),
        CheckConstraint("ordinal >= 0", name="ck_agent_session_episode_item_ordinal"),
        CheckConstraint(
            "char_length(text) between 1 and 300", name="ck_agent_session_episode_item_text"
        ),
        CheckConstraint(
            "(evidence_class in ('turn_derived', 'canonical_supported') and episode_turn_id is not null)"
            " or (evidence_class = 'observed_during_session' and episode_turn_id is null)",
            name="ck_agent_session_episode_item_turn_binding",
        ),
        # Kanonik gözlem KANIT taşımak zorundadır: H5'in `ReviewInsight` kilidi
        # gibi fail-closed. Ref'siz bir "gerçekleşti" iddiası uydurma olurdu.
        CheckConstraint(
            "evidence_class <> 'observed_during_session' or jsonb_array_length(support_refs) > 0",
            name="ck_agent_session_episode_item_observed_evidence",
        ),
        CheckConstraint(
            "evidence_class <> 'canonical_supported' or jsonb_array_length(support_refs) > 0",
            name="ck_agent_session_episode_item_canonical_evidence",
        ),
        CheckConstraint(
            "evidence_class <> 'turn_derived' or jsonb_array_length(support_refs) = 0",
            name="ck_agent_session_episode_item_turn_derived_evidence",
        ),
        CheckConstraint(
            "source_role is null or source_role in ('user', 'assistant', 'mixed')",
            name="ck_agent_session_episode_item_source_role",
        ),
        CheckConstraint(
            "evidence_digest is null or char_length(evidence_digest) = 64",
            name="ck_agent_session_episode_item_evidence_digest",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    episode_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agent_session_episode.id", ondelete="CASCADE"), nullable=False
    )
    episode_turn_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agent_session_episode_turn.id", ondelete="CASCADE")
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    text: Mapped[str] = mapped_column(String(300), nullable=False)
    evidence_class: Mapped[str] = mapped_column(String(32), nullable=False)
    support_refs: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    source_role: Mapped[str | None] = mapped_column(String(16))
    evidence_digest: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
