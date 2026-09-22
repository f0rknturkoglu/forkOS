"""Yalnızca kimliği özetlenmiş, içeriksiz agent oturum metadata'sı.

Bu tablolar source_run gibi operasyonel destek kayıtlarıdır: bağımsız aranabilir
veya linklenebilir entity değildir. Kullanıcının A1 sözleşmesi bu iki tabloyu
ve ham kimlik yerine hash saklanmasını açıkça tanımlar.
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AgentSession(Base):
    __tablename__ = "agent_session"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    harness: Mapped[str] = mapped_column(String(16), nullable=False)
    session_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    platform: Mapped[str] = mapped_column(String(64), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    start_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    turn_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class AgentSessionTurn(Base):
    __tablename__ = "agent_session_turn"
    __table_args__ = (UniqueConstraint("session_id", "turn_key", name="uq_agent_session_turn_identity"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("agent_session.id", ondelete="CASCADE"), nullable=False)
    turn_key: Mapped[str] = mapped_column(String(64), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
