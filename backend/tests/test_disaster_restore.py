"""Faz 16: merge import ile gercek disaster restore ayrimi.

- `/backup/restore` MERGE eder: mevcut kayitlar degismez, eksikler eklenir.
- Preflight (`inspect_payload`) hicbir sey yazmadan yedegi inceler.
- Disaster restore app disi bakim islemidir: temiz schema + dogrulama.
- Onay degeri olmadan veya hatali dosyayla hicbir sey degismez.
"""

from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text

from app.db import SessionLocal
from app.modules.system import export, restore
from app.modules.system.disaster import disaster_restore

BACKEND_DIR = Path(__file__).resolve().parents[1]
CLI_PATH = BACKEND_DIR / "scripts" / "disaster_restore.py"


def _load_cli():
    spec = importlib.util.spec_from_file_location("disaster_cli", CLI_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


async def _seed(session) -> uuid.UUID:
    todo_id = uuid.uuid4()
    parent_id = uuid.uuid4()
    await session.execute(
        text("insert into entity (id, type, title, search_text) values (:id,'todo','Ebeveyn','')"),
        {"id": parent_id},
    )
    await session.execute(
        text("insert into todo (id, priority, status, position, parent_id) "
             "values (:id,2,'open',0,NULL)"),
        {"id": parent_id},
    )
    await session.execute(
        text("insert into entity (id, type, title, search_text) values (:id,'todo','Cocuk','')"),
        {"id": todo_id},
    )
    await session.execute(
        text("insert into todo (id, priority, status, position, parent_id) "
             "values (:id,1,'open',1,:parent)"),
        {"id": todo_id, "parent": parent_id},
    )
    await session.execute(
        text("insert into link (from_id, to_id, relation) values (:f,:t,'related')"),
        {"f": todo_id, "t": parent_id},
    )
    return todo_id


async def test_merge_import_adds_missing_and_keeps_existing() -> None:
    async with SessionLocal() as session:
        todo_id = await _seed(session)
        await session.commit()
        payload = await export.full_json(session)

        # Mevcut kayitlari DEGISTIRMEDEN eksikleri ekler: onceki veri duruyor.
        existing_priority = (
            await session.execute(text("select priority from todo where id=:id"), {"id": todo_id})
        ).scalar_one()
        summary = await restore.restore(session, payload)
        assert summary["todo"]["skipped"] >= 1
        assert (
            await session.execute(text("select priority from todo where id=:id"), {"id": todo_id})
        ).scalar_one() == existing_priority


async def test_disaster_restore_clean_schema_and_verify() -> None:
    async with SessionLocal() as session:
        await _seed(session)
        await session.commit()
        payload = await export.full_json(session)

        result = await disaster_restore(session, payload)
        await session.commit()

        verification = result["verification"]
        assert verification["row_counts"]["entity"] == len(payload["entities"])
        assert verification["row_counts"]["link"] == len(payload["links"])
        # restore() kendi backup.restored event'ini yazar (kural 3).
        assert verification["row_counts"]["event"] == len(payload["events"]) + 1
        assert verification["orphan_links"] == 0
        assert verification["orphan_parents"] == 0


async def test_verify_restore_catches_orphans() -> None:
    async with SessionLocal() as session:
        await _seed(session)
        await session.commit()
        payload = await export.full_json(session)

        # Simule hata: var olmayan entity'ye link satiri (yetim). FK bypass
        # gerekli -- normal yoldan FK, boyle bir satirin girmesini engeller.
        await session.execute(text("set session_replication_role = replica"))
        await session.execute(
            text("insert into link (from_id, to_id, relation) values (:f,:t,'related')"),
            {"f": uuid.uuid4(), "t": uuid.uuid4()},
        )
        await session.execute(text("set session_replication_role = default"))
        await session.commit()

        verification = await restore.verify_restore(session, payload)
        assert verification["orphan_links"] >= 1


def test_inspect_payload_flags_problems() -> None:
    base = {
        "version": 2,
        "manifest": {"app": "forkos", "row_counts": {
            "entities": 1, "links": 0, "events": 0,
            "modules": {"mystery_table": 1, "setting": 1},
        }},
        "entities": [{"id": str(uuid.uuid4())}],
        "links": [],
        "events": [],
        "modules": {
            "mystery_table": [{"x": 1}],
            "setting": [{"key": "media.tmdb_key", "value": "s"}],
        },
    }
    report = restore.inspect_payload(base)
    assert report["unknown_tables"] == ["mystery_table"]
    assert report["secret_settings"] == 1
    assert report["integrity_ok"] is True

    broken = dict(base)
    broken["manifest"]["row_counts"]["entities"] = 99
    assert restore.inspect_payload(broken)["integrity_ok"] is False

    missing = {k: v for k, v in base.items() if k != "events"}
    assert restore.inspect_payload(missing)["missing_sections"] == ["events"]


def test_parse_backup_versions() -> None:
    v1 = {"version": 1, "entities": [], "links": [], "events": [], "modules": {}}
    v2 = {"version": 2, "entities": [], "links": [], "events": [], "modules": {}}
    assert restore.parse_backup(__import__("json").dumps(v1).encode())["version"] == 1
    assert restore.parse_backup(__import__("json").dumps(v2).encode())["version"] == 2
    with pytest.raises(ValueError, match="desteklenmeyen"):
        restore.parse_backup(
            b'{"version": 3, "entities": [], "links": [], "events": [], "modules": {}}'
        )


def test_cli_requires_explicit_file_and_confirmation() -> None:
    cli = _load_cli()

    with pytest.raises(SystemExit, match="onay"):
        cli.parse_args(["--file", str(CLI_PATH), "--confirm", "wrong"])
    with pytest.raises(SystemExit, match="glob"):
        cli.parse_args(
            ["--file", str(BACKEND_DIR / "backups/*.gz"), "--confirm", cli.CONFIRM_VALUE]
        )
    with pytest.raises(SystemExit, match="bulunamadi"):
        cli.parse_args(
            ["--file", "/yok/boyle-dosya.json.gz", "--confirm", cli.CONFIRM_VALUE]
        )
