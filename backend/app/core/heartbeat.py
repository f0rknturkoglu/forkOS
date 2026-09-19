"""Worker kalp atisi sozlesmesi -- TEK kaynak.

Kalp atisi ARALIGI ile "bayat" ESIGI ayni yerde durur. Ayri yerlere
yazilirlarsa (worker, healthcheck, /system/stats) biri digerinden habersiz
degisir ve saglikli bir worker arayuzde "durdu" gorunur.

Gunluk kullanimda worker saatlerce bosa kalabilir. Dakikada bir yazilan
UPDATE+COMMIT kayda deger bir SSD yazisi uretiyordu; aralik 5 dakikaya
cikarildi ve esik araligin tam 3 kati secildi ki tek bir gecikmis tur
(uzun suren bir cekim, GC) yanlis alarm uretmesin.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

#: `worker.heartbeat` ayarinin anahtari.
WORKER_HEARTBEAT_KEY = "worker.heartbeat"

#: Kalp atisinin yazim araligi (dakika).
HEARTBEAT_INTERVAL_MINUTES = 5

#: Bu sureden eski kalp atisi "bayat" sayilir.
HEARTBEAT_STALE_AFTER = timedelta(minutes=15)


def heartbeat_is_fresh(at: datetime, *, now: datetime | None = None) -> bool:
    """Kalp atisi bayat mi? `at` timezone-aware olmalidir."""
    return at >= (now or datetime.now(UTC)) - HEARTBEAT_STALE_AFTER
