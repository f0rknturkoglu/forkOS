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

    # Denylist dar kalmali: kullanici anlamli veri tam kapsanir.
    assert excluded == {"oauth_token", "source_run", "source_sync_batch"}
    assert covered == set(Base.metadata.tables) - excluded
    assert {
        "note",
        "todo",
        "project",
        "course",
        "media_item",
        "expense",
        "opportunity",
        "bookmark",
        "review",
        "document",
        "tag",
        "link",
        "event",
        "setting",
    } <= covered


async def test_backup_round_trip_restores_user_tables_and_skips_operational() -> None:
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
        # Operasyonel kayitlar kullanici yedegine GIRMEZ: satirlar var olsa bile
        # payload'da ve restore ozetinde gorunmezler.
        assert "source_sync_batch" not in payload["modules"]
        assert "source_run" not in payload["modules"]

        names = ", ".join(f'"{table.name}"' for table in reversed(Base.metadata.sorted_tables))
        await session.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"))
        await session.commit()

        summary = await restore.restore(session, payload)

        assert summary["saved_view"]["inserted"] == 1
        assert summary["notification"]["inserted"] == 1
        assert "source_sync_batch" not in summary
        assert "source_run" not in summary
        assert (
            await session.execute(
                text("select count(*) from saved_view where id=:id"), {"id": view_id}
            )
        ).scalar_one() == 1
        assert (
            await session.execute(
                text("select parent_id from todo where id=:id"), {"id": child_id}
            )
        ).scalar_one() == parent_id


async def test_backup_and_restore_local_documents(tmp_path, monkeypatch) -> None:
    from app.modules.document import service as doc_svc

    monkeypatch.setattr(doc_svc, "DOCUMENTS_DIR", tmp_path / "documents")
    async with SessionLocal() as session:
        doc_data = await doc_svc.create_local_document(
            session,
            title="test_cv.pdf",
            category="cv",
            mime="application/pdf",
            content=b"%PDF-1.4 test resume content",
        )
        doc_id = str(doc_data["id"])
        file_path = tmp_path / "documents" / doc_id / "test_cv.pdf"
        assert file_path.is_file()

        payload = await export.full_json(session)
        assert "files" in payload
        assert doc_id in payload["files"]
        assert payload["files"][doc_id]["filename"] == "test_cv.pdf"
        assert len(payload["files"][doc_id]["data_b64"]) > 0

        # Diskteki dosyayı sil
        file_path.unlink()
        assert not file_path.exists()

        # Restore çağrısı dosyayı diske geri açmalı
        summary = await restore.restore(session, payload)
        assert "_files" in summary
        assert summary["_files"]["restored"] >= 1
        assert file_path.is_file()
        assert file_path.read_bytes() == b"%PDF-1.4 test resume content"


async def test_markdown_export_includes_notes_todos_and_learning() -> None:
    async with SessionLocal() as session:
        note_id = uuid.uuid4()
        todo_id = uuid.uuid4()
        course_id = uuid.uuid4()
        await session.execute(
            text(
                "insert into entity (id, type, title, search_text) values "
                "(:note, 'note', 'Strateji Notu', ''), "
                "(:todo, 'todo', 'Raporu hazırla', ''), "
                "(:course, 'course', 'Python İleri', '')"
            ),
            {"note": note_id, "todo": todo_id, "course": course_id},
        )
        await session.execute(
            text(
                "insert into note (id, body, journal_day, pinned) values "
                "(:note, 'Stratejik büyüme hedefleri...', '2026-09-04', false)"
            ),
            {"note": note_id},
        )
        await session.execute(
            text(
                "insert into todo (id, status, priority, position) values "
                "(:todo, 'open', 3, 0)"
            ),
            {"todo": todo_id},
        )
        await session.execute(
            text(
                "insert into course (id, platform, status) values "
                "(:course, 'Coursera', 'in_progress')"
            ),
            {"course": course_id},
        )
        await session.commit()

        md = await export.markdown_export(session)
        assert "## Notes" in md
        assert "Strateji Notu" in md
        assert "Stratejik büyüme hedefleri..." in md
        assert "## Tasks" in md
        assert "- [ ] Raporu hazırla (P3)" in md
        assert "## Learning" in md
        assert "Python İleri" in md
        assert "Coursera" in md


async def test_backup_drive_failure_creates_notification(monkeypatch, tmp_path) -> None:
    from app.modules.system import backup as backup_svc

    monkeypatch.setattr(backup_svc, "BACKUP_DIR", tmp_path / "backups")

    async def mock_fail(*args, **kwargs):
        return "Simulated 403 Google Token Expired"

    monkeypatch.setattr(backup_svc, "upload_drive", mock_fail)

    async with SessionLocal() as session:
        await session.execute(
            text("insert into setting (key, value) values ('backup.drive_folder_id', '\"test_folder\"') "
                 "on conflict (key) do update set value='\"test_folder\"'")
        )
        await session.commit()

        await backup_svc.create_backup(session)

        # Notification tablosunda backup_drive_failed olmalı
        notif = (
            await session.execute(
                text("select title, body from notification where kind='backup_drive_failed'")
            )
        ).mappings().first()
        assert notif is not None
        assert notif["title"] == "Google Drive yedeği yüklenemedi"
        assert "Simulated 403" in notif["body"]

