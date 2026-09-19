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

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Integer,
    Numeric,
    Uuid,
    func,
    select,
    text,
    update,
)
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
    "note_folder": "parent_id",
    "todo": "parent_id",
    "study_topic": "parent_id",
}

CHUNK = 400  # asyncpg bind parametre limitine takilmamak icin parcali insert


def parse_backup(content: bytes) -> dict:
    """gzip ya da duz JSON kabul eder. Eksik/bilinmeyen surum -> ValueError.

    v1 (manifest'siz) ve v2 (manifest'li) desteklenir; bilinmeyen gelecek
    surumler sessizce kabul edilmez.
    """
    if content[:2] == b"\x1f\x8b":
        content = gzip.decompress(content)
    payload = json.loads(content.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("yedek ust seviye bir JSON objesi olmali")
    if payload.get("version") not in (1, 2):
        raise ValueError(f"desteklenmeyen yedek versiyonu: {payload.get('version')!r}")
    for key in ("entities", "links", "events", "modules"):
        if key not in payload:
            raise ValueError(f"yedek eksik: '{key}' bolumu yok")
    return payload


def _counts_of(payload: dict) -> dict:
    return {
        "entities": len(payload.get("entities", [])),
        "links": len(payload.get("links", [])),
        "events": len(payload.get("events", [])),
        "modules": {
            name: len(rows)
            for name, rows in payload.get("modules", {}).items()
        },
    }


def inspect_payload(payload: dict) -> dict:
    """Import oncesi preflight (Faz 16): hicbir sey yazmadan yedegi inceler.

    Bilinmeyen tablolar, eksik zorunlu bolumler, secret setting satirlari ve
    v2 manifest butunlugu raporlanir. Frontend bu raporu gosterip kullaniciya
    onaylatir; ancak ondan sonra merge/import calisir.
    """
    known = set(Base.metadata.tables)
    modules = payload.get("modules", {})
    manifest = payload.get("manifest") or {}
    reported = manifest.get("row_counts") or {}
    actual = _counts_of(payload)
    return {
        "version": payload.get("version"),
        "app": manifest.get("app"),
        "exported_at": payload.get("exported_at") or manifest.get("exported_at"),
        "table_counts": actual,
        "unknown_tables": sorted(set(modules) - known),
        "missing_sections": [
            key for key in ("entities", "links", "events", "modules")
            if key not in payload
        ],
        "secret_settings": sum(
            1 for row in modules.get("setting", [])
            if is_secret_setting(str(row.get("key", "")))
        ),
        "files_count": len(payload.get("files") or {}),
        "integrity_ok": reported == actual if reported else None,
    }


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


async def restore(
    session: AsyncSession, payload: dict, *, commit: bool = True,
) -> dict:
    """Yedek yukler. Doner: tablo bazinda {inserted, skipped} ozeti.

    `commit=False`: yukleme islemi transaction'i commit ETMEZ -- cagiran
    (disaster restore) dogrulamayi ayni transaction icinde yapip ya commit
    ya rollback eder (Faz 28). Normal merge endpoint'i default True ile
    onceki davranisi korur.
    """
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

    # 4. Asama: fiziksel dosyalari diske ac (yerel dokumanlar + not ekleri)
    files_restored = restore_files(payload)
    if files_restored:
        summary["_files"] = {"restored": files_restored}
    attachments_restored = restore_attachments(payload)
    if attachments_restored:
        summary["_attachments"] = {"restored": attachments_restored}

    restored_total = sum(
        entry["inserted"] for entry in summary.values() if "inserted" in entry
    )
    await log_event(
        session, verb="backup.restored",
        payload={"restored": restored_total, "tables": summary},
    )
    if commit:
        await session.commit()
    else:
        await session.flush()
    return summary


def restore_files(payload: dict) -> int:
    """Yedekte base64 olarak saklanan yerel doküman dosyalarını (CV/PDF) diske yazar."""
    files = payload.get("files") or {}
    if not isinstance(files, dict) or not files:
        return 0
    import base64

    from app.modules.document.service import DOCUMENTS_DIR

    restored = 0
    for doc_id, file_info in files.items():
        if not isinstance(file_info, dict):
            continue
        filename = file_info.get("filename")
        data_b64 = file_info.get("data_b64")
        if not filename or not data_b64:
            continue
        try:
            target_dir = DOCUMENTS_DIR / str(doc_id)
            target_dir.mkdir(parents=True, exist_ok=True)
            target_file = target_dir / filename
            target_file.write_bytes(base64.b64decode(data_b64))
            restored += 1
        except Exception:
            pass
    return restored


def restore_attachments(payload: dict) -> int:
    """Yedekteki not eki blob'larini `data/attachments/<sha256>` altina yaz.

    Ad, ICERIGIN ozetinden dogrulanir: yedekteki anahtar ile icerigin sha256'si
    tutmuyorsa dosya YAZILMAZ (bozuk/kurcalanmis yedek sessizce kabul edilmez).
    `store_blob` content-addressed oldugu icin tekrar calistirmak zararsizdir.
    """
    entries = payload.get("attachments") or {}
    if not isinstance(entries, dict) or not entries:
        return 0
    import base64

    from app.modules.note import storage as attachment_storage

    restored = 0
    for digest, data_b64 in entries.items():
        if not isinstance(data_b64, str) or not attachment_storage.is_digest(str(digest)):
            continue
        try:
            content = base64.b64decode(data_b64, validate=True)
        except Exception:  # noqa: BLE001 - bozuk kayit digerlerini durdurmamali
            continue
        if attachment_storage.digest_of(content) != digest:
            continue
        try:
            attachment_storage.store_blob(content)
            restored += 1
        except OSError:
            continue
    return restored


async def verify_restore(session: AsyncSession, payload: dict) -> dict:
    """Disaster restore sonrasi butunluk kontrolu (Faz 16).

    Tablo sayilari yedekle birebir, link uclari entity'de, todo parent'lari
    todo'da olmali. Herhangi biri tutmazsa restore sonucu guvenilir degildir.
    """
    tables = ["entity", "link", "event", *sorted(payload.get("modules", {}))]
    row_counts: dict[str, int] = {}
    for table_name in tables:
        if table_name not in Base.metadata.tables:
            continue
        count = (
            await session.execute(
                select(func.count()).select_from(Base.metadata.tables[table_name])
            )
        ).scalar_one()
        row_counts[table_name] = int(count)
    orphan_links = (
        await session.execute(text(
            "select count(*) from link l "
            "where not exists (select 1 from entity e where e.id = l.from_id) "
            "or not exists (select 1 from entity e where e.id = l.to_id)"
        ))
    ).scalar_one()
    orphan_parents = (
        await session.execute(text(
            "select count(*) from todo t "
            "where t.parent_id is not null "
            "and not exists (select 1 from todo p where p.id = t.parent_id)"
        ))
    ).scalar_one()
    return {
        "row_counts": row_counts,
        "orphan_links": int(orphan_links),
        "orphan_parents": int(orphan_parents),
    }
