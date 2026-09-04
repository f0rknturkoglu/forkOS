from __future__ import annotations

import gzip
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import events as event_svc
from app.core.events import log_event
from app.core.notifications import notify
from app.core.time import local_today
from app.integrations.google_auth import access_token
from app.modules.system.export import backup_table_names, full_json
from app.modules.system.models import Setting


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
VERB_DRIVE_OK = "backup.drive_uploaded"
VERB_DRIVE_FAIL = "backup.drive_upload_failed"

FOLDER_SETTING = "backup.drive_folder_id"

def _counts(payload: dict) -> dict:
    modules = payload.get("modules", {})
    return {
        "entities": len(payload.get("entities", [])),
        "events": len(payload.get("events", [])),
        "modules": {name: len(rows) for name, rows in modules.items()},
    }


async def create_backup(session: AsyncSession) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    # Yedek gunu backend ortak zaman servisinden (Faz 14) -- sabit tz yok.
    local_day = local_today().isoformat()
    target = BACKUP_DIR / f"lifeos-{local_day}.json.gz"
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

    folder = await session.get(Setting, FOLDER_SETTING)
    if folder and folder.value:
        error = await upload_drive(session, target, str(folder.value))
        if error:
            await log_event(session, verb=VERB_DRIVE_FAIL,
                            payload={"file": target.name, "error": error})
            await notify(
                session,
                kind="backup_drive_failed",
                title="Google Drive yedeği yüklenemedi",
                body=f"{target.name}: {error[:150]}",
                dedup_key=f"backup_drive_failed:{target.name}",
                importance=2,
            )
        else:
            await log_event(session, verb=VERB_DRIVE_OK,
                            payload={"file": target.name, "folder_id": str(folder.value)})

    await session.commit()
    return target


async def upload_drive(session: AsyncSession, path: Path, folder_id: str) -> str | None:
    """Drive'a gzip yedegi yukler. Doner: None basariliysa, yoksa hata metni.

    Yerel yedek birincildir -- yukleme hatasi yedegin alinmasini engellemez,
    sadece durum sayfasinda gorunur.
    """
    try:
        token = await access_token(session)
        metadata = {"name": path.name, "parents": [folder_id]}
        files = {
            "metadata": (None, json.dumps(metadata), "application/json"),
            "file": (path.name, path.read_bytes(), "application/gzip"),
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
                headers={"Authorization": f"Bearer {token}"},
                files=files,
            )
            response.raise_for_status()
        return None
    except Exception as exc:
        return f"{type(exc).__name__}: {str(exc)[:300]}"


async def backup_status(session: AsyncSession) -> dict:
    """Durum sayfasi/widjet icin tek kaynak -- son yedek, Drive yukleme gecmisi."""
    verbs = [VERB_CREATED, VERB_DRIVE_OK, VERB_DRIVE_FAIL]
    events = await event_svc.recent_events(session, limit=12, verbs=verbs)
    last_created = next((e for e in events if e.verb == VERB_CREATED), None)
    last_ok = next((e for e in events if e.verb == VERB_DRIVE_OK), None)
    last_fail = next((e for e in events if e.verb == VERB_DRIVE_FAIL), None)
    folder = await session.get(Setting, FOLDER_SETTING)

    return {
        "drive_folder_id": folder.value if folder and folder.value else None,
        "last_backup": {
            "file": last_created.payload.get("file"),
            "size": last_created.payload.get("size"),
            "at": last_created.occurred_at,
            "counts": last_created.payload.get("counts"),
        } if last_created else None,
        "last_drive_upload": {
            "file": last_ok.payload.get("file"),
            "at": last_ok.occurred_at,
        } if last_ok else None,
        "last_drive_error": {
            "message": last_fail.payload.get("error"),
            "at": last_fail.occurred_at,
        } if last_fail else None,
        "next_backup_scheduled": SCHEDULED_AT,
        "retention_days": RETENTION_DAYS,
        "backup_dir": str(BACKUP_DIR),
        "includes": backup_table_names(),
    }


async def backup_if_stale(session: AsyncSession) -> Path | None:
    newest = max(BACKUP_DIR.glob("lifeos-*.json.gz"), key=lambda p: p.stat().st_mtime, default=None)
    if newest and datetime.fromtimestamp(newest.stat().st_mtime, UTC) > datetime.now(
        UTC
    ) - timedelta(hours=24):
        return None
    return await create_backup(session)
