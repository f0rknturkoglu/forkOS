from __future__ import annotations

import gzip
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import events as event_svc
from app.core.events import log_event
from app.core.time import local_today
from app.modules.system import dirty
from app.modules.system.export import backup_table_names, full_json


def _backup_dir() -> Path:
    """Yedek dizini: FORKOS_BACKUP_DIR env'i, Docker'da /app/backups, yerelde
    repo kokunun altindaki data/backups. Sabit /app yolu Docker disinda
    (yerel terminal) calistiginda PermissionError uretiyordu."""
    configured = __import__("os").environ.get("FORKOS_BACKUP_DIR")
    if configured:
        return Path(configured)
    if Path("/app").is_dir():
        return Path("/app/backups")
    return Path(__file__).resolve().parents[3] / "data" / "backups"


BACKUP_DIR = _backup_dir()
RETENTION_DAYS = 14
SCHEDULED_AT = "03:00"

VERB_CREATED = "backup.created"

def _counts(payload: dict) -> dict:
    modules = payload.get("modules", {})
    return {
        "entities": len(payload.get("entities", [])),
        "events": len(payload.get("events", [])),
        "files": len(payload.get("files") or {}),
        "attachments": len(payload.get("attachments") or {}),
        "modules": {name: len(rows) for name, rows in modules.items()},
    }


async def create_backup(session: AsyncSession) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    # Yedek gunu backend ortak zaman servisinden (Faz 14) -- sabit tz yok.
    local_day = local_today().isoformat()
    target = BACKUP_DIR / f"lifeos-{local_day}.json.gz"
    # Revizyon ANLIK goruntuden ONCE okunur: yedek alinirken olusan bir
    # degisiklik yedekte vardir ama revizyonda yoktur -> bir sonraki kontrol
    # "degisti" der ve fazladan yedek alinir (guvenli yon).
    revision = await dirty.revision(session)
    payload = await full_json(session)
    with gzip.open(target, "wt", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)

    # Eski yedekleri ve disaster dump dosyalarını sil (14 gun)
    cutoff = datetime.now(UTC) - timedelta(days=RETENTION_DAYS)
    for pattern in ("lifeos-*.json.gz", "pre-disaster-*.dump"):
        for path in BACKUP_DIR.glob(pattern):
            if datetime.fromtimestamp(path.stat().st_mtime, UTC) < cutoff:
                path.unlink()

    # Kural 3: anlamli aksiyon -> event. Yedek icerigi de payload'a isler.
    await log_event(session, verb=VERB_CREATED, payload={
        "file": target.name,
        "size": target.stat().st_size,
        "counts": _counts(payload),
    })

    # "Anlamli veri" imleci yedekle birlikte ilerler; zamanlanmis yedek bir
    # sonraki turda buna bakip ATLAYABILIR (bkz. backup_if_stale).
    await dirty.record_revision(session, revision)
    await session.commit()
    return target


async def backup_status(session: AsyncSession) -> dict:
    """Durum sayfasi icin tek kaynak -- yerel yedek durumu.

    `changes_since_backup` arayuze NEDEN yeni yedek gorunmedigini anlatir:
    zamanlanmis yedek, anlamli degisiklik yoksa bilincli olarak atlanir.
    """
    verbs = [VERB_CREATED]
    events = await event_svc.recent_events(session, limit=12, verbs=verbs)
    last_created = next((e for e in events if e.verb == VERB_CREATED), None)
    stored = await dirty.stored_revision(session)
    changes = True if stored is None else await dirty.has_changes_since_last_backup(session)

    return {
        "last_backup": {
            "file": last_created.payload.get("file"),
            "size": last_created.payload.get("size"),
            "at": last_created.occurred_at,
            "counts": last_created.payload.get("counts"),
        } if last_created else None,
        "next_backup_scheduled": SCHEDULED_AT,
        "changes_since_backup": changes,
        "retention_days": RETENTION_DAYS,
        "backup_dir": str(BACKUP_DIR),
        "includes": backup_table_names(),
    }


async def backup_if_stale(session: AsyncSession) -> Path | None:
    """Zamanlanmis yedek: tazeyse ya da anlamli degisiklik yoksa ATLA.

    Iki kapi vardir:
      1. Son yedek 24 saatten yeni (mevcut davranis).
      2. Son yedekten bu yana anlamli veri DEGISMEDI. Kullanici forkOS'u bir
         sure kullanmadiysa her gece ayni veriyi yeniden yazmanin anlami yok.
    Elle "Backup now" bu fonksiyonu KULLANMAZ; her zaman yedek uretir.
    """
    newest = max(BACKUP_DIR.glob("lifeos-*.json.gz"), key=lambda p: p.stat().st_mtime, default=None)
    if newest and datetime.fromtimestamp(newest.stat().st_mtime, UTC) > datetime.now(
        UTC
    ) - timedelta(hours=24):
        return None
    if not await dirty.has_changes_since_last_backup(session):
        return None
    return await create_backup(session)
