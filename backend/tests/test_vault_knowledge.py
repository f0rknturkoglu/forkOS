"""Vault bilgi yazmaları: hızlı yakalama + kanonik bilgi notları (PHASE 3).

Bu dosya bilgi sahipliği sınırını kanıtlar:

  - Yeni bilgi notu Vault'ta doğar; forkOS veritabanına `entity`, `note` veya
    `link` satırı EKLEMEZ.
  - Kimliği sunucu üretir; ilişki hedefi sunucuda çözülür.
  - Yazma atomiktir ve sessiz üzerine yazmaz.
  - Vault yoksa/salt-okunursa işlem AÇIKÇA başarısız olur (fail-closed).
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.config import settings
from app.core.entity import create_entity
from app.core.models import Entity, Link
from app.db import SessionLocal
from app.integrations.obsidian.frontmatter import parse_frontmatter
from app.integrations.obsidian.service import (
    VaultStaleWriteError,
    read_managed_note_body,
    update_managed_note_body,
    vault_index,
)
from app.main import app
from app.modules.note.models import Note, NoteAttachment, NoteFolder


@pytest.fixture(autouse=True)
def reset_vault_index():
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
def vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "vault"
    path.mkdir()
    monkeypatch.setattr(settings, "obsidian_vault_path", str(path))
    monkeypatch.setattr(settings, "obsidian_vault_name", "TestVault")
    return path


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def table_counts() -> dict[str, int]:
    """Dondurulmuş arşiv + çekirdek tablo sayıları."""
    async with SessionLocal() as session:
        return {
            "note": int((await session.execute(select(func.count()).select_from(Note))).scalar_one()),
            "note_folder": int(
                (await session.execute(select(func.count()).select_from(NoteFolder))).scalar_one()
            ),
            "note_attachment": int(
                (await session.execute(select(func.count()).select_from(NoteAttachment))).scalar_one()
            ),
            "link": int((await session.execute(select(func.count()).select_from(Link))).scalar_one()),
        }


async def make_entity(entity_type: str, title: str) -> uuid.UUID:
    async with SessionLocal() as session:
        entity = await create_entity(session, type=entity_type, title=title, search_text=title)
        await session.commit()
        return entity.id


# ---------------------------------------------------------------------
# 1. Hızlı yakalama
# ---------------------------------------------------------------------


async def test_capture_writes_inbox_note_and_touches_no_database_tables(
    client: AsyncClient, vault: Path
) -> None:
    before_entities = 0
    async with SessionLocal() as session:
        before_entities = int(
            (await session.execute(select(func.count()).select_from(Entity))).scalar_one()
        )

    response = await client.post("/api/obsidian/capture", json={"body": "İlk hızlı not"})
    assert response.status_code == 201, response.text
    item = response.json()

    # Kimliği SUNUCU üretti ve Vault'a yazdı.
    assert uuid.UUID(item["forkos_id"])
    assert item["forkos_type"] == "note"
    assert item["note_kind"] == "personal"
    assert item["relative_path"] == "00 Inbox/İlk hızlı not.md"
    assert item["relation_count"] == 0

    metadata, body = parse_frontmatter(
        (vault / item["relative_path"]).read_text(encoding="utf-8")
    )
    assert metadata is not None
    assert metadata["forkos_id"] == item["forkos_id"]
    assert metadata["forkos_type"] == "note"
    assert metadata["forkos_note_kind"] == "personal"
    assert metadata["forkos_captured_from"] == "forkOS"
    assert metadata["forkos_created_at"] and metadata["forkos_updated_at"]
    assert "İlk hızlı not" in body

    # ForkOS tarafı DEĞİŞMEDİ: yeni entity, not ya da bağ satırı yok.
    assert await table_counts() == {
        "note": 0,
        "note_folder": 0,
        "note_attachment": 0,
        "link": 0,
    }
    async with SessionLocal() as session:
        assert int(
            (await session.execute(select(func.count()).select_from(Entity))).scalar_one()
        ) == before_entities


async def test_capture_resolves_relation_target_server_side(
    client: AsyncClient, vault: Path
) -> None:
    entity_id = await make_entity("opportunity", "Backend Engineer")

    response = await client.post(
        "/api/obsidian/capture",
        json={"body": "Görüşme notu", "relate_to": str(entity_id)},
    )
    assert response.status_code == 201, response.text
    item = response.json()

    metadata, _ = parse_frontmatter((vault / item["relative_path"]).read_text(encoding="utf-8"))
    assert metadata is not None
    # Tip ve başlık İSTEMCİDEN değil, `entity` tablosundan çözülür.
    assert metadata["forkos_relations"] == [
        {
            "relation": "notes_about",
            "target_id": str(entity_id),
            "target_type": "opportunity",
            "target_title": "Backend Engineer",
        }
    ]
    assert item["relation_count"] == 1
    # İlişki DB'ye `link` satırı olarak YAZILMAZ.
    assert (await table_counts())["link"] == 0


async def test_capture_rejects_unknown_relation_target(client: AsyncClient, vault: Path) -> None:
    response = await client.post(
        "/api/obsidian/capture",
        json={"body": "Yetim not", "relate_to": str(uuid.uuid4())},
    )
    assert response.status_code == 400
    assert not list(vault.rglob("*.md"))


@pytest.mark.parametrize(
    ("body", "expected_stem"),
    [
        ("# Başlıklı not\n\ngövde", "Başlıklı not"),
        ('Soru: "ne" / zaman?', "Soru- -ne- - zaman"),
        ("> alıntı satırı", "alıntı satırı"),
    ],
)
async def test_capture_derives_safe_title_from_body(
    client: AsyncClient, vault: Path, body: str, expected_stem: str
) -> None:
    response = await client.post("/api/obsidian/capture", json={"body": body})
    assert response.status_code == 201, response.text
    relative_path = response.json()["relative_path"]
    assert relative_path == f"00 Inbox/{expected_stem}.md"
    # Dosya gerçekten Vault kökünün ALTINDA.
    assert (vault / relative_path).resolve().is_relative_to(vault.resolve())


async def test_capture_collision_uses_deterministic_suffix_and_never_overwrites(
    client: AsyncClient, vault: Path
) -> None:
    first = await client.post("/api/obsidian/capture", json={"body": "Aynı başlık"})
    second = await client.post("/api/obsidian/capture", json={"body": "Aynı başlık"})
    assert first.status_code == second.status_code == 201

    first_item, second_item = first.json(), second.json()
    assert first_item["relative_path"] == "00 Inbox/Aynı başlık.md"
    expected_suffix = uuid.UUID(second_item["forkos_id"]).hex[:8]
    assert second_item["relative_path"] == f"00 Inbox/Aynı başlık--{expected_suffix}.md"
    # İki ayrı dosya; hiçbiri diğerinin üzerine yazılmadı.
    assert len(list((vault / "00 Inbox").glob("*.md"))) == 2
    assert uuid.UUID(first_item["forkos_id"]) != uuid.UUID(second_item["forkos_id"])


async def test_capture_preserves_unmanaged_user_file(client: AsyncClient, vault: Path) -> None:
    """Vault'taki kullanıcı dosyası ASLA ezilmez."""
    inbox = vault / "00 Inbox"
    inbox.mkdir(parents=True)
    user_file = inbox / "Kullanıcı notu.md"
    user_file.write_text("Elle yazılmış, frontmatter'sız içerik", encoding="utf-8")

    response = await client.post("/api/obsidian/capture", json={"body": "Kullanıcı notu"})
    assert response.status_code == 201
    assert response.json()["relative_path"] != "00 Inbox/Kullanıcı notu.md"
    assert user_file.read_text(encoding="utf-8") == "Elle yazılmış, frontmatter'sız içerik"


# ---------------------------------------------------------------------
# 2. Kanonik bilgi notları (ensure)
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("entity_type", "title", "forkos_type", "expected_path"),
    [
        ("study_topic", "ASP.NET Core", "learning", "40 Learning/ASP.NET Core.md"),
        ("opportunity", "Backend Engineer", "note", "00 Inbox/Backend Engineer.md"),
        ("project", "forkOS", "project", "20 Projects/forkOS/forkOS.md"),
    ],
)
async def test_ensure_creates_canonical_note_per_entity_type(
    client: AsyncClient,
    vault: Path,
    entity_type: str,
    title: str,
    forkos_type: str,
    expected_path: str,
) -> None:
    entity_id = await make_entity(entity_type, title)

    response = await client.post("/api/obsidian/ensure", json={"forkos_id": str(entity_id)})
    assert response.status_code == 200, response.text
    item = response.json()

    assert item["forkos_id"] == str(entity_id)
    assert item["forkos_type"] == forkos_type
    assert item["entity_type"] == entity_type
    assert item["relative_path"] == expected_path

    metadata, _ = parse_frontmatter((vault / item["relative_path"]).read_text(encoding="utf-8"))
    assert metadata is not None
    assert metadata["forkos_id"] == str(entity_id)
    assert metadata["forkos_type"] == forkos_type
    assert metadata["forkos_entity_type"] == entity_type
    # `note` tipi "kayıt hakkında"dır: ilişki metadata'sı yazılır.
    if forkos_type == "note":
        assert metadata["forkos_relations"][0]["target_id"] == str(entity_id)
    else:
        assert "forkos_relations" not in metadata

    assert await table_counts() == {
        "note": 0,
        "note_folder": 0,
        "note_attachment": 0,
        "link": 0,
    }


async def test_ensure_is_idempotent_for_same_entity(client: AsyncClient, vault: Path) -> None:
    entity_id = await make_entity("study_topic", "Kubernetes")

    first = await client.post("/api/obsidian/ensure", json={"forkos_id": str(entity_id)})
    second = await client.post("/api/obsidian/ensure", json={"forkos_id": str(entity_id)})

    assert first.json()["forkos_id"] == second.json()["forkos_id"]
    assert len(list((vault / "40 Learning").glob("*.md"))) == 1


async def test_ensure_rejects_unknown_entity_and_unsupported_type(
    client: AsyncClient, vault: Path
) -> None:
    unknown = await client.post("/api/obsidian/ensure", json={"forkos_id": str(uuid.uuid4())})
    assert unknown.status_code == 400

    todo_id = await make_entity("todo", "Kapsam dışı kayıt")
    unsupported = await client.post("/api/obsidian/ensure", json={"forkos_id": str(todo_id)})
    assert unsupported.status_code == 400
    assert not list(vault.rglob("*.md"))


async def test_bookmark_source_note_carries_source_metadata_and_highlights(
    client: AsyncClient, vault: Path
) -> None:
    capture = await client.post(
        "/api/capture",
        json={"url": "https://example.com/makale", "title": "Örnek makale", "collection": "inbox"},
    )
    assert capture.status_code == 201, capture.text
    bookmark_id = capture.json()["id"]

    response = await client.post(
        f"/api/bookmarks/{bookmark_id}/source-note", json={"additional_text": "Kendi ekim"}
    )
    assert response.status_code == 201, response.text
    item = response.json()

    assert item["forkos_id"] == bookmark_id
    assert item["forkos_type"] == "source"
    assert item["relative_path"] == "60 Sources/Örnek makale.md"
    assert item["source_bookmark_id"] == bookmark_id

    metadata, body = parse_frontmatter((vault / item["relative_path"]).read_text(encoding="utf-8"))
    assert metadata is not None
    assert metadata["forkos_source_bookmark_id"] == bookmark_id
    assert metadata["source"] == "https://example.com/makale"
    assert metadata["source_title"] == "Örnek makale"
    # §36: makale gövdesi KOPYALANMAZ; yalnız şablon + kullanıcı katkısı.
    assert "Kendi ekim" in body
    assert "## Öne çıkanlar" in body

    # Yer iminin kendi operasyonel alanları korunur.
    detail = (await client.get(f"/api/bookmarks/{bookmark_id}")).json()
    assert detail["url"] == "https://example.com/makale"
    assert await table_counts() == {
        "note": 0,
        "note_folder": 0,
        "note_attachment": 0,
        "link": 0,
    }

    # İkinci çağrı aynı dosyayı çözer.
    again = await client.post(f"/api/bookmarks/{bookmark_id}/source-note", json={})
    assert again.json()["forkos_id"] == item["forkos_id"]
    assert len(list((vault / "60 Sources").glob("*.md"))) == 1


async def test_resolve_follows_file_after_user_moves_it(client: AsyncClient, vault: Path) -> None:
    entity_id = await make_entity("study_topic", "Taşınan konu")
    created = await client.post("/api/obsidian/ensure", json={"forkos_id": str(entity_id)})
    original = vault / created.json()["relative_path"]

    moved = vault / "40 Learning/Alt klasör/Taşınan konu.md"
    moved.parent.mkdir(parents=True)
    original.rename(moved)

    resolved = await client.get(f"/api/obsidian/items/{entity_id}")
    assert resolved.status_code == 200
    assert resolved.json()["relative_path"] == "40 Learning/Alt klasör/Taşınan konu.md"


# ---------------------------------------------------------------------
# 3. Fail-closed davranışı
# ---------------------------------------------------------------------


async def test_capture_fails_closed_when_vault_is_unconfigured(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "obsidian_vault_path", "")
    response = await client.post("/api/obsidian/capture", json={"body": "Yazılamamalı"})
    assert response.status_code == 503
    assert await table_counts() == {
        "note": 0,
        "note_folder": 0,
        "note_attachment": 0,
        "link": 0,
    }


async def test_capture_fails_closed_when_vault_directory_is_missing(
    client: AsyncClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "obsidian_vault_path", str(tmp_path / "yok"))
    response = await client.post("/api/obsidian/capture", json={"body": "Yazılamamalı"})
    assert response.status_code == 503


async def test_capture_fails_closed_on_read_only_vault(client: AsyncClient, vault: Path) -> None:
    os.chmod(vault, 0o500)
    try:
        if os.access(vault, os.W_OK):  # root/ACL ortamlarında kural uygulanamaz
            pytest.skip("yazma izni düşürülemedi")
        response = await client.post("/api/obsidian/capture", json={"body": "Yazılamamalı"})
        assert response.status_code == 403
    finally:
        os.chmod(vault, 0o700)


async def test_duplicate_managed_id_fails_closed(client: AsyncClient, vault: Path) -> None:
    entity_id = await make_entity("study_topic", "Çakışan konu")
    target = vault / "40 Learning"
    target.mkdir(parents=True)
    for name in ("Bir.md", "İki.md"):
        (target / name).write_text(
            f"---\nforkos_id: {entity_id}\nforkos_type: learning\ntitle: Çakışma\n---\n\ngövde\n",
            encoding="utf-8",
        )

    assert (await client.get(f"/api/obsidian/items/{entity_id}")).status_code == 409
    assert (
        await client.post("/api/obsidian/ensure", json={"forkos_id": str(entity_id)})
    ).status_code == 409
    assert len(list(target.glob("*.md"))) == 2


async def test_ensure_requires_an_existing_record(client: AsyncClient, vault: Path) -> None:
    """Kaydı olmayan kimlik için not ÜRETİLMEZ (fail-closed)."""
    response = await client.post("/api/obsidian/ensure", json={"forkos_id": str(uuid.uuid4())})
    assert response.status_code == 400
    assert not list(vault.rglob("*.md"))


# ---------------------------------------------------------------------
# 4. Gövde okuma/güncelleme sözleşmesi
# ---------------------------------------------------------------------


async def test_update_body_preserves_user_frontmatter_and_rejects_stale_write(
    client: AsyncClient, vault: Path
) -> None:
    captured = await client.post("/api/obsidian/capture", json={"body": "İlk gövde"})
    item = captured.json()
    file_path = vault / item["relative_path"]

    # Kullanıcı Obsidian'da kendi alanını ekledi.
    raw = file_path.read_text(encoding="utf-8")
    file_path.write_text(
        raw.replace("forkos_type: note", "forkos_type: note\nkullanici_alani: korunmali"),
        encoding="utf-8",
    )

    async with SessionLocal() as session:
        fresh = await _reload_item(session, item["forkos_id"])

    updated = update_managed_note_body(item["forkos_id"], "Yeni gövde", expected_mtime=fresh.mtime)
    assert updated.forkos_id == item["forkos_id"]

    metadata, body = parse_frontmatter(file_path.read_text(encoding="utf-8"))
    assert metadata is not None
    assert metadata["kullanici_alani"] == "korunmali"
    assert metadata["forkos_id"] == item["forkos_id"]
    assert metadata["forkos_created_at"] == parse_frontmatter(
        raw
    )[0]["forkos_created_at"]
    assert "Yeni gövde" in body

    # Bayat yazma reddedilir: gövde DEĞİŞMEZ.
    with pytest.raises(VaultStaleWriteError):
        update_managed_note_body(item["forkos_id"], "Ezilmemeli", expected_mtime=fresh.mtime)
    assert "Yeni gövde" in file_path.read_text(encoding="utf-8")


async def test_read_body_returns_markdown_without_frontmatter(
    client: AsyncClient, vault: Path
) -> None:
    captured = await client.post("/api/obsidian/capture", json={"body": "Okunacak gövde"})
    forkos_id = captured.json()["forkos_id"]

    read = read_managed_note_body(forkos_id)
    assert read is not None
    item, body = read
    assert item.forkos_id == forkos_id
    assert "Okunacak gövde" in body
    assert "forkos_id" not in body


async def _reload_item(session, forkos_id: str):
    """İndeksi dosya sisteminden tazeler ve kaydı döner."""
    from app.integrations.obsidian.service import refresh_vault_index, resolve_managed_item

    refresh_vault_index()
    item = resolve_managed_item(forkos_id)
    assert item is not None
    return item
