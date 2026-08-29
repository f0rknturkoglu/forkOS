"""Backup geri yukleme (restore).

GUVENLIK SOZLESMESI
--------------------
- Idempotent: ayni yedek kac kez yuklenirse yuklensin sonuc aynidir.
- Cakismasiz: her satir "insert ... on conflict do nothing" ile eklenir;
  zaten var olan kayitlara DOKUNULMAZ (mevcut veri korunur, uzerine yazilmaz).
- FK guvenli: ekleme sirasi bagimliliklara gore sabit; self-FK (parent_id)
  iki asamali (once satir, sonra ebeveyn referansi).
- Yeni makinede tablolar bostur -> hepsi eklenir; mevcut makinede ise
  sadece eksik satirlar girer. Bu yuzden "macOS -> Windows" tasimada
  yedeginizi istediginiz kadar tekrar yukleyebilirsiniz.

Generated (computed) kolonlar (entity.search_vec) dogrudan insert edilemez;
insert sirasinda elenir, DB yeniden uretir.
"""
from __future__ import annotations

import gzip
import json
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, Date, DateTime, Integer, Numeric, Uuid, text, update
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import TypeEngine

from app.core.events import log_event
from app.db import Base
from app.modules.system.export import backup_table_names
from app.modules.system.secrets import is_secret_setting


def insert_order() -> list[str]:
    """SQLAlchemy FK grafiğinden restore sırasını üret; yeni tablo unutulmasın."""
    allowed = set(backup_table_names())
    return [table.name for table in Base.metadata.sorted_tables if table.name in allowed]

# Self-referencing FK: parent_id ayni batch'te onceden eklenmis olmayabilir.
# Once parent_id=NULL ile insert, ardindan geri bagla (FK db'de dogrulanir).
SELF_FK_TABLES: dict[str, str] = {
    "todo": "parent_id",
    "study_topic": "parent_id",
}

CHUNK = 400  # asyncpg bind parametre limitine takilmamak icin parcali insert


def parse_backup(content: bytes) -> dict:
    """gzip ya da duz JSON kabul eder. Eksik/bilunmeyen surum -> ValueError."""
    if content[:2] == b"\x1f\x8b":
        content = gzip.decompress(content)
    payload = json.loads(content.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("yedek ust seviye bir JSON objesi olmali")
    if payload.get("version") != 1:
        raise ValueError(f"desteklenmeyen yedek versiyonu: {payload.get('version')!r}")
    for key in ("entities", "links", "events", "modules"):
        if key not in payload:
            raise ValueError(f"yedek eksik: '{key}' bolumu yok")
    return payload


def _rows(payload: dict, table_name: str) -> list[dict]:
    """Koktepe ve 'modules' icindeki tablolar icin ortak erisim."""
    if table_name == "entity":
        return payload.get("entities", [])
    if table_name == "link":
        return payload.get("links", [])
    if table_name == "event":
        return payload.get("events", [])
    return payload.get("modules", {}).get(table_name, [])


def _insertable(table_name: str) -> list[str]:
    """Generated kolonlari atla (entity.search_vec) -- insert edilemez."""
    table = Base.metadata.tables[table_name]
    return [col.name for col in table.columns if col.computed is None]


def _coerce(value: Any, col_type: TypeEngine) -> Any:
    """JSON'da string olarak gelen degerleri kolon tipine cevirir.

    asyncpg tip katidir: timestamptz icin datetime, uuid icin UUID, numeric
    icin Decimal ister -- ISO string'leri reddeder. (Yedek JSON'da her sey
    string/primitive'tir; ornek: "2026-08-21T07:52:54+00:00".)
    """
    if value is None or isinstance(value, (dict, list, bool, int, float)):
        return value
    if isinstance(col_type, DateTime):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    if isinstance(col_type, Date):
        return date.fromisoformat(str(value))
    if isinstance(col_type, Numeric):
        return Decimal(str(value))
    if isinstance(col_type, (PgUUID, Uuid)):
        return uuid.UUID(str(value))
    return value


async def _insert_batch(
    session: AsyncSession, table_name: str, rows: list[dict]
) -> tuple[int, int]:
    """ON CONFLICT DO NOTHING ile parcali insert. Doner: (eklenen, atlanan)."""
    table = Base.metadata.tables[table_name]
    columns = _insertable(table_name)
    inserted = 0
    skipped = 0
    for start in range(0, len(rows), CHUNK):
        chunk = rows[start : start + CHUNK]
        values = [
            {col: _coerce(row[col], table.c[col].type) for col in columns if col in row}
            for row in chunk
        ]
        if not values:
            continue
        statement = insert(table).values(values).on_conflict_do_nothing()
        result = await session.execute(statement)
        inserted += result.rowcount or 0
        skipped += len(values) - (result.rowcount or 0)
    return inserted, skipped


async def restore(session: AsyncSession, payload: dict) -> dict:
    """Yedek yukler. Doner: tablo bazinda {inserted, skipped} ozeti."""
    summary: dict[str, dict[str, int]] = {}

    # 1. Asama: FK sirasiyla, cakisma olursa yok sayarak ekle.
    for table_name in insert_order():
        rows = _rows(payload, table_name)
        # Eski yedeklerde secret setting satiri olabilir (Faz 15): bunlar
        # ICERI ALINMAZ -- secret'lar yalnizca canli DB'de yasamali.
        secret_rows: list[dict] = []
        if table_name == "setting":
            secret_rows = [row for row in rows if is_secret_setting(str(row.get("key", "")))]
            rows = [row for row in rows if not is_secret_setting(str(row.get("key", "")))]
        if not rows:
            if secret_rows:
                summary[table_name] = {"inserted": 0, "skipped": 0,
                                       "secret_skipped": len(secret_rows)}
            continue
        inserted, skipped = await _insert_batch(session, table_name, rows)
        entry: dict = {"inserted": inserted, "skipped": skipped}
        if secret_rows:
            entry["secret_skipped"] = len(secret_rows)
        summary[table_name] = entry

    # 2. Asama: self-FK referanslarini geri bagla.
    for table_name, column in SELF_FK_TABLES.items():
        rows = _rows(payload, table_name)
        if not rows:
            continue
        table = Base.metadata.tables[table_name]
        fixed = 0
        for row in rows:
            parent = row.get(column)
            if not parent:
                continue
            result = await session.execute(
                update(table).where(table.c.id == row["id"]).values({column: parent})
            )
            fixed += result.rowcount or 0
        if fixed:
            entry = summary.setdefault(table_name, {"inserted": 0, "skipped": 0})
            entry["parent_refs_linked"] = fixed

    # 3. Asama: bigserial PK'lerin sequence'ini son id'ye ilerlet.
    # Explicit id ile insert edilen satirlar sequence'i ilerletmez; sonraki
    # insert (event gibi) id cakismasina duser. setval ile onune geceriz.
    for table_name in insert_order():
        table = Base.metadata.tables[table_name]
        pk = next(iter(table.primary_key.columns))
        if not isinstance(pk.type, (Integer, BigInteger)):
            continue
        bound = await session.execute(
            text("select pg_get_serial_sequence(:t, :c)"),
            {"t": table_name, "c": pk.name},
        )
        sequence = bound.scalar_one_or_none()
        if not sequence:
            continue
        await session.execute(
            text(f'select setval(:seq, coalesce(max("{pk.name}"), 1)) from "{table_name}"'),
            {"seq": sequence},
        )

    restored_total = sum(
        entry["inserted"] for entry in summary.values()
    )
    await log_event(
        session, verb="backup.restored",
        payload={"restored": restored_total, "tables": summary},
    )
    await session.commit()
    return summary
