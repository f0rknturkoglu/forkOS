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


async def test_failed_restore_leaves_original_data_intact() -> None:
    """Faz 28: restore ortasinda hata olursa (FK ihlali gibi) truncate/import
    ROLLBACK olmali -- eski seed veri yerinde kalir."""
    async with SessionLocal() as session:
        todo_id = await _seed(session)
        await session.commit()
        payload = await export.full_json(session)

        # Ebeveyni payload'dan dusur: cocugun parent_id'si sarkan kalir,
        # restore ortasinda FK ihlali -> tum transaction rollback olmali.
        parent_id = str(
            (
                await session.execute(
                    text("select parent_id from todo where id=:id"), {"id": todo_id}
                )
            ).scalar_one()
        )
        payload["entities"] = [
            row for row in payload["entities"] if row["id"] != parent_id
        ]
        payload["modules"]["todo"] = [
            row for row in payload["modules"]["todo"] if row["id"] != parent_id
        ]

        with pytest.raises(Exception):  # noqa: B017 -- FK ihlali ture bagli
            await disaster_restore(session, payload)

        # Rollback sonrasi seed veri hala duruyor (gorev + ebeveyn).
        remaining = (
            await session.execute(text("select count(*) from todo where id=:id"), {"id": todo_id})
        ).scalar_one()
        parent_left = (
            await session.execute(text("select count(*) from todo where id=:id"), {"id": parent_id})
        ).scalar_one()
        assert remaining == 1
        assert parent_left == 1
        await session.rollback()


def test_cli_requires_safety_dump_before_any_db_write() -> None:
    cli = _load_cli()
    # --safety-dump verilmezse argparse istegi reddeder (DB'ye dokunmaz).
    with pytest.raises(SystemExit):
        cli.parse_args(["--file", str(CLI_PATH), "--confirm", cli.CONFIRM_VALUE])
    # Safety dump yoksa/boşsa CLI kendi mesajiyla durur.
    with pytest.raises(SystemExit, match="safety dump"):
        cli.parse_args(
            [
                "--file", str(CLI_PATH),
                "--confirm", cli.CONFIRM_VALUE,
                "--safety-dump", "/yok/boyle.dump",
            ]
        )


def test_cli_full_flow_safety_migrate_restore_verify_commit(tmp_path) -> None:
    """Faz 28: CLI safety-dump dogrulamasi + migration + transactional restore + commit."""
    import asyncio as _asyncio
    import json as _json

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.config import settings

    cli = _load_cli()

    # Paylasilan engine pytest loop'una bagli olabilir; test icin ayri engine.
    def _local_session():
        local_engine = create_async_engine(settings.database_url)
        return local_engine, async_sessionmaker(local_engine, expire_on_commit=False)

    async def _seed_and_export():
        local_engine, Session = _local_session()
        try:
            async with Session() as session:
                todo_id = await _seed(session)
                await session.commit()
                payload = await export.full_json(session)
                return str(todo_id), payload
        finally:
            await local_engine.dispose()

    todo_id, payload = _asyncio.run(_seed_and_export())

    backup_file = tmp_path / "yedek.json"
    backup_file.write_text(_json.dumps(payload), encoding="utf-8")
    safety = tmp_path / "pre-disaster.dump"
    safety.write_bytes(b"pg_dump-placeholder")

    code = cli.run(
        ["--file", str(backup_file), "--safety-dump", str(safety),
         "--confirm", cli.CONFIRM_VALUE]
    )
    assert code == 0

    # Commit edildi: gorev yeni session'da gorunur.
    async def _check():
        local_engine, Session = _local_session()
        try:
            async with Session() as session:
                return (
                    await session.execute(
                        text("select count(*) from todo where id=:id"), {"id": todo_id}
                    )
                ).scalar_one()
        finally:
            await local_engine.dispose()

    assert _asyncio.run(_check()) == 1


def test_makefile_dumps_from_db_container_not_api() -> None:
    """Faz 28: pg_dump db konteynerinde alinir (API imajinda pg_dump yok)."""
    makefile = (BACKEND_DIR.parent / "Makefile").read_text(encoding="utf-8")
    target = makefile[makefile.index("disaster-restore:"):]
    assert "exec -T db" in target and "pg_dump" in target
    # CLI satirinda pg_dump cagrisi yok -- api konteyneri dump yapmaz.
    cli_line = [line for line in target.splitlines() if "disaster_restore.py" in line]
    assert cli_line and "pg_dump" not in cli_line[0]


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
    # Safety dump olarak CLI_PATH'in kendisi verilir (var olan dosya).
    safety = str(CLI_PATH)

    with pytest.raises(SystemExit, match="onay"):
        cli.parse_args(["--file", str(CLI_PATH), "--confirm", "wrong", "--safety-dump", safety])
    with pytest.raises(SystemExit, match="glob"):
        cli.parse_args(
            [
                "--file", str(BACKEND_DIR / "backups/*.gz"),
                "--confirm", cli.CONFIRM_VALUE,
                "--safety-dump", safety,
            ]
        )
    with pytest.raises(SystemExit, match="bulunamadi"):
        cli.parse_args(
            [
                "--file", "/yok/boyle-dosya.json.gz",
                "--confirm", cli.CONFIRM_VALUE,
                "--safety-dump", safety,
            ]
        )
