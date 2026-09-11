"""Faz 1: 0048 migration'i upgrade/downgrade turunda satirlari korur.

Postgres + alembic zinciri gerektirir (test_media_domain_migration.py deseni).
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import subprocess
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings

HEAD_REVISION = "0048_learning_workspace"
LEGACY_REVISION = "0047_media_session_action"
BACKEND = pathlib.Path(__file__).resolve().parents[1]


def _alembic(revision: str) -> None:
    direction = "upgrade" if revision == HEAD_REVISION else "downgrade"
    env = {**os.environ, "DATABASE_URL": settings.database_url}
    result = subprocess.run(
        ["alembic", direction, revision],
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
                return result.mappings().all()
    finally:
        await engine.dispose()


def _count(sql: str, parameters: dict | None = None) -> int:
    rows = asyncio.run(_execute(sql, parameters))
    return int(rows[0]["count"])


_AREA = uuid.uuid4()
_TOPIC = uuid.uuid4()
_RESOURCE = uuid.uuid4()


def _seed() -> None:
    asyncio.run(
        _execute(
            "insert into entity (id,type,title) values"
            " (:area,'study_area','Migration alani'),"
            " (:topic,'study_topic','Migration konusu'),"
            " (:resource,'learning_resource','Migration kaynagi')",
            {"area": _AREA, "topic": _TOPIC, "resource": _RESOURCE},
        )
    )
    asyncio.run(
        _execute(
            "insert into study_area (id,active,position) values (:area,true,0)",
            {"area": _AREA},
        )
    )
    asyncio.run(
        _execute(
            """insert into study_topic
               (id,area_id,status,confidence,target_min,position,mastery,
                interval_days,ease,review_count)
               values (:topic,:area,'done',4,60,0,75,3,2.7,2)""",
            {"topic": _TOPIC, "area": _AREA},
        )
    )
    asyncio.run(
        _execute(
            """insert into learning_resource
               (id,topic_id,url,kind,position,source,estimated_min)
               values (:resource,:topic,'https://example.com/x','article',0,'import',25)""",
            {"resource": _RESOURCE, "topic": _TOPIC},
        )
    )


def _cleanup() -> None:
    asyncio.run(
        _execute(
            "delete from entity where id = any(cast(:ids as uuid[]))",
            {"ids": [str(_AREA), str(_TOPIC), str(_RESOURCE)]},
        )
    )


def _column_count(table: str, column: str) -> int:
    return _count(
        "select count(*) as count from information_schema.columns"
        " where table_name = :table and column_name = :column",
        {"table": table, "column": column},
    )


def _constraint_count(name: str) -> int:
    return _count(
        "select count(*) as count from pg_constraint where conname = :name", {"name": name}
    )


def _index_count(name: str) -> int:
    return _count(
        "select count(*) as count from pg_indexes where indexname = :name", {"name": name}
    )


def test_learning_workspace_migration_roundtrip_keeps_rows() -> None:
    _alembic(HEAD_REVISION)
    _seed()
    try:
        # Upgrade hali: yeni kolon/kisit/index'ler yerinde.
        assert _column_count("study_topic", "mastery") == 1
        assert _column_count("study_topic", "next_review_at") == 1
        assert _column_count("learning_resource", "bookmark_id") == 1
        assert _column_count("learning_resource", "source") == 1
        assert _constraint_count("study_topic_status_check") == 1
        assert _constraint_count("learning_resource_bookmark_uniq") == 0
        assert _index_count("learning_resource_bookmark_uniq") == 1
        assert _index_count("study_topic_next_review_idx") == 1
        assert _index_count("study_topic_last_studied_idx") == 1

        _alembic(LEGACY_REVISION)
        # Downgrade kolonlari ve kisitlari dusurur.
        assert _column_count("study_topic", "mastery") == 0
        assert _column_count("study_topic", "ease") == 0
        assert _column_count("learning_resource", "bookmark_id") == 0
        assert _column_count("learning_resource", "course_id") == 0
        assert _constraint_count("study_topic_status_check") == 0
        assert _constraint_count("course_progress_pct_check") == 0
        assert _index_count("learning_resource_bookmark_uniq") == 0
        assert _index_count("study_topic_next_review_idx") == 0
        # Satirlar DURUR -- downgrade veri silmez.
        assert _count("select count(*) as count from study_topic") == 1
        assert _count("select count(*) as count from learning_resource") == 1
        assert _count("select count(*) as count from study_area") == 1
        remaining = asyncio.run(
            _execute("select status from study_topic where id = :topic", {"topic": _TOPIC})
        )
        assert remaining[0]["status"] == "done"
    finally:
        _alembic(HEAD_REVISION)

    # Yeniden upgrade: kolonlar geri gelir, satirlar hala yerinde.
    assert _column_count("study_topic", "mastery") == 1
    assert _index_count("study_topic_next_review_idx") == 1
    assert _count("select count(*) as count from study_topic") == 1
    # Yeni kolonlar varsayilanlarina doner (downgrade'de dusen veri geri gelmez
    # -- kayit silinmedi, yalnizca yeni alanlar sifirlandi).
    defaults = asyncio.run(
        _execute(
            "select mastery, interval_days, review_count from study_topic where id = :topic",
            {"topic": _TOPIC},
        )
    )
    assert defaults[0]["mastery"] is None
    assert defaults[0]["interval_days"] == 0
    assert defaults[0]["review_count"] == 0
    _cleanup()
