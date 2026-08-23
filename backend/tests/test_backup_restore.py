from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.db import Base, SessionLocal
from app.modules.system import export, restore


@pytest.mark.no_database
def test_backup_policy_covers_every_table_except_explicit_secrets() -> None:
    covered = set(export.backup_table_names())
    excluded = export.BACKUP_EXCLUDED_TABLES

    assert excluded == {"oauth_token"}
    assert covered == set(Base.metadata.tables) - excluded


async def test_backup_round_trip_restores_operational_and_user_tables() -> None:
    view_id = uuid.uuid4()
    batch_id = uuid.uuid4()
    parent_id = uuid.uuid4()
    child_id = uuid.uuid4()
    async with SessionLocal() as session:
        await session.execute(
            text(
                "insert into entity (id,type,title,search_text) values "
                "(:parent,'todo','Üst görev',''),(:child,'todo','Alt görev','')"
            ),
            {"parent": parent_id, "child": child_id},
        )
        await session.execute(
            text(
                "insert into todo (id,status,priority,position,parent_id) values "
                "(:parent,'open',2,0,null),(:child,'open',2,0,:parent)"
            ),
            {"parent": parent_id, "child": child_id},
        )
        await session.execute(
            text(
                "insert into saved_view (id,name,module,filter,pinned,position) "
                "values (:id,'Bugün','todo','{}',true,2)"
            ),
            {"id": view_id},
        )
        await session.execute(
            text(
                "insert into notification "
                "(id,kind,title,dedup_key,importance,created_at) "
                "values (41,'test','Bildirim','backup-test',2,now())"
            )
        )
        await session.execute(
            text(
                "insert into source_sync_batch "
                "(id,status,source_ids,total_sources,completed_sources) "
                "values (:id,'completed','[\"osym\"]',1,1)"
            ),
            {"id": batch_id},
        )
        await session.execute(
            text(
                "insert into source_run "
                "(id,source,status,items_found,batch_id,started_at,finished_at) "
                "values (51,'osym','ok',3,:id,now(),now())"
            ),
            {"id": batch_id},
        )
        await session.execute(
            text("insert into setting (key,value) values ('backup.test','true')")
        )
        await session.commit()

        payload = await export.full_json(session)
        # Yedek satır sırası FK sırası değildir; child önce gelse de restore çalışmalı.
        payload["modules"]["todo"].reverse()

        assert payload["modules"]["saved_view"][0]["id"] == str(view_id)
        assert payload["modules"]["notification"][0]["dedup_key"] == "backup-test"
        assert payload["modules"]["source_sync_batch"][0]["id"] == str(batch_id)
        assert payload["modules"]["source_run"][0]["batch_id"] == str(batch_id)

        names = ", ".join(f'"{table.name}"' for table in reversed(Base.metadata.sorted_tables))
        await session.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"))
        await session.commit()

        summary = await restore.restore(session, payload)

        assert summary["saved_view"]["inserted"] == 1
        assert summary["notification"]["inserted"] == 1
        assert summary["source_sync_batch"]["inserted"] == 1
        assert summary["source_run"]["inserted"] == 1
        assert (
            await session.execute(
                text("select count(*) from saved_view where id=:id"), {"id": view_id}
            )
        ).scalar_one() == 1
        assert (
            await session.execute(
                text("select count(*) from source_run where batch_id=:id"), {"id": batch_id}
            )
        ).scalar_one() == 1
        assert (
            await session.execute(text("select parent_id from todo where id=:id"), {"id": child_id})
        ).scalar_one() == parent_id
