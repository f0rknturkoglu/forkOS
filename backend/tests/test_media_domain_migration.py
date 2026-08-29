from __future__ import annotations

import asyncio
import os
import pathlib
import subprocess
import uuid

import pytest
import sqlalchemy
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
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
                          provider_id, provider_ids
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
        assert upgraded["provider_id"] is None
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
        _alembic("head")


def test_media_item_provider_identity_has_database_unique_partial_index():
    first_id = uuid.uuid4()
    second_id = uuid.uuid4()
    _alembic(LEGACY_REVISION)
    _alembic(MIGRATION_REVISION)
    try:
        asyncio.run(
            _execute(
                "insert into entity (id,type,title) values "
                "(:first_id,'media_item','First'),(:second_id,'media_item','Second')",
                {"first_id": first_id, "second_id": second_id},
            )
        )
        asyncio.run(
            _execute(
                "insert into media_item (id,kind,provider,provider_id) "
                "values (:id,'book','openlibrary','same')",
                {"id": first_id},
            )
        )
        with pytest.raises(IntegrityError):
            asyncio.run(
                _execute(
                    "insert into media_item (id,kind,provider,provider_id) "
                    "values (:id,'book','openlibrary','same')",
                    {"id": second_id},
                )
            )
    finally:
        asyncio.run(_execute("delete from entity where id in (:first_id,:second_id)", {
            "first_id": first_id,
            "second_id": second_id,
        }))
        _alembic("head")


def test_raw_media_parent_deletion_requires_explicit_child_entity_deletion():
    media_id = uuid.uuid4()
    unit_id = uuid.uuid4()
    child_unit_id = uuid.uuid4()
    cycle_id = uuid.uuid4()
    consumption_id = uuid.uuid4()
    _alembic(LEGACY_REVISION)
    _alembic(MIGRATION_REVISION)
    try:
        asyncio.run(
            _execute(
                """insert into entity (id,type,title) values
                   (:media_id,'media_item','Media'),
                   (:unit_id,'media_unit','Unit'),
                   (:child_unit_id,'media_unit','Child unit'),
                   (:cycle_id,'media_cycle','Cycle'),
                   (:consumption_id,'media_consumption','Consumption')""",
                {
                    "media_id": media_id,
                    "unit_id": unit_id,
                    "child_unit_id": child_unit_id,
                    "cycle_id": cycle_id,
                    "consumption_id": consumption_id,
                },
            )
        )
        asyncio.run(
            _execute(
                "insert into media_item (id,kind) values (:id,'book')",
                {"id": media_id},
            )
        )
        asyncio.run(
            _execute(
                """insert into media_unit (id,media_id,parent_id,unit_type)
                   values (:id,:media_id,:parent_id,'chapter')""",
                {"id": unit_id, "media_id": media_id, "parent_id": None},
            )
        )
        asyncio.run(
            _execute(
                """insert into media_unit (id,media_id,parent_id,unit_type)
                   values (:id,:media_id,:parent_id,'chapter')""",
                {"id": child_unit_id, "media_id": media_id, "parent_id": unit_id},
            )
        )
        asyncio.run(
            _execute(
                """insert into media_cycle (id,media_id,ordinal,started_at)
                   values (:id,:media_id,1,now())""",
                {"id": cycle_id, "media_id": media_id},
            )
        )
        asyncio.run(
            _execute(
                """insert into media_consumption
                   (id,media_id,cycle_id,unit_id,client_uuid,action)
                   values (:id,:media_id,:cycle_id,:unit_id,:client_uuid,'quick')""",
                {
                    "id": consumption_id,
                    "media_id": media_id,
                    "cycle_id": cycle_id,
                    "unit_id": child_unit_id,
                    "client_uuid": uuid.uuid4(),
                },
            )
        )

        with pytest.raises(IntegrityError):
            asyncio.run(_execute("delete from media_item where id=:id", {"id": media_id}))

        asyncio.run(
            _execute("delete from entity where id=:id", {"id": consumption_id})
        )
        asyncio.run(_execute("delete from entity where id=:id", {"id": cycle_id}))
        asyncio.run(_execute("delete from entity where id=:id", {"id": unit_id}))
        child_unit = asyncio.run(
            _execute("select parent_id from media_unit where id=:id", {"id": child_unit_id})
        )
        assert child_unit["parent_id"] is None
        asyncio.run(_execute("delete from entity where id=:id", {"id": child_unit_id}))
        asyncio.run(_execute("delete from entity where id=:id", {"id": media_id}))

        remaining = asyncio.run(
            _execute(
                """select count(*) as count from entity
                   where id in (:media_id,:unit_id,:child_unit_id,:cycle_id,:consumption_id)""",
                {
                    "media_id": media_id,
                    "unit_id": unit_id,
                    "child_unit_id": child_unit_id,
                    "cycle_id": cycle_id,
                    "consumption_id": consumption_id,
                },
            )
        )
        assert remaining["count"] == 0
    finally:
        _alembic("head")


def test_downgrade_removes_new_domain_entities_and_their_links():
    media_id = uuid.uuid4()
    unit_id = uuid.uuid4()
    cycle_id = uuid.uuid4()
    consumption_id = uuid.uuid4()
    collection_id = uuid.uuid4()
    _alembic(LEGACY_REVISION)
    _alembic(MIGRATION_REVISION)
    try:
        asyncio.run(
            _execute(
                """insert into entity (id,type,title) values
                   (:media_id,'media_item','Media'),
                   (:unit_id,'media_unit','Unit'),
                   (:cycle_id,'media_cycle','Cycle'),
                   (:consumption_id,'media_consumption','Consumption'),
                   (:collection_id,'media_collection','Collection')""",
                {
                    "media_id": media_id,
                    "unit_id": unit_id,
                    "cycle_id": cycle_id,
                    "consumption_id": consumption_id,
                    "collection_id": collection_id,
                },
            )
        )
        asyncio.run(
            _execute("insert into media_item (id,kind) values (:id,'book')", {"id": media_id})
        )
        asyncio.run(
            _execute(
                """insert into media_unit (id,media_id,unit_type)
                   values (:id,:media_id,'chapter')""",
                {"id": unit_id, "media_id": media_id},
            )
        )
        asyncio.run(
            _execute(
                """insert into media_cycle (id,media_id,ordinal,started_at)
                   values (:id,:media_id,1,now())""",
                {"id": cycle_id, "media_id": media_id},
            )
        )
        asyncio.run(
            _execute(
                """insert into media_consumption
                   (id,media_id,cycle_id,client_uuid,action)
                   values (:id,:media_id,:cycle_id,:client_uuid,'quick')""",
                {
                    "id": consumption_id,
                    "media_id": media_id,
                    "cycle_id": cycle_id,
                    "client_uuid": uuid.uuid4(),
                },
            )
        )
        asyncio.run(
            _execute(
                "insert into media_collection (id) values (:id)", {"id": collection_id}
            )
        )
        asyncio.run(
            _execute(
                """insert into link (from_id,to_id,relation)
                   values (:from_id,:to_id,'media.collection_item')""",
                {"from_id": collection_id, "to_id": media_id},
            )
        )

        _alembic(LEGACY_REVISION)

        stale_entities = asyncio.run(
            _execute(
                """select count(*) as count from entity
                   where id in (:unit_id,:cycle_id,:consumption_id,:collection_id)""",
                {
                    "unit_id": unit_id,
                    "cycle_id": cycle_id,
                    "consumption_id": consumption_id,
                    "collection_id": collection_id,
                },
            )
        )
        assert stale_entities["count"] == 0
        stale_links = asyncio.run(
            _execute(
                """select count(*) as count from link
                   where from_id=:collection_id or to_id=:collection_id""",
                {"collection_id": collection_id},
            )
        )
        assert stale_links["count"] == 0
    finally:
        _alembic("head")
        asyncio.run(_execute("delete from entity where id=:id", {"id": media_id}))


def test_book_to_media_item_roundtrip_preserves_links_and_events():
    """Faz 11: learning.book -> media_item. entity.id KORUNUR; downgrade geri alir."""
    book_revision = "0027_book_to_media_item"
    entity_id = uuid.uuid4()
    bookmark_id = uuid.uuid4()
    _alembic(LEGACY_REVISION)
    try:
        # 1) Eski duzen: book entity + kayit + event + bookmark linki.
        asyncio.run(
            _execute(
                "insert into entity (id,type,title) values (:id,'book','Faz11 Kitap')",
                {"id": entity_id},
            )
        )
        asyncio.run(
            _execute(
                """insert into book (id,author,status,total_pages,current_page,
                                     started_at,finished_at,rating,notes)
                   values (:id,'Yazar X','want',300,42,'2026-01-05','2026-02-01',4,'okunacak')""",
                {"id": entity_id},
            )
        )
        asyncio.run(
            _execute(
                """insert into event (verb,entity_id,entity_type,payload)
                   values ('book.finished',:eid,'book','{}')""",
                {"eid": entity_id},
            )
        )
        asyncio.run(
            _execute(
                """insert into entity (id,type,title) values (:id,'bookmark','Kaynak sayfa')""",
                {"id": bookmark_id},
            )
        )
        asyncio.run(
            _execute(
                """insert into link (from_id,to_id,relation,created_at)
                   values (:from,:to,'saved_from',now())""",
                {"from": bookmark_id, "to": entity_id},
            )
        )

        # 2) Upgrade: book -> media_item (0027, medya domain'inin ustune).
        _alembic(book_revision)

        row = asyncio.run(
            _execute(
                """select m.id, m.kind, m.status, m.progress::text, m.total::text,
                          m.score, m.notes, m.meta ->> 'author' as author,
                          m.progress_measure, m.meta ->> 'legacy_book' as legacy,
                          e.type
                   from media_item m join entity e on e.id = m.id
                   where m.id = :id""",
                {"id": entity_id},
            )
        )
        assert row["id"] == entity_id, "entity.id korunmali"
        assert row["kind"] == "book" and row["status"] == "planned", row
        assert row["progress"] in ("42", "42.00") and row["total"] in ("300", "300.00")
        assert row["score"] == 4 and row["notes"] == "okunacak"
        assert row["author"] == "Yazar X" and row["progress_measure"] == "page"
        assert row["legacy"] == "true" and row["type"] == "media_item"

        # Gecmis event ve bookmark linki aynen duruyor.
        event = asyncio.run(
            _execute(
                "select verb from event where entity_id = :id",
                {"id": entity_id},
            )
        )
        assert event["verb"] == "book.finished"
        link = asyncio.run(
            _execute(
                "select relation from link where to_id = :id",
                {"id": entity_id},
            )
        )
        assert link["relation"] == "saved_from"

        # 3) Downgrade: media_item -> book (yalniz legacy_book isaretliler).
        _alembic(LEGACY_REVISION)

        book = asyncio.run(
            _execute(
                """select b.author, b.status, b.current_page, b.total_pages,
                          b.rating, b.notes, e.type
                   from book b join entity e on e.id = b.id where b.id = :id""",
                {"id": entity_id},
            )
        )
        assert book["author"] == "Yazar X" and book["status"] == "want"
        assert book["current_page"] == 42 and book["total_pages"] == 300
        assert book["rating"] == 4 and book["notes"] == "okunacak"
        assert book["type"] == "book"
        try:
            asyncio.run(_execute("select 1 from media_item where id = :id", {"id": entity_id}))
            raise AssertionError("tasinan media_item kaydi silinmeli")
        except sqlalchemy.exc.NoResultFound:
            pass
        # Gecmis veri downgrade'de de duruyor.
        assert asyncio.run(
            _execute("select 1 from event where entity_id = :id", {"id": entity_id})
        )
        assert asyncio.run(
            _execute("select 1 from link where to_id = :id", {"id": entity_id})
        )
    finally:
        # DB'yi her zaman HEAD'e birak (Faz 0 dersi: sonraki testler head ister).
        _alembic("head")
        asyncio.run(
            _execute(
                "delete from entity where id in (:a, :b)",
                {"a": entity_id, "b": bookmark_id},
            )
        )


def test_book_downgrade_tolerates_null_media_progress():
    """Downgrade: media_item.progress NULL ise current_page'e 0 yazilir.

    progress nullable ama book.current_page NOT NULL -- medya arayuzunde
    ilerlemesi temizlenmis kitap geri alinirken patlamamali (Faz 11 notu).
    """
    book_revision = "0027_book_to_media_item"
    entity_id = uuid.uuid4()
    _alembic(LEGACY_REVISION)
    try:
        asyncio.run(
            _execute(
                "insert into entity (id,type,title) values (:id,'book','Null progress')",
                {"id": entity_id},
            )
        )
        asyncio.run(
            _execute(
                """insert into book (id,author,status,total_pages,current_page,
                                     started_at,finished_at,rating,notes)
                   values (:id,'Yazar','want',200,42,null,null,null,null)""",
                {"id": entity_id},
            )
        )

        _alembic(book_revision)
        # Medya arayuzunde ilerleme temizlendi (progress NULL).
        asyncio.run(
            _execute(
                "update media_item set progress = null where id = :id",
                {"id": entity_id},
            )
        )

        _alembic(LEGACY_REVISION)
        row = asyncio.run(
            _execute(
                "select current_page from book where id = :id",
                {"id": entity_id},
            )
        )
        assert row["current_page"] == 0, row
    finally:
        _alembic("head")
        asyncio.run(
            _execute(
                "delete from entity where id = :id",
                {"id": entity_id},
            )
        )
