"""Yedek icin "anlamli veri degisti mi?" sinyali.

Amac: kullanici verisi degismediyse gece yedegini ATLAMAK. Sinyal "kullanici
bir seye dokundu mu" degil, **"yedek kapsamindaki veri degisti mi"**
sorusunu yanitlar.

Nereden turetiliyor: `event` tablosu zaten anlamli her mutasyonun yazildigi
tek gecis noktasidir (AGENTS.md kural 3). Yani event gecmisi, mutasyon
gecmisidir. Sinyal, EN BUYUK anlamli `event.id`'dir; yalnizca makine/cache
gurultusu (`OPERATIONAL_EVENT_VERBS`) disarida kalir.

Neden satir sayaclari (`pg_stat_user_tables`) KULLANILMIYOR: istatistikler
commit aninda degil ~1 saniye gecikmeyle yazilir ve varsayilan
`stats_fetch_consistency = cache` ile okuma goruntusu transaction boyunca
onbelleklenir. Gunluk bir karar icin surekli yanlis "degismedi" riski tasiyan
bir sinyal, tek ve deterministik bir sinyalden daha kotudur; ayrica event
gecmisi zaten ayni bilgiyi daha kesin veriyor.

Yon bilincli: sinyal "degisti" demeye EGILIMLIDIR. Operasyonel olarak
isaretlenmeyen her fiil anlamli sayilir. Yanlis tarafa duserse fazladan bir
yedek alinir (zararsiz); tersi olsaydi bir degisiklik hicbir yedege girmezdi
(veri kaybi).

`OPERATIONAL_EVENT_VERBS` listesi capta tutulur: yeni bir operasyonel fiil
eklenmezse yalnizca fazladan yedek alinir -- sessiz veri kaybi olmaz.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.system.models import Setting

#: Revizyonu tutan ayar satiri. Runtime durumdur (kullanici tercihi degil).
REVISION_KEY = "backup.revision"

#: Makine kaynakli fiiller: yalnizca operasyonel/cache durumunu degistirir,
#: yedege giren kullanici verisini degil.
OPERATIONAL_EVENT_VERBS: frozenset[str] = frozenset(
    {
        # kaynak kuyrugu ve saglik kaydi (yedek kapsami disinda)
        "source_sync.queued",
        "source_sync.started",
        "source_sync.sources_added",
        "source_sync.completed",
        "source.stalled",
        "source.failing",
        # cache/bakim
        "rss.pruned",
        "media.artwork_pruned",
        "system.maintenance",
        # elle yenileme: kendi basina veri degistirmez, tetikledigi isler
        # kendi fiillerini yazar
        "system.refresh.started",
        "system.refresh.completed",
        # yedegin kendi denetim kaydi: yedek kendini "degisti" saymamali
        "backup.created",
        "backup.drive_uploaded",
        "backup.drive_upload_failed",
    }
)


async def meaningful_event_watermark(session: AsyncSession) -> int:
    """En buyuk `event.id`, operasyonel fiiller haric.

    Dogrudan tablodan ve islem icinde okunur: az once yapilmis bir degisiklik
    ANINDA gorunur (istatistik gecikmesi yok).
    """
    value = (
        await session.execute(
            text(
                "SELECT coalesce(max(id), 0) FROM event "
                "WHERE NOT (verb = any(cast(:verbs as text[])))"
            ),
            {"verbs": sorted(OPERATIONAL_EVENT_VERBS)},
        )
    ).scalar_one()
    return int(value or 0)


async def revision(session: AsyncSession) -> dict[str, Any]:
    """Yedek kapsaminin anlik revizyonu."""
    return {
        "event": await meaningful_event_watermark(session),
        "at": datetime.now(UTC).isoformat(),
    }


async def stored_revision(session: AsyncSession) -> dict[str, Any] | None:
    row = await session.get(Setting, REVISION_KEY)
    return row.value if row is not None and isinstance(row.value, dict) else None


async def record_revision(session: AsyncSession, value: dict[str, Any]) -> None:
    """Revizyonu kaydet. Commit CAGIRMAZ; yedek akisi kendi commit'ini yapar."""
    row = await session.get(Setting, REVISION_KEY)
    if row is None:
        session.add(Setting(key=REVISION_KEY, value=value))
    else:
        row.value = value


async def has_changes_since_last_backup(session: AsyncSession) -> bool:
    """Son yedekten bu yana anlamli degisiklik var mi?

    Hic yedek alinmamis (revizyon yok) ise True: bilinmeyen durumda yedek
    ALINIR.
    """
    stored = await stored_revision(session)
    if stored is None:
        return True
    return await meaningful_event_watermark(session) != int(stored.get("event", 0))
