"""Durum kisitlarinin gercek upgrade/downgrade davranisi (Faz 10/11).

`tests/test_migrations.py` zinciri statik olarak dogrular; bu dosya kisitlarin
GERCEKTEN uygulandigini ve geri alindigini veritabani uzerinde sinar.
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import subprocess
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings

REVISION = "0055_status_constraints"
PREVIOUS = "0054_source_run_scope"
BACKEND = pathlib.Path(__file__).resolve().parents[1]


def _alembic(*args: str) -> None:
    result = subprocess.run(
        ["alembic", *args],
        cwd=BACKEND,
        env={**os.environ, "DATABASE_URL": settings.database_url},
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
                return result.mappings().all()
    finally:
        await engine.dispose()


async def _insert_opportunity(item_id: uuid.UUID, *, kind: str, status: str) -> None:
    await _execute(
        "insert into entity (id, type, title, search_text) values (:id, 'opportunity', 'X', '')",
        {"id": item_id},
    )
    await _execute(
        "insert into opportunity (id, kind, status, found_at, source) "
        "values (:id, :kind, :status, now(), 'constraint-test')",
        {"id": item_id, "kind": kind, "status": status},
    )


def test_status_constraints_reject_invalid_values_and_roll_back():
    """Kısıtlar geçerli değerleri kabul eder, uydurma değerleri reddeder."""
    valid_job = uuid.uuid4()
    valid_announcement = uuid.uuid4()
    asyncio.run(_insert_opportunity(valid_job, kind="job", status="discovered"))
    asyncio.run(_insert_opportunity(valid_announcement, kind="announcement", status="action_required"))

    try:
        # Duyuru durumu is ilanina yazilamaz.
        with pytest.raises(IntegrityError):
            asyncio.run(_insert_opportunity(uuid.uuid4(), kind="job", status="action_required"))
        # Uydurma durum hicbir ture yazilamaz.
        with pytest.raises(IntegrityError):
            asyncio.run(_insert_opportunity(uuid.uuid4(), kind="job", status="satisfied"))
        # Kaynak durumu bilinen kume ile sinirli.
        with pytest.raises(IntegrityError):
            asyncio.run(
                _execute(
                    "update opportunity set source_status = 'gone' where id = :id",
                    {"id": valid_job},
                )
            )
    finally:
        asyncio.run(
            _execute(
                "delete from entity where id = any(:ids)",
                {"ids": [str(valid_job), str(valid_announcement)]},
            )
        )


def test_constraints_survive_downgrade_and_upgrade():
    """Kısıtlar downgrade ile kalkar, upgrade ile geri gelir; veri korunur."""
    item_id = uuid.uuid4()
    try:
        _alembic("downgrade", PREVIOUS)
        # Kisit yokken uydurma deger yazilabilir (downgrade gercekten indirdi).
        asyncio.run(_insert_opportunity(item_id, kind="job", status="discovered"))
        asyncio.run(
            _execute(
                "update opportunity set status = 'legacy-value' where id = :id", {"id": item_id}
            )
        )
        # Geri donuste kisit geri gelir; mevcut ihlal eden satir varsa migration
        # BASARISIZ olurdu, bu yuzden once temizlenir.
        asyncio.run(
            _execute(
                "update opportunity set status = 'discovered' where id = :id", {"id": item_id}
            )
        )
        _alembic("upgrade", REVISION)
        rows = asyncio.run(
            _execute(
                "select count(*) as total from pg_constraint where conname like '%status_check%'"
            )
        )
        assert rows[0]["total"] >= 4
        with pytest.raises(IntegrityError):
            asyncio.run(
                _execute(
                    "update opportunity set status = 'legacy-value' where id = :id",
                    {"id": item_id},
                )
            )
    finally:
        asyncio.run(_execute("delete from entity where id = :id", {"id": item_id}))
        _alembic("upgrade", "head")
