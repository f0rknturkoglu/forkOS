"""H7 — Durable Decision & Bounded Execution kalıcı durumu.

Üç tablo, tek amaç: **onaylanan tam revizyonun**, **H1 üzerinden**, **yarıda
kesilse bile doğru devam eden** biçimde yürütülmesi.

Bu tablolar `source_run`/`proactivity_run` ile AYNI SINIFTIR: ajan/iş akışı
operasyonel durumu — bağımsız aranabilir/linklenebilir nesne DEĞİL (kural 1'in
belgelenmiş istisnası; H7 görev tanımı bu kalıcılığı açıkça onaylar).

Tasarım kararı: **bir satır = bir IMMUTABLE plan revizyonu**. Aynı `plan_id`
altındaki satırlar bir soy ağacıdır; `revision`, plan içeriğinin kanonik
özetidir (bkz. `revision.py`). Onay HER ZAMAN bir revizyona bağlanır; bu yüzden
onaydan sonra plan değişirse eski onay "stale" olur ve yürütme reddedilir.

Saklanmayanlar (bilinçli): tam model konuşma dökümü, ham istem/yanıt, sınırsız
kanıt gövdesi. Plan gerekçesi ve kanıt referansları sınırlıdır.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base

# ---------------------------------------------------------------------------
# Durum makinesi
# ---------------------------------------------------------------------------

#: Plan yasam dongusu. `state.py` bu kumenin DISINA cikilmasina izin vermez.
#: NOT: doğrulama AYRI bir plan durumu DEĞİLDİR — satır yazılmadan ÖNCE
#: çalışır ve sonucu denetim izine (`validated` / `validation_failed`) düşer.
#: Böylece "tanımlı ama hiç üretilmeyen durum" oluşmaz (§57 ayrımı korunur:
#: doğrulama ile karar ayrı adımlardır).
PLAN_STATES: tuple[str, ...] = (
    "draft",
    "input_required",
    "awaiting_approval",
    "approved",
    "executing",
    "completed",
    "partial",
    "failed",
    "rejected",
    "cancelled",
    "expired",
)

#: Terminal durumlar: artik yuritme baslatilamaz.
TERMINAL_PLAN_STATES: frozenset[str] = frozenset(
    {"completed", "partial", "failed", "rejected", "cancelled", "expired"}
)

#: Kullanicinin kararini bekleyen durumlar (karar yuzeyi bunlari gosterir).
DECISION_REQUIRED_STATES: frozenset[str] = frozenset(
    {"awaiting_approval", "input_required"}
)

#: Dogrulama sonucu. Gecersiz plan KAYDEDILMEZ; bu yuzden yalnizca iki deger
#: kalici plan satirinda gorulur.
VALIDATION_STATUSES: tuple[str, ...] = ("valid", "input_required")

#: Karar kaydi turleri (append-only denetim izi).
DECISION_KINDS: tuple[str, ...] = (
    "created",
    "validated",
    "validation_failed",
    "input_requested",
    "input_supplied",
    "revision_created",
    "approved",
    "rejected",
    "cancelled",
    "expired",
    "execution_started",
    "execution_recovered",
    "step_completed",
    "step_failed",
    "execution_finished",
    "execution_blocked",
)

#: Adim sonucu. Iki "yapilmadi" hali AYRI degerdir:
#:   not_attempted → hic denenmedi (onceki adim dustu; GUVENLE surdurulebilir)
#:   unresolved    → denenmis OLABILIR, sonuc bilinmiyor (MUTABAKAT gerekir;
#:                   ayrim `error_code=RECONCILIATION_REQUIRED` ile de tasinir)
STEP_STATUSES: tuple[str, ...] = ("completed", "failed", "not_attempted", "unresolved")

#: Yurutucu lease'i: bu kadar saniye kalp atisi gelmezse sahiplik BAYAT sayilir
#: ve atomik olarak devralinabilir. Sure, tek bir adimin makul ust sinirindan
#: buyuk secildi (Vault yazmalari dâhil).
EXECUTOR_STALE_AFTER_SECONDS = 120
#: Kalp atisi adim sinirlarinda yazilir (ekstra zamanlayici YOK).
EXECUTOR_HEARTBEAT_INTERVAL_SECONDS = 30

#: Plan sonucu (yuritme bittiginde). `cancelled` yalnizca yurutme baslamadan
#: kapatilan planlar icin terminal durumdur.
FINAL_STATUSES: tuple[str, ...] = ("completed", "partial", "failed", "cancelled")

#: Onay verilebilir azami plan yasi (saat). Sinirsiz plan YOKTUR.
DEFAULT_PLAN_TTL_HOURS = 72

# ---------------------------------------------------------------------------
# Sinirlar (§13/§64) — sınırsız yürütme yasak
# ---------------------------------------------------------------------------

MAX_PLAN_STEPS = 10
MAX_PLAN_MUTATIONS = 10
MAX_PLAN_TITLE = 160
MAX_PLAN_SUMMARY = 400
MAX_PLAN_REASON = 600
MAX_STEP_DESCRIPTION = 240
MAX_ARGUMENT_BYTES = 8192
MAX_SOURCE_REFS = 20
MAX_EVIDENCE_REFS = 20
MAX_VALIDATION_ERRORS = 10
MAX_RECEIPT_DETAIL = 400
MAX_LIST_LIMIT = 50
MAX_INPUT_QUESTIONS = 3
MAX_INPUT_ANSWER = 1000


class ExecutionPlan(Base):
    """Tek bir IMMUTABLE plan revizyonu + karar/yürütme durumu.

    `plan_id` soy ağacıdır; `revision` içeriğin deterministik özetidir.
    Aynı `plan_id` için yeni revizyon yeni satırdır: eski onay tarih olarak
    korunur, "hangi versiyonu onaylamıştım?" sorusu cevaplanabilir kalır.
    """

    __tablename__ = "execution_plan"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    #: Soy ağacı kimliği: aynı planın revizyonları bu değeri paylaşır.
    plan_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    #: İçerik özeti (`plan-v1:<sha256>`). Onay bu değere bağlanır.
    revision: Mapped[str] = mapped_column(String(80), nullable=False)
    #: Bu revizyon hangi revizyonu GEÇERSİZ kıldı (varsa).
    supersedes_revision: Mapped[str | None] = mapped_column(String(80))
    state: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")

    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    #: "Neden bu plan var?" — olgusal, sınırlı; serbest model anlatısı DEĞİL.
    reason: Mapped[str | None] = mapped_column(Text)

    #: Kapalı H1 action sözlüğünden adımlar (bkz. `steps.py`).
    steps: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    step_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mutation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    budget: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    #: Kanıt soyu: H3/H5/H6 referansları (sınırlı liste).
    source_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    evidence_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    #: Dogrulama sonucu: hangi referans GERCEKTEN dogrulandi, hangisi yalnizca
    #: sozdizimi olarak kabul edildi (H7 onu cozemez).
    verified_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    unresolved_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    validation_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    validation_errors: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    #: `input_required` durumunda kullaniciya sorulacak SINIRLI sorular.
    input_questions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    input_answers: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    #: Sunucu tarafi onay kaydi: model bu alanlari URETEMEZ (§6/§38).
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_revision: Mapped[str | None] = mapped_column(String(80))
    decided_by: Mapped[str | None] = mapped_column(String(32))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    #: Yurutme sahipligi (DB-destekli CAS ile alinir; §22).
    execution_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    execution_finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    executor_token: Mapped[str | None] = mapped_column(String(64))
    #: Canli yurutucu izi. Bayatlarsa sahiplik devralinabilir (kurtarma).
    execution_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    final_status: Mapped[str | None] = mapped_column(String(16))
    failure_code: Mapped[str | None] = mapped_column(String(48))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ExecutionReceipt(Base):
    """Adim basina TEK durable makbuz (append-only, idempotans çapası).

    `(plan_row_id, step_id)` UNIQUE'tir: aynı adım restart sonrası İKİNCİ kez
    körlemesine yürütülmez; makbuz varsa adım "yapıldı" kabul edilir.
    """

    __tablename__ = "execution_receipt"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    plan_row_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("execution_plan.id", ondelete="CASCADE"), nullable=False
    )
    step_id: Mapped[str] = mapped_column(String(48), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(48), nullable=False)
    target: Mapped[str | None] = mapped_column(Text)
    #: Adim icin deterministik yurutme kimligi (plan + revizyon + step).
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(48))
    #: H1 sonucundan gelen SINIRLI referans (or. entity id) — tam govde DEGIL.
    result_ref: Mapped[str | None] = mapped_column(Text)
    detail: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    #: Devam eden bir adimin sahibi (crash sonrasi mutabakat icin).
    claimed_by: Mapped[str | None] = mapped_column(String(64))


class ExecutionDecision(Base):
    """Append-only karar/yürütme denetim izi (§36)."""

    __tablename__ = "execution_decision"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    plan_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    plan_row_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("execution_plan.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    revision: Mapped[str | None] = mapped_column(String(80))
    #: Sinirli ayrinti: kod/step id/sayilar. Serbest metin govdesi DEGIL.
    detail: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    actor: Mapped[str] = mapped_column(String(32), nullable=False, default="system")
    #: Aktif plan revizyonu mu (denetim listesinde isaretlemek icin).
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
