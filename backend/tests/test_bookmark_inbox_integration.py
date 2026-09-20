from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.config import settings
from app.db import engine
from app.integrations.obsidian.service import vault_index
from app.main import app


async def _database_ready() -> bool:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("select 1 from bookmark limit 1"))
        return True
    except Exception:
        return False


@pytest.fixture(autouse=True)
def reset_vault_index():
    """Global Vault indeksi testler arasinda sizmasin."""
    def clear() -> None:
        vault_index._items.clear()
        vault_index._conflicts.clear()
        vault_index._invalid_files.clear()
        vault_index._last_scanned = None
        vault_index._last_status = None
        vault_index._last_root = None

    clear()
    yield
    clear()


@pytest.fixture
def vault(tmp_path, monkeypatch: pytest.MonkeyPatch):
    """Bilgi yazmalari GECICI bir Vault'a gider; kullanicinin kasasina dokunulmaz."""
    path = tmp_path / "vault"
    path.mkdir()
    monkeypatch.setattr(settings, "obsidian_vault_path", str(path))
    monkeypatch.setattr(settings, "obsidian_vault_name", "TestVault")
    return path

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
async def test_inbox_convert_to_task_and_create_source_note(vault: Path):
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

        # Ayni bookmark'tan kanonik Vault kaynak notu olustur.
        # PHASE 3: kimlik yer iminin UUID'sidir; forkOS'ta not kaydi OLUSMAZ.
        note_res = await client.post(f"/api/bookmarks/{b_id}/source-note", json={
            "additional_text": "Ek analiz dusunceleri",
        })
        assert note_res.status_code == 201, note_res.text
        item = note_res.json()
        assert item["forkos_id"] == b_id
        assert item["forkos_type"] == "source"
        assert item["relative_path"] == "60 Sources/Arastirma Yazisi.md"
        written = (vault / item["relative_path"]).read_text(encoding="utf-8")
        assert "https://example.com/research" in written
        assert "Ek analiz dusunceleri" in written
