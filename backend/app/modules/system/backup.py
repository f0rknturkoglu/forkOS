from __future__ import annotations

import gzip
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.google_auth import access_token
from app.modules.system.export import full_json
from app.modules.system.models import Setting

BACKUP_DIR = Path("/app/backups")


async def create_backup(session: AsyncSession) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    local_day = datetime.now(ZoneInfo("Europe/Istanbul")).date().isoformat()
    target = BACKUP_DIR / f"lifeos-{local_day}.json.gz"
    payload = await full_json(session)
    with gzip.open(target, "wt", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)
    cutoff = datetime.now(UTC) - timedelta(days=14)
    for path in BACKUP_DIR.glob("lifeos-*.json.gz"):
        if datetime.fromtimestamp(path.stat().st_mtime, UTC) < cutoff:
            path.unlink()
    folder = await session.get(Setting, "backup.drive_folder_id")
    if folder and folder.value:
        await upload_drive(session, target, str(folder.value))
    return target


async def upload_drive(session: AsyncSession, path: Path, folder_id: str) -> None:
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


async def backup_if_stale(session: AsyncSession) -> Path | None:
    newest = max(BACKUP_DIR.glob("lifeos-*.json.gz"), key=lambda p: p.stat().st_mtime, default=None)
    if newest and datetime.fromtimestamp(newest.stat().st_mtime, UTC) > datetime.now(
        UTC
    ) - timedelta(hours=24):
        return None
    return await create_backup(session)
