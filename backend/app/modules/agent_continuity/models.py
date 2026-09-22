"""A2: Ephemeral agent oturum bağlamı ve kaynak devamlılığı modelleri.

Bu tablolar source_run ve agent_session gibi operasyonel destek kayıtlarıdır:
bağımsız aranabilir veya linklenebilir entity değildir. Kanonik bilgi
f0rknbrain Vault'unda ve forkOS operasyonel tablolarında kalır; bu tablolar
yalnızca oturum içi bağlam bütçesini, tanılamaları ve teslim edilen kaynakların
devamlılığını takip eder.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AgentSessionContext(Base):
    """Enjekte edilen bağlamların özet metrikleri ve tanılamaları."""

    __tablename__ = "agent_session_context"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agent_session.id", ondelete="CASCADE"), nullable=False
    )
    turn_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agent_session_turn.id", ondelete="CASCADE"), nullable=True
    )
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_first_turn: Mapped[bool] = mapped_column(Boolean, nullable=False)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    omitted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    degraded_reasons: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    scope_project: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AgentSessionSource(Base):
    """Oturum içinde modele teslim edilen bounded kaynak referansları."""

    __tablename__ = "agent_session_source"
    __table_args__ = (
        UniqueConstraint("session_id", "source_id", name="uq_agent_session_source_identity"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agent_session.id", ondelete="CASCADE"), nullable=False
    )
    turn_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agent_session_turn.id", ondelete="CASCADE"), nullable=True
    )
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    scope_project: Mapped[str | None] = mapped_column(String(64), nullable=True)
    topic_signature: Mapped[str | None] = mapped_column(String(64), nullable=True)
    delivered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
