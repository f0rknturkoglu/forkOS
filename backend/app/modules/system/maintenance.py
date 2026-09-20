"""Hafif bakim: gunde en fazla bir kez, ag cagrisi yok.

Neden ayri bir mekanizma gerekti: budama isleri yalnizca worker cron'una
bagliydi. Worker varsayilan olarak KAPALI oldugu icin gunluk kullanimda bu
isler hic kosmuyor ve veritabani sessizce buyuyordu. Bakim artik worker'dan
bagimsiz: worker kapaliyken API acilista bir kez dener.

Tasarim kurallari:

  - **Gunde en fazla bir kez.** Gun, `app.core.time.local_today()` ile
    belirlenir (container UTC olsa da kullanici gunu).
  - **Concurrency-safe.** Gun talebi tek bir atomik
    `INSERT ... ON CONFLICT DO UPDATE ... WHERE day <> :day` ile alinir.
    Iki surec (api + worker) ayni anda denerse yalnizca biri satiri alir,
    digeri sessizce atlar. Kilit tutmaya gerek yok.
  - **Idempotent.** Ayni gun ikinci kez kosmasi zarar vermez: silinecek bir
    sey kalmazsa adimlar bos doner.
  - **Sinirli ve agsiz.** Yalnizca yerel DB + dosya sistemi. Ag cagrisi YOK.
  - **Adimlar bagimsiz.** Biri patlarsa transaction geri alinir, digerleri
    devam eder; hata listesi sonuca yazilir ve log'lanir.

Bilinen sinir: kosum ortasinda surec olurse satir `running` kalir ve o gun
tekrar denenmez (ertesi gun telafi edilir). Bu bilincli: ayni gun icinde
yeniden talep etmek, calisan bir kosumla yarisa girerdi. Yarim kalan kosum
durum ekraninda gorunur, sessizce kaybolmaz.

Bakim hicbir kisisel veriye dokunmaz: `event` budanmaz, kullanici ayarlari
silinmez. Kapsam `app.core.retention` + RSS + medya gorsel onbellegi.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import retention
from app.core.events import log_event
from app.core.time import local_today
from app.modules.system.models import Setting

log = logging.getLogger("maintenance")

#: Gun talebini ve son sonucu tutan tek ayar satiri.
MAINTENANCE_KEY = "maintenance.last_run"

MAX_ERROR_CHARS = 300


async def last_run(session: AsyncSession) -> dict | None:
    """Son bakim kaydi (durum ekranlari icin), yoksa None."""
    row = await session.get(Setting, MAINTENANCE_KEY)
    return row.value if row is not None and isinstance(row.value, dict) else None


async def _claim_day(session: AsyncSession, day: str, moment: datetime) -> bool:
    """Bugunun bakimini sahiplen. Ayni gun icin ikinci cagri False doner."""
    claimed = (
        await session.execute(
            text(
                """
                INSERT INTO setting (key, value)
                VALUES (:key, jsonb_build_object(
                    'day', cast(:day as text),
                    'at', cast(:at as text),
                    'status', 'running'
                ))
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                WHERE setting.value ->> 'day' IS DISTINCT FROM cast(:day as text)
                RETURNING key
                """
            ),
            {"key": MAINTENANCE_KEY, "day": day, "at": moment.isoformat()},
        )
    ).scalar_one_or_none()
    if claimed is None:
        await session.rollback()
        return False
    # Talebi HEMEN commit et: uzun suren adimlar sirasinda baska bir surec
    # ayni gunu talep etmesin.
    await session.commit()
    return True


async def _prune_retention(session: AsyncSession, moment: datetime) -> dict[str, int]:
    return await retention.prune_operational(session, now=moment)


async def _prune_rss(session: AsyncSession, moment: datetime) -> dict[str, int]:
    from app.modules.rss import service as rss

    return {"feed_item": await rss.prune_items(session)}


async def _prune_artwork(session: AsyncSession, moment: datetime) -> dict[str, int]:
    from app.modules.media.artwork import prune_artwork

    result = await prune_artwork(session)
    return {"files": result.removed, "freed_bytes": result.freed_bytes}


async def _migrate_note_attachments(session: AsyncSession, moment: datetime) -> dict[str, int]:
    """Eski base64 ekleri tasi ve yetim blob'lari temizle.

    Donusum bakim icinde kosar cunku kullanici aksiyonu gerektirmemeli: worker
    kapaliyken de API acilisinda bir tur ilerler ve biriken notlar zamanla
    tasinir. Zaten donusmus notlar sorguya girmez (JSONB bos).

    Yetim temizligi: kalici silme satirlari FK ile goturur ama diskteki
    dosyayi goturmez (bkz. note/storage.py).
    """
    from app.modules.note import service as note_service
    from app.modules.note import storage as attachment_storage

    return {
        "notes": await note_service.convert_legacy_attachments(session),
        "orphan_blobs": await attachment_storage.prune_orphan_blobs(session),
    }


#: Adim adi -> calistirici. Once DB satirlari, sonra dosya sistemi.
#: Her adim ayni imzayi tasir: (session, moment) -> {etiket: sayi}.
STEPS: tuple[tuple[str, Callable[[AsyncSession, datetime], Awaitable[dict[str, int]]]], ...] = (
    ("retention", _prune_retention),
    ("rss", _prune_rss),
    ("artwork", _prune_artwork),
    ("attachments", _migrate_note_attachments),
)


async def run_maintenance(
    session: AsyncSession, *, now: datetime | None = None, force: bool = False
) -> dict[str, Any] | None:
    """Gunluk bakimi kos. Doner: ozet, ya da gun kapisi kapaliysa None.

    `force=True` gun kapisini atlar (elle tetikleme); adimlar yine bagimsiz
    kosar.
    """
    moment = now or datetime.now(UTC)
    day = local_today(moment).isoformat()
    if not force and not await _claim_day(session, day, moment):
        return None

    results: dict[str, dict[str, int]] = {}
    errors: list[str] = []
    for name, step in STEPS:
        try:
            step_result = await step(session, moment)
            await session.commit()
            results[name] = step_result
        except Exception as exc:  # noqa: BLE001 - bir adim digerlerini durdurmamali
            # Postgres bir hata sonrasi transaction'i iptal eder; sonraki
            # adimlarin calisabilmesi icin bu adimin geri alinmasi ZORUNLU.
            # Onceki adimlar commit edildigi icin etkilenmez.
            await session.rollback()
            errors.append(f"{name}: {type(exc).__name__}: {exc}"[:MAX_ERROR_CHARS])
            log.exception("bakim adimi basarisiz: %s", name)

    summary = {
        "day": day,
        "at": moment.isoformat(),
        "status": "completed_with_errors" if errors else "completed",
        "results": results,
        "errors": errors,
    }
    row = await session.get(Setting, MAINTENANCE_KEY)
    if row is None:
        session.add(Setting(key=MAINTENANCE_KEY, value=summary))
    else:
        row.value = summary
    await log_event(
        session,
        verb="system.maintenance",
        payload={"day": day, "results": results, "errors": errors},
    )
    await session.commit()
    log.info("bakim tamamlandi: %s (hatalar=%d)", results, len(errors))
    return summary
