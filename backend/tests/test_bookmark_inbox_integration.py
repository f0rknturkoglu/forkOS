from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db import engine
from app.main import app


async def _database_ready() -> bool:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("select 1 from bookmark limit 1"))
        return True
    except Exception:
        return False


@pytest.mark.asyncio
async def test_inbox_bulk_action_move_and_delete():
    if not await _database_ready():
        pytest.skip("Postgres calismiyor")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 3 bookmark olustur
        b1_res = await client.post("/api/capture", json={
            "url": "https://example.com/item1",
            "title": "Item 1",
            "collection": "inbox",
            "source": "manual",
            "client_uuid": str(uuid.uuid4()),
        })
        assert b1_res.status_code == 201
        b1_id = b1_res.json()["id"]

        b2_res = await client.post("/api/capture", json={
            "url": "https://example.com/item2",
            "title": "Item 2",
            "collection": "inbox",
            "source": "manual",
            "client_uuid": str(uuid.uuid4()),
        })
        assert b2_res.status_code == 201
        b2_id = b2_res.json()["id"]

        # Toplu tasi: read_later
        bulk_move = await client.post("/api/bookmarks/bulk-action", json={
            "bookmark_ids": [b1_id, b2_id],
            "action": "move",
            "collection": "read_later",
        })
        assert bulk_move.status_code == 200
        assert bulk_move.json()["affected"] == 2

        # Dogrula: artik inbox'ta yoklar, read_later'dalar
        inbox_list = await client.get("/api/bookmarks?collection=inbox")
        assert inbox_list.status_code == 200
        inbox_ids = [b["id"] for b in inbox_list.json()]
        assert b1_id not in inbox_ids
        assert b2_id not in inbox_ids

        # Toplu sil
        bulk_del = await client.post("/api/bookmarks/bulk-action", json={
            "bookmark_ids": [b1_id],
            "action": "delete",
        })
        assert bulk_del.status_code == 200
        assert bulk_del.json()["affected"] == 1

        get_res = await client.get(f"/api/bookmarks/{b1_id}")
        assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_inbox_convert_to_task_and_create_note():
    if not await _database_ready():
        pytest.skip("Postgres calismiyor")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Bookmark olustur (not ve alinti iceren)
        b_res = await client.post("/api/capture", json={
            "url": "https://example.com/research",
            "title": "Arastirma Yazisi",
            "note": "Onemli mimari notu",
            "selection": "Bu bolum cok kritik",
            "collection": "inbox",
            "source": "manual",
            "client_uuid": str(uuid.uuid4()),
        })
        assert b_res.status_code == 201
        b_id = b_res.json()["id"]

        # Goreve donustur
        conv_res = await client.post(f"/api/bookmarks/{b_id}/convert-to-task", json={
            "priority": 1,
            "plan_day": "2026-09-12",
        })
        assert conv_res.status_code == 200
        todo_id = conv_res.json()["todo_id"]

        # Bookmark archive'e gecmis olmali
        b_get = await client.get(f"/api/bookmarks/{b_id}")
        assert b_get.status_code == 200
        assert b_get.json()["collection"] == "archive"

        # Todo detayini kontrol et (GET /todos uzerinden)
        todos_res = await client.get("/api/todos")
        assert todos_res.status_code == 200
        todo_matches = [t for t in todos_res.json() if t["id"] == todo_id]
        assert len(todo_matches) == 1
        todo_data = todo_matches[0]
        assert todo_data["title"] == "Arastirma Yazisi"
        assert "https://example.com/research" in todo_data["description"]
        assert "Onemli mimari notu" in todo_data["description"]

        # Ayni bookmark'tan baglantili not olustur
        note_res = await client.post(f"/api/bookmarks/{b_id}/create-note", json={
            "pinned": True,
            "additional_text": "Ek analiz dusunceleri",
        })
        assert note_res.status_code == 200
        note_id = note_res.json()["note_id"]

        note_get = await client.get(f"/api/notes/{note_id}")
        assert note_get.status_code == 200
        assert note_get.json()["pinned"] is True
        assert "https://example.com/research" in note_get.json()["body"]
