"""Not ekleri: binary dosya sisteminde, metadata veritabaninda.

En riskli faz: mevcut kullanicinin ekleri base64 JSONB'den dosya sistemine
tasinir. Bu yuzden kilitlenen davranislar:

  - yeni ekler icin binary DB'ye HIC yazilmaz (JSONB bos kalir),
  - ayni icerik diskte tek kopya tutulur (dedup) ama satirlar ayri kalir,
  - blob yalnizca son referans silinince diskten gider,
  - eski (donusmemis) kayitlar okunmaya devam eder ve donusum ID KORUR,
  - donusum idempotent ve not bazli: hata olursa JSONB DOKUNULMAZ,
  - dosya adi istemciden degil ozetten turetilir (path traversal imkansiz),
  - yedek/geri yukleme ek blob'larini tasir ve ozeti dogrular.
"""

from __future__ import annotations

import base64
import json
import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text

from app.core.models import Entity
from app.db import SessionLocal
from app.main import app
from app.modules.note import service as note_service
from app.modules.note import storage as attachment_storage
from app.modules.note.models import Note, NoteAttachment
from app.modules.system import export, restore


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


def _blobs(root: Path) -> dict[str, int]:
    if not root.is_dir():
        return {}
    return {p.name: p.stat().st_size for p in root.iterdir() if p.is_file()}


async def _create_note(client: AsyncClient, body: str = "Ek testi") -> dict:
    response = await client.post("/api/notes", json={"body": body})
    assert response.status_code == 201, response.text
    return response.json()


async def _upload(client: AsyncClient, note_id: str, content: bytes, name: str = "ek.png") -> dict:
    response = await client.post(
        f"/api/notes/{note_id}/attachments",
        files={"file": (name, content, "image/png")},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_upload_keeps_binary_out_of_the_database(
    client: AsyncClient, isolated_data_dirs: Path
) -> None:
    note = await _create_note(client)
    content = b"png-binary-payload"

    attachment = await _upload(client, note["id"], content)

    async with SessionLocal() as session:
        row = await session.get(NoteAttachment, uuid.UUID(attachment["id"]))
        stored_jsonb = (await session.get(Note, uuid.UUID(note["id"]))).attachments

    assert row is not None
    assert row.sha256 == attachment_storage.digest_of(content)
    assert row.size == len(content)
    assert stored_jsonb == [], "yeni ek JSONB'ye YAZILMAMALI"
    assert _blobs(attachment_storage.ATTACHMENTS_DIR) == {row.sha256: len(content)}

    fetched = await client.get(attachment["url"])
    assert fetched.status_code == 200 and fetched.content == content


async def test_same_content_is_stored_once_but_listed_twice(
    client: AsyncClient,
) -> None:
    note = await _create_note(client)
    content = b"aynisi"

    first = await _upload(client, note["id"], content, name="a.png")
    second = await _upload(client, note["id"], content, name="b.png")

    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(NoteAttachment).where(NoteAttachment.note_id == uuid.UUID(note["id"]))
            )
        ).scalars().all()

    assert len(rows) == 2
    assert len({row.sha256 for row in rows}) == 1
    assert len(_blobs(attachment_storage.ATTACHMENTS_DIR)) == 1, "blob DEDUP edilmeli"
    assert first["id"] != second["id"]

    listed = (await client.get(f"/api/notes/{note['id']}")).json()["attachments"]
    assert [item["name"] for item in listed] == ["a.png", "b.png"]


async def test_blob_is_removed_only_with_the_last_reference(client: AsyncClient) -> None:
    note = await _create_note(client)
    content = b"paylasilan"
    first = await _upload(client, note["id"], content)
    second = await _upload(client, note["id"], content)

    assert (await client.delete(first["url"])).status_code == 204
    assert len(_blobs(attachment_storage.ATTACHMENTS_DIR)) == 1, "diger ek hala kullaniyor"

    assert (await client.delete(second["url"])).status_code == 204
    assert _blobs(attachment_storage.ATTACHMENTS_DIR) == {}


async def test_legacy_attachment_is_converted_with_the_same_id(
    client: AsyncClient,
) -> None:
    note = await _create_note(client)
    legacy_id = str(uuid.uuid4())
    content = b"eski-base64-icerik"
    async with SessionLocal() as session:
        await session.execute(
            text("update note set attachments = cast(:value as jsonb) where id = cast(:id as uuid)"),
            {
                "id": note["id"],
                "value": json.dumps(
                    [
                        {
                            "id": legacy_id,
                            "name": "eski.png",
                            "mime": "image/png",
                            "size": len(content),
                            "data": base64.b64encode(content).decode("ascii"),
                        }
                    ]
                ),
            },
        )
        await session.commit()

    # Donusumden ONCE indirme calisir (eski yol).
    before = await client.get(f"/api/notes/{note['id']}/attachments/{legacy_id}")
    assert before.status_code == 200 and before.content == content

    async with SessionLocal() as session:
        migrated = await note_service.convert_legacy_attachments(session)

    assert migrated == 1
    async with SessionLocal() as session:
        row = await session.get(NoteAttachment, uuid.UUID(legacy_id))
        remaining = (await session.get(Note, uuid.UUID(note["id"]))).attachments

    assert row is not None, "ID KORUNMALI"
    assert row.name == "eski.png" and row.sha256 == attachment_storage.digest_of(content)
    assert remaining == [], "donusum sonrasi eski temsil temizlenir"

    # Ayni URL donusumden SONRA da calisir.
    after = await client.get(f"/api/notes/{note['id']}/attachments/{legacy_id}")
    assert after.status_code == 200 and after.content == content

    listed = (await client.get(f"/api/notes/{note['id']}")).json()["attachments"]
    assert [item["id"] for item in listed] == [legacy_id]

    # Idempotent: ikinci tur is yok.
    async with SessionLocal() as session:
        assert await note_service.convert_legacy_attachments(session) == 0


async def test_conversion_failure_leaves_the_legacy_payload_intact(
    client: AsyncClient,
) -> None:
    """Bozuk bir kayit notun JSONB'sini BOZMAMALI (veri kaybi olmaz)."""
    note = await _create_note(client)
    async with SessionLocal() as session:
        await session.execute(
            text("update note set attachments = cast(:value as jsonb) where id = cast(:id as uuid)"),
            {
                "id": note["id"],
                # `data` base64 DEGIL: cozumleme patlar.
                "value": json.dumps(
                    [
                        {
                            "id": str(uuid.uuid4()),
                            "name": "bozuk.png",
                            "mime": "image/png",
                            "size": 3,
                            "data": "%%%%",
                        }
                    ]
                ),
            },
        )
        await session.commit()

    async with SessionLocal() as session:
        assert await note_service.convert_legacy_attachments(session) == 0
        intact = (await session.get(Note, uuid.UUID(note["id"]))).attachments

    assert intact and intact[0]["name"] == "bozuk.png", "eski temsil korunmali"

    # Liste hala eski kaydi gosterir.
    listed = (await client.get(f"/api/notes/{note['id']}")).json()["attachments"]
    assert [item["name"] for item in listed] == ["bozuk.png"]


@pytest.mark.no_database
def test_blob_path_never_accepts_client_supplied_names() -> None:
    """Dosya adi yalnizca ozetten turetilir; istemci verisi yol olamaz."""
    for hostile in ("../../etc/passwd", "a/b", "..", "0" * 63, "g" * 64, ""):
        with pytest.raises(ValueError):
            attachment_storage.blob_path(hostile)

    valid = "a" * 64
    assert attachment_storage.blob_path(valid).name == valid
    assert attachment_storage.read_blob("../../etc/passwd") is None


async def test_backup_and_restore_carry_attachment_blobs(client: AsyncClient) -> None:
    note = await _create_note(client)
    content = b"yedeklenecek-ek"
    attachment = await _upload(client, note["id"], content)
    digest = attachment_storage.digest_of(content)

    async with SessionLocal() as session:
        payload = await export.full_json(session)

    assert payload["attachments"] == {
        digest: base64.b64encode(content).decode("ascii")
    }

    # Diski bosalt: restore geri getirmeli.
    for path in attachment_storage.ATTACHMENTS_DIR.iterdir():
        path.unlink()
    assert _blobs(attachment_storage.ATTACHMENTS_DIR) == {}

    assert restore.restore_attachments(payload) == 1
    assert _blobs(attachment_storage.ATTACHMENTS_DIR) == {digest: len(content)}
    assert (await client.get(attachment["url"])).status_code == 200


@pytest.mark.no_database
def test_restore_rejects_attachment_with_a_mismatched_digest() -> None:
    """Ozet ile icerik tutmuyorsa dosya YAZILMAZ (bozuk yedek kabul edilmez)."""
    content = b"icerik"
    wrong_digest = attachment_storage.digest_of(b"baska-icerik")
    payload = {
        "attachments": {
            wrong_digest: base64.b64encode(content).decode("ascii"),
            "not-a-digest": base64.b64encode(content).decode("ascii"),
        }
    }

    assert restore.restore_attachments(payload) == 0
    assert _blobs(attachment_storage.ATTACHMENTS_DIR) == {}


async def test_soft_delete_keeps_attachment_restorable(client: AsyncClient) -> None:
    """Cop kutusuna tasima ekleri SILMEZ: not geri alinabilmeli."""
    note = await _create_note(client)
    attachment = await _upload(client, note["id"], b"geri-alinabilir")

    assert (await client.delete(f"/api/notes/{note['id']}")).status_code == 204

    async with SessionLocal() as session:
        rows = (
            await session.execute(select(func.count()).select_from(NoteAttachment))
        ).scalar_one()

    assert rows == 1
    assert len(_blobs(attachment_storage.ATTACHMENTS_DIR)) == 1
    assert (await client.get(attachment["url"])).status_code == 200


async def test_permanent_delete_removes_rows_and_orphan_blob(client: AsyncClient) -> None:
    """Kalici silme satirlari FK ile goturur; DOSYAYI yetim temizligi toplar."""
    note = await _create_note(client)
    attachment = await _upload(client, note["id"], b"kalici-silinecek")
    assert (await client.delete(f"/api/notes/{note['id']}")).status_code == 204

    assert (await client.delete(f"/api/notes/{note['id']}/permanent")).status_code == 204

    async with SessionLocal() as session:
        rows = (
            await session.execute(select(func.count()).select_from(NoteAttachment))
        ).scalar_one()
        entities = (
            await session.execute(
                select(func.count()).select_from(Entity).where(Entity.id == uuid.UUID(note["id"]))
            )
        ).scalar_one()

    assert rows == 0, "FK cascade satirlari silmeli"
    assert entities == 0

    # Dosya hala diskte: yas esigi gecince yetim temizligi toplar.
    assert len(_blobs(attachment_storage.ATTACHMENTS_DIR)) == 1
    async with SessionLocal() as session:
        assert (
            await attachment_storage.prune_orphan_blobs(session, grace_seconds=0)
        ) == 1
    assert _blobs(attachment_storage.ATTACHMENTS_DIR) == {}
    assert (await client.get(attachment["url"])).status_code == 404


async def test_orphan_sweep_spares_referenced_and_fresh_blobs(client: AsyncClient) -> None:
    """Temizlik yalnizca GERCEKTEN yetim ve yasli dosyalara dokunur."""
    note = await _create_note(client)
    await _upload(client, note["id"], b"kullanilan")
    # Satiri olmayan ama YENI bir blob: commit yarisi olabilir, silinmemeli.
    fresh = attachment_storage.store_blob(b"henuz-satiri-yok")

    async with SessionLocal() as session:
        assert await attachment_storage.prune_orphan_blobs(session) == 0

    assert len(_blobs(attachment_storage.ATTACHMENTS_DIR)) == 2
    assert attachment_storage.read_blob(fresh) == b"henuz-satiri-yok"


async def test_commit_failure_preserves_blob_on_disk(client: AsyncClient) -> None:
    note = await _create_note(client)
    content = b"guvenli-silme-testi"
    att = await _upload(client, note["id"], content)
    digest = attachment_storage.digest_of(content)
    assert attachment_storage.blob_path(digest).exists()

    async with SessionLocal() as session:
        async def fail_commit():
            raise RuntimeError("simule edilmis veritabani commit hatasi")

        session.commit = fail_commit  # type: ignore[method-assign]
        with pytest.raises(RuntimeError, match="simule edilmis"):
            await note_service.delete_attachment(
                session, uuid.UUID(note["id"]), uuid.UUID(att["id"])
            )

    # Commit basarisiz oldugu icin blob diskte KESINLIKLE kalmali (veri kaybi yok)
    assert attachment_storage.blob_path(digest).exists(), "DB commit basarisiz olunca blob SILINMEMELI"


async def test_backup_export_fails_if_referenced_blob_missing_from_disk(
    client: AsyncClient,
) -> None:
    note = await _create_note(client)
    content = b"kaybolacak-ek-icerigi"
    await _upload(client, note["id"], content)
    digest = attachment_storage.digest_of(content)

    blob_file = attachment_storage.blob_path(digest)
    assert blob_file.is_file()
    blob_file.unlink()
    assert not blob_file.exists()

    async with SessionLocal() as session:
        with pytest.raises(RuntimeError, match="diskte bulunamadı"):
            await export.full_json(session)


async def test_backup_export_fails_if_blob_corrupted_on_disk(
    client: AsyncClient,
) -> None:
    note = await _create_note(client)
    content = b"orijinal-ek-icerigi-12345"
    await _upload(client, note["id"], content)
    digest = attachment_storage.digest_of(content)

    blob_file = attachment_storage.blob_path(digest)
    assert blob_file.is_file()
    # Ayni boyutta ama farkli icerik/hash ile uzerine yazarak boz
    corrupt_content = b"X" * len(content)
    assert len(corrupt_content) == len(content)
    blob_file.write_bytes(corrupt_content)

    async with SessionLocal() as session:
        with pytest.raises(RuntimeError, match="özeti uyuşmuyor"):
            await export.full_json(session)


async def test_inspect_and_restore_detect_missing_and_corrupt_attachments() -> None:
    fake_digest = "a" * 64
    valid_content = b"gecerli-icerik"
    valid_digest = attachment_storage.digest_of(valid_content)
    mismatched_digest = "b" * 64

    # 1. Eksik attachment: note_attachment tablosunda var ama attachments haritasinda yok
    missing_payload = {
        "version": 2,
        "manifest": {"app": "forkos", "row_counts": {"entities": 0, "links": 0, "events": 0, "modules": {"note_attachment": 1}}},
        "entities": [],
        "links": [],
        "events": [],
        "modules": {
            "note_attachment": [
                {"id": str(uuid.uuid4()), "note_id": str(uuid.uuid4()), "sha256": fake_digest, "name": "ek.png", "mime": "image/png", "size": 10}
            ]
        },
        "attachments": {},
    }
    report_missing = restore.inspect_payload(missing_payload)
    assert report_missing["integrity_ok"] is False
    assert fake_digest in report_missing["missing_attachments"]

    async with SessionLocal() as session:
        with pytest.raises(ValueError, match="eksik ekler"):
            await restore.restore(session, missing_payload)

    # 2. Bozuk attachment: hash ile icerik uyusmuyor
    corrupt_payload = {
        "version": 2,
        "manifest": {"app": "forkos", "row_counts": {"entities": 0, "links": 0, "events": 0, "modules": {"note_attachment": 2}}},
        "entities": [],
        "links": [],
        "events": [],
        "modules": {
            "note_attachment": [
                {"id": str(uuid.uuid4()), "note_id": str(uuid.uuid4()), "sha256": valid_digest, "name": "ok.png", "mime": "image/png", "size": len(valid_content)},
                {"id": str(uuid.uuid4()), "note_id": str(uuid.uuid4()), "sha256": mismatched_digest, "name": "bad.png", "mime": "image/png", "size": len(valid_content)},
            ]
        },
        "attachments": {
            valid_digest: base64.b64encode(valid_content).decode("ascii"),
            mismatched_digest: base64.b64encode(valid_content).decode("ascii"),
        },
    }
    report_corrupt = restore.inspect_payload(corrupt_payload)
    assert report_corrupt["integrity_ok"] is False
    assert mismatched_digest in report_corrupt["corrupt_attachments"]
    assert valid_digest not in report_corrupt["corrupt_attachments"]

    async with SessionLocal() as session:
        with pytest.raises(ValueError, match="bozuk ekler"):
            await restore.restore(session, corrupt_payload)


async def test_restore_legacy_jsonb_attachments_succeeds() -> None:
    note_id = uuid.uuid4()
    legacy_attachment = {
        "id": str(uuid.uuid4()),
        "name": "legacy_doc.txt",
        "mime": "text/plain",
        "size": 18,
        "data": base64.b64encode(b"legacy-text-binary").decode("ascii"),
    }
    payload = {
        "version": 2,
        "manifest": {
            "app": "forkos",
            "row_counts": {
                "entities": 1,
                "links": 0,
                "events": 0,
                "modules": {"note": 1},
            },
        },
        "entities": [
            {
                "id": str(note_id),
                "type": "note",
                "title": "Eski Not",
                "search_text": "",
                "created_at": "2026-09-01T10:00:00+00:00",
                "updated_at": "2026-09-01T10:00:00+00:00",
            }
        ],
        "links": [],
        "events": [],
        "modules": {
            "note": [
                {
                    "id": str(note_id),
                    "body": "Eski usul JSONB ekli not gövdesi",
                    "attachments": [legacy_attachment],
                    "canvas_state": {},
                    "default_view": "page",
                }
            ]
        },
    }

    # inspect preflight: eksik ya da bozuk ek raporlamamali
    report = restore.inspect_payload(payload)
    assert report["missing_attachments"] == []
    assert report["corrupt_attachments"] == []
    assert report["integrity_ok"] is True

    async with SessionLocal() as session:
        summary = await restore.restore(session, payload)
        assert summary["note"]["inserted"] == 1

        # Veritabanindaki notun JSONB attachments kolonu korunmus olmali
        stored_note = await session.get(Note, note_id)
        assert stored_note is not None
        assert stored_note.attachments == [legacy_attachment]
