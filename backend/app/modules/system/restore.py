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

import base64
import gzip
import json
import os
import tempfile
import uuid
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
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
def self_fk_columns() -> dict[str, list[str]]:
    """Discover every self reference, including recurrence and historical tables."""
    return {
        table.name: [column.name for column in table.columns
                     if any(fk.column.table is table for fk in column.foreign_keys)]
        for table in Base.metadata.sorted_tables
        if any(fk.column.table is table for column in table.columns for fk in column.foreign_keys)
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


def check_attachments_integrity(payload: dict) -> dict[str, Any]:
    """Yedek eklerinin bütünlüğünü denetler (Faz 16/32).

    1. note_attachment tablosunda referans verilen her sha256, payload['attachments']
       haritasında bulunmalıdır.
    2. payload['attachments'] içindeki her kaydın SHA-256 özeti içeriğiyle
       uyuşmalıdır (bozuk veya sahte payload engellenir).
    3. Eski tip legacy JSONB ekler (note.attachments) bu tablodan
       bağımsızdır ve hataya yol açmaz.
    """
    import base64

    from app.modules.note import storage as attachment_storage

    modules = payload.get("modules", {})
    note_attachment_rows = modules.get("note_attachment") or []

    referenced_digests: set[str] = set()
    invalid_rows: list[str] = []
    for row in note_attachment_rows:
        digest = str(row.get("sha256") or "")
        if not attachment_storage.is_digest(digest):
            invalid_rows.append(digest)
        else:
            referenced_digests.add(digest)

    attachments_map = payload.get("attachments")
    if not isinstance(attachments_map, dict):
        attachments_map = {}

    missing: list[str] = sorted(d for d in referenced_digests if d not in attachments_map)

    corrupt: list[str] = []
    for digest, data_b64 in attachments_map.items():
        if not attachment_storage.is_digest(str(digest)) or not isinstance(data_b64, str):
            corrupt.append(str(digest))
            continue
        try:
            content = base64.b64decode(data_b64, validate=True)
        except Exception:
            corrupt.append(str(digest))
            continue
        if attachment_storage.digest_of(content) != str(digest):
            corrupt.append(str(digest))

    corrupt.extend(invalid_rows)
    corrupt = sorted(set(corrupt))

    is_ok = len(missing) == 0 and len(corrupt) == 0
    return {
        "ok": is_ok,
        "missing": missing,
        "corrupt": corrupt,
        "referenced_count": len(referenced_digests),
        "payload_count": len(attachments_map),
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
    att_check = check_attachments_integrity(payload)

    manifest_ok = (reported == actual) if reported else None
    if manifest_ok is False or not att_check["ok"]:
        integrity_ok: bool | None = False
    elif manifest_ok is True and att_check["ok"]:
        integrity_ok = True
    elif att_check["ok"]:
        integrity_ok = manifest_ok
    else:
        integrity_ok = False

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
        "attachments_count": len(payload.get("attachments") or {}),
        "missing_attachments": att_check["missing"],
        "corrupt_attachments": att_check["corrupt"],
        "integrity_ok": integrity_ok,
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
    session: AsyncSession, table_name: str, rows: list[dict], *, added_ids: set | None = None
) -> tuple[int, int]:
    """ON CONFLICT DO NOTHING ile parcali insert. Doner: (eklenen, atlanan)."""
    table = Base.metadata.tables[table_name]
    columns = _insertable(table_name)
    self_columns = self_fk_columns().get(table_name, [])
    inserted = 0
    skipped = 0
    for start in range(0, len(rows), CHUNK):
        chunk = rows[start : start + CHUNK]
        values = [
            {col: _coerce(row[col], table.c[col].type) for col in columns if col in row}
            for row in chunk
        ]
        for value in values:
            for column in self_columns:
                value[column] = None
        if not values:
            continue
        statement = insert(table).values(values).on_conflict_do_nothing()
        if added_ids is not None:
            result = await session.execute(statement.returning(table.c.id))
            new_ids = set(result.scalars().all())
            added_ids.update(new_ids)
            count = len(new_ids)
        else:
            result = await session.execute(statement)
            count = result.rowcount or 0
        inserted += count
        skipped += len(values) - count
    return inserted, skipped


async def restore(
    session: AsyncSession, payload: dict, *, commit: bool = True,
    file_journal: list[Path] | None = None,
) -> dict:
    """Rollback newly created files along with a failed database transaction.

    A caller using commit=False owns the journal until its final verification
    and commit (disaster restore). Existing files are never overwritten.
    """
    journal = file_journal if file_journal is not None else []
    try:
        summary = await _restore(session, payload, file_journal=journal)
    except BaseException:
        try:
            await session.rollback()
        finally:
            rollback_files(journal)
        raise
    if commit:
        try:
            await session.commit()
        except BaseException:
            # A lost acknowledgement cannot prove the COMMIT failed. Preserve
            # complete, exclusive files so a committed row never loses its data;
            # an idempotent retry reconciles a failed/unknown delivery safely.
            await session.rollback()
            raise
    return summary


async def _restore(
    session: AsyncSession, payload: dict, *,
    file_journal: list[Path],
) -> dict:
    """Yedek yukler. Doner: tablo bazinda {inserted, skipped} ozeti.

    `commit=False`: yukleme islemi transaction'i commit ETMEZ -- cagiran
    (disaster restore) dogrulamayi ayni transaction icinde yapip ya commit
    ya rollback eder (Faz 28). Normal merge endpoint'i default True ile
    onceki davranisi korur.
    """
    att_check = check_attachments_integrity(payload)
    if not att_check["ok"]:
        errors = []
        if att_check["missing"]:
            errors.append(f"eksik ekler: {', '.join(att_check['missing'])}")
        if att_check["corrupt"]:
            errors.append(f"bozuk ekler: {', '.join(att_check['corrupt'])}")
        raise ValueError(f"Yedek ek bütünlük hatası: {'; '.join(errors)}")

    # Validate every destination before the first database or file write.
    _document_files(payload)
    summary: dict[str, dict[str, int]] = {}
    self_references = self_fk_columns()
    added_ids: dict[str, set] = {name: set() for name in self_references}

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
        inserted, skipped = await _insert_batch(session, table_name, rows, added_ids=added_ids.get(table_name))
        entry: dict = {"inserted": inserted, "skipped": skipped}
        if secret_rows:
            entry["secret_skipped"] = len(secret_rows)
        summary[table_name] = entry

    # 2. Asama: self-FK referanslarini geri bagla.
    for table_name, columns in self_references.items():
        rows = _rows(payload, table_name)
        if not rows:
            continue
        table = Base.metadata.tables[table_name]
        fixed = 0
        for row in rows:
            if _coerce(row["id"], table.c.id.type) not in added_ids[table_name]:
                continue
            references = {column: _coerce(row[column], table.c[column].type)
                          for column in columns if row.get(column) is not None}
            if not references:
                continue
            result = await session.execute(
                update(table).where(table.c.id == _coerce(row["id"], table.c.id.type)).values(references)
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
    files_restored = restore_files(payload, journal=file_journal)
    if files_restored:
        summary["_files"] = {"restored": files_restored}
    attachments_restored = restore_attachments(payload, journal=file_journal)
    if attachments_restored:
        summary["_attachments"] = {"restored": attachments_restored}

    restored_total = sum(
        entry["inserted"] for entry in summary.values() if "inserted" in entry
    )
    await log_event(
        session, verb="backup.restored",
        payload={"restored": restored_total, "tables": summary},
    )
    await session.flush()
    return summary


def rollback_files(journal: list[Path]) -> None:
    """Remove only files created by this restore, never pre-existing data."""
    for path in reversed(journal):
        path.unlink(missing_ok=True)
    journal.clear()


def _document_files(payload: dict) -> list[tuple[Path, bytes]]:
    from app.modules.document.service import DOCUMENTS_DIR

    files = payload.get("files") or {}
    if not isinstance(files, dict):
        raise ValueError("Geçersiz belge dosyaları")
    root = DOCUMENTS_DIR.resolve()
    prepared = []
    for doc_id, info in files.items():
        try:
            directory = root / str(uuid.UUID(str(doc_id)))
            filename = info["filename"]
            if (not isinstance(filename, str) or filename in {"", ".", ".."}
                    or "/" in filename or "\\" in filename):
                raise ValueError("Geçersiz belge dosya adı")
            target = directory / filename
            if directory.is_symlink() or target.is_symlink():
                raise ValueError("Belge hedefi sembolik bağlantı olamaz")
            content = base64.b64decode(info["data_b64"], validate=True)
            if target.exists() and target.read_bytes() != content:
                raise ValueError("Belge dosyası çakışması; mevcut dosya korundu")
            prepared.append((target, content))
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Geçersiz veya çakışan belge yedeği: " + str(error)) from error
    return prepared


def _write_missing(target: Path, content: bytes, journal: list[Path]) -> bool:
    if target.is_symlink():
        raise ValueError("Yedek hedefi sembolik bağlantı olamaz")
    if target.exists():
        if target.read_bytes() != content:
            raise ValueError("Yedek dosyası çakışması; mevcut dosya korundu")
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    # Publish a complete file atomically, without replacing a concurrent writer.
    handle, temporary_name = tempfile.mkstemp(prefix=".restore-", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "wb") as sink:
            sink.write(content)
            sink.flush()
            os.fsync(sink.fileno())
        os.link(temporary, target)
        journal.append(target)
    finally:
        temporary.unlink(missing_ok=True)
    return True


def restore_files(payload: dict, *, journal: list[Path] | None = None) -> int:
    """Validate paths and preserve existing document content; errors are visible."""
    own_journal = journal if journal is not None else []
    restored = 0
    try:
        for target, content in _document_files(payload):
            restored += int(_write_missing(target, content, own_journal))
    except BaseException:
        rollback_files(own_journal)
        raise
    return restored


def restore_attachments(payload: dict, *, journal: list[Path] | None = None) -> int:
    from app.modules.note import storage as attachment_storage

    check = check_attachments_integrity(payload)
    if not check["ok"]:
        raise ValueError("Yedek ek bütünlük hatası")
    own_journal = journal if journal is not None else []
    restored = 0
    try:
        for digest, data_b64 in (payload.get("attachments") or {}).items():
            target = attachment_storage.blob_path(digest)
            restored += int(_write_missing(target, base64.b64decode(data_b64, validate=True), own_journal))
    except BaseException:
        rollback_files(own_journal)
        raise
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
