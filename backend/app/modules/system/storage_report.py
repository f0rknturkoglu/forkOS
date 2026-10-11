"""Depolama ve runtime gorunurlugu (diagnostics).

Amac: kullanici "forkOS bugun ne kadar disk kullaniyor, hangi veri buyuyor?"
sorusunu tek ekranda gorebilsin. Yalnizca OKUMA yapar; hicbir sey silmez,
hicbir sey onbellege almaz.

Iki kural:
  - **Yetki guvenli.** `pg_ls_waldir()` gibi fonksiyonlar superuser ister;
    erisilemezse ilgili alan `null` doner ve ekran KIRILMAZ.
  - **Tahmini etiketlenir.** Tablo satir sayilari `pg_stat_user_tables`'tan
    (tahmini) gelir; kesin sayim yalnizca kritik birkac tablo icin yapilir.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

#: Kesin satir sayimi yapilan tablolar (operasyonel buyume takibi).
COUNTED_TABLES = ("source_run", "source_sync_batch", "event", "notification")
#: En buyuk tablo listesinin uzunlugu.
TOP_TABLES = 12


def _dir_bytes(*roots: Path) -> int:
    total = 0
    for root in roots:
        if not root.is_dir():
            continue
        for current, _dirs, files in os.walk(root, followlinks=False):
            for name in files:
                try:
                    total += (Path(current) / name).stat().st_size
                except OSError:
                    continue
    return total


def _filesystem_buckets() -> dict[str, int]:
    """Runtime veri dizinlerinin boyutlari (bayt).

    Dizinler uygulamanin kendi sabitlerinden gelir; burada yol tahmini
    yapilmaz. Bir dizin yoksa 0.
    """
    from app.modules.document.service import DOCUMENTS_DIR
    from app.modules.media.archive import default_asset_dir
    from app.modules.note import storage as attachment_storage
    from app.modules.system.backup import BACKUP_DIR
    from app.sources.forkjob_core.scrapers.base import ScraperConfig

    return {
        "documents": _dir_bytes(DOCUMENTS_DIR),
        "attachments": _dir_bytes(attachment_storage.ATTACHMENTS_DIR),
        "media_artwork": _dir_bytes(default_asset_dir()),
        "scraper_cache": _dir_bytes(ScraperConfig().cache_dir),
        "backups": _dir_bytes(BACKUP_DIR),
    }


async def _database_report(session: AsyncSession) -> dict[str, Any]:
    total = (
        await session.execute(text("select pg_database_size(current_database())"))
    ).scalar_one()
    tables = (
        await session.execute(
            text(
                """
                select relname,
                       pg_total_relation_size(relid) as bytes,
                       n_live_tup as rows
                from pg_stat_user_tables
                order by pg_total_relation_size(relid) desc
                limit :limit
                """
            ),
            {"limit": TOP_TABLES},
        )
    ).all()
    counts = {}
    for table in COUNTED_TABLES:
        counts[table] = (
            await session.execute(text(f'select count(*) from "{table}"'))
        ).scalar_one()
    wal: dict[str, int] | None = None
    try:
        wal_bytes = (await session.execute(text("select sum(size) from pg_ls_waldir()"))).scalar_one()
        wal = {"bytes": int(wal_bytes or 0)}
    except Exception:  # noqa: BLE001 - yetki yoksa alan null kalir, ekran kirilmaz
        wal = None
    return {
        "total_bytes": int(total or 0),
        "tables": [
            {"name": row.relname, "bytes": int(row.bytes or 0), "rows": int(row.rows or 0)}
            for row in tables
        ],
        "rows": counts,
        "wal": wal,
    }


async def storage_report(session: AsyncSession) -> dict[str, Any]:
    """Tek okumada depolama dokumu."""
    from app.modules.system.maintenance import MAINTENANCE_KEY
    from app.modules.system.models import Setting

    maintenance_row = await session.get(Setting, MAINTENANCE_KEY)
    maintenance_summary = (
        maintenance_row.value
        if maintenance_row and isinstance(maintenance_row.value, dict)
        else None
    )
    return {
        "database": await _database_report(session),
        "files": _filesystem_buckets(),
        "maintenance": maintenance_summary,
    }


#: Uyari esikleri (bayt). Asilinca ekranda uyari olarak gosterilir; bildirim
#: URETILMEZ (spam olmasin) ve hicbir sey otomatik silinmez.
WARN_LIMITS: dict[str, int] = {
    "media_artwork": 512 * 1024 * 1024,  # artwork butce tavaniyla ayni
    "backups": 2 * 1024 * 1024 * 1024,
    "attachments": 4 * 1024 * 1024 * 1024,
    "scraper_cache": 1024 * 1024 * 1024,
    "source_run_rows": 200_000,
}

WARN_LABELS: dict[str, str] = {
    "media_artwork": "Medya görsel önbelleği beklenenden büyük",
    "backups": "Yedek dizini beklenenden büyük",
    "attachments": "Ek deposu beklenenden büyük",
    "scraper_cache": "Scraper önbelleği beklenenden büyük",
    "source_run_rows": "Kaynak koşu kaydı beklenenden çok",
}


def warnings(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Esik asimlari: (anahtar, kullanim, esik). Bildirim degil, teshis."""
    files = report.get("files", {})
    rows = report.get("database", {}).get("rows", {})
    values = {**files, "source_run_rows": int(rows.get("source_run", 0))}
    alerts: list[dict[str, Any]] = []
    for key, limit in WARN_LIMITS.items():
        used = int(values.get(key, 0))
        if used > limit:
            alerts.append(
                {
                    "key": key,
                    "label": WARN_LABELS.get(key, key),
                    "used": used,
                    "limit": limit,
                }
            )
    return alerts
