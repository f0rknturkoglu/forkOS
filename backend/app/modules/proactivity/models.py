"""H6 proaktivite: kural konfigurasyonu ve kosu yasam dongusu.

Bu tablolar `source_run`/`source_sync_batch` ile AYNI SINIFTIR: bagimsiz
aranabilir/linklenebilir nesne DEGIL, motorun operasyonel kaydidir. Bu yuzden
PK'leri `entity.id`'ye FK degildir (kural 1'in belgelenmis istisnasi; H6
gorev tanimi bu kalici durumu acikca onaylar). Kullaniciya donuk kayit
`notification` tablosudur ve o zaten cekirdektedir.

Neden kalici? Idempotans, cooldown, snooze, ertelenmis teslim ve "neden simdi"
aciklamasi surecler arasi HAYATTA KALMALIDIR. Bellek ici durum worker yeniden
basladiginda kosuyu unutur ve ayni kosul ikinci kez duserdi.

Saklanmayanlar (bilincli): H5 paketleri, Vault alintilari, sicak hafiza
govdeleri, model istem/yanitlari. Kosu satiri yalnizca kosulu yeniden
cozmeye yetecek kadar yapisal kimlik tasir; kullaniciya giden metin teslim
aninda yeniden uretilir.
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
# Kural kimlikleri
# ---------------------------------------------------------------------------

#: Kapali kural kumesi (H6 v1). Genel bir kural DSL'i YOKTUR: yeni davranis
#: eklemek kod yazmak demektir, kullanici tanimli ifade degil.
RULE_KINDS: tuple[str, ...] = (
    "morning_continuity",
    "daily_close",
    "weekly_review",
    "deadline_staircase",
    "continuity_gap",
    "project_stalled",
)

#: Kural semantigi degistiginde artar; kosu gecmisi eski surumle okunabilir kalir.
RULE_VERSION = 1

#: Global kapsam anahtari. Entity kapsamli kuralda yerine entity id'si yazilir.
SCOPE_GLOBAL = "global"

# ---------------------------------------------------------------------------
# Kosu durum makinesi
# ---------------------------------------------------------------------------

#: Terminal durumlar: bu durumdaki kosu artik teslim edilmez.
TERMINAL_RUN_STATES: frozenset[str] = frozenset(
    {"resolved", "cancelled", "dismissed", "failed"}
)
#: Hala teslim edilebilecek (bekleyen) durumlar. Budama bunlara DOKUNMAZ.
ACTIVE_RUN_STATES: frozenset[str] = frozenset(
    {"candidate", "deferred", "digest_queued", "snoozed"}
)
#: Teslim edilmis kosular: tekrar teslim ancak yeni episode ile olur.
DELIVERED_RUN_STATES: frozenset[str] = frozenset({"delivered"})
RUN_STATES: frozenset[str] = (
    ACTIVE_RUN_STATES | DELIVERED_RUN_STATES | TERMINAL_RUN_STATES | {"suppressed"}
)


class ProactivityRule(Base):
    """Kullaniciya ait proaktivite kurali (ac/kapa + esik konfigurasyonu).

    Kimlik SEMANTIKTIR: `logical_key` = `<kind>:v<version>:<scope>`
    (or. `project_stalled:v1:global`, `project_stalled:v1:<project_id>`).
    Ayni kural her acilista yeniden uretilmez: UNIQUE kisit bunu engeller.
    """

    __tablename__ = "proactivity_rule"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    #: Kapali kume: RULE_KINDS (serbest metin DEGIL).
    kind: Mapped[str] = mapped_column(String(48), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=RULE_VERSION)
    #: `kind:v<version>:<scope>` -- tekil kural kimligi.
    logical_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    #: Entity kapsamli kural icin hedef; silinirse kural da gider.
    scope_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE")
    )
    #: Kural turune ozel, KAPALI semali ayarlar (esik, saat, cooldown).
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    #: Kullanici acik override'i: bu ana kadar sus.
    snoozed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ProactivityRun(Base):
    """TEK proaktif kosulun (episodun) olgusal yasam dongusu.

    Kosu bir tetikleyicinin degil, KOSULUN kaydidir: ayni mantiksal tetik
    yuz kez degerlendirilse de tek satir kalir. Kullaniciya giden bildirim
    ayri tablodadir (`notification`); kosu ondan bagimsiz olarak
    susturulabilir, ertelenebilir veya iptal edilebilir.
    """

    __tablename__ = "proactivity_run"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    rule_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("proactivity_rule.id", ondelete="CASCADE"), nullable=False
    )
    #: Mantiksal tekillik anahtari (or. `deadline:v1:<entity>:<rev>:3d`).
    logical_trigger_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    #: RUN_STATES kumesinden biri.
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="candidate")
    #: Sinirli gerekce kodlari (or. ["DEADLINE_3D", "RITUAL_DUE"]).
    reason_codes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    #: "Neden simdi" -- olgusal, sinirli, opak puan DEGIL.
    why_now: Mapped[str | None] = mapped_column(Text)
    #: Konu kimligi. Entity silinse bile TARIH kaybolmaz: FK yok, yalnizca
    #: sinirli yapisal kimlik (kural 1 istisnasi, bilincli).
    subject_type: Mapped[str | None] = mapped_column(String(48))
    subject_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True))
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deferred_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivery_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    snoozed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    #: Teslim edilen bildirim; bildirim budanirsa kosu OKUNABILIR kalir.
    notification_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("notification.id", ondelete="SET NULL")
    )
    #: Sinirli hata kodu (ham yigin izi DEGIL).
    failure_code: Mapped[str | None] = mapped_column(String(48))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
