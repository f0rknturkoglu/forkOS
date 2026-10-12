"""Synthetic-only restore preservation, filesystem boundaries and failure rollback."""
import base64
from copy import deepcopy
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.entity import create_entity
from app.db import SessionLocal
from app.modules.document import service as documents
from app.modules.system import export, restore
from app.modules.todo.models import Todo


async def test_merge_keeps_existing_parent_and_relinks_only_inserted_children():
    async with SessionLocal() as db:
        ids = []
        for title in ("parent old", "parent current", "child"):
            entity = await create_entity(db, type="todo", title=title)
            ids.append(entity.id)
            db.add(Todo(id=entity.id, parent_id=ids[0] if title == "child" else None))
        await db.commit()
        payload = await export.full_json(db)
        child = await db.get(Todo, ids[2])
        child.parent_id = ids[1]
        await db.commit()
        await restore.restore(db, payload)
        db.expire_all()
        assert (await db.get(Todo, ids[2])).parent_id == ids[1]


def file_payload(doc_id=None, filename="sentinel.pdf", content=b"old"):
    return {"files": {str(doc_id or uuid4()): {"filename": filename,
             "data_b64": base64.b64encode(content).decode()}}}


@pytest.mark.no_database
@pytest.mark.parametrize("filename", ["../outside", "/tmp/outside", "..\\outside"])
def test_document_restore_rejects_path_escape_before_writing(tmp_path, monkeypatch, filename):
    monkeypatch.setattr(documents, "DOCUMENTS_DIR", tmp_path / "documents")
    with pytest.raises(ValueError):
        restore.restore_files(file_payload(filename=filename))
    assert not list(tmp_path.rglob("*"))


@pytest.mark.no_database
def test_document_restore_rejects_directory_escape(tmp_path, monkeypatch):
    monkeypatch.setattr(documents, "DOCUMENTS_DIR", tmp_path / "documents")
    with pytest.raises(ValueError):
        restore.restore_files(file_payload(doc_id="../escape"))
    assert not list(tmp_path.rglob("*"))


@pytest.mark.no_database
def test_document_restore_never_overwrites_a_different_existing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(documents, "DOCUMENTS_DIR", tmp_path / "documents")
    doc_id = uuid4()
    path = documents.DOCUMENTS_DIR / str(doc_id) / "sentinel.pdf"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"new personal version")
    with pytest.raises(ValueError, match="[Cc]ak|[Çç]ak|conflict"):
        restore.restore_files(file_payload(doc_id))
    assert path.read_bytes() == b"new personal version"


async def test_precommit_disconnect_removes_only_new_restore_files_and_rolls_back(tmp_path, monkeypatch):
    monkeypatch.setattr(documents, "DOCUMENTS_DIR", tmp_path / "documents")
    async with SessionLocal() as db:
        entity = await create_entity(db, type="todo", title="Synthetic sentinel")
        sentinel_id = entity.id
        db.add(Todo(id=sentinel_id))
        await db.commit()
        payload = await export.full_json(db)
        doc_id = uuid4()
        payload.update(file_payload(doc_id))
        original_flush = db.flush
        async def disconnect(*args, **kwargs):
            if (documents.DOCUMENTS_DIR / str(doc_id) / "sentinel.pdf").exists():
                raise ConnectionError("synthetic lost connection before commit")
            return await original_flush(*args, **kwargs)
        monkeypatch.setattr(db, "flush", disconnect)
        with pytest.raises(ConnectionError):
            await restore.restore(db, payload)
        monkeypatch.setattr(db, "flush", original_flush)
        assert not (documents.DOCUMENTS_DIR / str(doc_id) / "sentinel.pdf").exists()
        assert await db.scalar(select(Todo.id).where(Todo.id == sentinel_id)) == sentinel_id


async def test_lost_commit_reply_preserves_complete_files_and_allows_retry(tmp_path, monkeypatch):
    monkeypatch.setattr(documents, "DOCUMENTS_DIR", tmp_path / "documents")
    async with SessionLocal() as db:
        doc = await documents.create_local_document(db, title="sentinel.pdf", category="cv",
            mime="application/pdf", content=b"synthetic committed content")
        payload = await export.full_json(db)
        path = documents.DOCUMENTS_DIR / str(doc["id"]) / "sentinel.pdf"
        path.unlink()
        real_commit = db.commit
        async def lost_reply():
            await real_commit()
            raise ConnectionError("synthetic lost commit acknowledgement")
        monkeypatch.setattr(db, "commit", lost_reply)
        with pytest.raises(ConnectionError):
            await restore.restore(db, payload)
        monkeypatch.setattr(db, "commit", real_commit)
        assert path.read_bytes() == b"synthetic committed content"
        await restore.restore(db, payload)
        assert (await export.full_json(db))["files"] == payload["files"]


async def test_disaster_verification_failure_removes_new_files(tmp_path, monkeypatch):
    from app.modules.system.disaster import disaster_restore
    monkeypatch.setattr(documents, "DOCUMENTS_DIR", tmp_path / "documents")
    async with SessionLocal() as db:
        entity = await create_entity(db, type="todo", title="Keep me")
        sentinel_id = entity.id
        db.add(Todo(id=sentinel_id))
        await db.commit()
        payload = deepcopy(await export.full_json(db))
        payload["entities"].append(deepcopy(payload["entities"][0]))
        doc_id = uuid4()
        payload.update(file_payload(doc_id))
        with pytest.raises(ValueError, match="dogrulama"):
            await disaster_restore(db, payload)
        assert not (documents.DOCUMENTS_DIR / str(doc_id) / "sentinel.pdf").exists()
        assert await db.scalar(select(Todo.id).where(Todo.id == sentinel_id)) == sentinel_id


@pytest.mark.no_database
def test_restore_rejects_symlink_and_corrupt_base64(tmp_path, monkeypatch):
    monkeypatch.setattr(documents, "DOCUMENTS_DIR", tmp_path / "documents")
    doc_id = uuid4()
    outside = tmp_path / "outside"
    outside.mkdir()
    documents.DOCUMENTS_DIR.mkdir()
    (documents.DOCUMENTS_DIR / str(doc_id)).symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="sembolik"):
        restore.restore_files(file_payload(doc_id))
    assert not list(outside.iterdir())
    payload = file_payload()
    next(iter(payload["files"].values()))["data_b64"] = "not base64!"
    with pytest.raises(ValueError):
        restore.restore_files(payload)


@pytest.mark.no_database
def test_file_io_failure_is_visible_and_rolls_back_only_new_files(tmp_path, monkeypatch):
    monkeypatch.setattr(documents, "DOCUMENTS_DIR", tmp_path / "documents")
    keep_id, first_id, second_id = uuid4(), uuid4(), uuid4()
    keep = documents.DOCUMENTS_DIR / str(keep_id) / "sentinel.pdf"
    keep.parent.mkdir(parents=True)
    keep.write_bytes(b"old")
    payload = file_payload(keep_id)
    payload["files"].update(file_payload(first_id)["files"])
    payload["files"].update(file_payload(second_id)["files"])
    real_link = restore.os.link
    def disk_full(source, destination):
        if str(second_id) in str(destination):
            raise OSError("synthetic disk full")
        return real_link(source, destination)
    monkeypatch.setattr(restore.os, "link", disk_full)
    with pytest.raises(OSError, match="disk full"):
        restore.restore_files(payload)
    assert keep.read_bytes() == b"old"
    assert not (documents.DOCUMENTS_DIR / str(first_id) / "sentinel.pdf").exists()
    assert not list(tmp_path.rglob(".restore-*"))


@pytest.mark.no_database
def test_document_restore_is_idempotent_without_overwriting(tmp_path, monkeypatch):
    monkeypatch.setattr(documents, "DOCUMENTS_DIR", tmp_path / "documents")
    payload = file_payload()
    assert restore.restore_files(payload) == 1
    path = next(documents.DOCUMENTS_DIR.rglob("*.pdf"))
    before = path.stat().st_mtime_ns
    assert restore.restore_files(payload) == 0
    assert path.stat().st_mtime_ns == before


async def test_backup_missing_document_is_an_explicit_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(documents, "DOCUMENTS_DIR", tmp_path / "documents")
    async with SessionLocal() as db:
        doc = await documents.create_local_document(db, title="sentinel.pdf", category="cv",
            mime="application/pdf", content=b"synthetic")
        (documents.DOCUMENTS_DIR / str(doc["id"]) / "sentinel.pdf").unlink()
        with pytest.raises(RuntimeError, match="belge|Belge"):
            await export.full_json(db)


async def test_restore_goal_parent_across_chunk_boundaries():
    from app.modules.goal.models import Goal
    async with SessionLocal() as db:
        parent = await create_entity(db, type="goal", title="Parent")
        child = await create_entity(db, type="goal", title="Child")
        db.add(Goal(id=parent.id))
        db.add(Goal(id=child.id, parent_goal_id=parent.id))
        await db.commit()
        payload = await export.full_json(db)
        child_row = next(row for row in payload["modules"]["goal"] if row["parent_goal_id"])
        parent_row = next(row for row in payload["modules"]["goal"] if not row["parent_goal_id"])
        payload["modules"]["goal"] = [child_row, parent_row]
        from sqlalchemy import text

        from app.db import Base
        tables = ", ".join('"' + table.name + '"' for table in reversed(Base.metadata.sorted_tables))
        await db.execute(text("TRUNCATE TABLE " + tables + " RESTART IDENTITY CASCADE"))
        await db.commit()
        from unittest.mock import patch
        with patch.object(restore, "CHUNK", 1):
            await restore.restore(db, payload)
        assert (await db.get(Goal, child.id)).parent_goal_id == parent.id
