"""Disaster restore -- uygulama DISI bakim islemi (Faz 16).

Normal `/backup/restore` MERGE eder: idempotent, `ON CONFLICT DO NOTHING`,
mevcut veriye dokunmaz. Tam geri donus app-level degildir; tum veritabani
uygulama disindan degistirilir. Bu modul FastAPI endpoint'inden CAGIRILMAZ;
yalnizca `scripts/disaster_restore.py` (Makefile hedefi) kullanir.

Sınır: tum DB'nin degistirilmesi ayri bir disaster recovery siniridir;
uygulama ici append-only event kurali bu islem icin gecerli degildir.
Kullanici akisi su sirayla calisir:
1. API ve worker yazmalari durdurulur (compose).
2. Mevcut DB'nin guvenlik yedegi alinir (pg_dump).
3. Temiz schema hazirlanir, migration'lar uygulanir.
4. JSON yedek temiz DB'ye yuklenir.
5. Entity/link/event ve self-FK butunlugu dogrulanir.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Base
from app.modules.system import restore


async def clean_schema(session: AsyncSession) -> None:
    """Tum tablolari bosaltir. Yalnizca disaster restore icin (Faz 16)."""
    tables = ", ".join(f'"{table.name}"' for table in reversed(Base.metadata.sorted_tables))
    await session.execute(text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE"))
    await session.flush()


async def disaster_restore(session: AsyncSession, payload: dict) -> dict:
    """Temiz DB'ye yedek yukler + butunlugu dogrular.

    `clean_schema` -> `restore.restore` -> `restore.verify_restore`.
    Dogrulama tutmazsa ValueError firlatilir (islem commit edilmez).
    """
    await clean_schema(session)
    summary = await restore.restore(session, payload)
    verification = await restore.verify_restore(session, payload)

    expected = {
        "entity": len(payload.get("entities", [])),
        "link": len(payload.get("links", [])),
    }
    actual = verification["row_counts"]
    for table, count in expected.items():
        if actual.get(table) != count:
            raise ValueError(
                f"restore dogrulamasi basarisiz: {table} beklenen {count}, "
                f"gercek {actual.get(table)}"
            )
    # restore() kendi backup.restored event'ini yazar (kural 3): temiz DB'de
    # event sayisi payload + 1 olmali. Bu ekstra kayit beklenen ve istenendir.
    if actual.get("event") != len(payload.get("events", [])) + 1:
        raise ValueError(
            "restore dogrulamasi basarisiz: event beklenen "
            f"{len(payload.get('events', [])) + 1}, gercek {actual.get('event')}"
        )
    if verification["orphan_links"]:
        raise ValueError(f"yetim link var: {verification['orphan_links']}")
    if verification["orphan_parents"]:
        raise ValueError(f"yetim todo parent var: {verification['orphan_parents']}")
    return {"summary": summary, "verification": verification}
