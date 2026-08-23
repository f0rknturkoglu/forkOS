from __future__ import annotations

import asyncio
import os
import pathlib
import subprocess
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings

MIGRATION_REVISION = "0026_media_domain"
LEGACY_REVISION = "0025_document_folder_source"
BACKEND = pathlib.Path(__file__).resolve().parents[1]


def _alembic(revision: str) -> None:
    env = {**os.environ, "DATABASE_URL": settings.database_url}
    result = subprocess.run(
        ["alembic", "upgrade" if revision != LEGACY_REVISION else "downgrade", revision],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


async def _execute(sql: str, parameters: dict | None = None):
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.begin() as connection:
            result = await connection.execute(text(sql), parameters or {})
            if result.returns_rows:
                return result.mappings().one()
    finally:
        await engine.dispose()


def test_populated_legacy_media_row_survives_upgrade_and_downgrade():
    entity_id = uuid.uuid4()
    batch_id = uuid.uuid4()
    _alembic(LEGACY_REVISION)
    try:
        asyncio.run(
            _execute(
                "insert into entity (id,type,title) values (:id,'media_item','Legacy')",
                {"id": entity_id},
            )
        )
        asyncio.run(
            _execute(
                """insert into media_item
                   (id,kind,status,progress,total,score,notes,started_at,finished_at,meta)
                   values (:id,'book','completed',120,320,9,'legacy notes',
                           '2025-01-02T03:04:05Z','2025-02-03T04:05:06Z',
                           '{"legacy": true}')""",
                {"id": entity_id},
            )
        )
        asyncio.run(
            _execute(
                """insert into source_sync_batch
                   (id,status,source_ids,total_sources)
                   values (:id,'completed','["legacy-source"]',1)""",
                {"id": batch_id},
            )
        )

        _alembic(MIGRATION_REVISION)
        upgraded = asyncio.run(
            _execute(
                """select progress::text, total::text, score, notes, started_at,
                          finished_at, meta, favorite, owned, ownership, monitored,
                          provider_ids
                   from media_item where id=:id""",
                {"id": entity_id},
            )
        )
        assert upgraded["progress"] == "120.00"
        assert upgraded["total"] == "320.00"
        assert upgraded["score"] == 9
        assert upgraded["notes"] == "legacy notes"
        assert upgraded["meta"] == {"legacy": True}
        assert not upgraded["favorite"]
        assert not upgraded["owned"]
        assert upgraded["ownership"] == {}
        assert not upgraded["monitored"]
        assert upgraded["provider_ids"] == {}
        batch = asyncio.run(
            _execute("select scope from source_sync_batch where id=:id", {"id": batch_id})
        )
        assert batch["scope"] == "opportunity"

        asyncio.run(
            _execute(
                "update media_item set progress=121.75,total=321.25 where id=:id",
                {"id": entity_id},
            )
        )
        _alembic(LEGACY_REVISION)
        downgraded = asyncio.run(
            _execute(
                "select progress,total,score,notes,meta from media_item where id=:id",
                {"id": entity_id},
            )
        )
        assert downgraded == {
            "progress": 122,
            "total": 321,
            "score": 9,
            "notes": "legacy notes",
            "meta": {"legacy": True},
        }
        scope_column = asyncio.run(
            _execute(
                """select count(*) as count from information_schema.columns
                   where table_schema='public' and table_name='source_sync_batch'
                     and column_name='scope'"""
            )
        )
        assert scope_column["count"] == 0
    finally:
        _alembic(MIGRATION_REVISION)
