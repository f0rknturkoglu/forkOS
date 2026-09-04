"""Faz 21: yerel hizli not -- entity-backed, Documents icinde yasar.

- create body'den guvenli kisa baslik turetiyor (kullanici baslik vermez).
- update body degisince search_text guncellenir (global search bulur).
- pin/archive/delete event uretir; arsiv/silme Entity yasam dongusunden.
- notes_about baglantisi iki tarafta da gorunur (RELATIONS).
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as http:
        yield http


async def test_create_derives_title_from_body(client: AsyncClient) -> None:
    body = "  Marketten süt al\n  ikinci satır  "
    response = await client.post("/api/notes", json={"body": body})
    assert response.status_code == 201, response.text
    note = response.json()
    assert note["title"] == "Marketten süt al"
    assert note["body"] == "  Marketten süt al\n  ikinci satır  "
    assert note["pinned"] is False
    assert note["canvas_state"] == {}
    assert note["default_view"] == "page"
    assert note["page_width"] == "compact"
    assert note["folder_id"] is None
    await client.delete(f"/api/notes/{note['id']}")


async def test_note_canvas_state_and_view_preferences(client: AsyncClient) -> None:
    note = (await client.post("/api/notes", json={"body": "# Fikir tuvali"})).json()
    scene = {
        "type": "excalidraw",
        "version": 2,
        "elements": [{"id": "box-1", "type": "rectangle"}],
        "appState": {"viewBackgroundColor": "#ffffff"},
        "files": {},
    }
    patched = await client.patch(
        f"/api/notes/{note['id']}",
        json={"canvas_state": scene, "default_view": "canvas", "page_width": "full"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["canvas_state"] == scene
    assert patched.json()["default_view"] == "canvas"
    assert patched.json()["page_width"] == "full"

    listed = (await client.get("/api/notes")).json()
    summary = next(item for item in listed if item["id"] == note["id"])
    assert summary["canvas_state"] == {}
    detailed = (await client.get(f"/api/notes/{note['id']}")).json()
    assert detailed["canvas_state"] == scene
    await client.delete(f"/api/notes/{note['id']}")


async def test_note_rejects_invalid_canvas_preferences(client: AsyncClient) -> None:
    note = (await client.post("/api/notes", json={"body": "Tuval doğrulama"})).json()
    invalid_view = await client.patch(f"/api/notes/{note['id']}", json={"default_view": "board"})
    invalid_width = await client.patch(f"/api/notes/{note['id']}", json={"page_width": "giant"})
    invalid_scene = await client.patch(f"/api/notes/{note['id']}", json={"canvas_state": {"elements": {}}})
    assert invalid_view.status_code == 422
    assert invalid_width.status_code == 422
    assert invalid_scene.status_code == 422
    await client.delete(f"/api/notes/{note['id']}")


async def test_note_media_is_served_and_listed_in_graph(client: AsyncClient) -> None:
    note = (await client.post("/api/notes", json={"body": "# Görsel günlük"})).json()
    content = b"local-image-payload"
    uploaded = await client.post(
        f"/api/notes/{note['id']}/attachments",
        files={"file": ("gunluk.png", content, "image/png")},
    )
    assert uploaded.status_code == 201, uploaded.text
    attachment = uploaded.json()
    assert attachment["mime"] == "image/png"

    fetched = await client.get(attachment["url"])
    assert fetched.status_code == 200
    assert fetched.content == content

    refreshed = (await client.get(f"/api/notes/{note['id']}")).json()
    assert refreshed["attachments"][0]["name"] == "gunluk.png"
    graph = (await client.get("/api/graph")).json()
    assert note["id"] in {node["id"] for node in graph["nodes"]}

    removed = await client.delete(
        f"/api/notes/{note['id']}/attachments/{attachment['id']}"
    )
    assert removed.status_code == 204
    await client.delete(f"/api/notes/{note['id']}")


async def test_note_attachment_rejects_unsupported_content(client: AsyncClient) -> None:
    note = (await client.post("/api/notes", json={"body": "Dosya sınırı"})).json()
    response = await client.post(
        f"/api/notes/{note['id']}/attachments",
        files={"file": ("script.svg", b"<svg></svg>", "image/svg+xml")},
    )
    assert response.status_code == 422
    await client.delete(f"/api/notes/{note['id']}")


async def test_note_accepts_document_and_video_attachments(client: AsyncClient) -> None:
    note = (await client.post("/api/notes", json={"body": "Zengin ekler"})).json()
    pdf = await client.post(
        f"/api/notes/{note['id']}/attachments",
        files={"file": ("rapor.pdf", b"%PDF-local", "application/pdf")},
    )
    video = await client.post(
        f"/api/notes/{note['id']}/attachments",
        files={"file": ("demo.webm", b"local-video", "video/webm")},
    )
    assert pdf.status_code == 201, pdf.text
    assert video.status_code == 201, video.text
    fetched = await client.get(pdf.json()["url"])
    assert fetched.headers["x-content-type-options"] == "nosniff"
    assert fetched.headers["content-disposition"].startswith("inline")
    await client.delete(f"/api/notes/{note['id']}")


async def test_note_folders_are_nested_and_keep_notes_when_deleted(client: AsyncClient) -> None:
    root_response = await client.post("/api/note-folders", json={"name": "Araştırma"})
    assert root_response.status_code == 201, root_response.text
    root = root_response.json()
    child_response = await client.post(
        "/api/note-folders", json={"name": "Makaleler", "parent_id": root["id"]}
    )
    assert child_response.status_code == 201, child_response.text
    child = child_response.json()

    note_response = await client.post(
        "/api/notes", json={"body": "# Klasörlü bilgi", "folder_id": child["id"]}
    )
    assert note_response.status_code == 201, note_response.text
    note = note_response.json()
    assert note["folder_id"] == child["id"]

    folders = (await client.get("/api/note-folders")).json()
    assert {item["name"] for item in folders} >= {"Araştırma", "Makaleler"}
    child_out = next(item for item in folders if item["id"] == child["id"])
    assert child_out["note_count"] == 1

    cyclic = await client.patch(
        f"/api/note-folders/{root['id']}", json={"parent_id": child["id"]}
    )
    assert cyclic.status_code == 422

    deleted = await client.delete(f"/api/note-folders/{child['id']}")
    assert deleted.status_code == 204
    kept = (await client.get(f"/api/notes/{note['id']}")).json()
    assert kept["folder_id"] is None
    await client.delete(f"/api/notes/{note['id']}")
    await client.delete(f"/api/note-folders/{root['id']}")


async def test_note_accepts_valid_excalidraw_attachment(client: AsyncClient) -> None:
    note = (await client.post("/api/notes", json={"body": "Akış çizimi"})).json()
    drawing = b'{"type":"excalidraw","version":2,"elements":[],"appState":{}}'
    uploaded = await client.post(
        f"/api/notes/{note['id']}/attachments",
        files={"file": ("akis.excalidraw", drawing, "application/octet-stream")},
    )
    assert uploaded.status_code == 201, uploaded.text
    assert uploaded.json()["mime"] == "application/vnd.excalidraw+json"
    await client.delete(f"/api/notes/{note['id']}")


async def test_note_rejects_invalid_excalidraw_attachment(client: AsyncClient) -> None:
    note = (await client.post("/api/notes", json={"body": "Bozuk çizim"})).json()
    uploaded = await client.post(
        f"/api/notes/{note['id']}/attachments",
        files={"file": ("bozuk.excalidraw", b"not-json", "application/octet-stream")},
    )
    assert uploaded.status_code == 422
    await client.delete(f"/api/notes/{note['id']}")


async def test_update_touches_search_text(client: AsyncClient) -> None:
    note = (await client.post("/api/notes", json={"body": "Eski içerik"})).json()
    patched = await client.patch(f"/api/notes/{note['id']}", json={"body": "Yeni içerik burada"})
    assert patched.status_code == 200
    assert patched.json()["title"] == "Yeni içerik burada"

    # Global search body'den bulur (search_text guncellendi).
    hits = (await client.get("/api/search", params={"q": "Yeni içerik"})).json()
    assert note["id"] in {str(item["id"]) for item in hits}
    await client.delete(f"/api/notes/{note['id']}")


async def test_pin_archive_delete_events_and_listing(client: AsyncClient) -> None:
    note = (await client.post("/api/notes", json={"body": "Sabitlenecek"})).json()

    pinned = await client.patch(f"/api/notes/{note['id']}", json={"pinned": True})
    assert pinned.json()["pinned"] is True

    archived = await client.post(f"/api/notes/{note['id']}/archive")
    assert archived.status_code == 200
    active = (await client.get("/api/notes")).json()
    assert note["id"] not in {item["id"] for item in active}
    with_archived = (await client.get("/api/notes", params={"include_archived": True})).json()
    assert note["id"] in {item["id"] for item in with_archived}

    deleted = await client.delete(f"/api/notes/{note['id']}")
    assert deleted.status_code == 204
    assert (await client.get(f"/api/notes/{note['id']}")).status_code == 404


async def test_notes_about_relation_visible_on_both_sides(client: AsyncClient) -> None:
    note = (await client.post("/api/notes", json={"body": "Proje hakkında not"})).json()
    todo = (await client.post("/api/todos", json={"title": "Notlanan görev"})).json()

    linked = await client.post("/api/links", json={
        "from_id": note["id"], "to_id": todo["id"], "relation": "notes_about",
    })
    assert linked.status_code == 201

    # Not tarafinda: ileri etiket "Hakkında not".
    note_related = (await client.get(f"/api/entities/{note['id']}/related")).json()
    assert any(row["label"] == "Hakkında not" and row["entity"]["id"] == todo["id"]
               for row in note_related)
    # Konu tarafinda: geri etiket "Notları".
    todo_related = (await client.get(f"/api/entities/{todo['id']}/related")).json()
    assert any(row["label"] == "Notları" and row["entity"]["id"] == note["id"]
               for row in todo_related)

    await client.delete(f"/api/notes/{note['id']}")
    await client.delete(f"/api/todos/{todo['id']}")


async def test_note_with_relate_to_is_one_transaction(client: AsyncClient) -> None:
    """Faz 29: not + notes_about bagi tek transaction; iliski basarisizsa
    not da olusmaz (yarim kayit yok)."""
    todo = (await client.post("/api/todos", json={"title": "Notlanan"})).json()

    response = await client.post("/api/notes", json={
        "body": "Baglantili not", "relate_to": todo["id"],
    })
    assert response.status_code == 201, response.text
    note = response.json()
    related = (await client.get(f"/api/entities/{note['id']}/related")).json()
    assert any(row["relation"] == "notes_about" and row["entity"]["id"] == todo["id"]
               for row in related)

    # Gecersiz relate_to -> not OLUSMAZ.
    import uuid as _uuid
    failed = await client.post("/api/notes", json={
        "body": "Yarim kalmamali", "relate_to": str(_uuid.uuid4()),
    })
    assert failed.status_code == 400
    notes = (await client.get("/api/notes")).json()
    assert "Yarim kalmamali" not in {item["title"] for item in notes}

    await client.delete(f"/api/notes/{note['id']}")
    await client.delete(f"/api/todos/{todo['id']}")


def test_derive_title_edge_cases() -> None:
    from app.modules.note.service import derive_title

    assert derive_title("   ") == "Not"
    assert derive_title("Tek satır") == "Tek satır"
    assert len(derive_title("a" * 200)) <= 60
    assert derive_title("İlk satır\nİkinci satır") == "İlk satır"
