from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db import engine
from app.main import app


async def _database_ready() -> bool:
    async with engine.connect() as connection:
        await connection.execute(text("select 1 from bookmark limit 1"))
    return True


@pytest.mark.asyncio
async def test_bookmark_capture_with_pocket_metadata():
    if not await _database_ready():
        pytest.skip("Postgres calismiyor")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/capture", json={
            "url": "https://example.com/pocket-article",
            "title": "Pocket Tarzi Makale",
            "collection": "read_later",
            "source": "extension",
            "hero_image_url": "https://example.com/hero.png",
            "favicon_url": "https://example.com/favicon.ico",
            "author": "Caner Demir",
            "reading_time_min": 7,
            "word_count": 1400,
            "client_uuid": str(uuid.uuid4()),
        })
        assert res.status_code == 201
        b_id = res.json()["id"]

        get_res = await client.get(f"/api/bookmarks/{b_id}")
        assert get_res.status_code == 200
        data = get_res.json()
        assert data["hero_image_url"] == "https://example.com/hero.png"
        assert data["favicon_url"] == "https://example.com/favicon.ico"
        assert data["author"] == "Caner Demir"
        assert data["reading_time_min"] == 7
        assert data["word_count"] == 1400
        assert data["scroll_progress"] == 0


@pytest.mark.asyncio
async def test_bookmark_highlights_crud():
    if not await _database_ready():
        pytest.skip("Postgres calismiyor")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Bookmark olustur
        b_res = await client.post("/api/capture", json={
            "url": "https://example.com/highlight-test",
            "title": "Highlight Test Makalesi",
            "collection": "read_later",
            "source": "manual",
            "client_uuid": str(uuid.uuid4()),
        })
        assert b_res.status_code == 201
        b_id = b_res.json()["id"]

        # 2. Vurgu ekle
        hl_res = await client.post(f"/api/bookmarks/{b_id}/highlights", json={
            "text": "Bu cumle cok onemli bir prensiptir.",
            "note": "Mimari notu",
            "color": "yellow",
            "anchor_index": 1,
        })
        assert hl_res.status_code == 201
        hl_data = hl_res.json()
        assert hl_data["text"] == "Bu cumle cok onemli bir prensiptir."
        assert hl_data["color"] == "yellow"
        hl_id = hl_data["id"]

        # 3. Vurgulari listele
        list_res = await client.get(f"/api/bookmarks/{b_id}/highlights")
        assert list_res.status_code == 200
        highlights = list_res.json()
        assert len(highlights) == 1
        assert highlights[0]["id"] == hl_id

        # 4. Vurguyu sil
        del_res = await client.delete(f"/api/bookmarks/{b_id}/highlights/{hl_id}")
        assert del_res.status_code == 204

        # 5. Silindigini dogrula
        list_res2 = await client.get(f"/api/bookmarks/{b_id}/highlights")
        assert list_res2.status_code == 200
        assert len(list_res2.json()) == 0


@pytest.mark.asyncio
async def test_bookmark_scroll_progress_auto_mark_read():
    if not await _database_ready():
        pytest.skip("Postgres calismiyor")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        b_res = await client.post("/api/capture", json={
            "url": "https://example.com/scroll-test",
            "title": "Scroll Test",
            "collection": "read_later",
            "source": "manual",
            "client_uuid": str(uuid.uuid4()),
        })
        b_id = b_res.json()["id"]

        # %50 scroll guncelle
        p1_res = await client.patch(f"/api/bookmarks/{b_id}/progress", json={"scroll_progress": 50})
        assert p1_res.status_code == 200
        assert p1_res.json()["scroll_progress"] == 50
        assert p1_res.json()["read_status"] == "unread"

        # %95 scroll guncelle -> otomatik read olmali
        p2_res = await client.patch(f"/api/bookmarks/{b_id}/progress", json={"scroll_progress": 95})
        assert p2_res.status_code == 200
        assert p2_res.json()["scroll_progress"] == 95
        assert p2_res.json()["read_status"] == "read"


@pytest.mark.asyncio
async def test_highlight_convert_to_flashcard():
    if not await _database_ready():
        pytest.skip("Postgres calismiyor")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        b_res = await client.post("/api/capture", json={
            "url": "https://example.com/card-test",
            "title": "Flashcard Kaynagi",
            "collection": "read_later",
            "source": "manual",
            "client_uuid": str(uuid.uuid4()),
        })
        b_id = b_res.json()["id"]

        hl_res = await client.post(f"/api/bookmarks/{b_id}/highlights", json={
            "text": "Bilesenler arasi gevsek baglilik temel ilkedir.",
            "note": "Soru: Temel ilke nedir?",
            "color": "green",
            "anchor_index": 0,
        })
        hl_id = hl_res.json()["id"]

        # Flashcard'a donustur
        conv_res = await client.post(f"/api/bookmarks/{b_id}/highlights/{hl_id}/convert-to-flashcard")
        assert conv_res.status_code == 200
        card_id = conv_res.json()["card_id"]
        assert card_id is not None

        # Kartin destede olustugunu dogrula
        decks_res = await client.get("/api/flashcard/decks")
        assert decks_res.status_code == 200
        decks = decks_res.json()
        target_deck = next((d for d in decks if d["title"] == "Yer İmleri ve Okuma"), None)
        assert target_deck is not None

        cards_res = await client.get(f"/api/flashcard/decks/{target_deck['id']}/cards")
        assert cards_res.status_code == 200
        cards = cards_res.json()
        matched = next((c for c in cards if c["id"] == card_id), None)
        assert matched is not None
        assert "Soru: Temel ilke nedir?" in matched["front"]
        assert "Bilesenler arasi gevsek baglilik temel ilkedir." in matched["back"]


@pytest.mark.asyncio
async def test_bookmark_import_and_export():
    if not await _database_ready():
        pytest.skip("Postgres calismiyor")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Netscape HTML import testi
        html_sample = (
            "<!DOCTYPE NETSCAPE-Bookmark-file-1>\n"
            "<TITLE>Bookmarks</TITLE>\n"
            "<H1>Bookmarks</H1>\n"
            "<DL><p>\n"
            '    <DT><A HREF="https://example.com/netscape-item" TAGS="deneme,pocket">Netscape Baslik</A>\n'
            "</DL><p>"
        )
        imp_res = await client.post(
            "/api/bookmarks/import", json={"content": html_sample, "collection": "read_later"}
        )
        assert imp_res.status_code == 200
        assert imp_res.json()["imported"] == 1

        # Kutuphaneden Netscape HTML export testi
        exp_res = await client.get("/api/bookmarks/export")
        assert exp_res.status_code == 200
        assert "NETSCAPE-Bookmark-file-1" in exp_res.text
        assert "https://example.com/netscape-item" in exp_res.text

